"""Isolated tests for real receipts, attribution, permissions and encrypted contacts."""
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from backend import main,auth
from backend.test_support import BrowserClient,session_headers


class TrackingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name)
        self.patches=[patch.object(main,'DB',root/'test.db'),patch.object(main,'DEMO_DB',root/'demo.db'),patch.object(main,'CREDENTIALS',root/'credentials.txt'),patch.object(auth,'KEY_FILE',root/'auth.key'),patch.object(auth,'deliver_message'),patch.dict(os.environ,{'MH_ENV':'development','MH_MAIL_MODE':'local','MH_PUBLIC_URL':'http://127.0.0.1:5181'})]
        for p in self.patches:p.start()
        main.init_db();self.client=BrowserClient(main.app)
        credentials=dict(line.split() for line in main.CREDENTIALS.read_text().splitlines()[1:])
        self.a=self.login('admin@mueller.local',credentials)
        self.b=self.login('admin@autohaus.local',credentials)
        self.admin=self.login('admin@flh.local',credentials)
        self.org=self.client.get('/organizations',headers=self.a).json()[0]['id']
        self.campaign=self.client.post('/campaigns',headers=self.a,json={'organization_id':self.org,'briefing':{'role':'Tracking fixture','location':'Berlin'}}).json()['id']
        self.path=f'/campaigns/{self.campaign}/tracking'
        self.client.post(f'/campaigns/{self.campaign}/generate',headers=self.a)
        self.client.patch(f'/campaigns/{self.campaign}',headers=self.a,json={'status':'Review'})
        self.client.patch(f'/campaigns/{self.campaign}',headers=self.a,json={'status':'Live'})
        self.page={'enabled':True,'contact_email':'recruiting@example.test','privacy_url':'https://example.test/privacy','retention_days':7}
        self.application={'name':'Fictional Applicant','email':'applicant@example.test','message':'Fixture only','request_id':'fixture_application_123456'}

    def tearDown(self):
        self.client.close()
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()

    def login(self,email,credentials):
        self.assertEqual(self.client.post('/auth/login',json={'email':email,'password':credentials[email]}).status_code,200)
        headers=session_headers(self.client);self.client.cookies.clear();return headers

    def enable(self):
        r=self.client.post(self.path+'/page',headers=self.a,json=self.page)
        self.assertEqual(r.status_code,200,r.text)

    def link(self,channel='LinkedIn',variant='A'):
        r=self.client.post(self.path+'/links',headers=self.a,json={'channel':channel,'variant':variant,'kind':'hosted'})
        self.assertEqual(r.status_code,201,r.text);return r.json()

    def report(self):
        r=self.client.get(self.path+'/report',headers=self.a)
        self.assertEqual(r.status_code,200,r.text);return r.json()

    def submit(self,body=None):
        return self.client.post(f'/tracking/apply/{self.campaign}',json=body or self.application)

    def test_public_page_requires_explicit_activation_and_approval(self):
        self.assertEqual(self.client.get(f'/tracking/apply/{self.campaign}').status_code,404)
        self.enable()
        self.assertEqual(self.client.get(f'/tracking/apply/{self.campaign}').json()['title'],'Tracking fixture')
        self.assertEqual(self.client.get(f'/tracking/apply/{self.campaign}').headers['cache-control'],'no-store')
        self.assertEqual(self.client.post(self.path+'/page',headers=self.b,json=self.page).status_code,404)
        self.assertEqual(self.client.post(self.path+'/page',headers=self.admin,json=self.page).status_code,403)
        with main.db() as conn:conn.execute("UPDATE projects SET status='Review' WHERE id=?",(self.campaign,))
        self.assertEqual(self.client.get(f'/tracking/apply/{self.campaign}').status_code,404)
        self.assertEqual(self.submit().status_code,404)
        self.assertEqual(self.client.post(self.path+'/page',headers=self.a,json=self.page).status_code,409)

    def test_stable_links_unknown_receipts_and_duplicate_submission(self):
        self.enable();a=self.link();b=self.link('Instagram','B')
        self.assertEqual(a['id'],self.link()['id'])
        r=self.client.get('/tracking/r/'+a['id'],follow_redirects=False)
        self.assertEqual(r.status_code,302)
        self.assertIn('?mh_link='+a['id'],r.headers['location'])
        self.assertEqual(self.report()['total'],0)
        body={**self.application,'link_id':a['id']}
        for _ in range(2):self.assertEqual(self.submit(body).status_code,201)
        self.assertEqual(self.submit({**body,'message':'Changed'}).status_code,409)
        self.assertEqual(self.submit({**self.application,'request_id':'fixture_application_unknown'}).status_code,201)
        self.assertEqual(self.submit({**self.application,'request_id':'fixture_application_variantB','link_id':b['id']}).status_code,201)
        r=self.report();self.assertEqual((r['total'],r['attributed'],r['unknown']),(3,2,1))
        counts={x['id']:x for x in r['links']};self.assertEqual(counts[a['id']]['hits'],1)
        self.assertEqual(counts[a['id']]['applications'],1);self.assertEqual(counts[b['id']]['applications'],1)
        with main.db() as conn:
            raw=conn.execute('SELECT payload FROM hosted_applications LIMIT 1').fetchone()[0]
            self.assertNotIn(self.application['email'],raw)
            self.assertNotIn(self.application['name'],raw)
        contacts=self.client.get(self.path+'/applications',headers=self.a).json()['applications']
        self.assertEqual(len(contacts),3);self.assertEqual(contacts[0]['contact']['email'],self.application['email'])

    def test_missing_connection_and_period_boundaries(self):
        r=self.report();self.assertFalse(r['connected']);self.assertIsNone(r['total'])
        self.enable();self.submit()
        self.assertEqual(self.client.get(self.path+'/report?start=2000-01-01&end=2000-01-02',headers=self.a).json()['total'],0)
        self.assertEqual(self.client.get(self.path+'/report?start=2026-09-30&end=2026-01-01',headers=self.a).status_code,422)

    def test_foreign_or_forged_links_and_extra_personal_fields_rejected(self):
        self.enable();self.link()
        self.assertEqual(self.submit({**self.application,'link_id':'forged_link_12345678901234'}).status_code,422)
        self.assertEqual(self.submit({**self.application,'cv':'private'}).status_code,422)
        self.assertEqual(self.submit({**self.application,'website':'bot'}).status_code,422)
        self.assertEqual(self.report()['total'],0)
        self.assertEqual(self.client.get(self.path+'/report',headers=self.b).status_code,404)
        self.assertEqual(self.client.get(self.path+'/applications',headers=self.b).status_code,404)
        with main.db() as conn:conn.execute("UPDATE users SET role='kunde' WHERE email='admin@mueller.local'")
        self.assertEqual(self.client.get(self.path+'/applications',headers=self.a).status_code,403)
        self.assertEqual(self.client.post(self.path+'/links',headers=self.a,json={'channel':'LinkedIn','variant':'A'}).status_code,403)

    def test_contacts_expire_without_erasing_anonymous_counts(self):
        self.enable();self.submit()
        with main.db() as conn:conn.execute('UPDATE hosted_applications SET expires_at=0')
        contacts=self.client.get(self.path+'/applications',headers=self.a).json()['applications']
        self.assertIsNone(contacts[0]['contact']);self.assertEqual(self.report()['total'],1)
        with main.db() as conn:self.assertEqual(conn.execute('SELECT payload FROM hosted_applications').fetchone()[0],'')

    def test_link_deactivation_and_demo_isolation(self):
        self.enable();link=self.link()
        r=self.client.patch(self.path+'/links/'+link['id'],headers=self.a,json={'active':False})
        self.assertEqual(r.status_code,200)
        self.assertEqual(self.client.get('/tracking/r/'+link['id'],follow_redirects=False).status_code,404)
        self.client.post('/demo/context',headers=self.admin,json={'role':'firmen_admin','organization_id':self.org})
        self.assertEqual(self.client.get(self.path+'/links',headers=self.admin).json()['links'],[])
        self.assertEqual(self.client.post(self.path+'/links',headers=self.admin,json={'channel':'LinkedIn','variant':'A'}).status_code,403)

    def test_receipt_connector_auth_deduplication_and_company_scope(self):
        key=self.client.post('/tracking/connector',headers=self.a,json={}).json()['key']
        headers={'Authorization':'Bearer '+key}
        body={'application_id':'ats_application_fixture','campaign_id':self.campaign,'received_at':int(time.time())}
        self.assertEqual(self.client.post('/tracking/receipts',json=body).status_code,401)
        self.assertEqual(self.client.post('/tracking/receipts',headers={**headers,'Origin':'https://other.test'},json=body).status_code,403)
        self.assertEqual(self.client.post('/tracking/receipts',headers=headers,json=body).status_code,200)
        self.assertTrue(self.client.post('/tracking/receipts',headers=headers,json=body).json()['duplicate'])
        self.assertEqual(self.report()['total'],1)
        otherkey=self.client.post('/tracking/connector',headers=self.b,json={}).json()['key']
        self.assertEqual(self.client.post('/tracking/receipts',headers={'Authorization':'Bearer '+otherkey},json=body).status_code,404)
        self.client.post('/tracking/connector',headers=self.a,json={})
        self.assertEqual(self.client.post('/tracking/receipts',headers=headers,json=body).status_code,401)

    def test_public_submission_requires_csrf_and_respects_rate_limit(self):
        self.enable()
        # BrowserClient normally adds CSRF. A raw independent client must not bypass it.
        from fastapi.testclient import TestClient
        raw=TestClient(main.app)
        self.assertEqual(raw.post(f'/tracking/apply/{self.campaign}',json=self.application).status_code,403)
        raw.close()
        for i in range(10):self.assertEqual(self.submit({**self.application,'request_id':f'fixture_rate_application_{i}'}).status_code,201)
        self.assertEqual(self.submit().status_code,429)

    def test_production_requires_privacy_notice(self):
        with main.db() as conn:
            conn.execute("UPDATE users SET mfa_secret='fixture-enabled' WHERE email='admin@mueller.local'")
            conn.execute('UPDATE sessions SET mfa_ok=1')
        with patch.dict(os.environ,{'MH_ENV':'production'}):
            self.assertEqual(self.client.post(self.path+'/page',headers=self.a,json={**self.page,'privacy_url':''}).status_code,422)

    def test_external_redirect_preserves_query_and_rejects_unsafe_destinations(self):
        for target in ('javascript:alert(1)','http://example.test','https://user:password@example.test','https://127.0.0.1/apply'):
            self.assertEqual(self.client.post(self.path+'/links',headers=self.a,json={'channel':'LinkedIn','variant':'A','kind':'external','destination':target}).status_code,422)
        link=self.client.post(self.path+'/links',headers=self.a,json={'channel':'LinkedIn','variant':'A','kind':'external','destination':'https://example.test/jobs?job=42&utm_source=old#apply'}).json()
        r=self.client.get('/tracking/r/'+link['id'],follow_redirects=False)
        self.assertIn('job=42',r.headers['location']);self.assertIn('utm_source=linkedin',r.headers['location']);self.assertIn('mh_link='+link['id'],r.headers['location']);self.assertTrue(r.headers['location'].endswith('#apply'))
