"""Recruiting acceptance and security checks using isolated databases and fake contacts."""
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
import unittest
from backend import test_tracking as fixtures
from backend import main


class RecruitingTests(unittest.TestCase):
    login = fixtures.TrackingTests.login
    enable = fixtures.TrackingTests.enable
    link = fixtures.TrackingTests.link
    submit = fixtures.TrackingTests.submit
    tearDown = fixtures.TrackingTests.tearDown
    def setUp(self):
        fixtures.TrackingTests.setUp(self)
        self.base = f'/campaigns/{self.campaign}/recruiting'
        self.me = self.client.get('/auth/me', headers=self.a).json()['id']
        self.foreign = self.client.get('/auth/me', headers=self.b).json()['id']

    def workspace(self):
        r = self.client.get(self.base, headers=self.a)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def need(self, **changes):
        n = self.workspace()['need']
        body = {k: n[k] for k in ('version','owner_id','response_owner_id','desired_start','open_questions','response_hours','state','close_reason')}
        body.update(changes)
        return self.client.post(self.base+'/need', headers=self.a, json=body)

    def candidate(self):
        self.assertEqual(self.need(owner_id=self.me,response_owner_id=self.me,response_hours=24).status_code,200)
        self.enable()
        self.assertEqual(self.submit().status_code,201)
        return self.workspace()['applications'][0]

    def event(self, applicant, kind, **details):
        body = dict(version=applicant['version'], request_key=str(uuid.uuid4()), kind=kind, **details)
        r = self.client.post(self.base+f"/applications/{applicant['id']}/events", headers=self.a, json=body)
        return r, body

    def report_results(self):
        r = self.client.get(self.base+'/results', headers=self.a)
        self.assertEqual(r.status_code,200,r.text)
        return r.json()

    def test_existing_demo_database_migrates_without_overwriting_preview(self):
        response = self.client.post('/demo/context',headers=self.admin,json={'role':'firmen_admin','organization_id':self.org})
        self.assertEqual(response.status_code,200,response.text)
        with main.db({'view_role':'firmen_admin'}) as conn:
            conn.execute('ALTER TABLE projects DROP COLUMN generated_briefing')
            conn.execute("UPDATE projects SET status='Draft' WHERE id=?",(self.campaign,))
        main.init_db()
        response=self.client.post(f'/campaigns/{self.campaign}/generate',headers=self.admin)
        self.assertEqual(response.status_code,200,response.text)
        self.assertFalse(response.json()['briefing_stale'])
        with main.db() as conn:
            self.assertEqual(conn.execute('SELECT status FROM projects WHERE id=?',(self.campaign,)).fetchone()[0],'Live')

    def test_incomplete_need_is_saved_without_generation_or_fabricated_date(self):
        r = self.client.post('/campaigns', headers=self.a, json={'organization_id':self.org,'briefing':{'role':'Ungeklärter Bedarf'}})
        self.assertEqual(r.status_code,201,r.text)
        p = r.json(); self.assertEqual(p['location'],''); self.assertEqual(p['generated'],{})
        self.assertEqual(self.client.post(f"/campaigns/{p['id']}/generate",headers=self.a).status_code,422)
        r = self.need(owner_id=self.me,response_owner_id=self.me,desired_start='')
        self.assertEqual(r.status_code,200,r.text); self.assertEqual(r.json()['desired_start'],'')
        self.assertIn('Gewünschter Start',r.json()['missing'])
        with main.db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM token_ledger').fetchone()[0],0)

    def test_isolation_roles_owner_validation_csrf_and_optimistic_version(self):
        self.assertEqual(self.client.get(self.base,headers=self.b).status_code,404)
        self.assertEqual(self.client.get(self.base,headers=self.admin).status_code,403)
        self.assertEqual(self.need(owner_id=self.foreign).status_code,422)
        n = self.workspace()['need']; body = {k:n[k] for k in ('version','state')}
        self.assertEqual(self.client.post(self.base+'/need',headers=self.b,json=body).status_code,404)
        self.assertEqual(self.need(owner_id=self.me).status_code,200)
        self.assertEqual(self.client.post(self.base+'/need',headers=self.a,json=body).status_code,409)
        self.assertEqual(self.client.post(self.base+'/need',headers={**self.a,'X-CSRF-Token':'forged'},json=body).status_code,403)
        with main.db() as conn: conn.execute("UPDATE users SET role='kunde' WHERE id=?",(self.me,))
        self.assertEqual(self.client.get(self.base,headers=self.a).status_code,403)

    def test_paid_write_gate_applies_to_need_application_and_page(self):
        c = self.candidate()
        with main.db() as conn:
            conn.execute("INSERT INTO billing_accounts(organization_id,country) VALUES(?,'DE')",(self.org,))
        self.assertEqual(self.need(owner_id=self.me).status_code,402)
        self.assertEqual(self.event(c,'response',confirmed=True,contact_way='Telefon',note='Fiktiver Nachweis')[0].status_code,402)
        self.assertEqual(self.client.post(self.path+'/page',headers=self.a,json=self.page).status_code,402)
        self.assertEqual(self.client.get(self.base,headers=self.a).status_code,200)

    def test_real_response_not_read_or_task_and_idempotent_evidence(self):
        c = self.candidate(); self.assertEqual(self.report_results()['responses'],0)
        self.workspace(); self.client.get(self.base+f"/applications/{c['id']}/events",headers=self.a)
        self.assertEqual(self.report_results()['responses'],0)
        self.assertEqual(self.event(c,'response',note='Nur Entwurf',contact_way='E-Mail')[0].status_code,422)
        r,body=self.event(c,'response',confirmed=True,contact_way='Telefon',note='Tatsächlich angerufen')
        self.assertEqual(r.status_code,200,r.text)
        self.assertIsNotNone(r.json()['first_response_at']);self.assertEqual(self.report_results()['responses'],1)
        repeat=self.client.post(self.base+f"/applications/{c['id']}/events",headers=self.a,json=body)
        self.assertEqual(repeat.status_code,200,repeat.text)
        self.assertEqual(self.report_results()['responses'],1)
        self.assertEqual(self.client.post(self.base+f"/applications/{c['id']}/events",headers=self.a,json={**body,'note':'Andere Daten'}).status_code,409)
        self.assertEqual(self.event(c,'assign',owner_id=self.me)[0].status_code,409)
        events=self.client.get(self.base+f"/applications/{c['id']}/events",headers=self.a).json()
        self.assertEqual(len(events),1);self.assertEqual(events[0]['actor'],self.client.get('/auth/me',headers=self.a).json()['name'])

    def test_proposal_confirmation_reschedule_cancel_and_held_are_distinct(self):
        c=self.candidate()
        self.assertEqual(self.event(c,'confirmation',confirmed=True,note='Zugestimmt')[0].status_code,422)
        r,_=self.event(c,'proposal',confirmed=True,contact_way='Telefon',scheduled_at=int(time.time())+7200,place='Werkstatt')
        self.assertEqual(r.status_code,200,r.text);c=r.json()
        self.assertEqual(self.report_results()['confirmed'],0);self.assertEqual(self.report_results()['held'],0)
        r,_=self.event(c,'confirmation',confirmed=True,note='Telefonische Zustimmung')
        self.assertEqual(r.status_code,200,r.text);c=r.json()
        self.assertEqual(self.report_results()['confirmed'],1)
        self.assertEqual(self.event(c,'held',confirmed=True)[0].status_code,422)
        r,_=self.event(c,'proposal',confirmed=True,contact_way='Telefon',scheduled_at=int(time.time())+10800,place='Werkstatt')
        self.assertEqual(r.status_code,200,r.text);c=r.json();self.assertIsNone(c['confirmed_at'])
        r,_=self.event(c,'cancelled',confirmed=True,note='Bewerber hat abgesagt',next_action='Neu vereinbaren')
        self.assertEqual(r.status_code,200,r.text);self.assertIsNone(r.json()['scheduled_at'])
        self.assertEqual(len(self.client.get(self.base+f"/applications/{c['id']}/events",headers=self.a).json()),4)
        # Elapsed real time is emulated only in this isolated fixture.
        with main.db() as conn:
            conn.execute("UPDATE recruiting_cases SET state='confirmed',scheduled_at=? WHERE receipt_id=?",(int(time.time())-1,c['id']))
        c=self.workspace()['applications'][0]
        r,body=self.event(c,'held',confirmed=True,note='Gespräch durchgeführt',next_action='Team entscheidet')
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.report_results()['held'],1)
        self.assertEqual(self.client.post(self.base+f"/applications/{c['id']}/events",headers=self.a,json=body).status_code,200)
        self.assertEqual(self.report_results()['held'],1)

    def test_overdue_task_delegation_and_completion(self):
        c=self.candidate()
        r,_=self.event(c,'task',note='Frist im Pilot vereinbart',next_action='Antworten',due_at=int(time.time())-1)
        self.assertEqual(r.status_code,200,r.text);c=r.json();self.assertTrue(c['overdue'])
        self.assertEqual(self.event(c,'assign',owner_id=self.foreign)[0].status_code,422)
        r,_=self.event(c,'assign',owner_id=self.me);self.assertEqual(r.status_code,200,r.text);c=r.json()
        self.assertTrue(c['overdue'])
        r,_=self.event(c,'response',confirmed=True,contact_way='Telefon',note='Kontakt bestätigt')
        self.assertEqual(r.status_code,200,r.text);self.assertFalse(r.json()['overdue']);self.assertIsNone(r.json()['due_at'])

    def test_concurrent_claim_has_one_winner(self):
        c=self.candidate();url=self.base+f"/applications/{c['id']}/events"
        bodies=[dict(version=c['version'],request_key=str(uuid.uuid4()),kind='assign',owner_id=self.me) for _ in range(2)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(lambda b:self.client.post(url,headers=self.a,json=b).status_code,bodies))
        self.assertEqual(sorted(responses),[200,409])

    def test_retention_erases_workflow_notes_and_keeps_anonymous_counts(self):
        c=self.candidate()
        r,_=self.event(c,'response',confirmed=True,contact_way='Telefon',note='Private fixture applicant note')
        self.assertEqual(r.status_code,200,r.text)
        with main.db() as conn:
            raw=conn.execute('SELECT payload FROM recruiting_events').fetchone()[0]
            self.assertNotIn('Private fixture',raw)
            conn.execute('UPDATE hosted_applications SET expires_at=?',(int(time.time())-1,))
        c=self.workspace()['applications'][0];self.assertIsNone(c['contact']);self.assertFalse(c['overdue']);self.assertIsNone(c['owner_id'])
        events=self.client.get(self.base+f"/applications/{c['id']}/events",headers=self.a).json()
        self.assertIsNone(events[0]['details']);self.assertEqual(self.report_results()['responses'],1)
        self.assertEqual(self.event(c,'assign',owner_id=self.me)[0].status_code,410)
        with main.db() as conn:
            self.assertEqual(conn.execute('SELECT payload FROM recruiting_cases').fetchone()[0],'')

    def test_manual_publication_and_close_reuse_do_not_copy_contacts_or_charge(self):
        c=self.candidate();link=self.link('Website')
        body=dict(request_key=str(uuid.uuid4()),channel='Website',variant='A',posted_at=int(time.time()),confirmed=True,link_id=link['id'],proof_url='https://example.test/job')
        r=self.client.post(self.base+'/publications',headers=self.a,json=body)
        self.assertEqual(r.status_code,201,r.text);self.assertEqual(r.json()['source'],'manual')
        self.assertEqual(self.client.post(self.base+'/publications',headers=self.a,json=body).status_code,201)
        self.assertEqual(len(self.workspace()['publications']),1)
        self.assertEqual(self.need(state='closed',close_reason='Suche beendet').status_code,200)
        self.assertEqual(self.submit({**self.application,'request_id':'new_after_closed_application'}).status_code,404)
        self.assertEqual(self.client.get('/tracking/r/'+link['id']).status_code,404)
        self.assertEqual(self.client.patch(self.path+'/links/'+link['id'],headers=self.a,json={'active':True}).status_code,409)
        self.assertEqual(self.client.post(self.path+'/page',headers=self.a,json=self.page).status_code,409)
        self.assertIsNotNone(self.workspace()['applications'][0]['contact'])
        self.assertEqual(self.event(c,'response',confirmed=True,contact_way='Telefon',note='Nach Abschluss persönlich beantwortet')[0].status_code,200)
        reuse=dict(request_key=str(uuid.uuid4()))
        r=self.client.post(self.base+'/reuse',headers=self.a,json=reuse)
        self.assertEqual(r.status_code,201,r.text);p=r.json();self.assertEqual(p['status'],'Draft');self.assertTrue(p['briefing_stale'])
        self.assertEqual(self.client.post(self.base+'/reuse',headers=self.a,json=reuse).json()['id'],p['id'])
        fresh=self.client.get(f"/campaigns/{p['id']}/recruiting",headers=self.a).json()
        self.assertEqual(fresh['applications'],[]);self.assertEqual(fresh['publications'],[])
        with main.db() as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM token_ledger').fetchone()[0],0)

    def test_effort_comparison_unknowns_range_and_duplicate(self):
        r=self.report_results();self.assertIsNone(r['applications']);self.assertIsNone(r['link_requests']);self.assertIsNone(r['work_minutes']);self.assertIsNone(r['comparison_difference_minutes'])
        body=dict(request_key=str(uuid.uuid4()),day=r['end'],minutes=30,support_minutes=10,baseline_minutes=90,comparison='Selbe Vorbereitung, einmalige Begleitung',learning='Kanal im nächsten Pilot prüfen')
        self.assertEqual(self.client.post(self.base+'/effort',headers=self.a,json={**body,'comparison':''}).status_code,422)
        for _ in range(2):
            response=self.client.post(self.base+'/effort',headers=self.a,json=body)
            self.assertEqual(response.status_code,201,response.text)
        r=self.report_results();self.assertEqual(r['work_minutes'],30);self.assertEqual(r['support_minutes'],10);self.assertEqual(r['comparison_difference_minutes'],50)
        self.assertEqual(len(r['effort']),1);self.assertIsNone(r['spend_cents'])
        old=self.client.get(self.base+'/results?start=2000-01-01&end=2000-01-02',headers=self.a).json()
        self.assertIsNone(old['work_minutes'])
        self.assertEqual(self.client.get(self.base+'/results?start=2030-01-01&end=2000-01-02',headers=self.a).status_code,422)

    def test_material_snapshot_and_learnable_requirements_and_discarded_benefits(self):
        r=self.client.post('/campaigns',headers=self.a,json={'organization_id':self.org,'briefing':{'role':'Neuer Bedarf','location':'Berlin','requirements':'Elektroausbildung','learnable_requirements':'Neue Software','benefits':'','salary':''}})
        p=r.json();url=f"/campaigns/{p['id']}"
        p=self.client.post(url+'/generate',headers=self.a).json();self.assertFalse(p['briefing_stale'])
        self.assertIn('## Bei uns lernbar\nNeue Software',p['generated']['jobAd'])
        self.assertNotIn('Ein moderner Arbeitsplatz',p['generated']['social'])
        brief={**p['briefing'],'location':'Potsdam'}
        changed=self.client.patch(url,headers=self.a,json={'briefing':brief}).json()
        self.assertTrue(changed['briefing_stale']);self.assertEqual(changed['generated'],p['generated'])
        self.assertEqual(self.client.patch(url,headers=self.a,json={'reviewed_briefing':p['briefing_fingerprint']}).status_code,409)
        self.assertEqual(self.client.patch(url,headers=self.a,json={'status':'Review'}).status_code,200)
        self.assertEqual(self.client.patch(url,headers=self.a,json={'status':'Live'}).status_code,409)
        self.assertEqual(self.client.patch(url,headers=self.a,json={'reviewed_briefing':changed['briefing_fingerprint']}).status_code,200)
        self.assertEqual(self.client.patch(url,headers=self.a,json={'status':'Live'}).status_code,200)
