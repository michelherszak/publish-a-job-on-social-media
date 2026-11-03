"""Stripe Checkout integration. All entitlements come from signed server events.

Uses Stripe's versioned REST API; no card data or Stripe secret is sent to the UI.
"""
from __future__ import annotations
import calendar
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import ssl
import certifi
from . import invoice_mail
import re
import sqlite3
import time
from urllib.parse import urlencode, quote, urlparse
from urllib.request import Request as URLRequest, urlopen
from urllib.error import HTTPError, URLError

from fastapi import Depends, Header, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator

API_VERSION = "2026-08-26.dahlia"
EU = {"AT":"Österreich", "BE":"Belgien", "BG":"Bulgarien", "HR":"Kroatien", "CY":"Zypern", "CZ":"Tschechien", "DK":"Dänemark", "EE":"Estland", "FI":"Finnland", "FR":"Frankreich", "DE":"Deutschland", "GR":"Griechenland", "HU":"Ungarn", "IE":"Irland", "IT":"Italien", "LV":"Lettland", "LT":"Litauen", "LU":"Luxemburg", "MT":"Malta", "NL":"Niederlande", "PL":"Polen", "PT":"Portugal", "RO":"Rumänien", "SK":"Slowakei", "SI":"Slowenien", "ES":"Spanien", "SE":"Schweden"}
with (Path(__file__).resolve().parents[1] / "pricing_catalog.json").open() as catalog_file:
    CATALOG = json.load(catalog_file)


