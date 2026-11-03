"""Reviewed MFA recovery. Mailbox proof alone never resets an authenticator."""
import argparse
import hmac
import logging
import os
import secrets
import time

from fastapi import Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from . import auth, mail_templates

VERIFY = 'mfa-recovery-verify'
RESET = 'mfa-recovery-reset'
INVALID = 'Wiederherstellungsanfrage ist ungültig oder abgelaufen.'


def fingerprint(row):
    return auth.digest(row['password_hash'] + '|' + row['mfa_secret'])


def valid_case(conn, case_id, states):
    case = conn.execute('SELECT * FROM account_recoveries WHERE id=?', (case_id,)).fetchone()
    row = conn.execute('SELECT * FROM users WHERE id=?', (case['user_id'],)).fetchone() if case else None
    if (not case or case['state'] not in states or case['expires_at'] <= int(time.time())
            or not row or not row['email_verified'] or not row['mfa_secret']
            or case['email'] != row['email'] or not hmac.compare_digest(case['fingerprint'], fingerprint(row))):
        raise HTTPException(400, INVALID)
    return case, row


def case_for_link(conn, token, kind, states):
    link = conn.execute('SELECT user_id FROM auth_links WHERE token_hash=? AND kind=? AND expires_at>?',
                        (auth.digest(token), kind, int(time.time()))).fetchone()
    case = conn.execute('SELECT id FROM account_recoveries WHERE user_id=? ORDER BY created_at DESC,rowid DESC LIMIT 1',
                        (link['user_id'],)).fetchone() if link else None
    if not case:
        raise HTTPException(400, INVALID)
    return valid_case(conn, case['id'], states)


def decide(db, case_id, decision, reference, reviewer, confirmed_email):
    """Shared by MFA-authenticated admin review and the trusted host operator tool."""
    if decision not in {'approve', 'reject'} or not reference.strip() or len(reference.strip()) > 240:
        raise HTTPException(422, 'Eine Prüfungsreferenz ist erforderlich.')
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        case, row = valid_case(conn, case_id, {'verified', 'approved'})
        if confirmed_email.strip().lower() != row['email'] or not case['email_verified_at']:
            raise HTTPException(400, INVALID)
        if reviewer == 'admin:' + str(row['id']):
            raise HTTPException(403, 'Eigene Wiederherstellung darf nicht selbst freigegeben werden.')
        conn.execute('DELETE FROM auth_links WHERE user_id=? AND kind IN (?,?)', (row['id'], VERIFY, RESET))
        conn.execute('UPDATE account_recoveries SET state=?,reviewed_at=?,reviewed_by=?,review_reference=? WHERE id=?',
                     ('approved' if decision == 'approve' else 'rejected', int(time.time()), reviewer, reference.strip(), case_id))
        token = auth.issue_link(conn, row['id'], RESET, 30) if decision == 'approve' else None
        email, language = row['email'], row['email_language']
    if token:
        # A delivery failure leaves the approved case retryable; a fresh review rotates this link.
        auth.send_mail(email, 'MH: Kontowiederherstellung freigegeben', 'recover-reset', token, language)


class ReviewBody(BaseModel):
    decision: str = Field(pattern='^(approve|reject)$')
    reference: str = Field(min_length=3, max_length=240)
    email: str = Field(max_length=320)
    ownership_verified: bool = False
    code: str = Field(pattern='^[0-9]{6}$')


class RecoveryResetBody(auth.LinkBody, auth.PasswordBody):
    pass


