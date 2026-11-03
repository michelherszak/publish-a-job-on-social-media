"""Configure Gmail SMTP for the local MH test instance without exposing credentials."""
import argparse
import getpass
import smtplib
import ssl

import certifi
from email.message import EmailMessage

from .stripe_test import ENV_FILE, read_env, save_env

ACCOUNT = "Michel.herszak@gmail.com"
HOST = "smtp.gmail.com"
PORT = "587"


def prepare():
    """Save only public connection details; keep local mail delivery active."""
    values = read_env(ENV_FILE)
    values.update(MH_MAIL_FROM=f"MH <{ACCOUNT}>", MH_SMTP_HOST=HOST,
                  MH_SMTP_PORT=PORT, MH_SMTP_USER=ACCOUNT)
    values["MH_MAIL_MODE"] = "local"
    save_env(ENV_FILE, values)
    print("Gmail-Verbindungsdaten vorbereitet. Mailmodus bleibt lokal, bis der SMTP-Test erfolgreich ist.")


def connect():
    """Prompt invisibly, send one self-test, then enable SMTP atomically."""
    values = read_env(ENV_FILE)
    if values.get("MH_SMTP_USER", "").lower() != ACCOUNT.lower() or values.get("MH_SMTP_HOST") != HOST:
        raise ValueError("Zuerst 'prepare' ausführen.")
    password = getpass.getpass("Google-App-Passwort (unsichtbar, nicht im Chat eingeben): ").replace(" ", "").strip()
    if len(password) != 16 or not password.isascii() or not password.isalnum():
        raise ValueError("Ein Google-App-Passwort mit 16 Zeichen ist erforderlich.")
    message = EmailMessage()
    message["From"] = values["MH_MAIL_FROM"]
    message["To"] = ACCOUNT
    message["Subject"] = "MH · Gmail SMTP-Test"
    message.set_content("Die MH-Testinstanz konnte über Gmail SMTP eine E-Mail versenden. Es wurde keine Registrierung oder Rechnung ausgelöst.")
    stage = "Verbindung"
    try:
        with smtplib.SMTP(HOST, int(PORT), timeout=15) as smtp:
            stage = "TLS"
            smtp.starttls(context=ssl.create_default_context(cafile=certifi.where()))
            stage = "Anmeldung"
            smtp.login(ACCOUNT, password)
            stage = "Testversand"
            smtp.send_message(message)
    except smtplib.SMTPAuthenticationError as error:
        raise RuntimeError(f"Gmail hat das App-Passwort abgelehnt (SMTP {error.smtp_code}). Mailmodus bleibt lokal.") from None
    except (OSError, smtplib.SMTPException) as error:
        raise RuntimeError(f"Gmail-Test bei {stage} fehlgeschlagen ({type(error).__name__}). Mailmodus bleibt lokal.") from None
    values["MH_SMTP_PASSWORD"] = password
    values["MH_MAIL_MODE"] = "smtp"
    save_env(ENV_FILE, values)
    print("Testmail an das eigene Gmail-Konto gesendet. SMTP aktiviert; Backend neu starten.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "connect"))
    args = parser.parse_args()
    try:
        {"prepare": prepare, "connect": connect}[args.action]()
    except (ValueError, RuntimeError, KeyboardInterrupt, EOFError) as error:
        print(str(error) if isinstance(error, (ValueError, RuntimeError)) else "Einrichtung abgebrochen.")
        raise SystemExit(1)