def schema(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS billing_accounts (
      organization_id INTEGER PRIMARY KEY REFERENCES organizations(id),
      customer TEXT UNIQUE, subscription TEXT UNIQUE, plan TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'pending', country TEXT NOT NULL, mode TEXT NOT NULL DEFAULT 'test',
      included INTEGER NOT NULL DEFAULT 0 CHECK(included>=0),
      purchased INTEGER NOT NULL DEFAULT 0 CHECK(purchased>=0),
      period_start INTEGER NOT NULL DEFAULT 0, period_end INTEGER NOT NULL DEFAULT 0,
      credit_period_start INTEGER NOT NULL DEFAULT 0,
      hold TEXT NOT NULL DEFAULT '', cancel_at_period_end INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS billing_orders (
      id TEXT PRIMARY KEY, organization_id INTEGER NOT NULL REFERENCES organizations(id),
      sku TEXT NOT NULL, customer TEXT, price TEXT, checkout TEXT UNIQUE, url TEXT,
      status TEXT NOT NULL DEFAULT 'creating', created_at INTEGER NOT NULL,
      expires_at INTEGER NOT NULL, country TEXT NOT NULL,
      pdf_consent INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS billing_events (id TEXT PRIMARY KEY, type TEXT NOT NULL, processed_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS token_ledger (
      id INTEGER PRIMARY KEY, organization_id INTEGER NOT NULL REFERENCES organizations(id),
      reference TEXT NOT NULL UNIQUE, included_delta INTEGER NOT NULL DEFAULT 0,
      purchased_delta INTEGER NOT NULL DEFAULT 0, description TEXT NOT NULL, created_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS signup_limits (key TEXT PRIMARY KEY, attempts INTEGER NOT NULL, resets_at INTEGER NOT NULL);
    """)
    invoice_mail.schema(conn)
    if "pdf_consent" not in {row["name"] for row in conn.execute("PRAGMA table_info(billing_orders)")}:
        conn.execute("ALTER TABLE billing_orders ADD COLUMN pdf_consent INTEGER NOT NULL DEFAULT 0")
    if "mode" not in {row["name"] for row in conn.execute("PRAGMA table_info(billing_accounts)")}:
        conn.execute("ALTER TABLE billing_accounts ADD COLUMN mode TEXT NOT NULL DEFAULT 'test'")
    if "credit_period_start" not in {row["name"] for row in conn.execute("PRAGMA table_info(billing_accounts)")}:
        conn.execute("ALTER TABLE billing_accounts ADD COLUMN credit_period_start INTEGER NOT NULL DEFAULT 0")


def configuration():
    key = os.getenv("STRIPE_SECRET_KEY", "")
    mode = "live" if key.startswith("sk_live_") else "test"
    missing = []
    if not key.startswith(("sk_test_", "sk_live_")): missing.append("STRIPE_SECRET_KEY")
    if not os.getenv("STRIPE_WEBHOOK_SECRET", "").startswith("whsec_"): missing.append("STRIPE_WEBHOOK_SECRET")
    for sku in CATALOG:
        if not os.getenv("STRIPE_PRICE_" + sku.upper(), "").startswith("price_"): missing.append("STRIPE_PRICE_" + sku.upper())
    site = os.getenv("MH_PUBLIC_URL", "http://127.0.0.1:5181").rstrip("/")
    url = urlparse(site)
    if url.scheme not in {"http", "https"} or not url.netloc or url.username or url.password or url.path or url.query or url.fragment: missing.append("MH_PUBLIC_URL")
    if mode == "live":
        if os.getenv("MH_ENV") != "production": missing.append("MH_ENV=production")
        if url.scheme != "https" or url.hostname in {"localhost", "127.0.0.1", "::1"}: missing.append("MH_PUBLIC_URL_HTTPS")
        for flag in ("MH_STRIPE_LIVE_ENABLED", "MH_EU_RADAR_CONFIRMED", "MH_STRIPE_TAX_READY", "MH_PAID_PRODUCT_READY"):
            if os.getenv(flag) != "1": missing.append(flag)
        if os.getenv("MH_DEMO_SWITCHER", "1") != "0": missing.append("MH_DEMO_SWITCHER=0")
        if os.getenv("MH_INVOICE_READY") != "1": missing.append("MH_INVOICE_READY")
    return {"ready":not missing, "mode":mode, "missing":missing, "site":site}


def require_config():
    config = configuration()
    if not config["ready"]: raise HTTPException(503, "Zahlungen sind noch nicht eingerichtet. Bitte später erneut versuchen.")
    return config


def form_fields(value, prefix=""):
    fields = []
    if isinstance(value, dict):
        for key, child in value.items(): fields.extend(form_fields(child, f"{prefix}[{key}]" if prefix else key))
    elif isinstance(value, list):
        for index, child in enumerate(value): fields.extend(form_fields(child, f"{prefix}[{index}]"))
    elif value is not None: fields.append((prefix, str(value).lower() if isinstance(value, bool) else str(value)))
    return fields


def stripe_call(method, path, data=None, key=None, missing_ok=False):
    headers = {"Authorization":"Bearer " + os.getenv("STRIPE_SECRET_KEY", ""), "Stripe-Version":API_VERSION}
    if key: headers["Idempotency-Key"] = key
    encoded = urlencode(form_fields(data or {})).encode()
    url = "https://api.stripe.com/v1/" + path
    if method == "GET" and encoded: url += "?" + encoded.decode()
    if method != "GET": headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = URLRequest(url, data=encoded if method != "GET" else None, headers=headers, method=method)
    try:
        context = ssl.create_default_context()
        context.load_verify_locations(cafile=certifi.where())
        with urlopen(request, timeout=20, context=context) as response: return json.load(response)
    except HTTPError as error:
        error.close()
        if missing_ok and error.code == 404:
            return None
        # Never return provider responses that can contain keys, PII or request internals.
        raise HTTPException(502, "Stripe ist momentan nicht erreichbar oder die Konfiguration ist ungültig. Bitte erneut versuchen.")
    except (URLError, TimeoutError, ValueError):
        raise HTTPException(502, "Stripe ist momentan nicht erreichbar oder die Konfiguration ist ungültig. Bitte erneut versuchen.")


def object_id(value):
    return value.get("id") if isinstance(value, dict) else value


def remote(kind, ident):
    return stripe_call("GET", f"{kind}/{quote(str(ident), safe='')}")


def admin(user):
    if user.get("view_role") or user.get("base_role") != "firmen_admin" or user.get("role") != "firmen_admin" or not user.get("organization_id"):
        raise HTTPException(403, "Nur der echte Firmen-Admin kann Zahlungen verwalten; nicht in der Demo-Vorschau.")
    return user["organization_id"]


def account(conn, org):
    row = conn.execute("SELECT * FROM billing_accounts WHERE organization_id=?", (org,)).fetchone()
    return dict(row) if row else None


def usable(a):
    return a and a.get("mode", "test") == configuration()["mode"] and not a["hold"] and a["status"] == "active" and a["period_end"] > int(time.time())


def ledger(conn, org, reference, included, purchased, description):
    conn.execute("INSERT INTO token_ledger(organization_id,reference,included_delta,purchased_delta,description,created_at) VALUES(?,?,?,?,?,?)", (org, reference, included, purchased, description, int(time.time())))

def month_anniversary(anchor, months):
    """UTC calendar anniversary, clamping days such as January 31 to February 28."""
    start = datetime.fromtimestamp(anchor, timezone.utc)
    total = start.year * 12 + start.month - 1 + months
    year, month_index = divmod(total, 12)
    month = month_index + 1
    return int(start.replace(year=year, month=month,
                             day=min(start.day, calendar.monthrange(year, month)[1])).timestamp())


def credit_window(a, now=None):
    """Return the current included-credit window for a paid subscription."""
    item = CATALOG.get(a["plan"]) if a else None
    if not item or not a["period_start"] or not a["period_end"]:
        return (0, 0)
    if item.get("interval") != "year":
        return (a["period_start"], a["period_end"])
    now = int(time.time()) if now is None else now
    for month in range(12):
        start = month_anniversary(a["period_start"], month)
        end = min(month_anniversary(a["period_start"], month + 1), a["period_end"])
        if start <= now < end:
            return (start, end)
    return (0, a["period_end"])


def reconcile_included(conn, a, now=None):
    """Renew prepaid annual credits lazily, once per calendar anniversary."""
    if not a or CATALOG.get(a["plan"], {}).get("interval") != "year" or not usable(a):
        return a
    now = int(time.time()) if now is None else now
    start, _ = credit_window(a, now)
    if not start or start <= a["credit_period_start"]:
        return a
    reference = f"annual-credit:{a['subscription']}:{start}"
    if conn.execute("SELECT 1 FROM token_ledger WHERE reference=?", (reference,)).fetchone():
        return a
    amount = CATALOG[a["plan"]]["tokens"]
    conn.execute("UPDATE billing_accounts SET included=?,credit_period_start=? WHERE organization_id=?",
                 (amount, start, a["organization_id"]))
    ledger(conn, a["organization_id"], reference, amount-a["included"], 0,
           CATALOG[a["plan"]]["name"]+" Monatsguthaben (Rest des Vormonats verfällt)")
    return account(conn, a["organization_id"])


def debit_generation(conn, org, request_key, project_id):
    """Called within the generation transaction. Legacy demo accounts remain free."""
    a = reconcile_included(conn, account(conn, org))
    if not a: return True
    if not request_key or not re.fullmatch(r"[a-zA-Z0-9_-]{16,100}", request_key): raise HTTPException(400, "Eine eindeutige Anfrage-ID ist erforderlich.")
    reference = f"generation:{org}:{request_key}"
    previous = conn.execute("SELECT description FROM token_ledger WHERE reference=?", (reference,)).fetchone()
    description = f"Kampagnenentwurf #{project_id} · 50 Tokens"
    if previous:
        if previous[0] != description: raise HTTPException(409, "Anfrage-ID wurde bereits für eine andere Kampagne verwendet.")
        return False
    if not usable(a): raise HTTPException(402, "Für neue Entwürfe ist ein bezahltes, aktives Abo erforderlich. Bitte Abrechnung öffnen.")
    included = a["included"] if a["period_end"] > int(time.time()) else 0
    if included + a["purchased"] < 50: raise HTTPException(402, "Nicht genügend Tokens. Ein Kampagnenentwurf kostet 50 Tokens.")
    use_included = min(50, included)
    conn.execute("UPDATE billing_accounts SET included=included-?,purchased=purchased-? WHERE organization_id=?", (use_included, 50-use_included, org))
    ledger(conn, org, reference, -use_included, -(50-use_included), description)
    return True


def enforce_seats(conn, org, role):
    a = account(conn, org)
    if not a or role == "kunde": return
    if not usable(a): raise HTTPException(402, "Ein aktives Abo ist erforderlich, um weitere Bearbeiter hinzuzufügen.")
    seats = CATALOG.get(a["plan"], {}).get("seats", 0)
    count = conn.execute("SELECT COUNT(*) FROM users WHERE organization_id=? AND role IN ('firmen_admin','user')", (org,)).fetchone()[0]
    if count >= seats: raise HTTPException(409, "Die Nutzerplätze des Tarifs sind ausgeschöpft.")


class Registration(BaseModel):
    company: str = Field(min_length=2,max_length=160)
    name: str = Field(min_length=2,max_length=160)
    email: str = Field(min_length=5,max_length=254)
    password: str = Field(min_length=15,max_length=128)
    country: str
    business: bool
    @field_validator("email")
    @classmethod
    def email_valid(cls, value):
        value=value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",value): raise ValueError("Ungültige E-Mail-Adresse")
        return value
    @field_validator("country")
    @classmethod
    def country_valid(cls,value):
        if value not in EU: raise ValueError("Nur Unternehmen in der EU werden unterstützt.")
        return value


class Checkout(BaseModel):
    onboarding: bool = False
    sku: str
    country: str
    business: bool
    pdf_consent: bool = False
    request_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{16,100}$")


def validate_price(price, item):
    recurring = price.get("recurring")
    ok = price.get("active") and price.get("currency") == "eur" and price.get("unit_amount") == item["cents"] and price.get("tax_behavior") == "exclusive"
    if item["kind"] == "subscription": ok = ok and recurring and recurring.get("interval") == item["interval"] and recurring.get("interval_count") == 1
    else: ok = ok and not recurring
    if not ok: raise HTTPException(503, "Der Stripe-Preis stimmt nicht mit dem MH-Tarif überein. Bitte den Betreiber kontaktieren.")


def verify_signature(payload, signature):
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not secret: raise HTTPException(503, "Webhook nicht konfiguriert")
    try:
        parts = [part.split("=",1) for part in (signature or "").split(",")]
        timestamp = next(value for key,value in parts if key == "t")
        if abs(time.time()-int(timestamp)) > 300: raise ValueError()
        digest = hmac.new(secret.encode(), timestamp.encode()+b"."+payload, hashlib.sha256).hexdigest()
        if not any(key == "v1" and hmac.compare_digest(digest,value) for key,value in parts): raise ValueError()
        event = json.loads(payload)
        if not isinstance(event,dict) or not isinstance(event.get("id"),str) or not isinstance(event.get("data",{}).get("object"),dict): raise ValueError()
        if bool(event.get("livemode")) != (configuration()["mode"] == "live"): raise ValueError()
        return event
    except (ValueError, StopIteration, TypeError, KeyError): raise HTTPException(400, "Ungültige Webhook-Signatur oder Umgebung")


def hold(conn, org, reason):
    conn.execute("UPDATE billing_accounts SET hold=? WHERE organization_id=?", (reason,org))


def sync_subscription(conn, a, subscription):
    # Fetch current Stripe state instead of trusting event delivery order.
    sub = remote("subscriptions",subscription)
    if object_id(sub.get("customer")) != a["customer"]: raise HTTPException(409, "Abonnement gehört nicht zum Kunden")
    order = conn.execute("SELECT * FROM billing_orders WHERE organization_id=? AND id=?", (a["organization_id"],sub.get("metadata",{}).get("order_id"))).fetchone()
    if not order: raise HTTPException(409, "Unbekanntes Abonnement")
    if a["subscription"] and a["subscription"] != subscription:
        old = remote("subscriptions",a["subscription"])
        if sub.get("status") in {"canceled","incomplete_expired"} or old.get("status") not in {"canceled","incomplete_expired"}:
            return None  # a delayed old event must not overwrite the current subscription
    items = sub.get("items",{}).get("data",[])
    if len(items)!=1 or object_id(items[0].get("price"))!=order["price"] or items[0].get("quantity")!=1:
        hold(conn,a["organization_id"],"Tarifänderung muss geprüft werden")
        return None
    conn.execute("UPDATE billing_accounts SET subscription=?,plan=?,status=?,cancel_at_period_end=? WHERE organization_id=?", (subscription,order["sku"],sub["status"],int(bool(sub.get("cancel_at_period_end"))),a["organization_id"]))
    return sub


def process_event(conn, event):
    typ = event["type"]; obj = event["data"]["object"]
    customer = object_id(obj.get("customer"))
    if typ.startswith("charge.dispute."):
        charge = remote("charges",object_id(obj.get("charge")))
        customer = object_id(charge.get("customer"))
    row = conn.execute("SELECT * FROM billing_accounts WHERE customer=?", (customer,)).fetchone() if customer else None
    if not row: return  # unrelated Stripe products/accounts
    a = dict(row); org = a["organization_id"]
    if a["mode"] != configuration()["mode"]: raise HTTPException(409,"Billing-Umgebung stimmt nicht überein")
    if typ in {"charge.refunded","charge.dispute.created"}:
        hold(conn,org,"Erstattung oder Zahlungsstreit: Abrechnung wird geprüft")
        return
    if typ == "customer.updated":
        current = remote("customers",customer)
        if (current.get("address") or {}).get("country") not in EU: hold(conn,org,"Rechnungsadresse außerhalb der EU")
        return
    if typ.startswith("customer.subscription."):
        sync_subscription(conn,a,obj["id"])
        return
    if typ in {"checkout.session.completed","checkout.session.async_payment_succeeded"}:
        order = conn.execute("SELECT * FROM billing_orders WHERE id=? AND organization_id=?", (obj.get("metadata",{}).get("order_id"),org)).fetchone()
        if not order: return
        if order["checkout"] != obj["id"]: raise HTTPException(409,"Checkout-Zuordnung fehlt; erneut zustellen")
        item = CATALOG[order["sku"]]
        # Signature establishes authenticity; retrieve session to handle delayed events.
        session = remote("checkout/sessions",obj["id"])
        if object_id(session.get("customer"))!=customer or session.get("mode")!=item["kind"]: raise HTTPException(409,"Checkout stimmt nicht überein")
        country = ((session.get("customer_details") or {}).get("address") or {}).get("country")
        if country not in EU:
            hold(conn,org,"Zahlung mit Rechnungsadresse außerhalb der EU: Erstattung prüfen")
            conn.execute("UPDATE billing_orders SET status='review' WHERE id=?",(order["id"],))
            return
        if session.get("payment_status")!="paid": return
        if session.get("currency")!="eur" or session.get("amount_subtotal")!=item["cents"]:
            hold(conn,org,"Zahlungsbetrag stimmt nicht mit dem Tarif überein")
            return
        if item["kind"] == "subscription":
            sync_subscription(conn,a,object_id(session.get("subscription")))
            # Monthly tokens are granted ONLY by invoice.paid, not twice by Checkout.
        else:
            invoice_id = object_id(session.get("invoice"))
            invoice = remote("invoices", invoice_id) if invoice_id else None
            if not invoice or invoice.get("status") != "paid" or object_id(invoice.get("customer")) != customer:
                raise HTTPException(409, "Bezahlte Stripe-Rechnung fehlt; Ereignis erneut zustellen.")
            if invoice.get("currency") != "eur" or invoice.get("subtotal") != item["cents"]:
                hold(conn,org,"Rechnungsbetrag muss geprüft werden")
                return
            invoice_mail.queue(conn,org,customer,invoice_id,session["id"])
            reference = "checkout:"+session["id"]
            if not conn.execute("SELECT 1 FROM token_ledger WHERE reference=?",(reference,)).fetchone():
                conn.execute("UPDATE billing_accounts SET purchased=purchased+? WHERE organization_id=?",(item["tokens"],org))
                ledger(conn,org,reference,0,item["tokens"],item["name"]+" gekauft")
        conn.execute("UPDATE billing_orders SET status='paid' WHERE id=?",(order["id"],))
        return
    if typ in {"invoice.paid","invoice.payment_failed"}:
        invoice = remote("invoices",obj["id"])
        sub_id = object_id((invoice.get("parent") or {}).get("subscription_details",{}).get("subscription") or invoice.get("subscription"))
        if not sub_id: return
        sub = sync_subscription(conn,a,sub_id)
        if not sub: return
        if typ != "invoice.paid" or invoice.get("status")!="paid" or invoice.get("paid_out_of_band"): return
        if invoice.get("billing_reason") not in {"subscription_create","subscription_cycle"}: return
        country = (invoice.get("customer_address") or {}).get("country")
        if country not in EU:
            hold(conn,org,"Rechnungsadresse außerhalb der EU: Erstattung prüfen")
            return
        a = account(conn,org)
        if a["hold"]: return
        item = CATALOG[a["plan"]]
        if invoice.get("currency") != "eur" or invoice.get("subtotal") != item["cents"]:
            hold(conn,org,"Rechnungsbetrag muss geprüft werden")
            return
        lines = invoice.get("lines",{}).get("data",[])
        if len(lines)!=1 or lines[0].get("quantity")!=1: raise HTTPException(409,"Unerwartete Rechnungspositionen")
        line = lines[0]
        price = object_id((line.get("pricing") or {}).get("price_details",{}).get("price") or line.get("price"))
        order = conn.execute("SELECT * FROM billing_orders WHERE id=?",(sub.get("metadata",{}).get("order_id"),)).fetchone()
        if price!=order["price"]: raise HTTPException(409,"Unbekannter Rechnungspreis")
        start,end = line["period"]["start"],line["period"]["end"]
        reference = "invoice:"+invoice["id"]
        if conn.execute("SELECT 1 FROM token_ledger WHERE reference=?",(reference,)).fetchone(): return
        # Late older invoices cannot replace current credits; repeated invoices in one period cannot refill them.
        if start <= a["period_start"]: return
        grant = item["tokens"] if end > int(time.time()) else 0
        delta = grant-a["included"]
        conn.execute("UPDATE billing_accounts SET included=?,period_start=?,period_end=?,credit_period_start=?,country=? WHERE organization_id=?",(grant,start,end,start,country,org))
        ledger(conn,org,reference,delta,0,item["name"]+" Monatsguthaben (Rest des Vormonats verfällt)")
        invoice_mail.queue(conn,org,customer,invoice["id"],invoice["id"])


def install(app, db, current_user, password_hash):
    @app.get("/billing/config")
    def config():
        value = configuration()
        return {"ready":value["ready"], "mode":value["mode"], "countries":EU, "catalog":CATALOG, "message":"" if value["ready"] else "Kreditkartenzahlung wird eingerichtet. Momentan ist noch keine Buchung möglich."}

    @app.post("/auth/register",status_code=201)
    def register(body: Registration, request: Request, response: Response):
        from . import auth
        if not body.business: raise HTTPException(422,"Das Angebot richtet sich an Unternehmen in der EU.")
        if len(body.company.strip())<2 or len(body.name.strip())<2: raise HTTPException(422,"Name und Firma sind erforderlich")
        client = hashlib.sha256((request.client.host if request.client else "unknown").encode()).hexdigest()
        now = int(time.time())
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM signup_limits WHERE key=?",(client,)).fetchone()
            if row and row["resets_at"]>now and row["attempts"]>=5: raise HTTPException(429,"Zu viele Registrierungen. Bitte später erneut versuchen.")
            if not row or row["resets_at"]<=now: conn.execute("INSERT OR REPLACE INTO signup_limits VALUES(?,1,?)",(client,now+3600))
            else: conn.execute("UPDATE signup_limits SET attempts=attempts+1 WHERE key=?",(client,))
        with db() as conn:
            try:
                org=conn.execute("INSERT INTO organizations(name) VALUES(?)",(body.company.strip(),)).lastrowid
                uid=conn.execute("INSERT INTO users(email,name,password_hash,role,organization_id,email_verified,security_required) VALUES(?,?,?,'firmen_admin',?,0,1)",(body.email,body.name.strip(),password_hash(body.password),org)).lastrowid
                conn.execute("INSERT INTO billing_accounts(organization_id,country,mode) VALUES(?,?,?)",(org,body.country,configuration()["mode"]))
                language=auth.mail_templates.request_language(request)
                conn.execute("UPDATE users SET email_language=? WHERE id=?", (language,uid))
                token=auth.issue_link(conn,uid,"verify",60)
            except sqlite3.IntegrityError: raise HTTPException(409,"Firma oder E-Mail ist bereits registriert. Bitte anmelden.")
        auth.send_mail(body.email,"MH: E-Mail bestätigen","verify",token,language)
        auth.session(db,request,response,uid)
        return {"ok":True,"local_mail":not auth.production() and os.getenv("MH_MAIL_MODE","local")=="local"}

    @app.get("/billing/status")
    def status(user=Depends(current_user)):
        org=admin(user)
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            a=reconcile_included(conn,account(conn,org))
            entries=[dict(row) for row in conn.execute("SELECT included_delta,purchased_delta,description,created_at FROM token_ledger WHERE organization_id=? ORDER BY id DESC LIMIT 30",(org,))]
            pending=conn.execute("SELECT sku,status,url,expires_at FROM billing_orders WHERE organization_id=? AND status IN ('creating','open') ORDER BY created_at DESC LIMIT 1",(org,)).fetchone()
        if not a: return {"managed":False,"status":"demo","included":0,"purchased":0,"active":False,"ledger":[],"plan":"","hold":"","country":"DE","period_end":0,"credit_period_end":0,"cancel_at_period_end":False}
        _, credit_end = credit_window(a)
        checkout = None
        if pending:
            checkout = dict(pending)
            if checkout["expires_at"] <= int(time.time()): checkout["status"] = "expired"
            target = urlparse(checkout["url"] or "")
            if checkout["status"] != "open" or target.scheme != "https" or target.hostname != "checkout.stripe.com" or target.username or target.password:
                checkout["url"] = None
        return {"managed":True,**{k:a[k] for k in ("status","plan","purchased","hold","country","period_end","cancel_at_period_end")},"credit_period_end":credit_end,"included":a["included"] if a["period_end"]>int(time.time()) else 0,"active":bool(usable(a)),"ledger":entries,"checkout":checkout}

    @app.post("/billing/checkout")
    def checkout(body: Checkout,request: Request,user=Depends(current_user)):
        org=admin(user); cfg=require_config()
        if body.country not in EU or not body.business: raise HTTPException(422,"Nur Unternehmen mit Sitz und Rechnungsadresse in der EU können buchen.")
        if not body.pdf_consent: raise HTTPException(422,"Bitte stimme der Rechnung als PDF per E-Mail zu.")
        if body.sku not in CATALOG: raise HTTPException(422,"Unbekannter Tarif")
        item=CATALOG[body.sku]; price_id=os.getenv("STRIPE_PRICE_"+body.sku.upper())
        order_id=f"{org}_{body.request_id}"
        # Serialize local requests. If provider succeeds but connection is lost, same order/key is retried.
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            from . import mail_templates
            previous = conn.execute("SELECT email_language FROM users WHERE id=?", (user["id"],)).fetchone()
            checkout_language = mail_templates.request_language(request, previous[0])
            conn.execute("UPDATE users SET email_language=? WHERE id=?", (checkout_language, user["id"]))
            a=account(conn,org)
            if not a:
                conn.execute("INSERT INTO billing_accounts(organization_id,country,mode) VALUES(?,?,?)",(org,body.country,configuration()["mode"]));a=account(conn,org)
            if a["mode"] != cfg["mode"]: raise HTTPException(409,"Test- und Livekonten müssen getrennt betrieben werden.")
            if a["hold"]: raise HTTPException(409,"Deine Abrechnung wird geprüft. Bitte den Betreiber kontaktieren.")
            previous=conn.execute("SELECT * FROM billing_orders WHERE id=?",(order_id,)).fetchone()
            if previous and (previous["sku"]!=body.sku or previous["country"]!=body.country): raise HTTPException(409,"Anfrage-ID gehört zu einer anderen Bestellung")
            if previous and previous["status"]=="paid": raise HTTPException(409,"Diese Bestellung ist bereits bezahlt")
            if previous and previous["expires_at"]<=int(time.time()): raise HTTPException(409,"Bestellung abgelaufen. Bitte eine neue Anfrage starten.")
            if item["kind"]=="subscription":
                if a["subscription"]:
                    sub=remote("subscriptions",a["subscription"])
                    if sub["status"] not in {"canceled","incomplete_expired"}: raise HTTPException(409,"Es besteht bereits ein Abo. Bitte im Kundenportal verwalten.")
                if CATALOG[body.sku]["seats"] < conn.execute("SELECT COUNT(*) FROM users WHERE organization_id=? AND role IN ('user','firmen_admin')",(org,)).fetchone()[0]: raise HTTPException(409,"Dieser Tarif hat zu wenige Nutzerplätze.")
            elif not usable(a): raise HTTPException(402,"Token-Nachkäufe erfordern ein aktives Abo.")
            pending=conn.execute("SELECT * FROM billing_orders WHERE organization_id=? AND status IN ('creating','open') AND expires_at>? ORDER BY created_at DESC LIMIT 1",(org,int(time.time()))).fetchone()
            if pending and pending["id"]!=order_id:
                if pending["sku"]==body.sku and pending["country"]==body.country:
                    if pending["url"]: return {"url":pending["url"]}
                    order_id=pending["id"];previous=pending
                else:
                    raise HTTPException(409,"Ein Checkout ist noch offen. Bitte diesen abschließen oder verwerfen, bevor du einen anderen Tarif wählst.")
            if previous and previous["url"]: return {"url":previous["url"]}
            validate_price(remote("prices",price_id),item)
            if not previous:
                now=int(time.time());conn.execute("INSERT INTO billing_orders(id,organization_id,sku,price,created_at,expires_at,country,pdf_consent) VALUES(?,?,?,?,?,?,?,1)",(order_id,org,body.sku,price_id,now,now+1860,body.country))
            elif not previous["pdf_consent"]:
                conn.execute("UPDATE billing_orders SET pdf_consent=1 WHERE id=?",(order_id,))
        with db() as conn:
            a=account(conn,org);org_name=conn.execute("SELECT name FROM organizations WHERE id=?",(org,)).fetchone()[0]
            order=dict(conn.execute("SELECT * FROM billing_orders WHERE id=?",(order_id,)).fetchone())
        customer=a["customer"]
        if not customer:
            customer=stripe_call("POST","customers",{"email":user["email"],"name":org_name,"address":{"country":body.country},"metadata":{"organization_id":str(org)}},f"mh-customer-{org}")["id"]
            with db() as conn: conn.execute("UPDATE billing_accounts SET customer=? WHERE organization_id=?",(customer,org))
        metadata={"order_id":order_id,"organization_id":str(org),"sku":body.sku}
        return_path = "/onboarding" if body.onboarding else "/app"
        payload={"ui_mode":"hosted_page","mode":item["kind"],"customer":customer,"client_reference_id":str(org),"line_items":[{"price":order["price"],"quantity":1}],"payment_method_types":["card"],"billing_address_collection":"required","phone_number_collection":{"enabled":False},"customer_update":{"address":"auto","name":"auto"},"automatic_tax":{"enabled":True},"tax_id_collection":{"enabled":True},"allow_promotion_codes":False,"submit_type":"auto","integration_identifier":"hosted_web_0001","origin_context":"web","locale":checkout_language,"metadata":metadata,"expires_at":order["expires_at"],"success_url":cfg["site"]+return_path+"?billing=success","cancel_url":cfg["site"]+return_path+"?billing=cancelled","custom_text":{"submit":{"message":("Only for companies based in the European Union with an EU billing address. Prices are net; applicable taxes are shown before payment." if checkout_language == "en" else "Nur für Unternehmen mit Sitz und Rechnungsadresse in der Europäischen Union. Preise netto; anfallende Steuern werden vor Zahlung angezeigt.")}}}
        if item["kind"]=="subscription":
            payload.update({"payment_method_collection":"always","subscription_data":{"metadata":metadata}})
        else:
            payload.update({"payment_intent_data":{"metadata":metadata},"invoice_creation":{"enabled":True}})
        result=stripe_call("POST","checkout/sessions",payload,"mh-checkout-"+order_id)
        if urlparse(result.get("url","")).hostname!="checkout.stripe.com": raise HTTPException(502,"Ungültige Checkout-Antwort")
        with db() as conn: conn.execute("UPDATE billing_orders SET checkout=?,url=?,customer=?,status='open' WHERE id=?",(result["id"],result["url"],customer,order_id))
        return {"url":result["url"]}

    @app.post("/billing/checkout/cancel")
    def cancel_checkout(user=Depends(current_user)):
        org=admin(user);require_config()
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            orders=conn.execute("SELECT * FROM billing_orders WHERE organization_id=? AND status='open'",(org,)).fetchall()
            for order in orders:
                session=remote("checkout/sessions",order["checkout"])
                if session.get("status")=="complete": raise HTTPException(409,"Die Zahlung wurde bereits abgeschlossen. Bitte Status aktualisieren.")
                if session.get("status")=="open": stripe_call("POST",f"checkout/sessions/{quote(order['checkout'],safe='')}/expire",{},"mh-expire-"+order["id"])
                conn.execute("UPDATE billing_orders SET status='expired',expires_at=? WHERE id=?",(int(time.time()),order["id"]))
        return {"cancelled":True}

    @app.post("/billing/portal")
    def portal(request: Request, user=Depends(current_user)):
        from . import mail_templates
        portal_language = mail_templates.request_language(request)
        org=admin(user);cfg=require_config()
        with db() as conn:a=account(conn,org)
        if not a or not a["customer"]: raise HTTPException(409,"Noch kein Stripe-Kundenkonto vorhanden")
        if a["mode"] != cfg["mode"]: raise HTTPException(409,"Test- und Livekonten müssen getrennt betrieben werden.")
        # A dedicated restrictive configuration prevents unsynchronized plan changes/address edits.
        config=stripe_call("POST","billing_portal/configurations",{"business_profile":{"headline":"MH · Billing" if portal_language == "en" else "MH · Abrechnung verwalten"},"features":{"customer_update":{"enabled":False},"invoice_history":{"enabled":True},"payment_method_update":{"enabled":True},"subscription_cancel":{"enabled":True,"mode":"at_period_end"},"subscription_update":{"enabled":False}}},"mh-portal-eu-v2-" + portal_language)
        result=stripe_call("POST","billing_portal/sessions",{"customer":a["customer"],"configuration":config["id"],"locale":portal_language,"return_url":cfg["site"]+"/app?billing=portal"})
        if urlparse(result.get("url","")).hostname!="billing.stripe.com": raise HTTPException(502,"Ungültige Portal-Antwort")
        return {"url":result["url"]}

    @app.post("/billing/webhook")
    async def webhook(request: Request, stripe_signature: str | None=Header(default=None)):
        payload=await request.body()
        if len(payload)>1048576: raise HTTPException(413,"Payload too large")
        event=verify_signature(payload,stripe_signature)
        def commit_event():
            with db() as conn:
                conn.execute("BEGIN IMMEDIATE")
                if conn.execute("SELECT 1 FROM billing_events WHERE id=?",(event["id"],)).fetchone(): return
                process_event(conn,event)
                conn.execute("INSERT INTO billing_events VALUES(?,?,?)",(event["id"],event["type"],int(time.time())))
        await run_in_threadpool(commit_event)
        if event["type"] in {"invoice.paid", "checkout.session.completed", "checkout.session.async_payment_succeeded"}:
            await run_in_threadpool(invoice_mail.deliver, db, event["data"]["object"]["id"])
        return {"received":True}
