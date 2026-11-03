"""Stable ad links and server-confirmed application receipts, isolated by company."""
import json
import re
import hashlib
import ipaddress
import os
import secrets
import time
import threading
from datetime import date, datetime, timezone
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal
from . import auth

CHANNELS = ('Website','Instagram','Facebook','LinkedIn','XING','Meta','Video')


def schema(conn):
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS ad_links (
        id TEXT PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        channel TEXT NOT NULL, variant TEXT NOT NULL, destination TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1, created_at INTEGER NOT NULL,
        UNIQUE(project_id,channel,variant,destination));
    CREATE TABLE IF NOT EXISTS ad_link_hits (
        link_id TEXT NOT NULL REFERENCES ad_links(id) ON DELETE CASCADE,
        day TEXT NOT NULL, count INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(link_id,day));
    CREATE TABLE IF NOT EXISTS application_connectors (
        organization_id INTEGER PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
        key_hash TEXT NOT NULL UNIQUE, created_at INTEGER NOT NULL, last_seen INTEGER);
    CREATE TABLE IF NOT EXISTS application_receipts (
        id INTEGER PRIMARY KEY,
        organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        external_hash TEXT NOT NULL,
        project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        link_id TEXT REFERENCES ad_links(id) ON DELETE SET NULL,
        received_at INTEGER NOT NULL, recorded_at INTEGER NOT NULL,
        UNIQUE(organization_id,external_hash));
    CREATE TABLE IF NOT EXISTS application_pages (
        project_id INTEGER PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
        enabled INTEGER NOT NULL DEFAULT 0, contact_email TEXT NOT NULL, privacy_url TEXT NOT NULL,
        retention_days INTEGER NOT NULL DEFAULT 90);
    CREATE TABLE IF NOT EXISTS hosted_applications (
        receipt_id INTEGER PRIMARY KEY REFERENCES application_receipts(id) ON DELETE CASCADE,
        payload TEXT NOT NULL, expires_at INTEGER NOT NULL);
    CREATE INDEX IF NOT EXISTS application_report ON application_receipts(project_id,received_at);
    ''')


def public_origin():
    return os.getenv('MH_PUBLIC_URL','http://127.0.0.1:5181').rstrip('/')


def public_link(row):
    return {**dict(row),'url':public_origin()+'/r/'+row['id']}


class LinkBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    channel: str
    variant: str = Field(min_length=1,max_length=80)
    destination: str = Field(default="",max_length=2000)
    kind: Literal["hosted","external"] = "hosted"

    @field_validator('channel')
    @classmethod
    def valid_channel(cls,value):
        if value not in CHANNELS:
            raise ValueError('Unknown channel')
        return value

    @field_validator('variant')
    @classmethod
    def valid_variant(cls,value):
        if not value.strip():
            raise ValueError('Variant required')
        return value.strip()

    @field_validator('destination')
    @classmethod
    def valid_destination(cls,value):
        if not value:
            return value
        parsed=urlsplit(value)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or any(ord(c)<33 for c in value):
            raise ValueError('Use a public HTTPS application page without credentials')
        try:
            if not ipaddress.ip_address(parsed.hostname).is_global:
                raise ValueError('Private addresses are not supported')
        except ValueError as error:
            if str(error)=='Private addresses are not supported':
                raise
        if parsed.hostname.lower() in {'localhost','localhost.localdomain'} or '.' not in parsed.hostname:
            raise ValueError('Use a public application page')
        return value


class LinkState(BaseModel):
    active: bool


class Receipt(BaseModel):
    model_config = ConfigDict(extra='forbid')
    application_id: str = Field(min_length=1,max_length=200)
    campaign_id: int = Field(gt=0)
    link_id: str | None = Field(default=None,min_length=20,max_length=64)
    received_at: int = Field(ge=946684800)


class PageBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool
    contact_email: str = Field(min_length=5,max_length=254)
    privacy_url: str = Field(default='',max_length=2000)
    retention_days: int = Field(default=90,ge=7,le=365)

    @field_validator('contact_email')
    @classmethod
    def email(cls,value):
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",value):
            raise ValueError('Invalid contact email')
        return value.strip().lower()

    @field_validator('privacy_url')
    @classmethod
    def privacy(cls,value):
        return LinkBody.valid_destination(value)


class ApplicationBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=2,max_length=160)
    email: str = Field(min_length=5,max_length=254)
    message: str = Field(default='',max_length=5000)
    request_id: str = Field(min_length=20,max_length=80,pattern=r'^[A-Za-z0-9_-]+$')
    link_id: str | None = Field(default=None,min_length=20,max_length=64)
    website: str = Field(default='',max_length=200)
    portal_consent: str = Field(default='',max_length=2000)

    @field_validator('email')
    @classmethod
    def email_valid(cls,value):
        return PageBody.email(value)

    @field_validator('name')
    @classmethod
    def name_valid(cls,value):
        if len(value.strip())<2:
            raise ValueError('Name required')
        return value.strip()


def install(app, db, current_user, require, project_row):
    def real_company_admin(user):
        if user.get('view_role') or user.get('base_role')!='firmen_admin' or user['role']!='firmen_admin' or not user['organization_id']:
            raise HTTPException(403,'Firmen-Admin erforderlich.')
        return user['organization_id']

    def connector(request):
        # These two endpoints accept only a server-held company credential, never cookies.
        if request.headers.get('origin'):
            raise HTTPException(403,'Server-to-server requests only')
        header=request.headers.get('authorization','')
        if not header.startswith('Bearer ') or len(header)>200:
            raise HTTPException(401,'Invalid connector credential')
        key=header[7:]
        with db() as conn:
            row=conn.execute('SELECT * FROM application_connectors WHERE key_hash=?',(auth.digest(key),)).fetchone()
        if not row:
            raise HTTPException(401,'Invalid connector credential')
        auth.rate(db,request,'application-receipt',str(row['organization_id']),limit=300,seconds=60)
        return row

    @app.get('/campaigns/{project_id}/tracking/links')
    def links(project_id:int,user=Depends(current_user)):
        require(user,'campaigns:read')
        with db(user) as conn:
            project_row(conn,project_id,user)
            if user.get('view_role'):
                return {'links':[],'demo':True}
            return {'links':[public_link(r) for r in conn.execute('SELECT * FROM ad_links WHERE project_id=? ORDER BY created_at,id',(project_id,))],'demo':False}

    @app.post('/campaigns/{project_id}/tracking/links',status_code=201)
    def create_link(project_id:int,body:LinkBody,user=Depends(current_user)):
        require(user,'campaigns:write')
        if user.get('view_role'):
            raise HTTPException(403,'Tracking ist in der Demo-Rollenvorschau nicht verfügbar.')
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            project=project_row(conn,project_id,user)
            if body.kind=='external' and not body.destination:
                raise HTTPException(422,'HTTPS-Zielseite erforderlich.')
            destination=body.destination if body.kind=='external' else ''
            from .recruiting import ensure_open
            ensure_open(conn,project_id)
            conn.execute('INSERT OR IGNORE INTO ad_links(id,project_id,organization_id,channel,variant,destination,created_at) VALUES(?,?,?,?,?,?,?)',(secrets.token_urlsafe(24),project_id,project['organization_id'],body.channel,body.variant,destination,int(time.time())))
            row=conn.execute('SELECT * FROM ad_links WHERE project_id=? AND channel=? AND variant=? AND destination=?',(project_id,body.channel,body.variant,destination)).fetchone()
            return public_link(row)

    @app.patch('/campaigns/{project_id}/tracking/links/{link_id}')
    def update_link(project_id:int,link_id:str,body:LinkState,user=Depends(current_user)):
        require(user,'campaigns:write')
        if user.get('view_role'):
            raise HTTPException(403,'Tracking ist in der Demo-Rollenvorschau nicht verfügbar.')
        with db() as conn:
            project_row(conn,project_id,user)
            row=conn.execute('SELECT * FROM ad_links WHERE id=? AND project_id=?',(link_id,project_id)).fetchone()
            if not row:
                raise HTTPException(404,'Not found')
            if body.active:
                from .recruiting import ensure_open
                ensure_open(conn,project_id)
            conn.execute('UPDATE ad_links SET active=? WHERE id=?',(int(body.active),link_id))
        return {'ok':True}

    @app.get('/tracking/r/{link_id}')
    def redirect(link_id:str,request:Request):
        auth.rate(db,request,'ad-link',link_id,limit=120,seconds=60)
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row=conn.execute('SELECT * FROM ad_links WHERE id=? AND active=1',(link_id,)).fetchone()
            if not row:
                raise HTTPException(404,'Link unavailable')
            # Aggregate requests only. A hit is not a unique person or application.
            day=datetime.now(timezone.utc).date().isoformat()
            conn.execute('INSERT INTO ad_link_hits(link_id,day,count) VALUES(?,?,1) ON CONFLICT(link_id,day) DO UPDATE SET count=count+1',(link_id,day))
        if not row['destination']:
            with db() as conn:
                portal = conn.execute('SELECT 1 FROM job_portal_plans WHERE project_id=?',(row['project_id'],)).fetchone()
            route = '/jobs/' if portal else '/apply/'
            return RedirectResponse(public_origin()+route+str(row['project_id'])+'?mh_link='+row['id'],status_code=302,headers={'X-Robots-Tag':'noindex, nofollow','Referrer-Policy':'no-referrer','Cache-Control':'no-store'})
        target=urlsplit(row['destination'])
        replacements={'mh_link':row['id'],'utm_source':row['channel'].lower(),'utm_medium':'recruiting','utm_campaign':'mh_'+str(row['project_id']),'utm_content':row['variant']}
        query=[(k,v) for k,v in parse_qsl(target.query,keep_blank_values=True) if k not in replacements]+list(replacements.items())
        return RedirectResponse(urlunsplit((target.scheme,target.netloc,target.path,urlencode(query),target.fragment)),status_code=302,headers={'X-Robots-Tag':'noindex, nofollow','Referrer-Policy':'no-referrer','Cache-Control':'no-store'})

    @app.get('/tracking/connector')
    def connection(user=Depends(current_user)):
        org=real_company_admin(user)
        with db() as conn:
            row=conn.execute('SELECT created_at,last_seen FROM application_connectors WHERE organization_id=?',(org,)).fetchone()
        return {'configured':bool(row),'last_seen':row['last_seen'] if row else None}

    @app.post('/tracking/connector')
    def create_connection(user=Depends(current_user)):
        org=real_company_admin(user)
        key=secrets.token_urlsafe(48)
        with db() as conn:
            conn.execute('INSERT INTO application_connectors(organization_id,key_hash,created_at) VALUES(?,?,?) ON CONFLICT(organization_id) DO UPDATE SET key_hash=excluded.key_hash,created_at=excluded.created_at,last_seen=NULL',(org,auth.digest(key),int(time.time())))
        return {'key':key,'path':'/tracking/receipts','check_path':'/tracking/receipts/check'}

    @app.post('/tracking/receipts/check')
    def check_connection(request:Request):
        row=connector(request)
        with db() as conn:
            conn.execute('UPDATE application_connectors SET last_seen=? WHERE organization_id=?',(int(time.time()),row['organization_id']))
        return {'ok':True}

    @app.post('/tracking/receipts')
    def receipt(body:Receipt,request:Request):
        integration=connector(request)
        if body.received_at>int(time.time())+300:
            raise HTTPException(422,'Receipt timestamp is in the future')
        # Store a digest rather than an ATS identifier that may contain personal data.
        external=hashlib.sha256(body.application_id.encode()).hexdigest()
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            project=conn.execute('SELECT id FROM projects WHERE id=? AND organization_id=?',(body.campaign_id,integration['organization_id'])).fetchone()
            if not project:
                raise HTTPException(404,'Not found')
            if body.link_id and not conn.execute('SELECT 1 FROM ad_links WHERE id=? AND project_id=? AND organization_id=?',(body.link_id,body.campaign_id,integration['organization_id'])).fetchone():
                raise HTTPException(422,'Link does not belong to this campaign')
            existing=conn.execute('SELECT * FROM application_receipts WHERE organization_id=? AND external_hash=?',(integration['organization_id'],external)).fetchone()
            if existing:
                if existing['project_id']!=body.campaign_id or existing['link_id']!=body.link_id or existing['received_at']!=body.received_at:
                    raise HTTPException(409,'Application ID already recorded with different data')
            else:
                conn.execute('INSERT INTO application_receipts(organization_id,external_hash,project_id,link_id,received_at,recorded_at) VALUES(?,?,?,?,?,?)',(integration['organization_id'],external,body.campaign_id,body.link_id,body.received_at,int(time.time())))
            conn.execute('UPDATE application_connectors SET last_seen=? WHERE organization_id=?',(int(time.time()),integration['organization_id']))
        return {'ok':True,'duplicate':bool(existing)}

    @app.get('/campaigns/{project_id}/tracking/report')
    def report(project_id:int,start:date|None=None,end:date|None=None,user=Depends(current_user)):
        require(user,'campaigns:read')
        today=datetime.now(timezone.utc).date()
        start=start or today.replace(day=1)
        end=end or today
        if start>end:
            raise HTTPException(422,'Invalid date range')
        lower=int(datetime.combine(start,datetime.min.time(),timezone.utc).timestamp())
        upper=int(datetime.combine(end,datetime.min.time(),timezone.utc).timestamp())+86400
        with db(user) as conn:
            project=project_row(conn,project_id,user)
            if user.get('view_role'):
                return {'demo':True,'connected':False,'total':None,'attributed':None,'unknown':None,'links':[],'start':str(start),'end':str(end),'timezone':'UTC','last_seen':None,'updated_at':int(time.time())}
            integration=conn.execute('SELECT last_seen FROM application_connectors WHERE organization_id=?',(project['organization_id'],)).fetchone()
            page=conn.execute('SELECT enabled FROM application_pages WHERE project_id=?',(project_id,)).fetchone()
            connected=bool((integration and integration['last_seen']) or page)
            last_receipt=conn.execute('SELECT MAX(recorded_at) FROM application_receipts WHERE project_id=?',(project_id,)).fetchone()[0]
            counts=conn.execute('SELECT COUNT(*) AS total,COUNT(link_id) AS attributed FROM application_receipts WHERE project_id=? AND received_at>=? AND received_at<?',(project_id,lower,upper)).fetchone()
            result=[]
            for link in conn.execute('SELECT * FROM ad_links WHERE project_id=? ORDER BY created_at,id',(project_id,)).fetchall():
                hits=conn.execute('SELECT COALESCE(SUM(count),0) FROM ad_link_hits WHERE link_id=? AND day>=? AND day<=?',(link['id'],str(start),str(end))).fetchone()[0]
                applications=conn.execute('SELECT COUNT(*) FROM application_receipts WHERE link_id=? AND received_at>=? AND received_at<?',(link['id'],lower,upper)).fetchone()[0]
                result.append({**public_link(link),'hits':hits,'applications':applications if connected else None})
            return {'demo':False,'connected':connected,'total':counts['total'] if connected else None,'attributed':counts['attributed'] if connected else None,'unknown':counts['total']-counts['attributed'] if connected else None,'links':result,'start':str(start),'end':str(end),'timezone':'UTC','last_seen':last_receipt or (integration['last_seen'] if integration else None),'updated_at':int(time.time())}

    @app.get('/campaigns/{project_id}/tracking/page')
    def page_settings(project_id:int,user=Depends(current_user)):
        require(user,'campaigns:read')
        with db(user) as conn:
            project_row(conn,project_id,user)
            if user.get('view_role'):
                return {'page':None,'demo':True}
            row=conn.execute('SELECT * FROM application_pages WHERE project_id=?',(project_id,)).fetchone()
        return {'page':dict(row) if row else None,'demo':False,'url':public_origin()+'/apply/'+str(project_id)}

    @app.post('/campaigns/{project_id}/tracking/page')
    def configure_page(project_id:int,body:PageBody,user=Depends(current_user)):
        org=real_company_admin(user)
        require(user,'campaigns:write')
        if body.enabled and auth.production() and not body.privacy_url:
            raise HTTPException(422,'Datenschutz-URL für die öffentliche Bewerbungsseite erforderlich.')
        with db() as conn:
            project=project_row(conn,project_id,user)
            if project['organization_id']!=org:
                raise HTTPException(404,'Not found')
            if body.enabled:
                from .recruiting import ensure_open
                ensure_open(conn,project_id)
            if body.enabled and (project['status']!='Live' or not json.loads(project['generated']).get('jobAd')):
                raise HTTPException(409,'Anzeige zuerst freigeben und Stellenanzeigentext speichern.')
            conn.execute('INSERT INTO application_pages(project_id,enabled,contact_email,privacy_url,retention_days) VALUES(?,?,?,?,?) ON CONFLICT(project_id) DO UPDATE SET enabled=excluded.enabled,contact_email=excluded.contact_email,privacy_url=excluded.privacy_url,retention_days=excluded.retention_days',(project_id,int(body.enabled),body.contact_email,body.privacy_url,body.retention_days))
        return {'ok':True}

    def published(conn,project_id):
        from .job_portal import assert_not_expired
        assert_not_expired(conn,project_id)
        from .recruiting import ensure_open
        try:
            ensure_open(conn,project_id)
        except HTTPException:
            raise HTTPException(404,'Bewerbungsseite nicht verfügbar.') from None
        row=conn.execute("SELECT p.role,p.location,p.generated,p.organization_id,o.name AS company,a.* FROM application_pages a JOIN projects p ON p.id=a.project_id JOIN organizations o ON o.id=p.organization_id WHERE a.project_id=? AND a.enabled=1 AND p.status='Live'",(project_id,)).fetchone()
        if not row:
            raise HTTPException(404,'Bewerbungsseite nicht verfügbar.')
        return row

    @app.get('/tracking/apply/{project_id}')
    def public_page(project_id:int):
        with db() as conn:
            row=published(conn,project_id)
        return {'campaign_id':project_id,'title':row['role'],'location':row['location'],'company':row['company'],'text':json.loads(row['generated']).get('jobAd',''),'contact_email':row['contact_email'],'privacy_url':row['privacy_url'],'retention_days':row['retention_days'],'test':not auth.production()}

    @app.post('/tracking/apply/{project_id}',status_code=201)
    def apply(project_id:int,body:ApplicationBody,request:Request):
        if body.website:
            raise HTTPException(422,'Submission rejected')
        auth.rate(db,request,'hosted-application',str(project_id),limit=10,seconds=3600)
        data={'name':body.name,'email':body.email,'message':body.message}
        now=int(time.time())
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row=published(conn,project_id)
            if body.link_id and not conn.execute('SELECT 1 FROM ad_links WHERE id=? AND project_id=? AND organization_id=?',(body.link_id,project_id,row['organization_id'])).fetchone():
                raise HTTPException(422,'Anzeigenlink gehört nicht zu dieser Bewerbung.')
            external=auth.digest('hosted:'+str(project_id)+':'+body.request_id)
            existing=conn.execute('SELECT r.id,r.link_id,h.payload FROM application_receipts r JOIN hosted_applications h ON h.receipt_id=r.id WHERE r.organization_id=? AND r.external_hash=?',(row['organization_id'],external)).fetchone()
            if existing:
                if not existing['payload'] or existing['link_id']!=body.link_id or json.loads(auth.cipher().decrypt(existing['payload'].encode()))!=data:
                    raise HTTPException(409,'Anfrage bereits mit anderen Daten verarbeitet.')
            else:
                receipt_id=conn.execute('INSERT INTO application_receipts(organization_id,external_hash,project_id,link_id,received_at,recorded_at) VALUES(?,?,?,?,?,?)',(row['organization_id'],external,project_id,body.link_id,now,now)).lastrowid
                encrypted=auth.cipher().encrypt(json.dumps(data,ensure_ascii=False).encode()).decode()
                conn.execute('INSERT INTO hosted_applications(receipt_id,payload,expires_at) VALUES(?,?,?)',(receipt_id,encrypted,now+row['retention_days']*86400))
                from .recruiting import create_case
                create_case(conn,receipt_id)
                from .job_portal import application_event
                application_event(conn,project_id,body.portal_consent)
            conn.execute("UPDATE hosted_applications SET payload='' WHERE expires_at<=?",(now,))
        return {'ok':True,'duplicate':bool(existing)}

    @app.get('/campaigns/{project_id}/tracking/applications')
    def applications(project_id:int,user=Depends(current_user)):
        if user.get('view_role') or user['role'] not in {'firmen_admin','user'}:
            raise HTTPException(403,'Bewerbungen sind nur für das Firmenteam zugänglich.')
        with db() as conn:
            project_row(conn,project_id,user)
            conn.execute("UPDATE hosted_applications SET payload='' WHERE expires_at<=?",(int(time.time()),))
            rows=conn.execute("SELECT r.id,r.received_at,l.channel,l.variant,h.payload,h.expires_at FROM application_receipts r JOIN hosted_applications h ON h.receipt_id=r.id LEFT JOIN ad_links l ON l.id=r.link_id WHERE r.project_id=? ORDER BY r.received_at DESC,r.id DESC LIMIT 100",(project_id,)).fetchall()
        return {'applications':[{**{k:r[k] for k in ('id','received_at','channel','variant','expires_at')},'contact':json.loads(auth.cipher().decrypt(r['payload'].encode())) if r['payload'] else None} for r in rows]}

    stop = threading.Event()
    worker = None
    def purge():
        while not stop.is_set():
            with db() as conn:
                from .recruiting import purge as purge_workflow
                purge_workflow(conn)
            stop.wait(60)
    @app.on_event('startup')
    def start_purge():
        nonlocal worker
        stop.clear()
        worker=threading.Thread(target=purge,daemon=True,name='mh-application-retention')
        worker.start()
    @app.on_event('shutdown')
    def stop_purge():
        stop.set()
        if worker:
            worker.join(timeout=5)
