"""Offline publication safety tests. No real accounts, posts, mail or payments."""
import io
import os
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch, MagicMock

from backend import main, auth, social
from backend.test_support import BrowserClient, session_headers


class SocialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.patches = [patch.object(main, 'DB', root/'db'), patch.object(main, 'DEMO_DB', root/'demo'), patch.object(main, 'CREDENTIALS', root/'credentials'), patch.object(auth, 'KEY_FILE', root/'key'), patch.object(auth, 'deliver_message'), patch.dict(os.environ, {'MH_ENV':'development', 'MH_MAIL_MODE':'local', 'MH_PUBLIC_URL':'https://mh.example.com', 'MH_META_APP_ID':'123', 'MH_META_APP_SECRET':'fixture_app_secret', 'MH_META_CALLBACK_URL':'https://mh.example.com/api/social/meta/callback', 'MH_META_GRAPH_VERSION':'v25.0'})]
        for p in self.patches: p.start()
        self.provider_patch = patch.object(social, 'graph', side_effect=self.provider)
        self.provider = self.provider_patch.start()
        self.calls = []
        self.permissions = social.FACEBOOK_SCOPES | social.INSTAGRAM_SCOPES
        self.expires = 3600
        main.init_db()
        self.client = BrowserClient(main.app)
        self.passwords = dict(line.split() for line in main.CREDENTIALS.read_text().splitlines()[1:])
        self.a = self.login('admin@mueller.local')
        self.b = self.login('admin@autohaus.local')
        self.admin = self.login('admin@flh.local')
        self.org = self.client.get('/organizations', headers=self.a).json()[0]['id']
        self.project = self.client.post('/campaigns', headers=self.a, json={'organization_id':self.org,'briefing':{'role':'Fixture Electrician','location':'Berlin'}}).json()['id']
        self.client.post(f'/campaigns/{self.project}/generate', headers=self.a)
        self.client.patch(f'/campaigns/{self.project}', headers=self.a, json={'status':'Review'})
        self.client.patch(f'/campaigns/{self.project}', headers=self.a, json={'status':'Live'})
        self.client.post(f'/campaigns/{self.project}/tracking/page', headers=self.a, json={'enabled':True,'contact_email':'fixture@example.test','privacy_url':'https://mh.example.com/privacy','retention_days':7})
        self.link = self.client.post(f'/campaigns/{self.project}/tracking/links', headers=self.a, json={'channel':'Facebook','variant':'A'}).json()['id']
        self.path = f'/campaigns/{self.project}/social/facebook'

    def tearDown(self):
        self.client.close()
        self.provider_patch.stop()
        for p in reversed(self.patches): p.stop()
        self.tmp.cleanup()

    def login(self, email):
        self.assertEqual(self.client.post('/auth/login', json={'email':email,'password':self.passwords[email]}).status_code, 200)
        headers = session_headers(self.client)
        self.client.cookies.clear()
        return headers

    def provider(self, method, path, token='', data=None):
        self.calls.append((method,path,data))
        if path == 'oauth/access_token': return {'access_token':'fixture_user_token','expires_in':self.expires}
        if path == 'me/permissions': return {'data':[{'permission':p,'status':'granted'} for p in self.permissions]}
        if path == 'me/accounts':
            return {'data':[{'id':'444','name':'Fixture Company Page','access_token':'fixture_page_token','tasks':['CREATE_CONTENT'], 'instagram_business_account':{'id':'555','username':'fixture_ig'}}]}
        if path == '444/feed': return {'id':'444_777'}
        if path == '444_777':
            with main.db() as conn:
                message = conn.execute('SELECT message FROM social_publications WHERE project_id=?', (self.project,)).fetchone()[0]
            return {'id':'444_777','message':message}
        raise AssertionError('Unexpected provider endpoint')

    def begin(self, instagram=False):
        response = self.client.post('/social/meta/connect', headers=self.a, json={'instagram':instagram})
        self.assertEqual(response.status_code,200,response.text)
        return parse_qs(urlsplit(response.json()['url']).query)['state'][0]

    def callback(self, state, headers=None, **params):
        return self.client.get('/social/meta/callback', headers=headers or self.a, params={'state':state,'code':'fixture_code',**params}, follow_redirects=False)

    def connect(self, instagram=False):
        state = self.begin(instagram)
        self.assertEqual(self.callback(state).headers['location'], 'https://mh.example.com/app?social=select')
        selected = self.client.post('/social/meta/page', headers=self.a, json={'page_id':'444'})
        self.assertEqual(selected.status_code,200,selected.text)

    def test_meta_link_uses_the_shared_mh_application_page(self):
        self.connect()
        with main.db() as conn:
            conn.execute("UPDATE ad_links SET channel='Meta' WHERE id=?", (self.link,))
        result = self.preview()
        self.assertEqual(result['state'], 'preview')
        self.assertIn('/r/', result['link_url'])

    def preview(self):
        response = self.client.post(self.path+'/preview', headers=self.a, json={'message':'Join our fixture team','link_id':self.link})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    def publish(self, preview, headers=None):
        return self.client.post(self.path+'/publish', headers=headers or self.a, json={'preview_id':preview['id'],'confirmed':True})

    def test_configuration_fails_closed_without_domain_or_app(self):
        with patch.dict(os.environ, {'MH_PUBLIC_URL':'http://localhost:5181','MH_META_APP_ID':'','MH_META_APP_SECRET':''}):
            status = self.client.get('/social/meta/status',headers=self.a).json()
            self.assertFalse(status['ready'])
            self.assertIn('Öffentliche HTTPS-Adresse', status['missing'])
            self.assertEqual(self.client.post('/social/meta/connect',headers=self.a,json={}).status_code,503)
        self.provider.assert_not_called()
        for url in ('https://127.0.0.1','https://10.0.0.1','https://host.local','https://user:password@example.com','https://example.com/#secret'):
            self.assertFalse(social.public_https(url))

    def test_oauth_is_single_use_bound_to_company_session_and_expires(self):
        state = self.begin()
        self.assertEqual(self.callback(state,self.b).status_code,403)
        other_session = self.login('admin@mueller.local')
        self.assertEqual(self.callback(state,other_session).status_code,403)
        self.assertEqual(self.callback(state).status_code,303)
        count = self.provider.call_count
        self.assertEqual(self.callback(state).status_code,403)
        self.assertEqual(self.provider.call_count,count)
        state = self.begin()
        with main.db() as conn: conn.execute('UPDATE meta_oauth_states SET expires_at=0')
        self.assertEqual(self.callback(state).status_code,403)

    def test_cancelled_oauth_never_calls_provider(self):
        state = self.begin()
        response = self.callback(state,error='access_denied')
        self.assertTrue(response.headers['location'].endswith('social=cancelled'))
        self.provider.assert_not_called()

    def test_two_companies_keep_their_own_pages_and_disconnect_independently(self):
        self.connect()
        original_provider = self.provider.side_effect
        def second_company(method, path, token='', data=None):
            if path == 'me/accounts':
                return {'data':[{'id':'888','name':'Second Company Page','access_token':'second_fixture_page_token','tasks':['CREATE_CONTENT']}]}
            return original_provider(method, path, token, data)
        self.provider.side_effect = second_company
        begun = self.client.post('/social/meta/connect', headers=self.b, json={})
        self.assertEqual(begun.status_code, 200)
        state = parse_qs(urlsplit(begun.json()['url']).query)['state'][0]
        self.assertEqual(self.callback(state, self.b).status_code, 303)
        self.assertEqual(self.client.post('/social/meta/page', headers=self.a, json={'page_id':'888'}).status_code, 409)
        self.assertEqual(self.client.post('/social/meta/page', headers=self.b, json={'page_id':'444'}).status_code, 404)
        self.assertEqual(self.client.post('/social/meta/page', headers=self.b, json={'page_id':'888'}).status_code, 200)
        first = self.client.get('/social/meta/status', headers=self.a).json()['connection']
        second = self.client.get('/social/meta/status', headers=self.b).json()['connection']
        self.assertEqual(first['page_id'], '444')
        self.assertEqual(second['page_id'], '888')
        self.provider.side_effect = original_provider
        self.assertEqual(self.publish(self.preview()).json()['post_id'], '444_777')
        self.assertEqual(self.client.delete('/social/meta/connection', headers=self.a).status_code, 200)
        self.assertIsNone(self.client.get('/social/meta/status', headers=self.a).json()['connection'])
        self.assertEqual(self.client.get('/social/meta/status', headers=self.b).json()['connection']['page_id'], '888')

    def test_page_selection_never_trusts_browser_page_or_token_and_encrypts(self):
        state = self.begin(True)
        self.callback(state)
        status = self.client.get('/social/meta/status',headers=self.a)
        self.assertNotIn('fixture_page_token',status.text)
        self.assertEqual(status.json()['pages'][0]['instagram_name'],'fixture_ig')
        self.assertEqual(self.client.get('/social/meta/status',headers=self.b).json()['pages'],[])
        self.assertEqual(self.client.post('/social/meta/page',headers=self.a,json={'page_id':'999'}).status_code,404)
        self.assertEqual(self.client.post('/social/meta/page',headers=self.a,json={'page_id':'444','token':'fake'}).status_code,422)
        self.assertEqual(self.client.post('/social/meta/page',headers=self.a,json={'page_id':'444'}).status_code,200)
        with main.db() as conn:
            encrypted = conn.execute('SELECT token FROM meta_connections').fetchone()[0]
            self.assertNotIn('fixture_page_token',encrypted)
            self.assertEqual(social.unseal(encrypted),'fixture_page_token')
        self.assertNotIn('token',self.client.get('/social/meta/status',headers=self.a).text)

    def test_missing_facebook_permissions_blocks_but_instagram_is_optional(self):
        self.permissions = {'pages_show_list'}
        self.assertTrue(self.callback(self.begin()).headers['location'].endswith('social=failed'))
        self.permissions = social.FACEBOOK_SCOPES
        # Simulate a declined optional Instagram scope: basic Facebook remains usable.
        self.provider.side_effect = lambda method,path,token='',data=None: {'data':[{'id':'444','name':'Fixture','access_token':'fixture_page_token','tasks':['CREATE_CONTENT']}]} if path=='me/accounts' else SocialTests.provider(self,method,path,token,data)
        self.connect(True)
        self.assertEqual(self.client.get('/social/meta/status',headers=self.a).json()['connection']['instagram_id'],'')

    def test_publish_is_explicit_and_success_is_idempotent(self):
        self.connect()
        preview = self.preview()
        self.assertEqual(preview['state'],'preview')
        self.assertFalse(any(path.endswith('/feed') for _,path,_ in self.calls))
        self.assertEqual(self.client.post(self.path+'/publish',headers=self.a,json={'preview_id':preview['id'],'confirmed':False}).status_code,422)
        result = self.publish(preview)
        self.assertEqual(result.json()['state'],'published',result.text)
        self.assertEqual(result.json()['post_url'],'https://www.facebook.com/444/posts/777')
        self.assertEqual(self.publish(preview).json()['state'],'published')
        self.assertEqual(sum(path=='444/feed' for _,path,_ in self.calls),1)
        self.assertEqual(self.client.post(self.path+'/preview',headers=self.a,json={'message':'Second','link_id':self.link}).status_code,409)
        with main.db() as conn:
            self.assertEqual(conn.execute('SELECT status FROM projects WHERE id=?',(self.project,)).fetchone()[0],'Live')
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM campaign_history WHERE action=\'facebook_published\'').fetchone()[0],1)

    def test_unknown_response_never_retries_and_can_verify_existing_post(self):
        self.connect()
        preview = self.preview()
        self.provider.side_effect = social.ProviderError()
        self.assertEqual(self.publish(preview).json()['state'],'unknown')
        calls = self.provider.call_count
        self.assertEqual(self.publish(preview).status_code,409)
        self.assertEqual(self.provider.call_count,calls)
        self.provider.side_effect = lambda *args,**kwargs: SocialTests.provider(self,*args,**kwargs)
        with main.db() as conn: conn.execute('UPDATE social_publications SET updated_at=?',(int(time.time())-121,))
        self.assertEqual(self.client.post(self.path+'/verify',headers=self.a,json={'post_id':'999_777'}).status_code,422)
        response = self.client.post(self.path+'/verify',headers=self.a,json={'post_id':'444_777'})
        self.assertEqual(response.json()['state'],'published',response.text)

    def test_definite_provider_rejection_requires_new_preview(self):
        self.connect()
        preview = self.preview()
        self.provider.side_effect = social.ProviderError(rejected=True)
        self.assertEqual(self.publish(preview).json()['state'],'failed')
        self.assertEqual(self.publish(preview).status_code,409)
        self.assertNotEqual(self.preview()['id'],preview['id'])

    def test_link_campaign_and_connection_are_rechecked_before_publish(self):
        self.connect()
        preview = self.preview()
        with main.db() as conn: conn.execute("UPDATE meta_connections SET revision='new_connection'")
        self.assertEqual(self.publish(preview).status_code,409)
        preview = self.preview()
        with main.db() as conn: conn.execute('UPDATE ad_links SET active=0 WHERE id=?',(self.link,))
        self.assertEqual(self.publish(preview).status_code,422)
        self.assertFalse(any(path=='444/feed' for _,path,_ in self.calls))

    def test_foreign_campaign_customer_platform_admin_and_demo_cannot_publish(self):
        self.connect()
        preview = self.preview()
        self.assertEqual(self.publish(preview,self.b).status_code,404)
        self.assertEqual(self.client.get(f'/campaigns/{self.project}/social/publication',headers=self.b).status_code,404)
        self.assertEqual(self.publish(preview,self.admin).status_code,403)
        with main.db() as conn:
            password = conn.execute('SELECT password_hash FROM users LIMIT 1').fetchone()[0]
            conn.execute("INSERT INTO users(email,name,password_hash,role,organization_id) VALUES('fixture_client@example.test','Fixture',?,'kunde',?)",(password,self.org))
        self.passwords['fixture_client@example.test'] = next(iter(self.passwords.values()))
        # The hashes differ across seeded users; create the customer session directly.
        token = 'fixture_customer_session'
        with main.db() as conn:
            uid = conn.execute("SELECT id FROM users WHERE email='fixture_client@example.test'").fetchone()[0]
            csrf = self.a['X-CSRF-Token']
            conn.execute('INSERT INTO sessions(token_hash,user_id,expires_at,csrf_hash,mfa_ok,last_seen) VALUES(?,?,?,?,1,?)',(auth.digest(token),uid,int(time.time())+3600,auth.digest(csrf),int(time.time())))
        customer = {**self.a,'Cookie':f'mh_session={token}; mh_csrf={csrf}'}
        self.assertEqual(self.publish(preview,customer).status_code,403)
        self.client.post('/demo/context',headers=self.admin,json={'role':'firmen_admin','organization_id':self.org})
        self.assertEqual(self.client.post('/social/meta/connect',headers=self.admin,json={}).status_code,403)
        self.assertEqual(self.publish(preview,self.admin).status_code,403)
        self.assertFalse(any(path=='444/feed' for _,path,_ in self.calls))

    def test_billing_gate_and_csrf_still_apply(self):
        self.connect()
        preview = self.preview()
        with main.db() as conn:
            conn.execute('INSERT INTO billing_accounts(organization_id,mode,country) VALUES(?,?,?)',(self.org,'test','DE'))
        self.assertEqual(self.publish(preview).status_code,402)
        self.assertEqual(self.client.post('/social/meta/connect',headers=self.a,json={}).status_code,402)
        bad = {**self.a,'X-CSRF-Token':'wrong'}
        self.assertEqual(self.client.post(self.path+'/publish',headers=bad,json={'preview_id':preview['id'],'confirmed':True}).status_code,403)
        self.assertEqual(self.client.delete('/social/meta/connection',headers=self.a).status_code,200)

    def test_parallel_publish_calls_claim_one_provider_request(self):
        self.connect()
        preview = self.preview()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _:self.publish(preview),range(2)))
        self.assertTrue(all(r.status_code in {200,409} for r in results))
        self.assertEqual(sum(path=='444/feed' for _,path,_ in self.calls),1)

    def test_approval_link_channel_and_preview_expiry_are_enforced(self):
        self.connect()
        preview = self.preview()
        with main.db() as conn: conn.execute('UPDATE social_publications SET created_at=0')
        self.assertEqual(self.publish(preview).status_code,409)
        preview = self.preview()
        with main.db() as conn: conn.execute("UPDATE projects SET status='Draft' WHERE id=?",(self.project,))
        self.assertEqual(self.publish(preview).status_code,409)
        self.assertEqual(self.client.post(self.path+'/preview',headers=self.a,json={'message':'Fixture','link_id':self.link}).status_code,409)
        with main.db() as conn:
            conn.execute("UPDATE projects SET status='Live' WHERE id=?",(self.project,))
            conn.execute("UPDATE ad_links SET channel='Instagram' WHERE id=?",(self.link,))
        self.assertEqual(self.client.post(self.path+'/preview',headers=self.a,json={'message':'Fixture','link_id':self.link}).status_code,422)
        self.assertFalse(any(path=='444/feed' for _,path,_ in self.calls))

    def test_superseded_preview_and_expired_authorization_cannot_send(self):
        self.connect()
        old = self.preview()
        new = self.preview()
        self.assertEqual(self.publish(old).status_code,404)
        with main.db() as conn: conn.execute('UPDATE meta_connections SET expires_at=0')
        self.assertEqual(self.publish(new).status_code,409)
        self.assertTrue(self.client.get('/social/meta/status',headers=self.a).json()['connection']['expired'])
        self.assertFalse(any(path=='444/feed' for _,path,_ in self.calls))

    def test_verify_mismatched_post_cannot_mark_published(self):
        self.connect()
        preview = self.preview()
        self.provider.side_effect = social.ProviderError()
        self.publish(preview)
        with main.db() as conn: conn.execute('UPDATE social_publications SET updated_at=0')
        self.provider.side_effect = None
        self.provider.return_value = {'id':'444_777','message':'Different text'}
        self.assertEqual(self.client.post(self.path+'/verify',headers=self.a,json={'post_id':'444_777'}).status_code,409)
        self.assertEqual(self.client.get(f'/campaigns/{self.project}/social/publication',headers=self.a).json()['publication']['state'],'unknown')


