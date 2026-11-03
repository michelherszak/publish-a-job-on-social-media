"""Temporary data only: directory visibility, consent isolation and actual conversions."""
import io
import json
import time
import unittest
from unittest.mock import patch
from PIL import Image
from backend import main
from backend import test_tracking as tracking_tests


class PortalTests(tracking_tests.TrackingTests):
    # Reuse setup helpers without rerunning the parent's test cases in this suite.
    def setUp(self):
        super().setUp()
        self.portal=f'/campaigns/{self.campaign}/portal'
        self.plan={'revision':0,'contact_email':'fixture@example.test','privacy_url':'https://example.test/privacy','employment':'full_time','work_mode':'hybrid','budget_cents':15000,'duration_days':14,'retargeting':True}
        response=self.client.post(self.portal,headers=self.a,json=self.plan)
        self.assertEqual(response.status_code,200,response.text)
        response=self.client.post(self.portal+'/publish',headers=self.a,json={'revision':1,'image_revision':0})
        self.assertEqual(response.status_code,200,response.text)

    def consent(self, analytics=True, marketing=False, request_id='consented_fixture_123456'):
        result=self.client.post(f'/jobs/{self.campaign}/consent',json={'analytics':analytics,'marketing':marketing,'version':'jobs-v1','request_id':request_id})
        self.assertEqual(result.status_code,200,result.text)
        return result.json()['token']

    def event(self, token, event='engaged', **kwargs):
        return self.client.post(f'/jobs/{self.campaign}/events',json={'token':token,'event':event,'active_seconds':30,'section_percent':80,**kwargs})

    def totals(self):
        return self.client.get(self.portal+'/report',headers=self.a).json()

    def test_directory_filters_and_only_explicit_approved_open_stellen(self):
        data=self.client.get('/jobs').json()
        self.assertEqual([j['id'] for j in data['jobs']],[self.campaign])
        for query in ('q=tracking','location=berlin','employment=full_time','work_mode=hybrid'):
            self.assertEqual(self.client.get('/jobs?'+query).json()['total'],1)
        for query in ('q=no_match','location=Hamburg','employment=part_time','work_mode=remote','offset=24'):
            self.assertEqual(self.client.get('/jobs?'+query).json()['jobs'],[])
        self.assertEqual(self.client.get('/jobs?limit=101').status_code,422)
        public=self.client.get(f'/jobs/{self.campaign}')
        self.assertEqual(public.status_code,200)
        self.assertNotIn('briefing',public.json());self.assertFalse(public.json()['retargeting_ready'])
        self.assertNotIn('budget_cents',public.json());self.assertEqual(public.headers['cache-control'],'no-store')
        with main.db() as conn:conn.execute("UPDATE projects SET status='Review' WHERE id=?",(self.campaign,))
        self.assertEqual(self.client.get('/jobs').json()['total'],0)
        self.assertEqual(self.client.get(f'/jobs/{self.campaign}').status_code,404)

    def test_publication_date_is_stable_and_sitemap_follows_visibility(self):
        page = self.client.get(f'/jobs/{self.campaign}').json()
        self.assertGreater(page['date_posted'], 0)
        self.assertEqual(page['ends_at'], 0)
        published = page['date_posted']
        self.client.post(self.portal+'/publish',headers=self.a,json={'revision':1,'image_revision':0})
        self.assertEqual(self.client.get(f'/jobs/{self.campaign}').json()['date_posted'],published)
        self.assertEqual([j['id'] for j in self.client.get('/jobs/sitemap').json()['jobs']],[self.campaign])
        with main.db() as conn:
            conn.execute('UPDATE job_portal_plans SET ends_at=? WHERE project_id=?',(int(time.time())-1,self.campaign))
        self.assertEqual(self.client.get('/jobs/sitemap').json()['jobs'],[])
        self.assertEqual(self.client.get(f'/jobs/{self.campaign}').status_code,404)

    def test_public_image_exposes_only_selected_approved_asset(self):
        # Insert a sanitized fixture after approval to avoid changing the test workflow.
        out=io.BytesIO();Image.new('RGB',(100,100),'green').save(out,'JPEG')
        with main.db() as conn:
            conn.execute('INSERT INTO campaign_images(project_id,name,width,height,original,feed,story,crops,selected,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(self.campaign,'fixture',100,100,out.getvalue(),out.getvalue(),out.getvalue(),'{}',1,int(time.time())))
        result=self.client.get(f'/jobs/{self.campaign}/image')
        self.assertEqual(result.status_code,200);self.assertEqual(result.headers['content-type'],'image/jpeg')
        self.assertEqual(self.client.get(f'/jobs/{self.campaign}/image/original').status_code,404)
        self.client.post(self.portal+'/unpublish',headers=self.a)
        self.assertEqual(self.client.get(f'/jobs/{self.campaign}/image').status_code,404)

    def test_decline_has_no_flow_and_application_works_without_tracking(self):
        self.assertIsNone(self.consent(False,False))
        with main.db() as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM job_flows').fetchone()[0],0)
        self.assertEqual(self.submit().status_code,201)
        report=self.totals();self.assertEqual(report['applications'],1);self.assertEqual(report['totals']['consented_applications'],0)

    def test_consent_scope_idempotence_thresholds_withdraw_and_expiry(self):
        token=self.consent()
        self.consent()
        self.assertEqual(self.totals()['totals']['consented_views'],1)
        self.assertEqual(self.event(token,active_seconds=29).status_code,422)
        self.assertEqual(self.event(token,section_percent=79).status_code,422)
        for _ in range(2):self.assertEqual(self.event(token).status_code,200)
        self.assertEqual(self.totals()['totals']['engaged'],1)
        self.assertEqual(self.event(token+'invalid').status_code,403)
        self.assertEqual(self.client.post('/jobs/99999/events',json={'token':token,'event':'engaged'}).status_code,404)
        self.assertEqual(self.client.post(f'/jobs/{self.campaign}/withdraw',json={'token':token}).status_code,200)
        self.assertEqual(self.event(token).status_code,403)
        token=self.consent(request_id='expiry_fixture_123456')
        with main.db() as conn:conn.execute('UPDATE job_flows SET expires_at=0')
        self.assertEqual(self.event(token).status_code,403)

    def test_marketing_is_separate_no_form_events_and_no_provider_calls(self):
        with patch.object(main.social,'graph') as graph:
            token=self.consent(False,True)
            self.assertEqual(self.event(token,'form_started').status_code,403)
            self.assertEqual(self.event(token).status_code,200)
            totals=self.totals()['totals'];self.assertEqual(totals['consented_views'],0);self.assertEqual(totals['engaged'],0);self.assertEqual(totals['retargeting_eligible'],1)
            graph.assert_not_called()

    def test_actual_submission_is_only_conversion_and_not_client_event(self):
        token=self.consent()
        self.assertEqual(self.event(token,'form_started').status_code,200)
        self.assertEqual(self.client.post(f'/jobs/{self.campaign}/events',json={'token':token,'event':'submitted'}).status_code,422)
        body={**self.application,'portal_consent':token}
        for _ in range(2):self.assertEqual(self.submit(body).status_code,201)
        report=self.totals();self.assertEqual(report['applications'],1);self.assertEqual(report['totals']['consented_applications'],1)
        self.assertEqual(self.event(token).status_code,200)
        self.assertEqual(self.totals()['totals']['engaged'],0)
        invalid={**self.application,'request_id':'invalid_optional_token_fixture','portal_consent':'invalid'}
        self.assertEqual(self.submit(invalid).status_code,201)

    def test_shared_budget_and_revision_publication_is_idempotent_and_no_spend(self):
        data=self.client.get(self.portal,headers=self.a).json()
        self.assertEqual(data['plan']['budget_cents'],15000);self.assertEqual(len(data['tasks']),6)
        self.assertFalse(data['provider_live'])
        for _ in range(2):
            response=self.client.post(self.portal+'/publish',headers=self.a,json={'revision':1})
            self.assertEqual(response.json()['spent_cents'],0)
        with main.db() as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM job_distribution').fetchone()[0],6)
        self.assertEqual(self.client.post(self.portal+'/publish',headers=self.a,json={'revision':0}).status_code,422)
        self.assertEqual(self.client.post(self.portal,headers=self.a,json=self.plan).status_code,409)
        self.assertEqual(self.client.post(self.portal,headers=self.a,json={**data['plan'],'budget_cents':-1}).status_code,422)

    def test_tenant_paid_role_csrf_gates_and_foreign_consent(self):
        for suffix in ('','/report'):
            self.assertEqual(self.client.get(self.portal+suffix,headers=self.b).status_code,404)
        self.assertEqual(self.client.post(self.portal,headers=self.b,json=self.plan).status_code,404)
        self.assertEqual(self.client.post(self.portal,headers=self.admin,json=self.plan).status_code,403)
        with main.db() as conn:conn.execute("INSERT INTO billing_accounts(organization_id,mode,status,country) VALUES(?,'test','none','DE')",(self.org,))
        self.assertEqual(self.client.post(self.portal,headers=self.a,json=self.plan).status_code,402)
        self.assertEqual(self.client.get(self.portal+'/report',headers=self.a).status_code,200)
        from fastapi.testclient import TestClient
        with TestClient(main.app) as raw:
            self.assertEqual(raw.post(f'/jobs/{self.campaign}/consent',json={'analytics':True,'marketing':True,'version':'jobs-v1'}).status_code,403)

    def test_expired_closed_unpublished_are_removed_and_legacy_application_blocked(self):
        self.client.post(self.portal+'/unpublish',headers=self.a)
        self.assertEqual(self.client.get('/jobs').json()['total'],0)
        self.assertEqual(self.submit().status_code,404)
        self.client.post(self.portal+'/publish',headers=self.a,json={'revision':1})
        with main.db() as conn:conn.execute('UPDATE job_portal_plans SET ends_at=1')
        self.assertEqual(self.client.get('/jobs').json()['total'],0)
        self.assertEqual(self.submit().status_code,404)
        with main.db() as conn:
            conn.execute('UPDATE job_portal_plans SET ends_at=0')
            conn.execute("INSERT INTO recruiting_needs(project_id,state,updated_at) VALUES(?,'closed',?)",(self.campaign,int(time.time())))
        self.assertEqual(self.client.get('/jobs').json()['total'],0)
        self.assertEqual(self.client.get(f'/jobs/{self.campaign}').status_code,404)

# Inherited tracking cases are covered by their own unchanged suite.
for name in list(vars(tracking_tests.TrackingTests)):
    if name.startswith('test_'):
        setattr(PortalTests,name,None)

if __name__=='__main__':unittest.main()
