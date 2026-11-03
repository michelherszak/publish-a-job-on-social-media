"""Real cookie/CSRF and security flows against isolated local fixtures."""
from email import message_from_string
import os
from pathlib import Path
import re
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, unquote, urlparse
from fastapi.testclient import TestClient
from backend import main, auth


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patches = [patch.object(main, "DB", root / "test.db"), patch.object(main, "DEMO_DB", root / "demo.db"),
                        patch.object(main, "CREDENTIALS", root / "credentials.txt"), patch.object(auth, "OUTBOX", root / "outbox"),
                        patch.object(auth, "KEY_FILE", root / ".auth.key"), patch.dict(os.environ, {"MH_ENV":"development", "MH_MAIL_MODE":"local", "MH_PUBLIC_URL":"http://127.0.0.1:5181"})]
        for p in self.patches: p.start()
        main.init_db()
        self.client = TestClient(main.app)
        self.password = "a-long-security-test-password"

    def tearDown(self):
        self.client.close()
        for p in reversed(self.patches): p.stop()
        self.temp.cleanup()

    def post(self, path, body=None):
        csrf = self.client.get("/auth/csrf").json()["csrf"]
        return self.client.post(path, json=body or {}, headers={"X-CSRF-Token":csrf,"Origin":"http://127.0.0.1:5181"})

    def register(self):
        r = self.post("/auth/register", {"company":"Test Company", "name":"Jane Doe", "email":"jane@example.test",
                      "password":self.password, "country":"DE", "business":True})
        self.assertEqual(r.status_code, 201, r.text)
        return r

    def test_registration_and_recovery_use_browser_language(self):
        self.client.headers["Accept-Language"] = "en-GB"
        self.register()
        with main.db() as conn:
            self.assertEqual(conn.execute("SELECT email_language FROM users WHERE email='jane@example.test'").fetchone()[0], "en")
        message = message_from_string(sorted(auth.OUTBOX.glob("*.eml"))[-1].read_text())
        self.assertEqual(str(message["Subject"]), "MH: Verify your email")
        del self.client.headers["Accept-Language"]
        self.post("/auth/forgot", {"email":"jane@example.test"})
        message = message_from_string(sorted(auth.OUTBOX.glob("*.eml"))[-1].read_text())
        self.assertEqual(str(message["Subject"]), "MH: Reset your password")

    def token(self):
        message = message_from_string(sorted(auth.OUTBOX.glob("*.eml"))[-1].read_text())
        link = re.search(r"http[^\s]+", message.get_payload(decode=True).decode()).group()
        return parse_qs(urlparse(link).fragment)["token"][0]

    def verify(self):
        r = self.post("/auth/verify-email", {"token":self.token()})
        self.assertEqual(r.status_code, 200, r.text)

    def mfa_setup(self):
        self.register(); self.verify()
        secret = self.post("/auth/mfa/setup").json()["secret"]
        r = self.post("/auth/mfa/confirm", {"code":auth.totp(secret, int(time.time())//30)})
        self.assertEqual(r.status_code, 200, r.text)
        return secret, r.json()["recovery_codes"]

    def test_cookie_flags_no_session_token_in_json_and_bearer_rejected(self):
        r = self.register()
        self.assertNotIn("token", r.json())
        self.assertIn("HttpOnly", r.headers["set-cookie"])
        self.assertIn("SameSite=lax", r.headers["set-cookie"])
        token = self.client.cookies.get("mh_session")
        with main.db() as conn:
            self.assertIsNotNone(conn.execute("SELECT 1 FROM sessions WHERE token_hash=?", (auth.digest(token),)).fetchone())
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/auth/me", headers={"Authorization":"Bearer "+token}).status_code,401)

    def test_session_probe_handles_anonymous_valid_and_expired_sessions(self):
        response=self.client.get('/auth/session')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json(),{'authenticated':False,'user':None})
        self.assertEqual(self.client.get('/auth/me').status_code,401)
        self.register()
        response=self.client.get('/auth/session')
        self.assertTrue(response.json()['authenticated'])
        self.assertTrue(response.json()['user']['security_pending'])
        self.assertNotIn('csrf_hash',response.text)
        with main.db() as conn:conn.execute('UPDATE sessions SET expires_at=0')
        self.assertEqual(self.client.get('/auth/session').json(),{'authenticated':False,'user':None})
        self.assertEqual(self.client.get('/auth/me').status_code,401)

    def test_registration_works_without_stripe_but_gates_checkout_and_workspace(self):
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY":""}): self.register()
        self.assertEqual(self.client.get("/billing/status").status_code,403)
        self.assertEqual(self.client.get("/campaigns").status_code,403)
        self.assertFalse(self.client.get("/auth/me").json()["email_verified"])
        self.verify()
        self.assertEqual(self.client.get("/billing/status").status_code,403)
        self.assertTrue(self.client.get("/auth/me").json()["mfa_required"])

    def test_csrf_missing_bad_origin_and_session_binding(self):
        self.register()
        self.assertEqual(self.client.post("/auth/logout").status_code,403)
        token=self.client.get("/auth/csrf").json()["csrf"]
        self.assertEqual(self.client.post("/auth/logout", headers={"X-CSRF-Token":token,"Origin":"https://evil.example"}).status_code,403)
        with main.db() as conn:
            conn.execute("UPDATE sessions SET csrf_hash=?", (auth.digest("other"),))
        self.assertEqual(self.post("/auth/mfa/setup").status_code,403)

    def test_verification_is_hashed_single_use_and_expires(self):
        self.register(); token=self.token()
        with main.db() as conn:
            self.assertEqual(conn.execute("SELECT token_hash FROM auth_links").fetchone()[0],auth.digest(token))
        self.verify()
        self.assertEqual(self.post("/auth/verify-email",{"token":token}).status_code,400)

    def test_resend_invalidates_old_link_and_expired_link_rejected(self):
        self.register(); old=self.token()
        self.post("/auth/resend",{"email":"jane@example.test"}); new=self.token()
        self.assertNotEqual(old,new)
        self.assertEqual(self.post("/auth/verify-email",{"token":old}).status_code,400)
        with main.db() as conn: conn.execute("UPDATE auth_links SET expires_at=0")
        self.assertEqual(self.post("/auth/verify-email",{"token":new}).status_code,400)

    def test_reset_revokes_sessions_does_not_verify_email_and_no_auto_login(self):
        self.register()
        self.post("/auth/forgot",{"email":"jane@example.test"}); token=self.token()
        r=self.post("/auth/reset-password",{"token":token,"password":"the-new-secure-password"})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.client.get("/auth/me").status_code,401)
        self.assertEqual(self.post("/auth/reset-password",{"token":token,"password":self.password}).status_code,400)
        self.assertEqual(self.post("/auth/login",{"email":"jane@example.test","password":"the-new-secure-password"}).status_code,200)
        self.assertFalse(self.client.get("/auth/me").json()["email_verified"])

    def test_mfa_setup_uri_matches_seed_account_and_totp_parameters(self):
        self.register(); self.verify()
        # Reserved characters in an account label must not turn into URI delimiters.
        email = "jane+fixture&label@example.test"
        with main.db() as conn:
            conn.execute("UPDATE users SET email=? WHERE email='jane@example.test'", (email,))
        result = self.post("/auth/mfa/setup")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers["cache-control"], "no-store")
        data = result.json(); uri = urlparse(data["uri"]); query = parse_qs(uri.query)
        self.assertEqual(uri.scheme, "otpauth"); self.assertEqual(uri.netloc, "totp")
        issuer = "MH · 127.0.0.1 (5181)"
        self.assertEqual(data["website"], "http://127.0.0.1:5181")
        self.assertEqual(unquote(uri.path), "/" + issuer + ":" + email)
        self.assertEqual(query, {"secret":[data["secret"]], "issuer":[issuer], "algorithm":["SHA1"], "digits":["6"], "period":["30"]})
        with main.db() as conn:
            pending = conn.execute("SELECT mfa_pending,mfa_secret FROM users WHERE email=?", (email,)).fetchone()
            self.assertNotIn(data["secret"], pending[0]); self.assertFalse(pending[1])
            self.assertEqual(auth.cipher().decrypt(pending[0].encode()).decode(), data["secret"])
        code = auth.totp(query["secret"][0], int(time.time())//30)
        self.assertEqual(self.post("/auth/mfa/confirm", {"code":code}).status_code, 200)
        self.assertEqual(self.post("/auth/mfa/setup").status_code, 409)

    def test_authenticator_identity_uses_configured_website_and_login_email(self):
        # Public test seed only; the login email is the Authenticator account name.
        secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
        email = "jane+fixture&label@example.test"
        for website, issuer in [("http://127.0.0.1:5181", "MH · 127.0.0.1 (5181)"),
                                ("https://jobs.mh.example/", "MH · jobs.mh.example"),
                                ("https://jobs.mh.example:443", "MH · jobs.mh.example"),
                                ("http://[::1]:5181", "MH · ··1 (5181)")]:
            with self.subTest(website=website), patch.dict(os.environ, {"MH_PUBLIC_URL":website}):
                data = auth.authenticator_setup(email, secret)
                parsed = urlparse(data["uri"]); query = parse_qs(parsed.query)
                self.assertEqual(data["website"], website.rstrip("/"))
                self.assertEqual(unquote(parsed.path), "/" + issuer + ":" + email)
                self.assertEqual(query["issuer"], [issuer]); self.assertNotIn(":", issuer)
                self.assertEqual(query["secret"], [secret])

    def test_mfa_seed_encrypted_rotation_replay_and_recovery_once(self):
        old=None
        self.register(); self.verify(); old=self.client.cookies.get("mh_session")
        secret=self.post("/auth/mfa/setup").json()["secret"]
        code=auth.totp(secret,int(time.time())//30)
        r=self.post("/auth/mfa/confirm",{"code":code});self.assertEqual(r.status_code,200,r.text)
        codes=r.json()["recovery_codes"]
        self.assertNotEqual(old,self.client.cookies.get("mh_session"))
        with main.db() as conn:
            row=conn.execute("SELECT mfa_secret FROM users WHERE email='jane@example.test'").fetchone()
            self.assertNotIn(secret,row[0])
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM sessions WHERE token_hash=?",(auth.digest(old),)).fetchone()[0],0)
        self.post("/auth/logout")
        self.post("/auth/login",{"email":"jane@example.test","password":self.password})
        self.assertEqual(self.client.get("/billing/status").status_code,403)
        self.assertEqual(self.post("/auth/mfa/challenge",{"code":code}).status_code,400)
        self.assertEqual(self.post("/auth/mfa/challenge",{"code":codes[0]}).status_code,200)
        self.assertEqual(self.post("/auth/mfa/challenge",{"code":codes[0]}).status_code,400)

    def test_mfa_reset_requires_recovery_without_disabling_mfa(self):
        _,codes=self.mfa_setup()
        self.post("/auth/forgot",{"email":"jane@example.test"});token=self.token()
        self.assertEqual(self.post("/auth/reset-password",{"token":token,"password":"another-new-password"}).status_code,400)
        self.assertEqual(self.post("/auth/reset-password",{"token":token,"password":"another-new-password","recovery_code":codes[0]}).status_code,200)
        with main.db() as conn:
            self.assertTrue(conn.execute("SELECT mfa_secret FROM users WHERE email='jane@example.test'").fetchone()[0])

    def test_reconnect_qr_requires_one_use_recovery_and_never_unlocks_session(self):
        secret,codes=self.mfa_setup()
        self.post("/auth/logout")
        self.post("/auth/login",{"email":"jane@example.test","password":self.password})
        invalid=self.post("/auth/mfa/reconnect",{"code":"wrong-recovery-code"})
        self.assertEqual(invalid.status_code,400);self.assertNotIn(secret,invalid.text)
        result=self.post("/auth/mfa/reconnect",{"code":codes[0]})
        self.assertEqual(result.status_code,200);self.assertEqual(result.headers["cache-control"],"no-store")
        self.assertEqual(result.json()["secret"],secret)
        self.assertEqual(parse_qs(urlparse(result.json()["uri"]).query)["secret"],[secret])
        self.assertEqual(result.json(), auth.authenticator_setup("jane@example.test", secret))
        self.assertTrue(self.client.get("/auth/me").json()["security_pending"])
        self.assertEqual(self.client.get("/campaigns").status_code,403)
        self.assertEqual(self.post("/auth/mfa/reconnect",{"code":codes[0]}).status_code,400)
        self.assertEqual(self.post("/auth/mfa/setup").status_code,409)
        with main.db() as conn:
            row=conn.execute("SELECT * FROM users WHERE email='jane@example.test'").fetchone()
            self.assertEqual(auth.cipher().decrypt(row["mfa_secret"].encode()).decode(),secret)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM recovery_codes WHERE user_id=?",(row["id"],)).fetchone()[0],9)
        with patch("backend.auth.time.time",return_value=int(time.time())+60):
            code=auth.totp(secret,int(time.time())//30)
            self.assertEqual(self.post("/auth/mfa/challenge",{"code":code}).status_code,200)
        self.assertFalse(self.client.get("/auth/me").json()["security_pending"])

    def test_reconnect_is_account_bound_and_requires_verified_email_csrf_and_session(self):
        secret,codes=self.mfa_setup()
        self.assertEqual(self.client.post("/auth/mfa/reconnect",json={"code":codes[0]}).status_code,403)
        with main.db() as conn:
            conn.execute("UPDATE users SET email_verified=0 WHERE email='jane@example.test'")
        result=self.post("/auth/mfa/reconnect",{"code":codes[0]})
        self.assertEqual(result.status_code,403);self.assertNotIn(secret,result.text)
        with main.db() as conn:
            conn.execute("UPDATE users SET email_verified=1 WHERE email='jane@example.test'")
            foreign_id=conn.execute("SELECT id FROM users WHERE email='admin@flh.local'").fetchone()[0]
            conn.execute("INSERT INTO recovery_codes VALUES(?,?)",(foreign_id,auth.digest('foreign-account-recovery-fixture')))
        result=self.post("/auth/mfa/reconnect",{"code":"foreign-account-recovery-fixture"})
        self.assertEqual(result.status_code,400);self.assertNotIn(secret,result.text)
        with main.db() as conn:
            self.assertIsNotNone(conn.execute("SELECT 1 FROM recovery_codes WHERE user_id=?",(foreign_id,)).fetchone())
        for _ in range(3):
            self.assertEqual(self.post("/auth/mfa/reconnect",{"code":"wrong-recovery-code"}).status_code,400)
        self.assertEqual(self.post("/auth/mfa/reconnect",{"code":codes[0]}).status_code,429)
        self.post("/auth/logout")
        self.assertEqual(self.post("/auth/mfa/reconnect",{"code":codes[0]}).status_code,401)

    def test_enabled_mfa_is_enforced_for_non_admin_too(self):
        self.mfa_setup()
        with main.db() as conn:
            conn.execute("UPDATE users SET role='user' WHERE email='jane@example.test'")
        self.post("/auth/logout")
        self.post("/auth/login",{"email":"jane@example.test","password":self.password})
        self.assertTrue(self.client.get("/auth/me").json()["security_pending"])
        self.assertEqual(self.client.get("/campaigns").status_code,403)

    def test_login_rate_limit_and_generic_errors(self):
        for _ in range(10):
            self.assertEqual(self.post("/auth/login",{"email":"none@example.test","password":"bad"}).status_code,401)
        self.assertEqual(self.post("/auth/login",{"email":"none@example.test","password":"bad"}).status_code,429)

    def test_recovery_unknown_email_has_same_message(self):
        self.register()
        a=self.post("/auth/forgot",{"email":"jane@example.test"}).json()
        b=self.post("/auth/forgot",{"email":"none@example.test"}).json()
        self.assertEqual(a,b)

    def test_idle_session_expires_and_logout_revokes(self):
        self.register()
        with main.db() as conn: conn.execute("UPDATE sessions SET last_seen=?",(int(time.time())-1801,))
        self.assertEqual(self.client.get("/auth/me").status_code,401)
        self.post("/auth/login",{"email":"jane@example.test","password":self.password})
        self.assertEqual(self.post("/auth/logout").status_code,200)
        self.assertEqual(self.client.get("/auth/me").status_code,401)

    def test_invitation_role_scope_expiry_revoke_and_single_use(self):
        self.mfa_setup()
        with main.db() as conn:
            org=conn.execute("SELECT organization_id FROM users WHERE email='jane@example.test'").fetchone()[0]
            conn.execute("UPDATE billing_accounts SET status='active',plan='starter',period_end=? WHERE organization_id=?",(int(time.time())+3600,org))
        r=self.post("/auth/invitations",{"email":"team@example.test","role":"user"});self.assertEqual(r.status_code,201,r.text)
        token=self.token()
        self.assertEqual(self.post("/auth/accept-invite",{"token":token,"name":"Team Member","password":self.password}).status_code,200)
        self.assertEqual(self.post("/auth/accept-invite",{"token":token,"name":"Team Member","password":self.password}).status_code,400)
        with main.db() as conn:
            row=conn.execute("SELECT * FROM users WHERE email='team@example.test'").fetchone()
            self.assertEqual(row['organization_id'],org);self.assertEqual(row['role'],'user');self.assertEqual(row['email_verified'],1)
        self.post("/auth/invitations",{"email":"revoked@example.test","role":"kunde"});token=self.token()
        self.post("/auth/invitations/revoke",{"email":"revoked@example.test"})
        self.assertEqual(self.post("/auth/accept-invite",{"token":token,"name":"Team Member","password":self.password}).status_code,400)
        self.post("/auth/invitations",{"email":"expired@example.test","role":"kunde"});token=self.token()
        with main.db() as conn: conn.execute("UPDATE invitations SET expires_at=0")
        self.assertEqual(self.post("/auth/accept-invite",{"token":token,"name":"Team Member","password":self.password}).status_code,400)
        self.post("/auth/logout");self.post("/auth/login",{"email":"team@example.test","password":self.password})
        self.assertEqual(self.post("/auth/invitations",{"email":"foreign@example.test","role":"firmen_admin"}).status_code,403)

    def test_onboarding_checks_paid_profile_and_reviewed_draft(self):
        self.mfa_setup()
        self.assertEqual(self.post("/onboarding/complete").status_code,409)
        self.assertEqual(self.post("/onboarding/profile",{"industry":"Tech","location":"Berlin","brand_description":"Our company"}).status_code,200)
        with main.db() as conn:
            org=conn.execute("SELECT organization_id FROM users WHERE email='jane@example.test'").fetchone()[0]
            conn.execute("UPDATE billing_accounts SET status='active',plan='starter',period_end=? WHERE organization_id=?",(int(time.time())+3600,org))
            conn.execute("INSERT INTO projects(organization_id,role,location,status,generated,created_at,updated_at) VALUES(?,?,?,'Review',?,1,1)",(org,'Engineer','Berlin','{"jobAd":"A reviewed draft"}'))
        self.assertEqual(self.post("/onboarding/complete").status_code,200)
        self.assertTrue(self.client.get("/onboarding").json()["done"])

    def test_saved_brief_can_defer_onboarding_without_review_or_token_consumption(self):
        self.mfa_setup()
        with main.db() as conn:
            org = conn.execute("SELECT organization_id FROM users WHERE email='jane@example.test'").fetchone()[0]
            conn.execute("UPDATE billing_accounts SET status='active',plan='starter',included=250,period_end=? WHERE organization_id=?", (int(time.time())+3600, org))
        self.assertEqual(self.post('/onboarding/defer', {'campaign_id':9999}).status_code, 409)
        self.post('/onboarding/profile', {'industry':'Tech','location':'Berlin','brand_description':'Our company'})
        draft = self.post('/campaigns', {'organization_id':org,'briefing':{'role':'Engineer'}}).json()['id']
        for _ in range(2):
            self.assertEqual(self.post('/onboarding/defer', {'campaign_id':draft}).status_code, 200)
        state = self.client.get('/onboarding').json()
        self.assertTrue(state['deferred']); self.assertFalse(state['done'])
        self.assertEqual(state['campaign']['status'], 'Draft')
        self.assertEqual(state['campaign']['generated'], '{}')
        self.assertEqual(self.client.get('/tokens/wallet').json()['available'], 250)
        self.assertEqual(self.post('/onboarding/complete').status_code, 409)
        # Deferral survives a fresh sign-in, while authentication remains required.
        self.post('/auth/logout')
        self.assertEqual(self.client.get('/onboarding').status_code, 401)
        self.post('/auth/login', {'email':'jane@example.test','password':self.password})
        self.assertTrue(self.client.get('/onboarding').json()['deferred'])
        self.assertEqual(self.client.get('/campaigns').status_code, 403)

    def test_defer_requires_paid_profile_owned_brief_and_company_admin(self):
        self.register()
        self.assertEqual(self.post('/onboarding/defer', {'campaign_id':1}).status_code, 403)
        self.verify()
        secret = self.post('/auth/mfa/setup').json()['secret']
        self.post('/auth/mfa/confirm', {'code':auth.totp(secret,int(time.time())//30)})
        with main.db() as conn:
            org = conn.execute("SELECT organization_id FROM users WHERE email='jane@example.test'").fetchone()[0]
            other = conn.execute('SELECT id FROM organizations WHERE id!=? LIMIT 1', (org,)).fetchone()[0]
            foreign = conn.execute("INSERT INTO projects(organization_id,role,location,created_at,updated_at) VALUES(?,'Foreign draft','Berlin',1,1)", (other,)).lastrowid
        self.post('/onboarding/profile', {'industry':'Tech','location':'Berlin','brand_description':'Our company'})
        self.assertEqual(self.post('/onboarding/defer', {'campaign_id':foreign}).status_code, 409)
        with main.db() as conn:
            conn.execute("UPDATE billing_accounts SET status='active',plan='starter',included=250,period_end=? WHERE organization_id=?", (int(time.time())+3600,org))
        self.assertEqual(self.post('/onboarding/defer', {'campaign_id':foreign}).status_code, 409)
        draft = self.post('/campaigns', {'organization_id':org,'briefing':{'role':'Engineer'}}).json()['id']
        with main.db() as conn: conn.execute('UPDATE organizations SET profile_done=0 WHERE id=?', (org,))
        self.assertEqual(self.post('/onboarding/defer', {'campaign_id':draft}).status_code, 409)
        with main.db() as conn:
            conn.execute('UPDATE organizations SET profile_done=1 WHERE id=?', (org,))
            conn.execute("UPDATE users SET role='user' WHERE email='jane@example.test'")
        self.assertEqual(self.post('/onboarding/defer', {'campaign_id':draft}).status_code, 403)
        self.assertFalse(self.client.get('/onboarding').json()['deferred'])

    def test_production_cookie_is_secure_and_local_mail_forbidden(self):
        with patch.dict(os.environ,{"MH_ENV":"production"}):
            r=self.client.get("/auth/csrf")
            self.assertIn("Secure",r.headers["set-cookie"])
            self.assertIn("Strict-Transport-Security",r.headers)
            with self.assertRaises(Exception): auth.send_mail("test@example.test","Test","verify","token")


    def recovery_request(self):
        from backend import account_recovery
        result = self.post('/auth/recovery/request', {'email':'jane@example.test'})
        self.assertEqual(result.status_code, 200, result.text)
        proof = self.token()
        result = self.post('/auth/recovery/verify', {'token':proof})
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()['case_id'], proof

    def approve_recovery(self, case_id):
        from backend import account_recovery
        account_recovery.decide(main.db, case_id, 'approve', 'fixture-independent-contact-123', 'host-operator', 'jane@example.test')
        return self.token()

    def test_account_recovery_requires_mailbox_and_independent_review(self):
        from backend import account_recovery
        secret, codes = self.mfa_setup()
        result = self.post('/auth/recovery/request', {'email':'jane@example.test'})
        self.assertEqual(result.status_code, 200)
        proof = self.token()
        with main.db() as conn:
            case_id = conn.execute('SELECT id FROM account_recoveries').fetchone()[0]
            self.assertEqual(conn.execute('SELECT token_hash FROM auth_links WHERE kind=?', (account_recovery.VERIFY,)).fetchone()[0], auth.digest(proof))
        with self.assertRaises(Exception): self.approve_recovery(case_id)
        self.assertEqual(self.post('/auth/recovery/reset', {'token':proof,'password':self.password}).status_code,400)
        result = self.post('/auth/recovery/verify', {'token':proof})
        self.assertEqual(result.status_code,200)
        self.assertEqual(self.post('/auth/recovery/verify', {'token':proof}).status_code,400)
        with main.db() as conn:
            row=conn.execute("SELECT * FROM users WHERE email='jane@example.test'").fetchone()
            self.assertEqual(auth.cipher().decrypt(row['mfa_secret'].encode()).decode(),secret)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM recovery_codes WHERE user_id=?',(row['id'],)).fetchone()[0],10)
        grant=self.approve_recovery(case_id)
        self.assertNotEqual(grant,proof)
        self.assertTrue(self.client.get('/auth/me').json()['mfa_enabled'])
        self.assertEqual(self.post('/auth/recovery/reset', {'token':proof,'password':self.password}).status_code,400)

    def test_account_recovery_revokes_every_session_and_requires_fresh_mfa_for_nonadmins(self):
        old_secret, old_codes=self.mfa_setup()
        with main.db() as conn:conn.execute("UPDATE users SET role='user' WHERE email='jane@example.test'")
        case_id,_=self.recovery_request();grant=self.approve_recovery(case_id)
        result=self.post('/auth/recovery/reset',{'token':grant,'password':'replacement-security-password'})
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(self.client.get('/auth/me').status_code,401)
        self.assertEqual(self.post('/auth/recovery/reset',{'token':grant,'password':self.password}).status_code,400)
        self.assertEqual(self.post('/auth/login',{'email':'jane@example.test','password':self.password}).status_code,401)
        self.assertEqual(self.post('/auth/login',{'email':'jane@example.test','password':'replacement-security-password'}).status_code,200)
        self.assertTrue(self.client.get('/auth/me').json()['security_pending'])
        self.assertTrue(self.client.get('/auth/me').json()['mfa_required'])
        self.assertEqual(self.client.get('/campaigns').status_code,403)
        self.assertEqual(self.post('/auth/mfa/challenge',{'code':old_codes[0]}).status_code,400)
        new_secret=self.post('/auth/mfa/setup').json()['secret'];self.assertNotEqual(new_secret,old_secret)
        confirmed=self.post('/auth/mfa/confirm',{'code':auth.totp(new_secret,int(time.time())//30)})
        self.assertEqual(confirmed.status_code,200,confirmed.text)
        self.assertEqual(len(confirmed.json()['recovery_codes']),10)
        self.assertNotEqual(confirmed.json()['recovery_codes'],old_codes)
        self.assertFalse(self.client.get('/auth/me').json()['security_pending'])
        with main.db() as conn:
            self.assertEqual(conn.execute('SELECT state FROM account_recoveries WHERE id=?',(case_id,)).fetchone()[0],'consumed')
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM auth_links').fetchone()[0],0)

    def test_recovery_cancellation_rejection_expiry_and_account_change_invalidate_links(self):
        from backend import account_recovery
        self.mfa_setup();case_id,_=self.recovery_request();grant=self.approve_recovery(case_id)
        self.assertEqual(self.post('/auth/recovery/cancel',{'token':grant}).status_code,200)
        self.assertEqual(self.post('/auth/recovery/reset',{'token':grant,'password':self.password}).status_code,400)
        case_id,_=self.recovery_request()
        account_recovery.decide(main.db,case_id,'reject','fixture-case-123','host-operator','jane@example.test')
        with self.assertRaises(Exception):self.approve_recovery(case_id)
        case_id,_=self.recovery_request();old=self.approve_recovery(case_id);grant=self.approve_recovery(case_id)
        self.assertEqual(self.post('/auth/recovery/reset',{'token':old,'password':self.password}).status_code,400)
        with main.db() as conn:conn.execute('UPDATE auth_links SET expires_at=0')
        self.assertEqual(self.post('/auth/recovery/reset',{'token':grant,'password':self.password}).status_code,400)
        grant=self.approve_recovery(case_id)
        with main.db() as conn:conn.execute("UPDATE users SET password_hash=? WHERE email='jane@example.test'",(main.password_hash('independently-changed-password'),))
        self.assertEqual(self.post('/auth/recovery/reset',{'token':grant,'password':self.password}).status_code,400)

    def test_recovery_requests_are_generic_rate_limited_and_cannot_replace_verified_request(self):
        self.mfa_setup();case_id,_=self.recovery_request()
        eligible=self.post('/auth/recovery/request',{'email':'jane@example.test'})
        unknown=self.post('/auth/recovery/request',{'email':'absent@example.test'})
        self.assertEqual(eligible.json(),unknown.json())
        with main.db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM account_recoveries').fetchone()[0],1)
            self.assertEqual(conn.execute('SELECT state FROM account_recoveries WHERE id=?',(case_id,)).fetchone()[0],'verified')
        self.assertEqual(self.client.post('/auth/recovery/request',json={'email':'jane@example.test'}).status_code,403)
        self.assertEqual(self.post('/auth/recovery/request',{'email':'jane@example.test'}).status_code,200)
        self.assertEqual(self.post('/auth/recovery/request',{'email':'jane@example.test'}).status_code,429)
        self.assertEqual(self.client.get('/admin/account-recoveries').status_code,403)

    def test_recovery_admin_review_requires_real_admin_fresh_totp_and_ownership_attestation(self):
        self.mfa_setup();case_id,_=self.recovery_request()
        admin=TestClient(main.app)
        credentials=dict(line.split() for line in main.CREDENTIALS.read_text().splitlines()[1:])
        seed='JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP'
        with main.db() as conn:
            conn.execute("UPDATE users SET mfa_secret=? WHERE email='admin@flh.local'",(auth.cipher().encrypt(seed.encode()).decode(),))
        def post(path,body):
            csrf=admin.get('/auth/csrf').json()['csrf']
            return admin.post(path,json=body,headers={'X-CSRF-Token':csrf,'Origin':'http://127.0.0.1:5181'})
        self.assertEqual(post('/auth/login',{'email':'admin@flh.local','password':credentials['admin@flh.local']}).status_code,200)
        body={'decision':'approve','reference':'fixture-contact-check-123','email':'jane@example.test','ownership_verified':True,'code':auth.totp(seed,int(time.time())//30)}
        path='/admin/account-recoveries/'+case_id+'/review'
        self.assertEqual(post(path,body).status_code,403)
        self.assertEqual(post('/auth/mfa/challenge',{'code':body['code']}).status_code,200)
        rows=admin.get('/admin/account-recoveries').json()['requests'];self.assertEqual(rows[0]['id'],case_id)
        self.assertNotIn('fingerprint',rows[0])
        self.assertEqual(post(path,{**body,'ownership_verified':False}).status_code,422)
        self.assertEqual(post(path,body).status_code,403) # replayed sign-in code
        with main.db() as conn:conn.execute("UPDATE users SET mfa_last=-1 WHERE email='admin@flh.local'")
        self.assertEqual(post(path,body).status_code,200)
        self.assertEqual(admin.get('/admin/account-recoveries').json()['requests'][0]['state'],'approved')
        with main.db() as conn:conn.execute("UPDATE sessions SET view_role='platform_admin' WHERE user_id=(SELECT id FROM users WHERE email='admin@flh.local')")
        self.assertEqual(admin.get('/admin/account-recoveries').status_code,403)
        admin.close()

    def test_recovery_delivery_failure_can_resend_without_resetting_account(self):
        self.mfa_setup();case_id,_=self.recovery_request()
        with patch.object(auth,'send_mail',side_effect=auth.HTTPException(503,'fixture-mail-failure')):
            with self.assertRaises(Exception):self.approve_recovery(case_id)
        self.assertTrue(self.client.get('/auth/me').json()['mfa_enabled'])
        grant=self.approve_recovery(case_id)
        self.assertEqual(self.post('/auth/recovery/reset',{'token':grant,'password':self.password}).status_code,200)

    def test_recovery_host_operator_requires_explicit_independent_verification_and_no_self_review(self):
        import io
        from backend import account_recovery, stripe_test
        self.mfa_setup();case_id,_=self.recovery_request()
        with main.db() as conn:uid=conn.execute("SELECT id FROM users WHERE email='jane@example.test'").fetchone()[0]
        with self.assertRaises(auth.HTTPException) as error:
            account_recovery.decide(main.db,case_id,'approve','fixture-contact-check','admin:'+str(uid),'jane@example.test')
        self.assertEqual(error.exception.status_code,403)
        args=['account-recovery','approve','--case-id',case_id,'--reference','fixture-established-contact-123']
        with patch('sys.argv',args),patch.object(stripe_test,'read_env',return_value={}),patch('builtins.input',side_effect=['jane@example.test','NO']),patch('sys.stdout',new=io.StringIO()):
            with self.assertRaises(SystemExit):account_recovery.main()
        with main.db() as conn:self.assertEqual(conn.execute('SELECT state FROM account_recoveries WHERE id=?',(case_id,)).fetchone()[0],'verified')
        with patch('sys.argv',args),patch.object(stripe_test,'read_env',return_value={}),patch('builtins.input',side_effect=['jane@example.test','VERIFIED']),patch('sys.stdout',new=io.StringIO()):
            account_recovery.main()
        with main.db() as conn:self.assertEqual(conn.execute('SELECT state FROM account_recoveries WHERE id=?',(case_id,)).fetchone()[0],'approved')

    def test_recovery_mail_delivery_failure_has_same_public_response_as_unknown_account(self):
        self.mfa_setup()
        with patch.object(auth,'send_mail',side_effect=auth.HTTPException(503,'fixture-mail-failure')):
            known=self.post('/auth/recovery/request',{'email':'jane@example.test'})
            unknown=self.post('/auth/recovery/request',{'email':'absent@example.test'})
        self.assertEqual(known.status_code,200);self.assertEqual(known.json(),unknown.json())


class MailTemplateTests(unittest.TestCase):
    def test_bilingual_templates_and_language_priority(self):
        from backend import mail_templates
        from starlette.requests import Request
        for header, expected in [("en-GB,en;q=0.9,de;q=0.8", "en"), ("en;q=0.2,de-DE;q=0.9", "de"), ("fr,en;q=0", "de"), ("en;q=invalid,de", "de")]:
            request = Request({"type":"http", "headers":[(b"accept-language", header.encode())]})
            self.assertEqual(mail_templates.request_language(request), expected)
        de = mail_templates.previews("de")
        en = mail_templates.previews("en")
        self.assertEqual(len(en), 7)
        for original, translated in zip(de, en):
            self.assertNotEqual(original["subject"], translated["subject"])
            self.assertNotEqual(original["text"], translated["text"])
            self.assertEqual(original["content_type"], translated["content_type"])
            self.assertIn("https://preview.example.invalid/", translated["text"])
        self.assertIn("Verify your email", en[0]["subject"])
        self.assertIn("Reset your password", en[1]["subject"])
        self.assertIn("Invitation", en[2]["subject"])
        self.assertIn("We have received your payment", next(item for item in en if item['id']=='invoice')["text"])

    def test_auth_delivery_uses_preview_builder(self):
        from backend import auth, mail_templates
        with patch.object(auth, "deliver_message") as deliver, patch.dict(os.environ, {"MH_PUBLIC_URL":"https://mh.example", "MH_MAIL_FROM":"MH <sender@example.com>"}):
            auth.send_mail("recipient@example.com", "MH: E-Mail bestätigen", "verify", "fixture-token")
        actual=deliver.call_args.args[0]
        expected=mail_templates.auth_message("MH <sender@example.com>", "recipient@example.com", "MH: E-Mail bestätigen", "https://mh.example", "verify", "fixture-token")
        self.assertEqual(actual.as_string(),expected.as_string())
        self.assertIn('/auth#action=verify&token=fixture-token',actual.get_content())