class TransportTests(unittest.TestCase):
    def test_access_token_uses_header_and_provider_errors_do_not_expose_secrets(self):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = b'{"id":"444_777"}'
        with patch.object(social,'configured',return_value={'version':'v25.0'}), patch.dict(os.environ,{'MH_META_APP_SECRET':'fixture_app_secret'}), patch.object(social.http,'build_opener',return_value=opener):
            self.assertEqual(social.graph('POST','444/feed','fixture_page_token',{'message':'fixture'})['id'],'444_777')
            req = opener.open.call_args.args[0]
            self.assertEqual(req.get_header('Authorization'),'Bearer fixture_page_token')
            self.assertNotIn('fixture_page_token',req.full_url)
            self.assertIn(b'appsecret_proof=',req.data)
            for code in (400,500):
                opener.open.side_effect = social.error.HTTPError('https://graph.facebook.com/',code,'fixture error',{},io.BytesIO(b'{"error":{"message":"fixture_page_token"}}'))
                with self.assertRaises(social.ProviderError) as failure:
                    social.graph('POST','444/feed','fixture_page_token',{'message':'fixture'})
                self.assertEqual(failure.exception.rejected,code==400)
                self.assertNotIn('fixture_page_token',str(failure.exception))

    def test_provider_response_limit_and_redirects_fail_closed(self):
        opener=MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value=b'x'*(1024*1024+1)
        with patch.object(social,'configured',return_value={'version':'v25.0'}),patch.object(social.http,'build_opener',return_value=opener):
            with self.assertRaises(social.ProviderError): social.graph('GET','me/accounts')
        self.assertIsNone(social.NoRedirect().redirect_request(None,None,302,'',{},'https://other.example.com'))


