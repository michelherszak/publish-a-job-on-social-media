"""Local tenant and demo-isolation checks. Run with python3 -m unittest backend/test_security.py."""
import tempfile
import io
import os
import zipfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.test_support import BrowserClient as TestClient, session_headers
from backend import main


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.db_patch = patch.object(main, "DB", root / "test.db")
        self.demo_patch = patch.object(main, "DEMO_DB", root / "demo.db")
        self.credentials_patch = patch.object(main, "CREDENTIALS", root / "credentials.txt")
        self.settings_patch = patch.object(main, "INTEGRATION_SETTINGS", root / "integration_settings.json")
        self.mail_patch = patch.object(main.auth, "deliver_message")
        self.mail_patch.start()
        for item in (self.db_patch, self.demo_patch, self.credentials_patch, self.settings_patch):
            item.start()
        main.init_db()
        self.client = TestClient(main.app)
        credentials = dict(line.split() for line in main.CREDENTIALS.read_text().splitlines()[1:])
        self.admin = self.login("admin@flh.local", credentials)
        self.a = self.login("admin@mueller.local", credentials)
        self.b = self.login("admin@autohaus.local", credentials)

    def tearDown(self):
        self.client.close()
        self.mail_patch.stop()
        for item in (self.settings_patch, self.credentials_patch, self.demo_patch, self.db_patch):
            item.stop()
        self.temporary.cleanup()

    def login(self, email, credentials):
        response = self.client.post("/auth/login", json={"email": email, "password": credentials[email]})
        self.assertEqual(response.status_code, 200)
        headers = session_headers(self.client)
        self.client.cookies.clear()
        return headers

    def test_email_previews_are_admin_only_and_never_send(self):
        with patch.object(main.auth, "deliver_message") as send, patch.object(main.billing, "stripe_call") as stripe:
            self.assertEqual(self.client.get("/admin/email-previews").status_code,401)
            self.assertEqual(self.client.get("/admin/email-previews",headers=self.a).status_code,403)
            result=self.client.get("/admin/email-previews",headers=self.admin)
            self.assertEqual(result.status_code,200)
            rows=result.json()["previews"]
            self.assertEqual({row["id"] for row in rows},{"registration","password-reset","invitation","invoice","status-change","account-recovery-verify","account-recovery-reset"})
            self.assertEqual(result.headers["cache-control"],"no-store")
            for row in rows:
                self.assertEqual(row["content_type"],"text/plain")
                self.assertIn("example.invalid",row["sender"])
                self.assertIn("preview.example.invalid",row["text"])
            english = self.client.get("/admin/email-previews",headers={**self.admin,"Accept-Language":"en"})
            self.assertEqual(english.json()["previews"][0]["subject"],"MH: Verify your email")
            org=self.client.get("/organizations",headers=self.a).json()[0]["id"]
            self.client.post("/demo/context",headers=self.admin,json={"role":"firmen_admin","organization_id":org})
            self.assertEqual(self.client.get("/admin/email-previews",headers=self.admin).status_code,403)
            send.assert_not_called()
            stripe.assert_not_called()

    def status_campaign(self):
        org = self.client.get('/organizations',headers=self.a).json()[0]['id']
        campaign = self.client.post('/campaigns',headers=self.a,json={'organization_id':org,'briefing':{'role':'Status fixture','location':'Berlin'}}).json()['id']
        self.assertEqual(self.client.post(f'/campaigns/{campaign}/generate',headers=self.a).status_code,200)
        return org, campaign

    def test_status_mail_all_company_roles_languages_and_real_changes_only(self):
        org, campaign = self.status_campaign()
        with main.db() as conn:
            password = conn.execute('SELECT password_hash FROM users LIMIT 1').fetchone()[0]
            for email,role,language,verified in [('editor@example.test','user','en',1),('client@example.test','kunde','de',1),('unverified@example.test','user','en',0)]:
                conn.execute('INSERT INTO users(email,name,password_hash,role,organization_id,email_language,email_verified) VALUES(?,?,?,?,?,?,?)',(email,'Fixture',password,role,org,language,verified))
        delivery = main.auth.deliver_message
        delivery.reset_mock()
        self.assertEqual(self.client.patch(f'/campaigns/{campaign}',headers=self.a,json={'status':'Review'}).status_code,200)
        messages = [call.args[0] for call in delivery.call_args_list]
        self.assertEqual({str(message['To']) for message in messages},{'admin@mueller.local','editor@example.test','client@example.test'})
        english = next(message for message in messages if message['To']=='editor@example.test')
        self.assertEqual(english['Subject'],'MH: Campaign status changed')
        self.assertIn('Previous status: Draft',english.get_content())
        self.assertIn('New status: In review',english.get_content())
        german = next(message for message in messages if message['To']=='client@example.test')
        self.assertIn('Neuer Status: In Prüfung',german.get_content())
        count = delivery.call_count
        self.assertEqual(self.client.patch(f'/campaigns/{campaign}',headers=self.a,json={'status':'Review'}).status_code,200)
        self.assertEqual(self.client.patch(f'/campaigns/{campaign}',headers=self.a,json={'generated':{'jobAd':'Text edit'}}).status_code,200)
        self.assertEqual(delivery.call_count,count)
        self.assertEqual(self.client.patch(f'/campaigns/{campaign}',headers=self.a,json={'change_request':'Please revise'}).status_code,200)
        self.assertEqual(delivery.call_count,count+3)
        self.assertIn('New status: Draft',delivery.call_args_list[count+1].args[0].get_content())
        self.assertEqual(self.client.patch(f'/campaigns/{campaign}',headers=self.a,json={'status':'Review'}).status_code,200)
        self.assertEqual(self.client.patch(f'/campaigns/{campaign}',headers=self.a,json={'status':'Live'}).status_code,200)
        self.assertEqual(delivery.call_count,count+9)
        self.assertIn('Neuer Status: Freigegeben',delivery.call_args.args[0].get_content())
        self.assertEqual(self.client.patch(f'/campaigns/{campaign}',headers=self.b,json={'status':'Review'}).status_code,404)
        self.assertEqual(self.client.patch(f'/campaigns/{campaign}',headers=self.a,json={'status':'Draft'}).status_code,409)
        self.assertEqual(delivery.call_count,count+9)

    def test_status_mail_failure_retries_without_reverting_or_resending_success(self):
        from backend import status_mail
        org, campaign = self.status_campaign()
        delivery = main.auth.deliver_message
        delivery.side_effect = OSError('Mock transport unavailable')
        response = self.client.patch(f'/campaigns/{campaign}',headers=self.a,json={'status':'Review'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['status'],'Review')
        with main.db() as conn:
            row = conn.execute('SELECT state,attempts FROM status_deliveries WHERE project_id=?',(campaign,)).fetchone()
            self.assertEqual(tuple(row),('pending',1))
            conn.execute('UPDATE status_deliveries SET next_attempt=0 WHERE project_id=?',(campaign,))
        delivery.side_effect = None
        status_mail.drain(main.db)
        count = delivery.call_count
        status_mail.drain(main.db)
        self.assertEqual(delivery.call_count,count)
        with main.db() as conn:
            self.assertEqual(conn.execute('SELECT state FROM status_deliveries WHERE project_id=?',(campaign,)).fetchone()[0],'sent')

    def test_status_mail_demo_isolation_and_recipient_access_recheck(self):
        from backend import status_mail
        org, campaign = self.status_campaign()
        self.client.post('/demo/context',headers=self.admin,json={'role':'firmen_admin','organization_id':org})
        delivery = main.auth.deliver_message
        delivery.reset_mock()
        self.assertEqual(self.client.patch(f'/campaigns/{campaign}',headers=self.admin,json={'status':'Review'}).status_code,200)
        delivery.assert_not_called()
        with main.db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM status_deliveries').fetchone()[0],0)
            project = conn.execute('SELECT * FROM projects WHERE id=?',(campaign,)).fetchone()
            actor = conn.execute("SELECT id FROM users WHERE email='admin@mueller.local'").fetchone()[0]
            status_mail.queue(conn,project,'Draft','Review',actor,'fixture-event')
            status_mail.queue(conn,project,'Draft','Review',actor,'fixture-event')
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM status_deliveries').fetchone()[0],1)
            conn.execute('UPDATE users SET email_verified=0 WHERE id=?',(actor,))
        status_mail.drain(main.db)
        delivery.assert_not_called()
        with main.db() as conn:
            self.assertEqual(conn.execute('SELECT state FROM status_deliveries').fetchone()[0],'cancelled')

    def test_company_data_is_scoped(self):
        org_a = self.client.get("/organizations", headers=self.a).json()[0]["id"]
        org_b = self.client.get("/organizations", headers=self.b).json()[0]["id"]
        briefing = {"role": "Testrolle", "location": "Berlin", "channels": ["Website"]}
        response = self.client.post("/campaigns", headers=self.a, json={"organization_id": org_a, "briefing": briefing})
        self.assertEqual(response.status_code, 201)
        campaign_id = response.json()["id"]
        self.assertEqual(self.client.get(f"/campaigns/{campaign_id}", headers=self.b).status_code, 404)
        self.assertEqual(self.client.post("/campaigns", headers=self.b, json={"organization_id": org_a, "briefing": briefing}).status_code, 404)
        self.assertEqual(self.client.patch(f"/campaigns/{campaign_id}", headers=self.b, json={"status": "Review"}).status_code, 404)
        self.assertEqual(self.client.post(f"/campaigns/{campaign_id}/generate", headers=self.b).status_code, 404)
        self.assertEqual(self.client.get("/campaigns", headers=self.b).json(), [])
        self.assertEqual(self.client.get("/organizations", headers=self.b).json()[0]["id"], org_b)
        self.assertEqual(self.client.post("/users", headers=self.b, json={"email":"foreign@example.com","name":"Foreign","password":"a-long-password","role":"user","organization_id":org_a}).status_code, 404)

    def test_role_preview_does_not_change_primary_data(self):
        org_a = self.client.get("/organizations", headers=self.a).json()[0]["id"]
        response = self.client.post("/demo/context", headers=self.admin, json={"role": "firmen_admin", "organization_id": org_a})
        self.assertEqual(response.status_code, 200)
        briefing = {"role": "Nur Demo", "location": "Berlin", "channels": ["Website"]}
        response = self.client.post("/campaigns", headers=self.admin, json={"organization_id": org_a, "briefing": briefing})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(self.client.get("/campaigns", headers=self.admin).json()), 1)
        self.assertEqual(self.client.get("/campaigns", headers=self.a).json(), [])
        self.assertEqual(self.client.post("/demo/context", headers=self.admin, json={"role": "kunde", "organization_id": org_a}).status_code, 200)
        self.assertEqual(self.client.get("/campaigns", headers=self.admin).json(), [])
        self.assertEqual(self.client.post("/demo/context", headers=self.admin, json={"role": "user", "organization_id": org_a}).status_code, 200)
        self.assertEqual(len(self.client.get("/campaigns", headers=self.admin).json()), 1)
        self.assertEqual(self.client.post("/demo/context", headers=self.admin, json={"role": "platform_admin"}).status_code, 200)
        self.assertEqual(self.client.get("/campaigns", headers=self.admin).json(), [])

    def test_only_company_admin_and_company_user_can_approve(self):
        org_a = self.client.get("/organizations", headers=self.a).json()[0]["id"]
        org_b = self.client.get("/organizations", headers=self.b).json()[0]["id"]
        for headers, email, org_id in ((self.a, "user-a@example.com", org_a), (self.b, "user-b@example.com", org_b)):
            response = self.client.post("/users", headers=headers, json={"email": email, "name": email, "password": "a-long-test-password", "role": "user", "organization_id": org_id})
            self.assertEqual(response.status_code, 201)
        user_a = self.login("user-a@example.com", {"user-a@example.com": "a-long-test-password"})
        user_b = self.login("user-b@example.com", {"user-b@example.com": "a-long-test-password"})
        briefing = {"role": "Elektriker", "location": "Berlin", "channels": ["Website"]}
        response = self.client.post("/campaigns", headers=self.a, json={"organization_id": org_a, "briefing": briefing})
        self.assertEqual(response.status_code, 201)
        campaign_id = response.json()["id"]
        self.assertEqual(self.client.post(f"/campaigns/{campaign_id}/generate", headers=self.a).status_code, 200)
        self.assertEqual(self.client.patch(f"/campaigns/{campaign_id}", headers=self.a, json={"status": "Review"}).status_code, 200)
        self.assertEqual(self.client.patch(f"/campaigns/{campaign_id}", headers=self.admin, json={"status": "Live"}).status_code, 403)
        self.assertEqual(self.client.patch(f"/campaigns/{campaign_id}", headers=self.admin, json={"change_request": "Bitte ändern"}).status_code, 403)
        self.assertEqual(self.client.patch(f"/campaigns/{campaign_id}", headers=user_b, json={"status": "Live"}).status_code, 404)
        self.assertEqual(self.client.patch(f"/campaigns/{campaign_id}", headers=user_a, json={"status": "Live"}).status_code, 200)

    def test_integration_keys_are_role_and_company_scoped(self):
        admin_settings = self.client.get("/settings/integrations", headers=self.admin)
        self.assertEqual([item["provider"] for item in admin_settings.json()], ["openai"])
        company_settings = self.client.get("/settings/integrations", headers=self.a)
        self.assertEqual([item["provider"] for item in company_settings.json()], ["meta", "linkedin", "xing"])
        response = self.client.put("/settings/integrations/openai", headers=self.admin, json={"api_key":"test-local-secret","model":"local-test-model"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("test-local-secret", response.text)
        self.assertNotIn("test-local-secret", self.client.get("/settings/integrations", headers=self.admin).text)
        self.assertEqual(os.stat(main.INTEGRATION_SETTINGS).st_mode & 0o777, 0o600)
        self.assertEqual(self.client.put("/settings/integrations/openai", headers=self.a, json={"api_key":"foreign"}).status_code, 403)
        self.assertEqual(self.client.put("/settings/integrations/xing", headers=self.admin, json={"api_key":"global"}).status_code, 403)
        response = self.client.put("/settings/integrations/xing", headers=self.a, json={"api_key":"company-a-secret"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("company-a-secret", response.text)
        self.assertTrue(next(item for item in self.client.get("/settings/integrations", headers=self.a).json() if item["provider"] == "xing")["configured"])
        self.assertFalse(next(item for item in self.client.get("/settings/integrations", headers=self.b).json() if item["provider"] == "xing")["configured"])
        self.assertNotIn("company-a-secret", self.client.get("/settings/integrations", headers=self.a).text)
        org_a = self.client.get("/organizations", headers=self.a).json()[0]["id"]
        self.assertEqual(self.client.post("/demo/context", headers=self.admin, json={"role":"firmen_admin","organization_id":org_a}).status_code, 200)
        self.assertEqual(self.client.put("/settings/integrations/xing", headers=self.admin, json={"api_key":"demo-only-secret"}).status_code, 200)
        self.assertEqual(self.client.post("/demo/context", headers=self.admin, json={"role":"platform_admin"}).status_code, 200)
        with main.db() as conn:
            stored = conn.execute("SELECT api_key FROM integration_credentials WHERE organization_id=? AND provider='xing'", (org_a,)).fetchone()[0]
        self.assertEqual(stored, "company-a-secret")
        self.assertEqual(self.client.delete("/settings/integrations/xing", headers=self.a).status_code, 200)
        self.assertFalse(next(item for item in self.client.get("/settings/integrations", headers=self.a).json() if item["provider"] == "xing")["configured"])
        self.assertEqual(self.client.delete("/settings/integrations/openai", headers=self.admin).status_code, 200)
        self.assertFalse(self.client.get("/settings/integrations", headers=self.admin).json()[0]["configured"])

    def test_profile_history_export_metrics_and_read_only_customer(self):
        org_a = self.client.get("/organizations", headers=self.a).json()[0]["id"]
        profile = {"industry":"Handwerk","location":"Berlin","brand_description":"Familienbetrieb","benefits":"Flexible Zeiten","tone":"Freundlich","contact_name":"Testkontakt","contact_email":"kontakt@example.com","website":"https://example.com"}
        self.assertEqual(self.client.patch(f"/organizations/{org_a}", headers=self.a, json=profile).status_code, 403)
        response = self.client.patch(f"/organizations/{org_a}", headers=self.admin, json=profile)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["benefits"], "Flexible Zeiten")
        briefing = {"role":"Elektriker","location":"Berlin","channels":["Website"]}
        response = self.client.post("/campaigns", headers=self.a, json={"organization_id":org_a,"briefing":briefing})
        self.assertEqual(response.status_code, 201)
        campaign_id = response.json()["id"]
        for endpoint in ("history", "metrics", "creative.svg", "export"):
            self.assertEqual(self.client.get(f"/campaigns/{campaign_id}/{endpoint}", headers=self.b).status_code, 404)
        self.assertEqual(self.client.put(f"/campaigns/{campaign_id}/metrics", headers=self.b, json={"channel":"Website","impressions":1,"clicks":1,"applications":0}).status_code, 404)
        generated = self.client.post(f"/campaigns/{campaign_id}/generate", headers=self.a)
        self.assertEqual(generated.status_code, 200)
        self.assertEqual(set(generated.json()["generated"]), {"jobAd", "social", "meta"})
        self.assertEqual(self.client.post(f"/campaigns/{campaign_id}/comments", headers=self.b, json={"channel":"jobAd","message":"Foreign"}).status_code, 404)
        self.assertEqual(self.client.post(f"/campaigns/{campaign_id}/comments", headers=self.a, json={"channel":"jobAd","message":"Bitte prüfen"}).status_code, 201)
        self.assertEqual(self.client.patch(f"/campaigns/{campaign_id}", headers=self.a, json={"status":"Review"}).status_code, 200)
        self.assertEqual(self.client.patch(f"/campaigns/{campaign_id}", headers=self.a, json={"status":"Live"}).status_code, 200)
        actions = [item["action"] for item in self.client.get(f"/campaigns/{campaign_id}/history", headers=self.a).json()]
        self.assertTrue({"created","generated","commented","submitted","approved"}.issubset(actions))
        response = self.client.put(f"/campaigns/{campaign_id}/metrics", headers=self.a, json={"channel":"Website","impressions":100,"clicks":12,"applications":2,"source":"Manual report"})
        self.assertEqual(response.status_code, 200)
        analytics = self.client.get("/analytics", headers=self.a).json()
        self.assertEqual((analytics["impressions"], analytics["clicks"], analytics["applications"]), (100,12,2))
        self.assertEqual(self.client.get("/analytics", headers=self.b).json()["applications"], 0)
        response = self.client.get(f"/campaigns/{campaign_id}/export", headers=self.a)
        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(response.content)) as package:
            self.assertTrue({"briefing.json","creative.svg","content/jobAd.txt","content/social.txt","content/meta.txt"}.issubset(package.namelist()))
            self.assertFalse({"content/linkedin.txt","content/xing.txt","content/video.txt"} & set(package.namelist()))
        self.assertEqual(self.client.get(f"/campaigns/{campaign_id}/creative.svg", headers=self.a).status_code, 200)
        with main.db() as conn:
            conn.execute("INSERT INTO users(email,name,password_hash,role,organization_id) VALUES(?,?,?,?,?)", ("kunde@example.com","Kunde",main.password_hash("long-test-password"),"kunde",org_a))
        customer = self.login("kunde@example.com", {"kunde@example.com":"long-test-password"})
        self.assertEqual(self.client.get(f"/campaigns/{campaign_id}", headers=customer).status_code, 200)
        self.assertEqual(self.client.put(f"/campaigns/{campaign_id}/metrics", headers=customer, json={"channel":"Website","impressions":1,"clicks":1,"applications":0}).status_code, 403)

    def test_platform_admin_can_delete_a_customer(self):
        created = self.client.post("/organizations", headers=self.admin, json={"name": "Löschbar GmbH", "industry": "Test", "location": "Berlin"})
        self.assertEqual(created.status_code, 201)
        org_id = created.json()["id"]
        password = "a-long-test-password"
        self.assertEqual(self.client.post("/users", headers=self.admin, json={"email": "gone@example.com", "name": "Weg Nutzer", "password": password, "role": "user", "organization_id": org_id}).status_code, 201)
        campaign = self.client.post("/campaigns", headers=self.admin, json={"organization_id": org_id, "briefing": {"role": "Tester", "location": "Berlin", "channels": ["Website"]}})
        self.assertEqual(campaign.status_code, 201)
        campaign_id = campaign.json()["id"]
        self.assertEqual(self.client.post(f"/campaigns/{campaign_id}/comments", headers=self.admin, json={"channel": "jobAd", "message": "Hinweis"}).status_code, 201)
        self.assertEqual(self.client.put(f"/campaigns/{campaign_id}/metrics", headers=self.admin, json={"channel": "Website", "impressions": 3, "clicks": 1, "applications": 0}).status_code, 200)
        kept = self.client.get("/organizations", headers=self.a).json()[0]["id"]
        self.assertEqual(self.client.request("DELETE", f"/organizations/{org_id}", json={"confirmation_name": "Löschbar GmbH"}, headers=self.a).status_code, 403)
        self.assertEqual(self.client.request("DELETE", "/organizations/999999", json={"confirmation_name": "Löschbar GmbH"}, headers=self.admin).status_code, 404)
        self.assertEqual(self.client.post("/demo/context", headers=self.admin, json={"role": "firmen_admin", "organization_id": kept}).status_code, 200)
        self.assertEqual(self.client.request("DELETE", f"/organizations/{org_id}", json={"confirmation_name": "Löschbar GmbH"}, headers=self.admin).status_code, 403)
        self.assertEqual(self.client.post("/demo/context", headers=self.admin, json={"role": "platform_admin"}).status_code, 200)
        with main.db() as conn:
            conn.execute("INSERT INTO integration_credentials(organization_id,provider,api_key,updated_at) VALUES(?,?,?,?)", (org_id, "xing", "secret", 1))
            conn.execute("INSERT INTO invitations(token_hash,organization_id,email,role,expires_at) VALUES(?,?,?,?,?)", ("hash", org_id, "invite@example.com", "user", 1))
        preview = self.client.get(f"/organizations/{org_id}/deletion-preview", headers=self.admin)
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json()["name"], "Löschbar GmbH")
        self.assertEqual(preview.json()["counts"]["users"], 1)
        self.assertEqual(preview.json()["counts"]["campaigns"], 1)
        self.assertEqual(preview.json()["counts"]["invitations"], 1)
        self.assertFalse(preview.json()["billing_blocked"])
        self.assertEqual(self.client.request("DELETE", f"/organizations/{org_id}", json={"confirmation_name": "Löschbar GmbH"}, headers=self.admin).status_code, 200)
        listed = self.client.get("/organizations", headers=self.admin).json()
        self.assertNotIn("Löschbar GmbH", [item["name"] for item in listed])
        self.assertTrue(any(item["id"] == kept for item in listed))
        self.assertEqual(self.client.get(f"/campaigns/{campaign_id}", headers=self.admin).status_code, 404)
        self.assertEqual(self.client.post("/auth/login", json={"email": "gone@example.com", "password": password}).status_code, 401)
        with main.db() as conn:
            self.assertIsNone(conn.execute("SELECT 1 FROM campaign_metrics WHERE project_id=?", (campaign_id,)).fetchone())
            for table, column in (
                ("users", "organization_id"), ("projects", "organization_id"), ("activity", "organization_id"),
                ("campaign_history", "organization_id"), ("integration_credentials", "organization_id"),
                ("billing_accounts", "organization_id"), ("token_ledger", "organization_id"),
                ("invitations", "organization_id"), ("organizations", "id"),
            ):
                self.assertIsNone(conn.execute(f"SELECT 1 FROM {table} WHERE {column}=?", (org_id,)).fetchone(), table)
            self.assertIsNotNone(conn.execute("SELECT 1 FROM users WHERE email='admin@flh.local'").fetchone())

    def test_billing_customer_cannot_be_deleted_or_cancelled_remotely(self):
        org_id = self.client.post("/organizations", headers=self.admin, json={"name":"Stripe GmbH"}).json()["id"]
        with main.db() as conn:
            conn.execute("INSERT INTO billing_accounts(organization_id,customer,subscription,country,mode,status) VALUES(?,?,?,?,?,?)", (org_id,"cus_fixture","sub_fixture","DE","test","active"))
        with patch.object(main.billing, "stripe_call") as stripe:
            preview = self.client.get(f"/organizations/{org_id}/deletion-preview", headers=self.admin)
            result = self.client.request("DELETE", f"/organizations/{org_id}", headers=self.admin, json={"confirmation_name":"Stripe GmbH"})
        self.assertTrue(preview.json()["billing_blocked"])
        self.assertEqual(preview.json()["billing_records"]["billing_accounts"], 1)
        self.assertEqual(result.status_code,409)
        stripe.assert_not_called()
        with main.db() as conn:
            self.assertIsNotNone(conn.execute("SELECT 1 FROM organizations WHERE id=?",(org_id,)).fetchone())
            self.assertIsNotNone(conn.execute("SELECT 1 FROM billing_accounts WHERE organization_id=?",(org_id,)).fetchone())

    def test_deletion_confirmation_csrf_and_seed_persistence(self):
        org = self.client.get("/organizations",headers=self.a).json()[0]
        path = f"/organizations/{org['id']}"
        self.assertEqual(self.client.request("DELETE",path,headers=self.admin,json={"confirmation_name":"wrong"}).status_code,409)
        self.assertEqual(self.client.request("DELETE",path,headers={**self.admin,"X-CSRF-Token":"invalid"},json={"confirmation_name":org['name']}).status_code,403)
        self.assertEqual(self.client.request("DELETE",path,headers=self.admin,json={"confirmation_name":org['name']}).status_code,200)
        self.assertEqual(self.client.get("/auth/me",headers=self.a).status_code,401)
        main.init_db()
        self.assertNotIn(org['name'],[o['name'] for o in self.client.get("/organizations",headers=self.admin).json()])
        with main.db() as conn:
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(),[])

    def test_security_headers_and_bounded_input(self):
        response = self.client.get("/health")
        self.assertEqual(response.headers['x-frame-options'],'DENY')
        self.assertIn("frame-ancestors 'none'",response.headers['content-security-policy'])
        response = self.client.post("/organizations",headers=self.admin,json={"name":"Bounded", "industry":"x"*161})
        self.assertEqual(response.status_code,422)
        response = self.client.post("/auth/login",content=b'x'*(1024*1024+1))
        self.assertEqual(response.status_code,413)
        self.assertEqual(response.headers['cache-control'],'no-store')


