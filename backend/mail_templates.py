"""Side-effect-free message builders shared by delivery and admin previews."""
from email.message import EmailMessage
from urllib.parse import urlencode


def request_language(request, fallback="de"):
    """Resolve supported languages by Accept-Language priority; bound untrusted input."""
    choices = []
    for index, entry in enumerate(request.headers.get("accept-language", "")[:512].split(",")):
        parts = entry.strip().lower().split(";")
        language = parts[0].split("-")[0]
        try:
            quality = float(next((part.strip()[2:] for part in parts[1:] if part.strip().startswith("q=")), "1"))
        except ValueError:
            continue
        if language in {"de", "en"} and 0 < quality <= 1:
            choices.append((-quality, index, language))
    return min(choices)[2] if choices else fallback


def auth_message(sender, recipient, subject, origin, action, token, language="de"):
    subjects = {
        "verify": {"de": "MH: E-Mail bestätigen", "en": "MH: Verify your email"},
        "reset": {"de": "MH: Passwort zurücksetzen", "en": "MH: Reset your password"},
        "invite": {"de": "MH: Einladung in deinen Firmen-Workspace", "en": "MH: Invitation to your company workspace"},
        "recover-verify": {"de": "MH: Kontowiederherstellung prüfen", "en": "MH: Verify account recovery request"},
        "recover-reset": {"de": "MH: Kontowiederherstellung freigegeben", "en": "MH: Account recovery approved"},
    }
    language = language if language in {"de", "en"} else "de"
    subject = subjects.get(action, {}).get(language, subject)
    message = EmailMessage()
    message['From'] = sender
    message['To'] = recipient
    message['Subject'] = subject
    link = origin.rstrip('/') + '/auth#' + urlencode({'action': action, 'token': token})
    notice = ("This link expires and can only be used once.\nIf you did not expect this message, ignore it.\n"
              if language == "en" else "Der Link ist zeitlich begrenzt und nur einmal verwendbar.\nWenn du diese Nachricht nicht erwartet hast, ignoriere sie.\n")
    message['Content-Language'] = language
    details = ''
    if action == 'recover-verify':
        details = ('Confirm your mailbox within one hour. A Platform Admin must then independently verify account ownership before recovery is approved. This link does not reset MFA. You can cancel an unexpected request on the linked page.\n\n' if language == 'en' else 'Bestätige dein Postfach innerhalb einer Stunde. Danach muss ein Platform Admin die Kontoinhaberschaft unabhängig prüfen und die Wiederherstellung freigeben. Dieser Link setzt MFA nicht zurück. Eine unerwartete Anfrage kannst du auf der verlinkten Seite abbrechen.\n\n')
    elif action == 'recover-reset':
        details = ('Recovery was approved after an independent ownership check. This link expires in 30 minutes. Continuing sets a new password, revokes all old sessions and authenticator/recovery codes, and requires a new authenticator setup. If you did not request this, cancel on the linked page and contact your MH operator.\n\n' if language == 'en' else 'Die Wiederherstellung wurde nach unabhängiger Prüfung freigegeben. Dieser Link gilt 30 Minuten. Beim Fortfahren setzt du ein neues Passwort; alle bisherigen Sitzungen, Authenticator- und Recovery-Codes werden ungültig. Danach ist eine neue Authenticator-Einrichtung erforderlich. Wenn du dies nicht angefordert hast, brich auf der verlinkten Seite ab und kontaktiere deinen MH-Betreiber.\n\n')
    message.set_content(f'{subject}\n\n{details}{link}\n\n{notice}')
    return message


def invoice_message(sender, recipient, number, pdf, language="de"):
    message = EmailMessage()
    message['From'] = sender
    message['To'] = recipient
    language = language if language in {"de", "en"} else "de"
    message['Content-Language'] = language
    if language == "en":
        message['Subject'] = f'MH: Invoice {number} for your payment'
        message.set_content('We have received your payment. Download the associated Stripe invoice as a PDF here:\n\n' + pdf +
                            '\n\nIf the invoice details are incorrect, reply to this message or contact the listed support contact.\n')
        return message
    message['Subject'] = f'MH: Rechnung {number} zu deiner Zahlung'
    message.set_content(
        'Deine Zahlung ist bei uns eingegangen. Die zugehörige Rechnung von Stripe '
        'kannst du hier als PDF abrufen:\n\n' + pdf +
        '\n\nFalls die Rechnungsdaten nicht stimmen, antworte bitte auf diese Nachricht '
        'oder wende dich an den angegebenen Supportkontakt.\n'
    )
    return message


