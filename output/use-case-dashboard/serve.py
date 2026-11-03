"""Loopback digital twin. Explicit CSRF-protected local Codex start; no private file serving."""
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import twin

ROOT=twin.ROOT
HERE=Path(__file__).resolve().parent
TOKEN=secrets.token_urlsafe(32)
PORT=5190

def now(): return datetime.now(timezone.utc).isoformat()
def private_json(path,value):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as f: json.dump(value,f,ensure_ascii=False,indent=2)
class Rejected(Exception):
    def __init__(self,message,code=400): super().__init__(message); self.code=code

class Manager:
    def __init__(self,root=ROOT,binary=None):
        self.root=root; self.runs=root/'output/use-case-dashboard/runs'
        self.binary=binary or shutil.which('codex'); self.lock=threading.RLock()
        self.jobs={}; self.process=None; self.active=None
    def config(self):
        return dict(available=bool(self.binary),name='Lokaler Projekt-Agent · Codex',active=self.active,
                    authentication='Gespeicherte lokale Anmeldung; Anbieterzugang beim Start geprüft',project=str(self.root))
    def prepare(self,body):
        data=twin.status(self.root); ids=body.get('case_ids'); note=body.get('note','')
        if not isinstance(ids,list) or not ids or len(ids)>len(data['cases']) or any(not isinstance(x,str) for x in ids) or len(ids)!=len(set(ids)):
            raise Rejected('Wähle eindeutige Use Cases aus dem aktuellen Katalog.')
        by_id={c['id']:c for c in data['cases']}
        if any(x not in by_id or by_id[x]['status']=='removed' for x in ids): raise Rejected('Use Case unbekannt oder bereits entfernt.')
        if not isinstance(note,str) or len(note)>4000: raise Rejected('Änderungswunsch: höchstens 4.000 Zeichen.')
        if body.get('fingerprint')!=data['fingerprint']: raise Rejected('Quellstand verändert. Aktualisiere und prüfe den Batch erneut.',409)
        prompt=twin.batch_prompt(ids,data,note); key=secrets.token_hex(12)
        job=dict(id=key,state='prepared',created_at=now(),case_ids=ids,prompt=prompt,
                 digest=hashlib.sha256(prompt.encode()).hexdigest(),fingerprint=data['fingerprint'],checks=[],changed_files=[],
                 message='Batch vorbereitet. Der Agent startet erst mit deinem Start-Button.')
        with self.lock: self.jobs[key]=job
        return self.public(key)
    def public(self,key):
        with self.lock:
            if key not in self.jobs: raise Rejected('Batch nicht verfügbar. Nach Server-Neustart neu vorbereiten.',404)
            job=self.jobs[key]; result={k:v for k,v in job.items() if k!='before'}
            if job.get('before'):
                current=twin.hashes(self.root)
                result['changed_files']=[dict(file=f,kind='neu' if f not in job['before'] else 'entfernt' if f not in current else 'geändert')
                                        for f in sorted(set(current)|set(job['before'])) if current.get(f)!=job['before'].get(f)]
            return result
    def start(self,key,body):
        with self.lock:
            self.public(key); job=self.jobs[key]
            if body.get('confirmed') is not True or body.get('digest')!=job['digest']: raise Rejected('Prüfe den Batch und bestätige den Start ausdrücklich.',409)
            if job['state']!='prepared': return self.public(key)
            if self.active: raise Rejected('Ein Projektauftrag läuft bereits.',409)
            if twin.fingerprint(self.root)!=job['fingerprint']: raise Rejected('Quellen seit Vorschau verändert. Batch neu vorbereiten.',409)
            if not self.binary: raise Rejected('Codex ist lokal nicht verfügbar.',503)
            self.active=key; job.update(state='starting',message='Quellcode-Sicherung wird angelegt.',started_at=now())
            threading.Thread(target=self.run,args=(key,),daemon=True).start()
            return self.public(key)
    def cancel(self,key):
        with self.lock:
            self.public(key); job=self.jobs[key]
            if self.active!=key: return self.public(key)
            job['cancel_requested']=True; job['message']='Abbruch angefordert. Bereits erfolgte Änderungen bleiben zur Prüfung erhalten.'
            process=self.process
            if process and process.poll() is None:
                try: os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError: pass
                def finish_cancel():
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        try: os.killpg(process.pid,signal.SIGKILL)
                        except ProcessLookupError: pass
                threading.Thread(target=finish_cancel,daemon=True).start()
            return self.public(key)
    def run(self,key):
        job=self.jobs[key]; folder=self.runs/key
        try:
            folder.mkdir(parents=True,mode=0o700,exist_ok=False); os.chmod(self.runs,0o700)
            before=twin.hashes(self.root)
            if twin.fingerprint(self.root)!=job['fingerprint']: raise Rejected('Quellen vor dem Start verändert. Erneut prüfen.',409)
            for name,path in twin.source_files(self.root).items():
                target=folder/'backup'/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(path.read_bytes())
            if twin.hashes(self.root)!=before: raise Rejected('Quellen während Sicherung verändert. Kein Agent gestartet.',409)
            job['before']=before; private_json(folder/'source-hashes.json',before)
            (folder/'prompt.txt').write_text(job['prompt']); os.chmod(folder/'prompt.txt',0o600)
            schema={'type':'object','properties':{'summary':{'type':'string'},'removed_use_cases':{'type':'array','items':{'type':'string'}},
                    'blocked_use_cases':{'type':'array','items':{'type':'string'}}},'required':['summary','removed_use_cases','blocked_use_cases'],'additionalProperties':False}
            private_json(folder/'schema.json',schema)
            command=[self.binary,'exec','--sandbox','workspace-write','--approve-for-me','--skip-git-repo-check','--cd',str(self.root),
                     '--color','never','--json','--output-schema',str(folder/'schema.json'),'--output-last-message',str(folder/'outcome.json'),'-']
            allowed={'HOME','PATH','USER','LOGNAME','SHELL','LANG','LC_ALL','TMPDIR','CODEX_HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','SSL_CERT_FILE','SSL_CERT_DIR'}
            environment={k:v for k,v in os.environ.items() if k in allowed}
            with self.lock:
                if job.get('cancel_requested'): return
                job.update(state='running',message='Projekt-Agent bearbeitet den geprüften Lösch-Batch.')
            with open(folder/'agent.private.log','w') as log:
                os.chmod(log.name,0o600)
                with self.lock:
                    if job.get('cancel_requested'): return
                    self.process=subprocess.Popen(command,cwd=self.root,env=environment,stdin=subprocess.PIPE,stdout=log,stderr=log,text=True,start_new_session=True)
                    process=self.process
                try: process.communicate(job['prompt'],timeout=3600)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL); process.wait(); raise Rejected('Zeitlimit erreicht. Änderungen und Quellsicherung bleiben erhalten.')
            if job.get('cancel_requested'): return
            if process.returncode!=0: raise Rejected('Agent konnte den Auftrag nicht abschließen. Anmeldung, Anbieterzugang oder Freigaben prüfen. Details nur im privaten lokalen Laufprotokoll.')
            job.update(state='validating',message='Dashboard prüft die Änderungen unabhängig vom Agenten.')
            for arguments,subdir in twin.CHECKS:
                if job.get('cancel_requested'): return
                entry=dict(name='Backend-Vollprüfung' if not subdir else ' '.join(arguments),status='running'); job['checks'].append(entry)
                with open(folder/('check-'+str(len(job['checks']))+'.private.log'),'w') as log:
                    os.chmod(log.name,0o600)
                    with self.lock:
                        if job.get('cancel_requested'): return
                        self.process=subprocess.Popen(arguments,cwd=self.root/subdir,env=environment,stdout=log,stderr=log,start_new_session=True)
                        check=self.process
                    try: code=check.wait(timeout=900)
                    except subprocess.TimeoutExpired: os.killpg(check.pid,signal.SIGKILL); check.wait(); code=-1
                entry['status']='passed' if code==0 else 'failed'
            catalog=json.loads((self.root/'docs/requirements/use_case_status.json').read_text())
            removed=[c['id'] for c in catalog['cases'] if c['id'] in job['case_ids'] and c['status']=='removed']
            passed=all(c['status']=='passed' for c in job['checks'])
            job.update(removed_use_cases=removed,state='completed' if passed and set(removed)==set(job['case_ids']) else 'needs_review',
                       message='Prüfungen bestanden; ausgewählte Einträge als entfernt dokumentiert. Änderungen bitte ansehen.' if passed and set(removed)==set(job['case_ids'])
                       else 'Auftrag benötigt Prüfung: Tests oder dokumentierte Entfernung sind unvollständig.')
        except Exception as exc:
            job.update(state='failed',message=str(exc) if isinstance(exc,Rejected) else 'Lokale Ausführung fehlgeschlagen. Quellsicherung und private Laufdateien prüfen.')
        finally:
            with self.lock:
                if job.get('cancel_requested'): job.update(state='cancelled',message='Ausführung beendet. Änderungen wurden nicht automatisch zurückgesetzt.')
                job['finished_at']=now(); self.active=None; self.process=None
                if folder.exists(): private_json(folder/'result.json',self.public(key))

