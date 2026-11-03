"""Digital twin integration checks use an isolated source tree and a fake agent only."""
import copy
import http.client
import json
import os
import re
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
import serve
import twin

class TwinTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root=Path(self.temp.name)
        (self.root/'docs/requirements').mkdir(parents=True); (self.root/'backend').mkdir(); (self.root/'output/use-case-dashboard').mkdir(parents=True)
        self.source=self.root/'backend/feature.py'; self.source.write_text('@app.get("/feature")\ndef feature(): pass\n')
        self.catalog=copy.deepcopy(json.loads(twin.MANIFEST.read_text()))
        self.catalog['reviewed_sources']={'backend/feature.py':twin.hashes(self.root)['backend/feature.py']}
        self.manifest=self.root/'docs/requirements/use_case_status.json'; self.manifest.write_text(json.dumps(self.catalog))
        self.manager=serve.Manager(self.root,binary='/test/codex')
    def prepare(self,ids=None,note=''):
        return self.manager.prepare(dict(case_ids=ids or ['UC-Z12'],note=note,fingerprint=twin.fingerprint(self.root)))
    def test_all_original_cases_and_traceable_additions_visible(self):
        ids={c['id'] for c in self.catalog['cases']}
        for doc in ['USE_CASES.md','USE_CASES_ZIELBILD_REVIEW.md']:
            original=set(re.findall(r'^### (UC-(?:Z)?\d+)',(twin.ROOT/'docs/requirements'/doc).read_text(),re.M))
            self.assertTrue(original<=ids)
        self.assertEqual(len(ids),len(self.catalog['cases']))
        self.assertEqual(len(ids),57)
        for c in self.catalog['cases']:
            self.assertTrue(c['source_kind']); self.assertTrue(c['evidence'])
            for f in c['evidence']: self.assertTrue((twin.ROOT/f).is_file(),f)
    def test_inventory_reads_source_not_product_data(self):
        for name in ['.env.local','.auth.key','mh.db','integration_settings.json','demo_credentials.txt']:
            (self.root/'backend'/name).write_text('PRIVATE_SENTINEL')
        (self.root/'backend/mail_outbox').mkdir(); (self.root/'backend/mail_outbox/private.eml').write_text('PRIVATE_SENTINEL')
        names=twin.source_files(self.root)
        self.assertFalse(any(f.endswith(('.db','.key','.eml')) or '.env' in f or 'credentials' in f or 'integration_settings' in f for f in names))
        status=twin.status(self.root)
        self.assertNotIn('PRIVATE_SENTINEL',json.dumps(status))
        self.assertEqual(status['inventory']['routes'][0]['path'],'/feature')
    def test_new_source_and_changed_source_invalidate_fingerprint(self):
        initial=twin.fingerprint(self.root)
        self.source.write_text(self.source.read_text()+'# changed\n')
        self.assertNotEqual(twin.fingerprint(self.root),initial)
        self.assertIn('backend/feature.py',twin.status(self.root)['changed_sources'])
        (self.root/'backend/new_feature.py').write_text('def new(): pass\n')
        self.assertIn('backend/new_feature.py',twin.status(self.root)['unreviewed_sources'])
    def test_prompt_names_exact_selection_and_preserves_shared_features(self):
        job=self.prepare(['UC-I13','UC-Z12'],note='Anführungszeichen " und $(kein Shellaufruf)')
        self.assertEqual(job['state'],'prepared'); self.assertIsNone(self.manager.active)
        self.assertIn('Ich möchte den Use Case UC-I13',job['prompt']); self.assertIn('Ich möchte den Use Case UC-Z12',job['prompt'])
        self.assertNotIn('Ich möchte den Use Case UC-01 ',job['prompt'])
        self.assertIn('keine Kunden-, Bewerber- oder Abrechnungsdaten',job['prompt'])
        self.assertIn('$(kein Shellaufruf)',job['prompt'])
    def test_unknown_duplicate_empty_removed_and_stale_inputs_rejected(self):
        for ids in [[],['UC-UNKNOWN'],['UC-01','UC-01'],[1]]:
            with self.assertRaises(serve.Rejected): self.manager.prepare(dict(case_ids=ids,fingerprint=twin.fingerprint(self.root)))
        with self.assertRaises(serve.Rejected): self.manager.prepare(dict(case_ids=['UC-01'],fingerprint='outdated'))
        with self.assertRaises(serve.Rejected): self.prepare(note='x'*4001)
        self.catalog['cases'][0]['status']='removed'; self.manifest.write_text(json.dumps(self.catalog))
        with self.assertRaises(serve.Rejected): self.prepare(['UC-01'])
    def test_start_requires_review_unchanged_source_and_single_execution(self):
        job=self.prepare(); body=dict(digest=job['digest'],confirmed=True)
        with self.assertRaises(serve.Rejected): self.manager.start(job['id'],dict(digest=job['digest'],confirmed=False))
        with self.assertRaises(serve.Rejected): self.manager.start(job['id'],dict(digest='tampered',confirmed=True))
        with patch.object(serve.threading,'Thread') as thread:
            self.manager.start(job['id'],body); self.manager.start(job['id'],body)
            self.assertEqual(thread.call_count,1); self.assertEqual(thread.return_value.start.call_count,1)
            other=self.prepare(['UC-I13'])
            with self.assertRaises(serve.Rejected): self.manager.start(other['id'],dict(digest=other['digest'],confirmed=True))
        self.assertEqual(self.manager.cancel(job['id'])['cancel_requested'],True)
    def test_source_change_after_preview_blocks_start(self):
        job=self.prepare(); self.source.write_text(self.source.read_text()+'# edit\n')
        with patch.object(serve.subprocess,'Popen') as launch:
            with self.assertRaises(serve.Rejected): self.manager.start(job['id'],dict(digest=job['digest'],confirmed=True))
            launch.assert_not_called()
    def test_worker_snapshot_exact_stdin_fixed_flags_and_independent_checks(self):
        job=self.prepare(); key=job['id']; self.manager.active=key; self.manager.jobs[key]['state']='starting'; launched=[]
        root=self.root; manifest=self.manifest
        class FakeProcess:
            def __init__(self,args,**kwargs): self.returncode=0; self.pid=99999; self.args=args; self.kwargs=kwargs; launched.append(self)
            def communicate(self,prompt,timeout):
                self.prompt=prompt
                data=json.loads(manifest.read_text()); next(c for c in data['cases'] if c['id']=='UC-Z12')['status']='removed'; manifest.write_text(json.dumps(data))
                (root/'backend/feature.py').write_text('# retained infrastructure\n')
                return None,None
            def wait(self,timeout=None): return self.returncode
            def poll(self): return self.returncode
        with patch.object(serve.subprocess,'Popen',FakeProcess),patch.dict(os.environ,{'OPENAI_API_KEY':'DO_NOT_INHERIT','STRIPE_SECRET_KEY':'DO_NOT_INHERIT'}):
            self.manager.run(key)
        result=self.manager.public(key); self.assertEqual(result['state'],'completed'); self.assertEqual(len(result['checks']),6)
        agent=launched[0]; self.assertEqual(agent.prompt,job['prompt']); self.assertEqual(agent.kwargs['cwd'],root)
        self.assertNotIn('shell',agent.kwargs); self.assertIn('workspace-write',agent.args); self.assertIn('--approve-for-me',agent.args)
        self.assertNotIn('OPENAI_API_KEY',agent.kwargs['env']); self.assertNotIn('STRIPE_SECRET_KEY',agent.kwargs['env'])
        self.assertIn('--skip-git-repo-check',agent.args); self.assertEqual(agent.args[-1],'-')
        folder=self.manager.runs/key
        self.assertIn('/feature',(folder/'backup/backend/feature.py').read_text())
        self.assertTrue((folder/'result.json').exists()); self.assertEqual((folder/'agent.private.log').stat().st_mode&0o777,0o600)
        self.assertTrue(any(x['file']=='backend/feature.py' for x in result['changed_files']))
        self.assertIsNone(self.manager.active)
    def test_zero_exit_does_not_claim_undocumented_removal(self):
        job=self.prepare(); self.manager.active=job['id']
        class FakeProcess:
            returncode=0; pid=99999
            def __init__(self,*args,**kwargs): pass
            def communicate(self,*args,**kwargs): return None,None
            def wait(self,*args,**kwargs): return 0
            def poll(self): return 0
        with patch.object(serve.subprocess,'Popen',FakeProcess): self.manager.run(job['id'])
        self.assertEqual(self.manager.public(job['id'])['state'],'needs_review')
    def test_agent_failure_releases_lock_and_never_runs_checks(self):
        job=self.prepare(); self.manager.active=job['id']; launches=[]
        class FailedProcess:
            returncode=1; pid=99999
            def __init__(self,*args,**kwargs): launches.append(args)
            def communicate(self,*args,**kwargs): return None,None
            def poll(self): return 1
        with patch.object(serve.subprocess,'Popen',FailedProcess): self.manager.run(job['id'])
        result=self.manager.public(job['id'])
        self.assertEqual(result['state'],'failed'); self.assertEqual(result['checks'],[])
        self.assertEqual(len(launches),1); self.assertIsNone(self.manager.active)
    def test_cancel_targets_own_process_and_retains_partial_source_changes(self):
        job=self.prepare(); self.manager.active=job['id']; self.manager.jobs[job['id']]['state']='running'
        class RunningProcess:
            pid=424242
            def poll(self): return None
            def wait(self,timeout=None): return 0
        self.manager.process=RunningProcess()
        with patch.object(serve.os,'killpg') as terminate,patch.object(serve.threading,'Thread'):
            result=self.manager.cancel(job['id'])
            terminate.assert_called_once_with(424242,serve.signal.SIGTERM)
            self.assertTrue(result['cancel_requested'])
        self.assertTrue(self.source.is_file())

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=serve.ThreadingHTTPServer(('127.0.0.1',0),serve.Handler)
        cls.port=cls.server.server_port; cls.host=f'127.0.0.1:{cls.port}'
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True); cls.thread.start()
    @classmethod
    def tearDownClass(cls): cls.server.shutdown(); cls.server.server_close(); cls.thread.join()
    def request(self,path='/',method='GET',body=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
        base={'Host':self.host}; base.update(headers or {})
        conn.request(method,path,body=body,headers=base); response=conn.getresponse(); content=response.read(); conn.close()
        return response.status,response,content
    def test_host_cross_site_and_private_paths_rejected(self):
        for headers in [{'Host':'attacker.example'},{'Sec-Fetch-Site':'cross-site'}]: self.assertEqual(self.request('/api/config',headers=headers)[0],403)
        for path in ['/backend/mh.db','/../backend/.env.local','/api/batches/../../private','/runs/private.log']:
            self.assertEqual(self.request(path)[0],404)
    def test_mutations_require_origin_csrf_json_and_bounded_body(self):
        body=json.dumps({'case_ids':['UC-Z12']})
        for headers in [{},{'Origin':'http://attacker.example','X-MH-CSRF':serve.TOKEN},{'Origin':'http://'+self.host,'X-MH-CSRF':'invalid'}]:
            self.assertEqual(self.request('/api/batches','POST',body,headers)[0],403)
        auth={'Origin':'http://'+self.host,'X-MH-CSRF':serve.TOKEN,'Content-Type':'application/json'}
        self.assertEqual(self.request('/api/batches','POST','x'*32769,auth)[0],413)
        self.assertEqual(self.request('/api/batches','POST','invalid',auth)[0],400)
        self.assertEqual(self.request('/api/batches','POST','[]',auth)[0],400)
    def test_prepare_http_never_starts_agent_and_returns_current_prompt(self):
        status=json.loads(self.request('/status.json')[2]); body=json.dumps(dict(case_ids=['UC-Z12'],fingerprint=status['fingerprint']))
        auth={'Origin':'http://'+self.host,'X-MH-CSRF':serve.TOKEN,'Content-Type':'application/json'}
        with patch.object(serve.subprocess,'Popen') as launch:
            code,_,content=self.request('/api/batches','POST',body,auth)
            self.assertEqual(code,200); self.assertEqual(json.loads(content)['state'],'prepared'); launch.assert_not_called()
        code,response,_=self.request('/'); self.assertEqual(code,200); self.assertEqual(response.headers['X-Frame-Options'],'DENY'); self.assertEqual(response.headers['Cache-Control'],'no-store')

if __name__=='__main__': unittest.main()
