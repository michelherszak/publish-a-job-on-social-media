"""Local orchestration tests. No provider, mail, payment or real applicant data."""
import io
import time
import unittest
from unittest.mock import patch
from PIL import Image
from backend import main, campaign_workflow
from backend import test_job_portal as portal_tests


class WorkflowTests(portal_tests.PortalTests):
    def setUp(self):
        super().setUp()
        photo = io.BytesIO()
        Image.new('RGB',(100,100),'green').save(photo,'JPEG')
        with main.db() as conn:
            conn.execute('INSERT INTO campaign_images(project_id,name,width,height,original,feed,story,crops,selected,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                         (self.campaign,'fictional photo',100,100,photo.getvalue(),photo.getvalue(),photo.getvalue(),'{}',1,int(time.time())))
        self.publish()

    def publish(self):
        plan = self.settings()['plan']
        response = self.client.post(self.portal+'/publish',headers=self.a,json={'revision':plan['revision'],'image_revision':0})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()['workflow']

    def settings(self):
        return self.client.get(self.portal,headers=self.a).json()

    def exercise(self, key='fictional_delivery_123456'):
        return self.client.post(self.portal+'/workflow/simulate',headers=self.a,json={'run_id':self.settings()['workflow']['id'],'request_id':key})

    def retry(self, reconcile=False):
        return self.client.post(self.portal+'/workflow/retry',headers=self.a,json={'run_id':self.settings()['workflow']['id'],'reconcile':reconcile})

    def save_budget(self, amount):
        plan = self.settings()['plan']
        return self.client.post(self.portal,headers=self.a,json={**plan,'budget_cents':amount})

    def task(self, channel='Meta',kind='organic'):
        return next(t for t in self.settings()['workflow']['tasks'] if t['channel']==channel and t['kind']==kind)

    def reset_task(self):
        task = self.task()
        with main.db() as conn:
            conn.execute("UPDATE campaign_actions SET state='queued',reason='',provider_id='',attempts=0 WHERE id=?",(task['id'],))
        return task

    def test_combined_delivery_media_snapshot_and_duplicate_publish(self):
        workflow = self.settings()['workflow']
        self.assertEqual(len(workflow['tasks']),6)
        self.assertTrue(workflow['image']);self.assertEqual(workflow['mode'],'simulation')
        self.assertEqual({t['state'] for t in workflow['tasks'] if t['kind']!='retargeting'},{'simulated'})
        self.assertEqual({t['state'] for t in workflow['tasks'] if t['kind']=='retargeting'},{'waiting'})
        with patch.object(main.social,'graph') as graph:
            for _ in range(2):self.assertEqual(self.publish()['id'],workflow['id'])
            graph.assert_not_called()
        latest = self.settings()['workflow']
        self.assertEqual([t['provider_id'] for t in workflow['tasks']],[t['provider_id'] for t in latest['tasks']])
        self.assertEqual([t['attempts'] for t in workflow['tasks']],[t['attempts'] for t in latest['tasks']])
        with main.db() as conn:
            run = campaign_workflow.current(conn,self.campaign)
            self.assertTrue(run['feed']);self.assertTrue(run['story'])
            self.assertEqual(campaign_workflow.payload(run,conn.execute('SELECT * FROM campaign_actions WHERE id=?',(self.task('Instagram')['id'],)).fetchone())['placement'],'profile_or_story_link')
        self.assertFalse(latest['external_published']);self.assertEqual(latest['actual_spent_cents'],0)

    def test_failure_retry_and_uncertain_reconcile_do_not_repeat_delivery(self):
        self.reset_task()
        with patch.object(campaign_workflow.PROVIDER,'deliver',side_effect=campaign_workflow.DeliveryFailure()) as delivery:
            self.assertEqual(self.retry().status_code,200)
            self.assertEqual(self.task()['state'],'failed');self.assertEqual(delivery.call_count,1)
        self.retry();self.assertEqual(self.task()['state'],'simulated');self.assertEqual(self.task()['attempts'],2)
        self.reset_task()
        with patch.object(campaign_workflow.PROVIDER,'deliver',side_effect=campaign_workflow.DeliveryFailure(uncertain=True)) as delivery:
            self.retry();self.assertEqual(self.task()['state'],'unknown')
            self.retry();self.assertEqual(delivery.call_count,1)
            self.assertEqual(self.task()['state'],'unknown')
        self.assertEqual(self.retry(True).status_code,200)
        self.assertEqual(self.task()['state'],'simulated')

    def test_missing_image_is_actionable_partial_result(self):
        with main.db() as conn:conn.execute('UPDATE campaign_images SET selected=0 WHERE project_id=?',(self.campaign,))
        workflow = self.publish()
        instagram = [t for t in workflow['tasks'] if t['channel']=='Instagram']
        self.assertEqual({t['reason'] for t in instagram},{'missing_image'})
        self.assertEqual(self.task()['state'],'simulated')
        self.assertEqual(self.client.get('/jobs').json()['total'],1)

    def test_shared_budget_exhaustion_receipt_dedupe_and_no_real_spend(self):
        self.assertEqual(self.save_budget(301).status_code,200);self.publish()
        token = self.consent(True,True);self.event(token)
        with patch.object(main.social,'graph') as graph:
            response = self.exercise();self.assertEqual(response.status_code,200,response.text)
            graph.assert_not_called()
        result=response.json()
        self.assertEqual(result['simulated_spent_cents'],301);self.assertEqual(result['remaining_cents'],0)
        self.assertEqual(result['actual_spent_cents'],0)
        self.assertEqual(sum(t['allocation_cents'] for t in result['tasks']),301)
        self.assertEqual(self.exercise().json()['simulated_spent_cents'],301)
        self.assertEqual(self.exercise('another_delivery_123456').json()['simulated_spent_cents'],301)
        self.assertEqual(self.save_budget(300).status_code,409)

    def test_changed_plan_does_not_reset_spend_or_extend_existing_run(self):
        self.save_budget(500);before=self.publish()
        self.assertEqual(self.exercise().json()['simulated_spent_cents'],200)
        repeated=self.publish();self.assertEqual(repeated['ads_end_at'],before['ads_end_at'])
        self.assertEqual(self.save_budget(500).status_code,200)
        self.assertFalse(self.settings()['workflow']['enabled'])
        updated=self.publish();self.assertNotEqual(updated['id'],before['id'])
        self.assertEqual(sum(t['allocation_cents'] for t in updated['tasks']),300)
        self.assertEqual(self.exercise().json()['simulated_spent_cents'],350)

    def test_marketing_only_audience_application_and_withdraw_exclusion(self):
        token=self.consent(False,True);self.event(token)
        self.assertEqual(self.settings()['workflow']['audience'],1)
        self.assertEqual(self.task(kind='retargeting')['state'],'simulated')
        self.assertEqual(self.submit({**self.application,'portal_consent':token}).status_code,201)
        self.assertEqual(self.settings()['workflow']['audience'],0)
        self.assertEqual(self.task(kind='retargeting')['state'],'waiting')
        self.assertEqual(self.totals()['totals']['consented_applications'],0)
        other=self.consent(True,True,request_id='another_reading_123456');self.event(other)
        self.assertEqual(self.settings()['workflow']['audience'],1)
        self.client.post(f'/jobs/{self.campaign}/withdraw',json={'token':other})
        self.assertEqual(self.settings()['workflow']['audience'],0)

    def test_channel_reading_application_cohort_and_foreign_link(self):
        link=self.task(kind='paid')['link_id']
        response=self.client.post(f'/jobs/{self.campaign}/consent',json={'analytics':True,'marketing':False,'version':'jobs-v1','link_id':link,'request_id':'channel_visit_123456'})
        self.assertEqual(response.status_code,200,response.text)
        token=response.json()['token'];self.event(token)
        self.submit({**self.application,'portal_consent':token,'link_id':link})
        report=self.totals();self.assertEqual(report['totals']['engaged_applications'],1)
        self.assertEqual(report['channels'][0]['channel'],'Meta');self.assertEqual(report['channels'][0]['kind'],'paid')
        self.assertEqual(report['channels'][0]['engaged_applications'],1)
        other=self.client.post(f'/jobs/{self.campaign}/consent',json={'analytics':True,'marketing':False,'version':'jobs-v1','link_id':'not_our_link','request_id':'unknown_source_123456'})
        self.assertEqual(other.status_code,200)
        self.assertTrue(any(r['channel']=='Direct' for r in self.totals()['channels']))

    def test_pausing_expiry_closed_search_and_duration_block_delivery(self):
        self.client.post(self.portal+'/unpublish',headers=self.a)
        self.assertFalse(self.settings()['workflow']['enabled'])
        self.assertEqual(self.exercise().status_code,409)
        self.publish()
        with main.db() as conn:conn.execute('UPDATE campaign_runs SET ads_end_at=1 WHERE project_id=?',(self.campaign,))
        self.exercise();self.assertEqual(self.task(kind='paid')['reason'],'duration_ended')
        self.assertEqual(self.task()['state'],'simulated')
        with main.db() as conn:conn.execute('UPDATE job_portal_plans SET ends_at=1 WHERE project_id=?',(self.campaign,))
        self.assertFalse(self.settings()['workflow']['enabled'])
        self.assertEqual(self.exercise().status_code,409)
        with main.db() as conn:
            conn.execute('UPDATE job_portal_plans SET ends_at=0 WHERE project_id=?',(self.campaign,))
            conn.execute("INSERT INTO recruiting_needs(project_id,state,updated_at) VALUES(?,'closed',?)",(self.campaign,int(time.time())))
        self.assertEqual(self.retry().status_code,409)

    def test_invalid_receipt_rolls_back_and_write_tenant_role_csrf_gates(self):
        with patch.object(campaign_workflow.PROVIDER,'traffic',return_value={'spent_cents':999999,'clicks':1,'impressions':10}):
            self.assertEqual(self.exercise().status_code,502)
        self.assertEqual(self.settings()['workflow']['simulated_spent_cents'],0)
        run=self.settings()['workflow']['id']
        for headers,code in ((self.b,404),(self.admin,403)):
            self.assertEqual(self.client.post(self.portal+'/workflow/retry',headers=headers,json={'run_id':run}).status_code,code)
            self.assertEqual(self.client.post(self.portal+'/workflow/simulate',headers=headers,json={'run_id':run,'request_id':'scope_fixture_123456'}).status_code,code)
        self.assertEqual(self.client.post(self.portal+'/workflow/retry',headers=self.a,json={'run_id':run+999}).status_code,409)
        from fastapi.testclient import TestClient
        with TestClient(main.app) as raw:self.assertEqual(raw.post(self.portal+'/workflow/retry',json={'run_id':run}).status_code,403)
        with main.db() as conn:conn.execute("INSERT INTO billing_accounts(organization_id,mode,status,country) VALUES(?,'test','none','DE')",(self.org,))
        self.assertEqual(self.retry().status_code,402)
        with main.db() as conn, patch.object(campaign_workflow.PROVIDER,'deliver') as delivery:
            run=campaign_workflow.current(conn,self.campaign)
            campaign_workflow.execute(conn,run['id'])
            delivery.assert_not_called()
        self.assertFalse(self.settings()['workflow']['enabled'])

    def test_zero_budget_only_organic_and_expired_flow_not_retargeted(self):
        self.save_budget(0);workflow=self.publish()
        self.assertEqual(len(workflow['tasks']),2)
        self.assertEqual(self.exercise().json()['simulated_spent_cents'],0)
        token=self.consent(True,True);self.event(token)
        with main.db() as conn:conn.execute('UPDATE job_flows SET expires_at=1')
        self.assertEqual(self.settings()['workflow']['audience'],0)


for name in vars(portal_tests.PortalTests):
    if name.startswith('test_'):setattr(WorkflowTests,name,None)

if __name__=='__main__':unittest.main()