manager=Manager()
class Handler(BaseHTTPRequestHandler):
    def guard(self,mutation=False):
        host=self.headers.get('Host',''); allowed=(f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
        if host not in allowed or self.headers.get('Sec-Fetch-Site')=='cross-site': raise Rejected('Nur lokale direkte Zugriffe zugelassen.',403)
        if mutation:
            if self.headers.get('Origin')!='http://'+host: raise Rejected('Ungültige Herkunft.',403)
            if not hmac.compare_digest(self.headers.get('X-MH-CSRF',''),TOKEN): raise Rejected('Ungültige Startberechtigung. Seite neu laden.',403)
    def send(self,value,code=200,html=False):
        body=value if html else json.dumps(value,ensure_ascii=False).encode(); self.send_response(code)
        for k,v in [('Content-Type','text/html; charset=utf-8' if html else 'application/json; charset=utf-8'),('Cache-Control','no-store'),
                    ('X-Content-Type-Options','nosniff'),('X-Frame-Options','DENY'),('Referrer-Policy','no-referrer'),
                    ('Content-Security-Policy',"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"),('Content-Length',str(len(body)))]: self.send_header(k,v)
        self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        try:
            self.guard(); path=self.path.split('?')[0]
            if path in ('/','/index.html'): self.send((HERE/'index.html').read_bytes(),html=True)
            elif path=='/status.json':
                data=twin.status(); data.update(live=True,checked_at=now()); self.send(data)
            elif path=='/api/config': self.send(dict(csrf=TOKEN,**manager.config()))
            elif re.fullmatch(r'/api/batches/[a-f0-9]{24}',path): self.send(manager.public(path.rsplit('/',1)[1]))
            else: raise Rejected('Nicht verfügbar.',404)
        except Rejected as exc: self.send(dict(error=str(exc)),exc.code)
    def do_POST(self):
        try:
            self.guard(mutation=True)
            if self.headers.get('Transfer-Encoding') or self.headers.get_content_type()!='application/json': raise Rejected('JSON-Anfrage erforderlich.',415)
            length=self.headers.get('Content-Length','')
            if not length.isdecimal() or not 0<int(length)<=32768: raise Rejected('Anfrage zu groß oder unvollständig.',413)
            try: body=json.loads(self.rfile.read(int(length)))
            except (ValueError,UnicodeError): raise Rejected('Ungültige JSON-Anfrage.')
            if not isinstance(body,dict): raise Rejected('JSON-Objekt erforderlich.')
            if self.path=='/api/batches': self.send(manager.prepare(body))
            else:
                match=re.fullmatch(r'/api/batches/([a-f0-9]{24})/(start|cancel)',self.path)
                if not match: raise Rejected('Nicht verfügbar.',404)
                self.send(manager.start(match[1],body) if match[2]=='start' else manager.cancel(match[1]))
        except Rejected as exc: self.send(dict(error=str(exc)),exc.code)
    def log_message(self,*_): pass
if __name__=='__main__':
    print(f'MH Digitaler Zwilling: http://127.0.0.1:{PORT}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