class MetaSetupTests(unittest.TestCase):
    def test_private_setup_preserves_existing_configuration_and_hides_secret(self):
        from backend import meta_setup
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'.env.local'
            path.write_text('STRIPE_SECRET_KEY=fixture_preserved\nMH_MAIL_MODE=local\n')
            output=io.StringIO()
            with patch.object(meta_setup,'ENV_FILE',path),patch('builtins.input',side_effect=['https://mh.example.com','123','v25.0','https://mh.example.com/api/social/meta/callback']),patch.object(meta_setup.getpass,'getpass',return_value='fixture_hidden_secret'),patch('sys.stdout',output):
                meta_setup.setup()
            values=meta_setup.read_env(path)
            self.assertEqual(values['STRIPE_SECRET_KEY'],'fixture_preserved')
            self.assertEqual(values['MH_META_APP_SECRET'],'fixture_hidden_secret')
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertNotIn('fixture_hidden_secret',output.getvalue())

    def test_invalid_meta_setup_leaves_existing_file_untouched(self):
        from backend import meta_setup
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'.env.local'
            original='MH_PUBLIC_URL=http://127.0.0.1:5181\n'
            path.write_text(original)
            with patch.object(meta_setup,'ENV_FILE',path),patch('builtins.input',side_effect=['http://localhost:5181','123','v25.0','https://mh.example.com/api/social/meta/callback']),patch.object(meta_setup.getpass,'getpass',return_value='fixture_hidden_secret'),patch('sys.stdout',io.StringIO()):
                with self.assertRaises(ValueError):meta_setup.setup()
            self.assertEqual(path.read_text(),original)


if __name__ == '__main__': unittest.main()