def status_message(sender, recipient, company, title, actor, old_status, new_status, origin, language="de"):
    language = language if language in {"de", "en"} else "de"
    labels = {"de": {"Draft": "Entwurf", "Review": "In Prüfung", "Live": "Freigegeben"},
              "en": {"Draft": "Draft", "Review": "In review", "Live": "Approved"}}[language]
    old, new = labels[old_status], labels[new_status]
    message = EmailMessage()
    message['From'], message['To'] = sender, recipient
    message['Content-Language'] = language
    # User-entered job titles are body text, never mail headers.
    message['Subject'] = 'MH: Campaign status changed' if language == 'en' else 'MH: Anzeigenstatus geändert'
    link = origin.rstrip('/') + '/app'
    if language == 'en':
        text = f'The status of a campaign in {company} has changed.\n\nCampaign: {title}\nPrevious status: {old}\nNew status: {new}\nChanged by: {actor}\n\nOpen your workspace to view the campaign:\n\n{link}\n\nApproved is an internal workflow status. It does not publish the campaign to external channels.\n'
    else:
        text = f'Der Status einer Anzeige bei {company} hat sich geändert.\n\nAnzeige: {title}\nBisheriger Status: {old}\nNeuer Status: {new}\nGeändert von: {actor}\n\nÖffne deinen Workspace, um die Anzeige anzusehen:\n\n{link}\n\nFreigegeben ist ein interner Workflow-Status. Die Anzeige wird dadurch nicht auf externen Kanälen veröffentlicht.\n'
    message.set_content(text)
    return message


def previews(language="de"):
    sender = 'MH <noreply@example.invalid>'
    recipient = 'anna@beispielfirma.invalid'
    examples = []
    for kind, label, subject, action, description in (
        ('registration', 'Registrierung', 'MH: E-Mail bestätigen', 'verify', 'Bestätigt nach der Registrierung den Zugriff auf das Postfach.'),
        ('password-reset', 'Passwort zurücksetzen', 'MH: Passwort zurücksetzen', 'reset', 'Wird nach einer Anfrage zur Wiederherstellung des Passworts versendet.'),
        ('invitation', 'Einladung', 'MH: Einladung in deinen Firmen-Workspace', 'invite', 'Lädt eine Person in den Firmen-Workspace ein.'),
        ('account-recovery-verify', 'Wiederherstellungsanfrage', 'MH: Kontowiederherstellung prüfen', 'recover-verify', 'Bestätigt das Postfach vor einer unabhängigen Prüfung der Kontoinhaberschaft.'),
        ('account-recovery-reset', 'Wiederherstellung freigegeben', 'MH: Kontowiederherstellung freigegeben', 'recover-reset', 'Einmal-Link nach unabhängiger Prüfung; verlangt neues Passwort und neue MFA-Einrichtung.'),
    ):
        examples.append((kind, label, description, auth_message(sender, recipient, subject, 'https://preview.example.invalid', action, 'PREVIEW-NOT-A-VALID-TOKEN', language)))
    examples.append(('invoice', 'Rechnung', 'Benachrichtigung nach bestätigter Zahlung mit Link zum Stripe-Rechnungs-PDF. Gilt für Abos und Tokenkäufe; das PDF selbst ist kein Bestandteil dieser Vorlage.', invoice_message(sender, recipient, 'MH-BEISPIEL-2026-001', 'https://preview.example.invalid/rechnung.pdf', language)))
    examples.append(('status-change', 'Statusänderung', 'Benachrichtigt alle bestätigten Nutzer der Firma, wenn sich der Status einer Anzeige ändert.', status_message(sender, recipient, 'Beispielfirma', 'Elektroniker (m/w/d)', 'Anna Beispiel', 'Draft', 'Review', 'https://preview.example.invalid', language)))
    return [{'id':kind, 'label':label, 'description':description, 'subject':str(message['Subject']), 'sender':str(message['From']), 'recipient':str(message['To']), 'content_type':message.get_content_type(), 'text':message.get_content()} for kind,label,description,message in examples]