def install(app, db, current_user, password_hash):
    @app.post('/auth/recovery/request')
    def request_recovery(body: auth.EmailBody, request: Request):
        auth.rate(db, request, 'account-recovery-request', body.email, limit=3, seconds=3600)
        token = None
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT * FROM users WHERE email=?', (body.email,)).fetchone()
            if row and row['email_verified'] and row['mfa_secret']:
                active = conn.execute("SELECT * FROM account_recoveries WHERE user_id=? AND state IN ('requested','verified','approved') AND expires_at>? ORDER BY created_at DESC,rowid DESC LIMIT 1", (row['id'], int(time.time()))).fetchone()
                # An anonymous request must not invalidate a verified/approved request.
                if not active or active['state'] == 'requested':
                    conn.execute("UPDATE account_recoveries SET state='cancelled' WHERE user_id=? AND state IN ('requested','verified','approved')", (row['id'],))
                    conn.execute('DELETE FROM auth_links WHERE user_id=? AND kind IN (?,?)', (row['id'], VERIFY, RESET))
                    now = int(time.time())
                    conn.execute('INSERT INTO account_recoveries(id,user_id,email,fingerprint,state,created_at,expires_at) VALUES(?,?,?,?,?,?,?)',
                                 (secrets.token_urlsafe(18), row['id'], row['email'], fingerprint(row), 'requested', now, now + 7 * 86400))
                    token = auth.issue_link(conn, row['id'], VERIFY, 60)
        if token:
            try:
                auth.send_mail(row['email'], 'MH: Kontowiederherstellung prüfen', 'recover-verify', token,
                               mail_templates.request_language(request, row['email_language']))
            except HTTPException as error:
                if error.status_code != 503:
                    raise
                # The public response must not disclose account eligibility when SMTP fails.
                logging.getLogger(__name__).warning('Account recovery request email delivery failed')
        return {'message': 'Wenn das Konto dafür infrage kommt, wurde eine E-Mail vorbereitet. Prüfe dein Postfach.',
                'local_mail': not auth.production() and os.getenv('MH_MAIL_MODE', 'local') == 'local'}

    @app.post('/auth/recovery/verify')
    def verify_recovery(body: auth.LinkBody, request: Request):
        auth.rate(db, request, 'account-recovery-verify', limit=10)
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            case, row = case_for_link(conn, body.token, VERIFY, {'requested'})
            conn.execute("UPDATE account_recoveries SET state='verified',email_verified_at=? WHERE id=?", (int(time.time()), case['id']))
            conn.execute('DELETE FROM auth_links WHERE token_hash=?', (auth.digest(body.token),))
        return {'ok': True, 'case_id': case['id']}

    @app.post('/auth/recovery/cancel')
    def cancel_recovery(body: auth.LinkBody, request: Request):
        auth.rate(db, request, 'account-recovery-cancel', limit=10)
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            link = conn.execute('SELECT kind FROM auth_links WHERE token_hash=? AND kind IN (?,?) AND expires_at>?',
                                (auth.digest(body.token), VERIFY, RESET, int(time.time()))).fetchone()
            if not link:
                raise HTTPException(400, INVALID)
            case, row = case_for_link(conn, body.token, link['kind'], {'requested', 'approved'})
            conn.execute("UPDATE account_recoveries SET state='cancelled' WHERE id=?", (case['id'],))
            conn.execute('DELETE FROM auth_links WHERE user_id=? AND kind IN (?,?)', (row['id'], VERIFY, RESET))
        return {'ok': True}

    @app.post('/auth/recovery/reset')
    def reset_recovery(body: RecoveryResetBody, request: Request, response: Response):
        auth.rate(db, request, 'account-recovery-reset', limit=5)
        new_hash = password_hash(body.password)
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            case, row = case_for_link(conn, body.token, RESET, {'approved'})
            conn.execute("UPDATE users SET password_hash=?,mfa_secret='',mfa_pending='',mfa_last=-1,mfa_recovery_required=1 WHERE id=?", (new_hash, row['id']))
            conn.execute('DELETE FROM recovery_codes WHERE user_id=?', (row['id'],))
            conn.execute('DELETE FROM sessions WHERE user_id=?', (row['id'],))
            conn.execute('DELETE FROM auth_links WHERE user_id=?', (row['id'],))
            conn.execute("UPDATE account_recoveries SET state='consumed' WHERE id=?", (case['id'],))
        response.delete_cookie(auth.SESSION, path='/')
        response.delete_cookie(auth.CSRF, path='/')
        return {'ok': True}

    def admin(user):
        if user['base_role'] != 'platform_admin' or user['role'] != 'platform_admin' or user.get('view_role'):
            raise HTTPException(403, 'Platform admin required')

    @app.get('/admin/account-recoveries')
    def pending_recoveries(user=Depends(current_user)):
        admin(user)
        with db() as conn:
            rows = conn.execute("""SELECT r.id,r.email,r.state,r.created_at,r.expires_at,r.email_verified_at,
                r.reviewed_at,r.reviewed_by,r.review_reference,u.name,o.name AS company
                FROM account_recoveries r JOIN users u ON u.id=r.user_id LEFT JOIN organizations o ON o.id=u.organization_id
                WHERE r.expires_at>? AND r.state IN ('verified','approved') ORDER BY r.created_at LIMIT 100""", (int(time.time()),)).fetchall()
        return {'requests': [dict(row) for row in rows]}

    @app.post('/admin/account-recoveries/{case_id}/review')
    def review_recovery(case_id: str, body: ReviewBody, request: Request, user=Depends(current_user)):
        admin(user)
        auth.rate(db, request, 'account-recovery-review', str(user['id']), limit=5)
        if body.decision == 'approve' and not body.ownership_verified:
            raise HTTPException(422, 'Kontoinhaberschaft muss unabhängig geprüft werden.')
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            reviewer = conn.execute('SELECT * FROM users WHERE id=?', (user['id'],)).fetchone()
            if not user['mfa_ok'] or not auth.check_totp(conn, reviewer, body.code):
                raise HTTPException(403, 'Aktueller Authenticator-Code des Platform Admin ist erforderlich.')
        decide(db, case_id, body.decision, body.reference, 'admin:' + str(user['id']), body.email)
        return {'ok': True}


def main():
    """Host access is the operator trust boundary when all platform admins are locked out."""
    parser = argparse.ArgumentParser(description='Reviewed account recovery for the trusted MH host operator')
    parser.add_argument('decision', choices=['list', 'approve', 'reject'])
    parser.add_argument('--case-id')
    parser.add_argument('--reference')
    args = parser.parse_args()
    from .stripe_test import ENV_FILE, read_env
    for name, value in read_env(ENV_FILE).items():
        os.environ.setdefault(name, value)
    from . import main as product
    product.init_db()
    if args.decision == 'list':
        with product.db() as conn:
            for case in conn.execute("SELECT id,email,state FROM account_recoveries WHERE state IN ('verified','approved') AND expires_at>?", (int(time.time()),)):
                print(case['id'], case['email'], case['state'])
        return
    if not args.case_id or not args.reference:
        parser.error('--case-id and --reference are required; reference a completed independent ownership check')
    email = input('Confirmed account email: ').strip().lower()
    if input('Ownership independently verified using established contact/company records? Type VERIFIED: ') != 'VERIFIED':
        raise SystemExit('No change made.')
    decide(product.db, args.case_id, args.decision, args.reference, 'host-operator', email)
    print('Review recorded. Approval sends a one-time link; no account credentials have been reset yet.')


if __name__ == '__main__':
    main()