class RequestLimitTests(unittest.IsolatedAsyncioTestCase):
    async def test_chunked_body_rejected_before_app_is_called(self):
        from backend.security import RequestSizeLimit
        from unittest.mock import AsyncMock
        app = AsyncMock()
        receive = AsyncMock(side_effect=[
            {"type":"http.request", "body":b"12345", "more_body":True},
            {"type":"http.request", "body":b"67890", "more_body":False},
        ])
        send = AsyncMock()
        await RequestSizeLimit(app, maximum=8)({"type":"http","headers":[]}, receive, send)
        app.assert_not_called()
        self.assertEqual(send.call_args_list[0].args[0]["status"],413)

    async def test_webhook_bytes_are_preserved(self):
        from backend.security import RequestSizeLimit
        from unittest.mock import AsyncMock
        body = b'{ "signed": "exact bytes" }'
        received = []
        async def app(scope, receive, send):
            received.append((await receive())["body"])
        receive = AsyncMock(side_effect=[{"type":"http.request", "body":body[:5], "more_body":True}, {"type":"http.request", "body":body[5:], "more_body":False}])
        await RequestSizeLimit(app)({"type":"http","headers":[]}, receive, AsyncMock())
        self.assertEqual(received,[body])


if __name__ == "__main__":
    unittest.main()
