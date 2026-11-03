"""Cookie authentication, one-use email links, TOTP and company invitations."""
import base64
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import smtplib
import sqlite3
import ssl
import struct
import time
from urllib.parse import quote, urlencode, urlparse

import certifi
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from . import billing, mail_templates

OUTBOX = Path(__file__).parent / "mail_outbox"
KEY_FILE = Path(__file__).parent / ".auth.key"
SESSION = "mh_session"
CSRF = "mh_csrf"


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def production():
    return os.getenv("MH_ENV") == "production"


def cipher():
    key = os.getenv("MH_AUTH_ENCRYPTION_KEY")
    if not key:
        if production():
            raise RuntimeError("Production requires MH_AUTH_ENCRYPTION_KEY")
        try:
            fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(Fernet.generate_key())
        except FileExistsError:
            pass
        key = KEY_FILE.read_bytes()
    return Fernet(key)


def schema(conn):
    for table, additions in {
        "users": {"email_language": "TEXT NOT NULL DEFAULT 'de'", "email_verified": "INTEGER NOT NULL DEFAULT 1", "security_required": "INTEGER NOT NULL DEFAULT 0",
                  "mfa_secret": "TEXT NOT NULL DEFAULT ''", "mfa_pending": "TEXT NOT NULL DEFAULT ''", "mfa_last": "INTEGER NOT NULL DEFAULT -1", "mfa_recovery_required": "INTEGER NOT NULL DEFAULT 0"},
        "sessions": {"csrf_hash": "TEXT NOT NULL DEFAULT ''", "mfa_ok": "INTEGER NOT NULL DEFAULT 0", "last_seen": "INTEGER NOT NULL DEFAULT 0"},
        "organizations": {"onboarding_done": "INTEGER NOT NULL DEFAULT 0", "onboarding_deferred": "INTEGER NOT NULL DEFAULT 0", "profile_done": "INTEGER NOT NULL DEFAULT 0"},
    }.items():
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for name, declaration in additions.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS auth_links (
          token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
          kind TEXT NOT NULL, expires_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS auth_limits (
          key TEXT PRIMARY KEY, attempts INTEGER NOT NULL, resets_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS csrf_tokens (token_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS recovery_codes (
          user_id INTEGER NOT NULL REFERENCES users(id), code_hash TEXT NOT NULL,
          PRIMARY KEY(user_id,code_hash));
        CREATE TABLE IF NOT EXISTS invitations (
          token_hash TEXT PRIMARY KEY, organization_id INTEGER NOT NULL REFERENCES organizations(id),
          email TEXT NOT NULL, role TEXT NOT NULL, expires_at INTEGER NOT NULL,
          UNIQUE(organization_id,email));
        CREATE TABLE IF NOT EXISTS account_recoveries (
          id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          email TEXT NOT NULL, fingerprint TEXT NOT NULL, state TEXT NOT NULL,
          created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
          email_verified_at INTEGER NOT NULL DEFAULT 0, reviewed_at INTEGER NOT NULL DEFAULT 0,
          reviewed_by TEXT NOT NULL DEFAULT '', review_reference TEXT NOT NULL DEFAULT '');
    """)


def rate(db, request, action, identity="", limit=10, seconds=900):
    host = request.client.host if request.client else "unknown"
    now = int(time.time())
    blocked = False
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM auth_limits WHERE resets_at<=?", (now,))
        limits = {digest(action + '|' + host + '|' + identity.lower()): limit}
        if identity:
            limits[digest(action + '|' + host + '|')] = max(limit * 10, 50)
        for key, maximum in limits.items():
            row = conn.execute("SELECT attempts FROM auth_limits WHERE key=?", (key,)).fetchone()
            count = row[0] if row else 0
            blocked = blocked or count >= maximum
            if row:
                conn.execute("UPDATE auth_limits SET attempts=attempts+1 WHERE key=?", (key,))
            else:
                conn.execute("INSERT INTO auth_limits VALUES(?,?,?)", (key, 1, now + seconds))
    if blocked:
        raise HTTPException(429, "Zu viele Versuche. Bitte später erneut versuchen.")


def cookie(response, name, value, age=8 * 3600):
    response.set_cookie(name, value, httponly=True, secure=production(), samesite="lax", max_age=age, path="/")


def csrf(db, request, response, rotate=False):
    token = request.cookies.get(CSRF, "")
    with db() as conn:
        conn.execute("DELETE FROM csrf_tokens WHERE expires_at<=?", (int(time.time()),))
        exists = token and conn.execute("SELECT 1 FROM csrf_tokens WHERE token_hash=?", (digest(token),)).fetchone()
        if rotate or not exists:
            token = secrets.token_urlsafe(32)
            conn.execute("INSERT INTO csrf_tokens VALUES(?,?)", (digest(token), int(time.time()) + 8 * 3600))
    cookie(response, CSRF, token)
    return token


def session(db, request, response, uid, mfa_ok=False):
    token = secrets.token_urlsafe(32)
    csrf_token = csrf(db, request, response, rotate=True)
    now = int(time.time())
    with db() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash=? OR expires_at<=?", (digest(request.cookies.get(SESSION, "")), now))
        conn.execute("INSERT INTO sessions(token_hash,user_id,expires_at,csrf_hash,mfa_ok,last_seen) VALUES(?,?,?,?,?,?)",
                     (digest(token), uid, now + 8 * 3600, digest(csrf_token), int(mfa_ok), now))
    cookie(response, SESSION, token)
    return csrf_token


def deliver_message(message):
    """Deliver a transactional message through the configured local or SMTP transport."""
    if os.getenv("MH_MAIL_MODE", "local") == "smtp":
        try:
            with smtplib.SMTP(os.environ["MH_SMTP_HOST"], int(os.getenv("MH_SMTP_PORT", "587")), timeout=15) as smtp:
                smtp.starttls(context=ssl.create_default_context(cafile=certifi.where()))
                smtp.login(os.environ["MH_SMTP_USER"], os.environ["MH_SMTP_PASSWORD"])
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException, KeyError):
            raise HTTPException(503, "E-Mail konnte nicht versendet werden. Bitte später erneut anfordern.")
    else:
        if production():
            raise HTTPException(503, "E-Mail-Versand ist noch nicht eingerichtet.")
        OUTBOX.mkdir(mode=0o700, exist_ok=True)
        os.chmod(OUTBOX, 0o700)
        fd = os.open(OUTBOX / (str(time.time_ns()) + ".eml"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(message.as_string())


def send_mail(email, subject, action, token, language="de"):
    origin = os.getenv("MH_PUBLIC_URL", "http://127.0.0.1:5181").rstrip("/")
    # Fragment tokens never appear in HTTP access logs or referrer URLs.
    message = mail_templates.auth_message(
        os.getenv("MH_MAIL_FROM", "MH <noreply@mh.local>"), email, subject, origin, action, token, language)
    deliver_message(message)


def issue_link(conn, uid, kind, minutes):
    token = secrets.token_urlsafe(32)
    conn.execute("DELETE FROM auth_links WHERE user_id=? AND kind=?", (uid, kind))
    conn.execute("INSERT INTO auth_links VALUES(?,?,?,?)", (digest(token), uid, kind, int(time.time()) + minutes * 60))
    return token


def totp(secret, counter):
    hashed = hmac.new(base64.b32decode(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = hashed[-1] & 15
    return str((struct.unpack(">I", hashed[offset:offset + 4])[0] & 0x7fffffff) % 1000000).zfill(6)


def check_totp(conn, row, code, pending=False):
    encrypted = row["mfa_pending" if pending else "mfa_secret"]
    if not encrypted:
        return False
    secret = cipher().decrypt(encrypted.encode()).decode()
    for counter in range(int(time.time()) // 30 - 1, int(time.time()) // 30 + 2):
        if counter > row["mfa_last"] and hmac.compare_digest(totp(secret, counter), code):
            conn.execute("UPDATE users SET mfa_last=? WHERE id=?", (counter, row["id"]))
            return True
    return False


def recovery(conn, uid, code):
    return conn.execute("DELETE FROM recovery_codes WHERE user_id=? AND code_hash=?", (uid, digest(code.strip()))).rowcount == 1


def authenticator_setup(email, secret):
    site = urlparse(os.getenv("MH_PUBLIC_URL", "http://127.0.0.1:5181"))
    website = site.scheme + "://" + site.netloc
    # Issuer and account are standard Authenticator fields. A literal colon is
    # reserved for their separator, so show a local port in parentheses.
    host = (site.hostname or "").replace(":", "·")
    port = site.port if site.port != {"http": 80, "https": 443}.get(site.scheme) else None
    issuer = "MH · " + host + (f" ({port})" if port else "")
    return {"secret": secret, "website": website,
            "uri": "otpauth://totp/" + quote(issuer, safe="") + ":" + quote(email, safe="") + "?" +
            urlencode({"secret": secret, "issuer": issuer, "algorithm": "SHA1", "digits": 6, "period": 30})}


class EmailBody(BaseModel):
    email: str = Field(max_length=320)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Ungültige E-Mail-Adresse")
        return value


class PasswordBody(BaseModel):
    password: str = Field(min_length=15, max_length=128)


class LinkBody(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class ResetBody(LinkBody, PasswordBody):
    recovery_code: str = Field(default="", max_length=100)


class CodeBody(BaseModel):
    code: str = Field(min_length=6, max_length=100)


class InviteBody(EmailBody):
    role: str = Field(pattern=r"^(user|kunde|firmen_admin)$")


class AcceptBody(LinkBody, PasswordBody):
    name: str = Field(min_length=2, max_length=160)


def install(app, db, current_user, password_hash, verify_password, LoginBody, Profile):
    dummy_hash = password_hash("unknown-account-dummy-password", bytes(16))
    if production():
        origin = urlparse(os.getenv("MH_PUBLIC_URL", ""))
        if (origin.scheme != "https" or not origin.hostname or origin.hostname in {"localhost", "127.0.0.1", "::1"}
                or origin.username or origin.password or origin.path not in {"", "/"} or origin.query or origin.fragment
                or os.getenv("MH_MAIL_MODE") != "smtp" or os.getenv("MH_DEMO_SWITCHER", "1") != "0"
                or any(not os.getenv(name, "").strip() for name in ("MH_MAIL_FROM", "MH_SMTP_HOST", "MH_SMTP_USER", "MH_SMTP_PASSWORD"))):
            raise RuntimeError("Production requires HTTPS, SMTP and disabled demo switcher")
        cipher()

    @app.middleware("http")
    async def protection(request, call_next):
        origin = request.headers.get("origin")
        allowed = {os.getenv("MH_PUBLIC_URL", "http://127.0.0.1:5181").rstrip("/")}
        if not production():
            allowed.update({"http://127.0.0.1:5181", "http://localhost:5181", "http://127.0.0.1:4181"})
        if request.method not in {"GET", "HEAD", "OPTIONS"} and request.url.path not in {"/billing/webhook", "/tracking/receipts", "/tracking/receipts/check"}:
            token = request.cookies.get(CSRF, "")
            with db() as conn:
                valid = token and hmac.compare_digest(token, request.headers.get("x-csrf-token", "")) and conn.execute(
                    "SELECT 1 FROM csrf_tokens WHERE token_hash=? AND expires_at>?", (digest(token), int(time.time()))).fetchone()
            if not valid or (origin and origin not in allowed):
                return JSONResponse({"detail": "Sicherheitsprüfung fehlgeschlagen. Seite neu laden."}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'; object-src 'none'; base-uri 'none'"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if production():
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.get("/auth/csrf")
    def get_csrf(request: Request, response: Response):
        return {"csrf": csrf(db, request, response)}

    @app.post("/auth/login")
    def login(body: LoginBody, request: Request, response: Response):
        rate(db, request, "login", body.email)
        with db() as conn:
            row = conn.execute("SELECT * FROM users WHERE email=?", (body.email.strip().lower(),)).fetchone()
        # Do comparable password work for unknown accounts too.
        stored = row["password_hash"] if row else dummy_hash
        if not verify_password(body.password, stored) or not row:
            raise HTTPException(401, "E-Mail oder Passwort ist ungültig.")
        if not stored.startswith("scrypt2:"):
            with db() as conn:
                conn.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash(body.password), row["id"]))
        with db() as conn:
            conn.execute("UPDATE users SET email_language=? WHERE id=?", (mail_templates.request_language(request, row["email_language"]), row["id"]))
        session(db, request, response, row["id"])
        return {"ok": True}

    @app.post("/auth/logout")
    def logout(request: Request, response: Response):
        with db() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash=?", (digest(request.cookies.get(SESSION, "")),))
        response.delete_cookie(SESSION, path="/")
        response.delete_cookie(CSRF, path="/")
        return {"ok": True}

    @app.post("/auth/resend")
    @app.post("/auth/forgot")
    def request_link(body: EmailBody, request: Request):
        kind = "reset" if request.url.path.endswith("forgot") else "verify"
        rate(db, request, kind, body.email, limit=3, seconds=3600)
        token = None
        with db() as conn:
            row = conn.execute("SELECT * FROM users WHERE email=?", (body.email,)).fetchone()
            if row and (kind == "reset" or not row["email_verified"]):
                token = issue_link(conn, row["id"], kind, 30 if kind == "reset" else 60)
        if token:
            send_mail(body.email, "MH: Passwort zurücksetzen" if kind == "reset" else "MH: E-Mail bestätigen", kind, token, mail_templates.request_language(request, row["email_language"]))
        return {"message": "Wenn das Konto dafür infrage kommt, wurde eine E-Mail vorbereitet. Prüfe dein Postfach.", "local_mail": not production() and os.getenv("MH_MAIL_MODE", "local") == "local"}

    @app.post("/auth/verify-email")
    def verify_email(body: LinkBody, request: Request):
        rate(db, request, "verify-consume", limit=20)
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM auth_links WHERE token_hash=? AND kind='verify' AND expires_at>?", (digest(body.token), int(time.time()))).fetchone()
            if not row:
                raise HTTPException(400, "Link ist ungültig oder abgelaufen. Fordere eine neue E-Mail an.")
            conn.execute("UPDATE users SET email_verified=1 WHERE id=?", (row["user_id"],))
            conn.execute("DELETE FROM auth_links WHERE token_hash=?", (digest(body.token),))
        return {"ok": True}

    @app.post("/auth/reset-password")
    def reset_password(body: ResetBody, request: Request):
        rate(db, request, "reset-consume")
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            link = conn.execute("SELECT * FROM auth_links WHERE token_hash=? AND kind='reset' AND expires_at>?", (digest(body.token), int(time.time()))).fetchone()
            if not link:
                raise HTTPException(400, "Link ist ungültig oder abgelaufen.")
            row = conn.execute("SELECT * FROM users WHERE id=?", (link["user_id"],)).fetchone()
            if row["mfa_secret"] and not recovery(conn, row["id"], body.recovery_code):
                raise HTTPException(400, "Ein unbenutzter Wiederherstellungscode ist erforderlich.")
            conn.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash(body.password), row["id"]))
            conn.execute("DELETE FROM sessions WHERE user_id=?", (row["id"],))
            conn.execute("DELETE FROM auth_links WHERE user_id=? AND kind='reset'", (row["id"],))
        return {"ok": True}

    @app.post("/auth/mfa/setup")
    def setup_mfa(request: Request, user=Depends(current_user)):
        if not user["email_verified"]:
            raise HTTPException(403, "Bitte zuerst deine E-Mail bestätigen.")
        rate(db, request, "mfa-setup", str(user["id"]))
        secret = base64.b32encode(secrets.token_bytes(20)).decode()
        with db() as conn:
            if conn.execute("SELECT mfa_secret FROM users WHERE id=?", (user["id"],)).fetchone()[0]:
                raise HTTPException(409, "Zwei-Faktor-Anmeldung ist bereits eingerichtet.")
            conn.execute("UPDATE users SET mfa_pending=?,mfa_last=-1 WHERE id=?", (cipher().encrypt(secret.encode()).decode(), user["id"]))
        return authenticator_setup(user["email"], secret)

    @app.post("/auth/mfa/reconnect")
    def reconnect_mfa(body: CodeBody, request: Request, user=Depends(current_user)):
        # Possession of a one-use recovery code is required even in an MFA-verified session.
        # Password-only sessions must never receive the installed authenticator seed.
        rate(db, request, "mfa-reconnect", str(user["id"]), limit=5)
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
            if not row["email_verified"] or not row["mfa_secret"] or user.get("view_role"):
                raise HTTPException(403, "Authenticator-Verbindung nicht verfügbar.")
            if not recovery(conn, user["id"], body.code):
                raise HTTPException(400, "Ein unbenutzter Wiederherstellungscode ist erforderlich.")
            secret = cipher().decrypt(row["mfa_secret"].encode()).decode()
        # No session privilege is granted here; a code from the connected app must still pass challenge.
        return authenticator_setup(user["email"], secret)

    @app.post("/auth/mfa/confirm")
    @app.post("/auth/mfa/challenge")
    def mfa(body: CodeBody, request: Request, response: Response, user=Depends(current_user)):
        rate(db, request, "mfa-code", str(user["id"]), limit=5)
        pending = request.url.path.endswith("confirm")
        codes = []
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
            if not row["email_verified"] or (pending and row["mfa_secret"]):
                raise HTTPException(403, "Sicherheitseinrichtung nicht verfügbar.")
            valid = check_totp(conn, row, body.code, pending)
            if not valid and not pending and row["mfa_secret"]:
                valid = recovery(conn, user["id"], body.code)
            if not valid:
                raise HTTPException(400, "Code ungültig oder bereits verwendet.")
            if pending:
                conn.execute("UPDATE users SET mfa_secret=mfa_pending,mfa_pending='',mfa_recovery_required=0 WHERE id=?", (user["id"],))
                codes = [secrets.token_hex(16) for _ in range(10)]
                conn.executemany("INSERT INTO recovery_codes VALUES(?,?)", [(user["id"], digest(code)) for code in codes])
        session(db, request, response, user["id"], mfa_ok=True)
        return {"ok": True, "recovery_codes": codes}

    @app.post("/auth/invitations", status_code=201)
    def invite(body: InviteBody, request: Request, user=Depends(current_user)):
        if user["role"] != "firmen_admin" or user.get("view_role"):
            raise HTTPException(403, "Nur Firmen-Admins dürfen einladen.")
        rate(db, request, "invite", str(user["id"]), limit=20, seconds=3600)
        org = user["organization_id"]
        token = secrets.token_urlsafe(32)
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM invitations WHERE expires_at<=?", (int(time.time()),))
            if conn.execute("SELECT 1 FROM users WHERE email=?", (body.email,)).fetchone():
                raise HTTPException(409, "Diese Adresse ist bereits einem Konto zugeordnet.")
            billing.enforce_seats(conn, org, body.role)
            a = billing.account(conn, org)
            if a and body.role != "kunde":
                occupied = conn.execute("SELECT COUNT(*) FROM users WHERE organization_id=? AND role!='kunde'", (org,)).fetchone()[0]
                reserved = conn.execute("SELECT COUNT(*) FROM invitations WHERE organization_id=? AND role!='kunde' AND email!=?", (org, body.email)).fetchone()[0]
                if occupied + reserved >= billing.CATALOG[a["plan"]]["seats"]:
                    raise HTTPException(409, "Nutzerplätze einschließlich offener Einladungen sind ausgeschöpft.")
            conn.execute("INSERT OR REPLACE INTO invitations VALUES(?,?,?,?,?)", (digest(token), org, body.email, body.role, int(time.time()) + 48 * 3600))
        send_mail(body.email, "MH: Einladung in deinen Firmen-Workspace", "invite", token, mail_templates.request_language(request))
        return {"ok": True, "local_mail": not production() and os.getenv("MH_MAIL_MODE", "local") == "local"}

    @app.get("/auth/invitations")
    def invitations(user=Depends(current_user)):
        if user["role"] != "firmen_admin" or user.get("view_role"):
            raise HTTPException(403, "Firmen-Admin erforderlich.")
        with db() as conn:
            return [dict(row) for row in conn.execute("SELECT email,role,expires_at FROM invitations WHERE organization_id=? AND expires_at>?", (user["organization_id"], int(time.time())))]

    @app.post("/auth/invitations/revoke")
    def revoke(body: EmailBody, user=Depends(current_user)):
        if user["role"] != "firmen_admin" or user.get("view_role"):
            raise HTTPException(403, "Firmen-Admin erforderlich.")
        with db() as conn:
            conn.execute("DELETE FROM invitations WHERE organization_id=? AND email=?", (user["organization_id"], body.email))
        return {"ok": True}

    @app.post("/auth/accept-invite")
    def accept(body: AcceptBody, request: Request):
        rate(db, request, "accept-invite")
        if len(body.name.strip()) < 2:
            raise HTTPException(422, "Dein Name ist erforderlich.")
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            invite = conn.execute("SELECT * FROM invitations WHERE token_hash=? AND expires_at>?", (digest(body.token), int(time.time()))).fetchone()
            if not invite:
                raise HTTPException(400, "Einladung ist ungültig oder abgelaufen.")
            billing.enforce_seats(conn, invite["organization_id"], invite["role"])
            try:
                conn.execute("INSERT INTO users(email,name,password_hash,role,organization_id,email_verified,security_required) VALUES(?,?,?,?,?,1,1)",
                             (invite["email"], body.name.strip(), password_hash(body.password), invite["role"], invite["organization_id"]))
            except sqlite3.IntegrityError:
                raise HTTPException(409, "Diese Adresse ist bereits einem Konto zugeordnet.")
            conn.execute("UPDATE users SET email_language=? WHERE email=?", (mail_templates.request_language(request), invite["email"]))
            conn.execute("DELETE FROM invitations WHERE token_hash=?", (digest(body.token),))
        return {"ok": True}

    @app.get("/onboarding")
    def onboarding(user=Depends(current_user)):
        org = user["organization_id"]
        with db() as conn:
            company = conn.execute("SELECT * FROM organizations WHERE id=?", (org,)).fetchone()
            a = billing.account(conn, org)
            campaign = conn.execute("SELECT id,status,generated,generation_mode FROM projects WHERE organization_id=? ORDER BY id LIMIT 1", (org,)).fetchone()
        return {"required": bool(user["security_required"] and user["role"] == "firmen_admin"),
                "done": bool(company and company["onboarding_done"]), "profile_done": bool(company and company["profile_done"]),
                "deferred": bool(company and company["onboarding_deferred"]),
                "company": dict(company) if company else None, "paid": bool(a and billing.usable(a)),
                "campaign": dict(campaign) if campaign else None}

    @app.post("/onboarding/profile")
    def profile(body: Profile, user=Depends(current_user)):
        if user["role"] != "firmen_admin" or user.get("view_role"):
            raise HTTPException(403, "Firmen-Admin erforderlich.")
        if not body.industry.strip() or not body.location.strip() or not body.brand_description.strip():
            raise HTTPException(422, "Branche, Standort und Firmenbeschreibung sind erforderlich.")
        with db() as conn:
            fields = body.model_dump()
            conn.execute("UPDATE organizations SET " + ",".join(k + "=?" for k in fields) + ",profile_done=1 WHERE id=?", (*[v.strip() for v in fields.values()], user["organization_id"]))
        return {"ok": True}

    class DeferredDraft(BaseModel):
        campaign_id: int

    @app.post("/onboarding/defer")
    def defer(body: DeferredDraft, user=Depends(current_user)):
        if user["role"] != "firmen_admin" or user.get("view_role"):
            raise HTTPException(403, "Firmen-Admin erforderlich.")
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            org = user["organization_id"]
            company = conn.execute("SELECT profile_done FROM organizations WHERE id=?", (org,)).fetchone()
            a = billing.account(conn, org)
            draft = conn.execute("SELECT 1 FROM projects WHERE id=? AND organization_id=? AND length(trim(role))>=2", (body.campaign_id, org)).fetchone()
            if not company or not company[0] or not a or not billing.usable(a) or not draft:
                raise HTTPException(409, "Bitte Profil, bezahltes Abo und ein gespeichertes Briefing abschließen.")
            conn.execute("UPDATE organizations SET onboarding_deferred=1 WHERE id=?", (org,))
        return {"ok": True}

    @app.post("/onboarding/complete")
    def complete(user=Depends(current_user)):
        if user["role"] != "firmen_admin" or user.get("view_role"):
            raise HTTPException(403, "Firmen-Admin erforderlich.")
        with db() as conn:
            org = user["organization_id"]
            company = conn.execute("SELECT profile_done FROM organizations WHERE id=?", (org,)).fetchone()
            a = billing.account(conn, org)
            campaign = conn.execute("SELECT 1 FROM projects WHERE organization_id=? AND status IN ('Review','Live') AND generated!='{}'", (org,)).fetchone()
            if not company or not company[0] or not campaign or not a or not billing.usable(a):
                raise HTTPException(409, "Bitte Profil, bezahltes Abo und einen geprüften Entwurf abschließen.")
            conn.execute("UPDATE organizations SET onboarding_done=1 WHERE id=?", (org,))
        return {"ok": True}
