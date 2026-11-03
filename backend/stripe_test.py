"""Local test-mode setup. Never accepts live keys or prints credentials."""
import argparse
import getpass
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile

from backend import billing

ENV_FILE = Path(__file__).parent / ".env.local"
WEBHOOK_EVENTS = (
    "checkout.session.completed", "checkout.session.async_payment_succeeded",
    "invoice.paid", "invoice.payment_failed",
    "customer.subscription.created", "customer.subscription.updated",
    "customer.subscription.deleted", "customer.updated",
    "charge.refunded", "charge.dispute.created",
)


def read_env(path):
    values = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key, separator, raw = line.partition("=")
            if not separator or not key.strip().replace("_", "").isalnum():
                raise ValueError("Ungültiges Format in .env.local")
            parts = shlex.split(raw, comments=True)
            if len(parts) > 1:
                raise ValueError("Werte mit Leerzeichen müssen in Anführungszeichen stehen.")
            values[key.strip()] = parts[0] if parts else ""
    return values


def save_env(path, values):
    # Atomic replacement, restrictive permissions even on the temporary file.
    fd, temporary = tempfile.mkstemp(prefix=".stripe-config-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write("# Local credentials. Never commit or share this file.\n")
            for key, value in values.items():
                stream.write(f"{key}={shlex.quote(value)}\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def test_key(value):
    if not value.startswith("sk_test_") or len(value) < 16:
        raise ValueError("Nur ein Stripe-Test-Secret-Key (sk_test_...) ist erlaubt.")
    return value


def price_for(sku, item):
    lookup = "mh_test_v2_" + sku
    found = billing.stripe_call("GET", "prices", {"lookup_keys": [lookup], "limit": 1})["data"]
    if found:
        price = found[0]
        recurring = price.get("recurring")
        correct_interval = (
            recurring and recurring.get("interval") == item["interval"] and recurring.get("interval_count") == 1
        ) if item["kind"] == "subscription" else not recurring
        if (price.get("livemode") or not price.get("active") or price.get("currency") != "eur"
                or price.get("unit_amount") != item["cents"] or price.get("tax_behavior") != "exclusive"
                or not correct_interval):
            raise ValueError(f"Vorhandener Testpreis für {sku} passt nicht zum Katalog.")
        return price["id"]
    product = billing.stripe_call("POST", "products", {
        "name": "MH " + item["name"], "metadata": {"mh_test_sku": sku},
    }, key="mh-test-product-v2-" + sku)
    data = {"product": product["id"], "currency": "eur", "unit_amount": item["cents"],
            "tax_behavior": "exclusive", "lookup_key": lookup}
    if item["kind"] == "subscription":
        data["recurring"] = {"interval": item["interval"], "interval_count": 1}
    return billing.stripe_call("POST", "prices", data, key="mh-test-price-v2-" + sku)["id"]


def setup():
    values = read_env(ENV_FILE)
    key = test_key(values.get("STRIPE_SECRET_KEY") or getpass.getpass("Stripe-Test-Secret-Key (Eingabe unsichtbar): ").strip())
    values.update(STRIPE_SECRET_KEY=key, MH_PUBLIC_URL="http://127.0.0.1:5181",
                  MH_STRIPE_LIVE_ENABLED="0", MH_EU_RADAR_CONFIRMED="0",
                  MH_STRIPE_TAX_READY="0", MH_PAID_PRODUCT_READY="0", MH_DEMO_SWITCHER="1")
    os.environ.update(values)
    save_env(ENV_FILE, values)
    for sku, item in billing.CATALOG.items():
        values["STRIPE_PRICE_" + sku.upper()] = price_for(sku, item)
        save_env(ENV_FILE, values)
        print(f"Testpreis eingerichtet: {item['name']}")
    print("In einem zweiten Terminal: stripe listen --forward-to http://127.0.0.1:8011/billing/webhook")
    print("Die CLI muss im selben Stripe-Testkonto / derselben Sandbox angemeldet sein.")
    secret = getpass.getpass("Webhook-Secret der laufenden CLI (whsec_..., Eingabe unsichtbar): ").strip()
    if not secret.startswith("whsec_") or len(secret) < 16:
        raise ValueError("Ein gültiges CLI-Webhook-Secret wird benötigt.")
    values["STRIPE_WEBHOOK_SECRET"] = secret
    save_env(ENV_FILE, values)
    print("Testkonfiguration gespeichert (Berechtigung 600). Stripe Tax im Dashboard konfigurieren.")
    print("Backend starten: python3 -m backend.stripe_test start")


def sync_prices():
    """Create/reuse only the current test catalogue, preserving all private settings."""
    values = read_env(ENV_FILE)
    test_key(values.get("STRIPE_SECRET_KEY", ""))
    os.environ.update(values)
    for sku, item in billing.CATALOG.items():
        values["STRIPE_PRICE_" + sku.upper()] = price_for(sku, item)
        save_env(ENV_FILE, values)
        print(f"Testpreis bereit: {item['name']}")
    print("Neue Testpreise gespeichert. Backend neu starten.")


def verify():
    """Read-only verification of the configured Stripe test catalogue and Tax state."""
    values = read_env(ENV_FILE)
    test_key(values.get("STRIPE_SECRET_KEY", ""))
    os.environ.update(values)
    config = billing.configuration()
    if not config["ready"] or config["mode"] != "test":
        raise ValueError("Testkonfiguration unvollständig.")
    for sku, item in billing.CATALOG.items():
        price_id = values.get("STRIPE_PRICE_" + sku.upper(), "")
        billing.validate_price(billing.remote("prices", price_id), item)
    tax = billing.stripe_call("GET", "tax/settings")
    tax_code = bool((tax.get("defaults") or {}).get("tax_code"))
    print(f"{len(billing.CATALOG)} Testpreise stimmen mit dem MH-Katalog überein.")
    print(f"Stripe Tax: {tax.get('status', 'unbekannt')}; Standard-Steuercode: {'gesetzt' if tax_code else 'fehlt'}.")
    if tax.get("status") != "active" or not tax_code:
        print("Noch nicht zahlungsbereit: Stripe Tax im Dashboard mit echten Unternehmensdaten abschließen.")
        return False
    print("Technische Stripe-Testkonfiguration ist bereit. Radar-Regeln und Testzahlungen bleiben manuell zu prüfen.")
    return True


def listen(ready_file=None):
    """Forward only required test events and save the rotating signing secret privately."""
    values = read_env(ENV_FILE)
    test_key(values.get("STRIPE_SECRET_KEY", ""))
    env = os.environ.copy()
    env["STRIPE_API_KEY"] = values["STRIPE_SECRET_KEY"]
    command = [
        "stripe", "listen", "--events", ",".join(WEBHOOK_EVENTS),
        "--forward-to", "http://127.0.0.1:8011/billing/webhook",
    ]
    process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        assert process.stdout is not None
        for line in process.stdout:
            match = re.search(r"whsec_[A-Za-z0-9]+", line)
            if match:
                values["STRIPE_WEBHOOK_SECRET"] = match.group(0)
                save_env(ENV_FILE, values)
                if ready_file:
                    flag = Path(ready_file)
                    flag.write_text("ready\n")
                    flag.chmod(0o600)
            safe = re.sub(r"(?:sk|rk|whsec)_[A-Za-z0-9_]+", "[privat gespeichert]", line)
            print(safe, end="", flush=True)
    except KeyboardInterrupt:
        process.terminate()
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait()


def start():
    values = read_env(ENV_FILE)
    test_key(values.get("STRIPE_SECRET_KEY", ""))
    os.environ.update(values)
    if not billing.configuration()["ready"] or billing.configuration()["mode"] != "test":
        raise ValueError("Testkonfiguration unvollständig. Zuerst setup ausführen.")
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8011)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("setup", "start", "sync-prices", "verify", "listen"))
    parser.add_argument("--ready-file", help="Private startup readiness flag for the local listener.")
    args = parser.parse_args()
    try:
        result = listen(args.ready_file) if args.action == "listen" else {"setup": setup, "start": start, "sync-prices": sync_prices, "verify": verify}[args.action]()
        if args.action == "verify" and result is False:
            raise SystemExit(2)
    except (ValueError, KeyboardInterrupt, EOFError):
        print("Einrichtung abgebrochen oder Konfiguration ungültig. Prüfe die lokale Testkonfiguration.")
        raise SystemExit(1)
    except billing.HTTPException:
        print("Stripe-Anfrage fehlgeschlagen. Testschlüssel, Kontoberechtigungen und Verbindung prüfen.")
        raise SystemExit(1)
