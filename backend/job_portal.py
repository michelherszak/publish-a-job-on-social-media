"""Local job directory, consented engagement and a shared advertising plan.

No social, advertising or pixel provider calls are made by this module.
"""
import base64
import hashlib
import json
import re
import secrets
import time
from datetime import datetime, timezone, date
from typing import Literal
from zoneinfo import ZoneInfo

from cryptography.fernet import InvalidToken
from fastapi import Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from . import auth, tracking, recruiting, campaign_workflow

CONSENT_VERSION = 'jobs-v1'


def schema(conn):
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS job_portal_plans (
      project_id INTEGER PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
      country TEXT NOT NULL DEFAULT 'DE', employment TEXT NOT NULL DEFAULT '', work_mode TEXT NOT NULL DEFAULT '',
      ends_at INTEGER NOT NULL DEFAULT 0, budget_cents INTEGER NOT NULL DEFAULT 15000,
      duration_days INTEGER NOT NULL DEFAULT 14, retargeting INTEGER NOT NULL DEFAULT 1,
      revision INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS job_daily (
      project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, day TEXT NOT NULL,
      requests INTEGER NOT NULL DEFAULT 0, consented_views INTEGER NOT NULL DEFAULT 0,
      engaged INTEGER NOT NULL DEFAULT 0, form_started INTEGER NOT NULL DEFAULT 0,
      consented_applications INTEGER NOT NULL DEFAULT 0, retargeting_eligible INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(project_id,day));
    CREATE TABLE IF NOT EXISTS job_flows (
      key_hash TEXT PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
      day TEXT NOT NULL, expires_at INTEGER NOT NULL, analytics INTEGER NOT NULL, marketing INTEGER NOT NULL,
      engaged INTEGER NOT NULL DEFAULT 0, form_started INTEGER NOT NULL DEFAULT 0,
      applied INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS job_distribution (
      project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
      channel TEXT NOT NULL, kind TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'prepared',
      link_id TEXT NOT NULL REFERENCES ad_links(id) ON DELETE CASCADE,
      created_at INTEGER NOT NULL, PRIMARY KEY(project_id,channel,kind));
    ''')
    if 'published_at' not in {r['name'] for r in conn.execute('PRAGMA table_info(job_portal_plans)')}:
        conn.execute('ALTER TABLE job_portal_plans ADD COLUMN published_at INTEGER NOT NULL DEFAULT 0')
    columns = {r['name'] for r in conn.execute('PRAGMA table_info(job_flows)')}
    for name, default in [('channel','Direct'),('kind','direct')]:
        if name not in columns:
            conn.execute(f"ALTER TABLE job_flows ADD COLUMN {name} TEXT NOT NULL DEFAULT '{default}'")
    conn.executescript('''CREATE TABLE IF NOT EXISTS job_channel_daily (
      project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, day TEXT NOT NULL,
      channel TEXT NOT NULL, kind TEXT NOT NULL, consented_views INTEGER NOT NULL DEFAULT 0,
      engaged INTEGER NOT NULL DEFAULT 0,form_started INTEGER NOT NULL DEFAULT 0,consented_applications INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY(project_id,day,channel,kind));''')
    for table in ('job_daily','job_channel_daily'):
        if 'engaged_applications' not in {r['name'] for r in conn.execute(f'PRAGMA table_info({table})')}:
            conn.execute(f'ALTER TABLE {table} ADD COLUMN engaged_applications INTEGER NOT NULL DEFAULT 0')
    campaign_workflow.schema(conn)


def day_now():
    return datetime.now(timezone.utc).date().isoformat()


def increment(conn, pid, day, column):
    # Column is supplied only by fixed code paths, never by request input.
    conn.execute(f'INSERT INTO job_daily(project_id,day,{column}) VALUES(?,?,1) ON CONFLICT(project_id,day) DO UPDATE SET {column}={column}+1', (pid, day))


def increment_flow(conn, row, column):
    increment(conn, row['project_id'], row['day'], column)
    conn.execute(f'INSERT INTO job_channel_daily(project_id,day,channel,kind,{column}) VALUES(?,?,?,?,1) ON CONFLICT(project_id,day,channel,kind) DO UPDATE SET {column}={column}+1',
                 (row['project_id'],row['day'],row['channel'],row['kind']))


def purge(conn):
    conn.execute('DELETE FROM job_flows WHERE expires_at<=?', (int(time.time()),))


def open_rows(conn):
    return conn.execute('''SELECT p.id,p.role,p.location,p.briefing,p.generated,p.updated_at,o.name AS company,
      a.contact_email,a.privacy_url,a.retention_days,j.employment,j.work_mode,j.ends_at,j.retargeting,j.published_at,
      i.id AS image_id,i.revision AS image_revision
      FROM projects p JOIN organizations o ON o.id=p.organization_id
      JOIN application_pages a ON a.project_id=p.id
      LEFT JOIN job_portal_plans j ON j.project_id=p.id
      LEFT JOIN recruiting_needs n ON n.project_id=p.id
      LEFT JOIN campaign_images i ON i.project_id=p.id AND i.selected=1
      WHERE p.status='Live' AND a.enabled=1 AND COALESCE(n.state,'open')='open'
      AND j.country='DE' AND (COALESCE(j.ends_at,0)=0 OR j.ends_at>?)
      ORDER BY p.updated_at DESC,p.id DESC''', (int(time.time()),)).fetchall()


def public_row(conn, pid):
    row = next((r for r in open_rows(conn) if r['id'] == pid), None)
    if not row or not json.loads(row['generated']).get('jobAd', '').strip():
        raise HTTPException(404, 'Diese Stelle ist nicht mehr verfügbar.')
    return row


def assert_not_expired(conn, pid):
    row = conn.execute('SELECT ends_at FROM job_portal_plans WHERE project_id=?', (pid,)).fetchone()
    if row and row['ends_at'] and row['ends_at'] <= int(time.time()):
        raise HTTPException(404, 'Bewerbungsseite nicht verfügbar.')


def summary(row):
    briefing = json.loads(row['briefing'])
    return dict(id=row['id'], title=row['role'], location=row['location'], company=row['company'],
                employment=row['employment'] or '', employment_text=briefing.get('employment_type',''),
                work_mode=row['work_mode'] or '', country='DE', salary=briefing.get('salary',''),
                updated_at=row['updated_at'], date_posted=row['published_at'], ends_at=row['ends_at'], image=bool(row['image_id']))


class Plan(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: int = Field(default=0, ge=0)
    country: Literal['DE'] = 'DE'
    employment: Literal['', 'full_time', 'part_time', 'apprenticeship', 'mini_job', 'temporary'] = ''
    work_mode: Literal['', 'onsite', 'hybrid', 'remote'] = ''
    ends_at: int = Field(default=0, ge=0)
    ends_on: str = Field(default='',max_length=10)
    budget_cents: int = Field(default=15000, ge=0, le=1_000_000)
    duration_days: int = Field(default=14, ge=1, le=90)
    retargeting: bool = True
    contact_email: str = Field(min_length=5, max_length=254)
    privacy_url: str = Field(default='', max_length=2000)
    retention_days: int = Field(default=90, ge=7, le=365)

    @field_validator('contact_email')
    @classmethod
    def email(cls, value):
        return tracking.PageBody.email(value)

    @field_validator('privacy_url')
    @classmethod
    def privacy(cls, value):
        return tracking.PageBody.privacy(value)


class Publication(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: int = Field(ge=1)
    image_revision: int = Field(default=0, ge=0)


class Choice(BaseModel):
    model_config = ConfigDict(extra='forbid')
    analytics: bool
    marketing: bool
    version: Literal['jobs-v1']
    request_id: str = Field(default='',max_length=80,pattern=r'^[A-Za-z0-9_-]*$')
    link_id: str = Field(default='',max_length=64)


class Event(BaseModel):
    model_config = ConfigDict(extra='forbid')
    token: str = Field(min_length=40, max_length=2000)
    event: Literal['engaged', 'form_started']
    active_seconds: int = Field(default=0, ge=0, le=86400)
    section_percent: int = Field(default=0, ge=0, le=100)


class WorkflowRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    run_id: int = Field(ge=1)
    reconcile: bool = False


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    run_id: int = Field(ge=1)
    request_id: str = Field(min_length=16,max_length=80,pattern=r'^[A-Za-z0-9_-]+$')


class Token(BaseModel):
    token: str = Field(min_length=40, max_length=2000)


def flow(conn, pid, token):
    try:
        if base64.urlsafe_b64encode(base64.urlsafe_b64decode(token.encode())).decode() != token:
            raise ValueError()
        data = json.loads(auth.cipher().decrypt(token.encode(), ttl=86400))
        if data['pid'] != pid or data['version'] != CONSENT_VERSION:
            raise ValueError()
        row = conn.execute('SELECT * FROM job_flows WHERE key_hash=? AND project_id=? AND expires_at>?',
                           (hashlib.sha256((str(pid)+':'+data['key']).encode()).hexdigest(), pid, int(time.time()))).fetchone()
        if not row:
            raise ValueError()
        return row
    except (InvalidToken, ValueError, KeyError, TypeError):
        raise HTTPException(403, 'Analyse-Einwilligung fehlt oder ist abgelaufen.') from None


def application_event(conn, pid, token):
    if not token:
        return
    try:
        row = flow(conn, pid, token)
    except HTTPException:
        # Optional analytics must never block a legitimate application.
        return
    if not row['applied']:
        conn.execute('UPDATE job_flows SET applied=1 WHERE key_hash=?', (row['key_hash'],))
        if row['analytics']:
            increment_flow(conn, row, 'consented_applications')
            if row['engaged']:
                increment_flow(conn,row,'engaged_applications')
        campaign_workflow.reconcile_lifecycle(conn, pid)


def get_plan(conn, project):
    row = conn.execute('SELECT * FROM job_portal_plans WHERE project_id=?', (project['id'],)).fetchone()
    page = conn.execute('SELECT * FROM application_pages WHERE project_id=?', (project['id'],)).fetchone()
    plan = dict(row) if row else dict(country='DE', employment='', work_mode='', ends_at=0, budget_cents=15000,
                                    duration_days=14, retargeting=True, revision=0)
    plan.pop('project_id', None)
    plan.pop('published_at', None)  # Read-only SEO metadata is not part of the editable advertising plan.
    plan.update(contact_email=page['contact_email'] if page else '', privacy_url=page['privacy_url'] if page else '',
                retention_days=page['retention_days'] if page else 90)
    plan['ends_on'] = datetime.fromtimestamp(plan['ends_at'],ZoneInfo('Europe/Berlin')).date().isoformat() if plan['ends_at'] else ''
    return plan


def install(app, db, current_user, require, project_row, history):
    def admin(conn, pid, user):
        require(user, 'campaigns:write')
        project = project_row(conn, pid, user)
        if user.get('view_role') or user['role'] != 'firmen_admin' or user.get('base_role') != 'firmen_admin':
            raise HTTPException(403, 'Firmen-Admin erforderlich.')
        return project

    @app.get('/jobs')
    def directory(q: str = Query(default='', max_length=100), location: str = Query(default='', max_length=100),
                  company: str = Query(default='', max_length=160), employment: str = Query(default='', max_length=30),
                  work_mode: str = Query(default='', max_length=30), offset: int = Query(default=0, ge=0, le=100000),
                  limit: int = Query(default=24, ge=1, le=100)):
        with db() as conn:
            jobs = [summary(r) for r in open_rows(conn) if json.loads(r['generated']).get('jobAd', '').strip()]
        companies = sorted({j['company'] for j in jobs}, key=str.casefold)
        selected = [j for j in jobs if (not q or q.casefold() in (j['title']+' '+j['company']).casefold())
                    and (not location or location.casefold() in j['location'].casefold())
                    and (not company or company == j['company']) and (not employment or employment == j['employment'])
                    and (not work_mode or work_mode == j['work_mode'])]
        return {'jobs': selected[offset:offset+limit], 'total': len(selected), 'companies': companies, 'test': not auth.production()}

    @app.get('/jobs/sitemap')
    def job_sitemap():
        with db() as conn:
            rows = [r for r in open_rows(conn) if json.loads(r['generated']).get('jobAd', '').strip()]
        return {'test': not auth.production(), 'jobs': [{'id': r['id'], 'updated_at': r['updated_at']} for r in rows]}

    @app.get('/jobs/{project_id}')
    def job(project_id: int):
        with db() as conn:
            row = public_row(conn, project_id)
            increment(conn, project_id, day_now(), 'requests')
            data = summary(row)
        # This module never loads third-party tracking or activates an advertising audience.
        return {**data, 'text': json.loads(row['generated'])['jobAd'], 'contact_email': row['contact_email'],
                'privacy_url': row['privacy_url'], 'retention_days': row['retention_days'], 'test': not auth.production(),
                'retargeting_ready': False, 'consent_version': CONSENT_VERSION}

    @app.get('/jobs/{project_id}/image')
    def image(project_id: int):
        with db() as conn:
            public_row(conn, project_id)
            row = conn.execute('SELECT feed FROM campaign_images WHERE project_id=? AND selected=1', (project_id,)).fetchone()
        if not row:
            raise HTTPException(404, 'Not found')
        return Response(row['feed'], media_type='image/jpeg', headers={'Cache-Control': 'no-store'})

    @app.post('/jobs/{project_id}/consent')
    def consent(project_id: int, body: Choice, request: Request):
        auth.rate(db, request, 'job-consent', str(project_id), limit=90, seconds=60)
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            public_row(conn, project_id)
            purge(conn)
            if not body.analytics and not body.marketing:
                return {'token': None}
            key = body.request_id or secrets.token_urlsafe(24)
            digest = hashlib.sha256((str(project_id)+':'+key).encode()).hexdigest()
            existing = conn.execute('SELECT * FROM job_flows WHERE key_hash=?', (digest,)).fetchone()
            if existing:
                if bool(existing['analytics']) != body.analytics or bool(existing['marketing']) != body.marketing:
                    raise HTTPException(409, 'Einwilligung wurde inzwischen geändert.')
                return {'token': auth.cipher().encrypt(json.dumps({'pid': project_id, 'key': key, 'version': CONSENT_VERSION}).encode()).decode()}
            now = int(time.time())
            link = conn.execute("SELECT channel,variant FROM ad_links WHERE id=? AND project_id=? AND active=1 AND destination=''",(body.link_id,project_id)).fetchone() if body.link_id else None
            kinds = {'Beitrag':'organic','Anzeige':'paid','Retargeting':'retargeting'}
            channel, kind = (link['channel'],kinds.get(link['variant'],'other')) if link else ('Direct','direct')
            conn.execute('INSERT INTO job_flows(key_hash,project_id,day,expires_at,analytics,marketing,channel,kind) VALUES(?,?,?,?,?,?,?,?)',
                         (digest, project_id, day_now(), now+86400, int(body.analytics), int(body.marketing),channel,kind))
            if body.analytics:
                increment_flow(conn, conn.execute('SELECT * FROM job_flows WHERE key_hash=?',(digest,)).fetchone(), 'consented_views')
            token = auth.cipher().encrypt(json.dumps({'pid': project_id, 'key': key, 'version': CONSENT_VERSION}).encode()).decode()
        return {'token': token}

    @app.post('/jobs/{project_id}/withdraw')
    def withdraw(project_id: int, body: Token):
        with db() as conn:
            try:
                row = flow(conn, project_id, body.token)
            except HTTPException:
                return {'ok': True}
            conn.execute('DELETE FROM job_flows WHERE key_hash=?', (row['key_hash'],))
            campaign_workflow.reconcile_lifecycle(conn, project_id)
        return {'ok': True}

    @app.post('/jobs/{project_id}/events')
    def event(project_id: int, body: Event, request: Request):
        auth.rate(db, request, 'job-event', str(project_id), limit=180, seconds=60)
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            public_row(conn, project_id)
            purge(conn)
            row = flow(conn, project_id, body.token)
            if not row['analytics'] and not (row['marketing'] and body.event == 'engaged'):
                raise HTTPException(403, 'Analyse-Einwilligung fehlt oder ist abgelaufen.')
            if body.event == 'engaged' and (body.active_seconds < 30 or body.section_percent < 80):
                raise HTTPException(422, 'Lesesignal noch nicht erreicht.')
            if row['applied']:
                return {'ok': True}
            if not row[body.event]:
                conn.execute(f'UPDATE job_flows SET {body.event}=1 WHERE key_hash=?', (row['key_hash'],))
                if row['analytics']:
                    increment_flow(conn, row, body.event)
                if body.event == 'engaged' and row['marketing']:
                    plan = conn.execute('SELECT retargeting FROM job_portal_plans WHERE project_id=?',(project_id,)).fetchone()
                    if plan and plan['retargeting']:
                        increment(conn, project_id, row['day'], 'retargeting_eligible')
            run = campaign_workflow.current(conn,project_id)
            if run:
                campaign_workflow.execute(conn,run['id'])
        return {'ok': True}

    @app.get('/campaigns/{project_id}/portal')
    def settings(project_id: int, user=Depends(current_user)):
        require(user, 'campaigns:read')
        with db(user) as conn:
            project = project_row(conn, project_id, user)
            page = conn.execute('SELECT enabled FROM application_pages WHERE project_id=?', (project_id,)).fetchone()
            tasks = [dict(r) for r in conn.execute('SELECT d.channel,d.kind,d.state,l.id AS link_id FROM job_distribution d JOIN ad_links l ON l.id=d.link_id WHERE d.project_id=?', (project_id,))]
            for task in tasks:
                task['url'] = tracking.public_origin()+'/r/'+task['link_id']
            return {'plan': get_plan(conn, project), 'enabled': bool(page and page['enabled']), 'url': tracking.public_origin()+'/jobs/'+str(project_id), 'tasks': tasks, 'provider_live': False, 'demo': bool(user.get('view_role')), 'workflow': campaign_workflow.projection(conn,project_id)}

    @app.post('/campaigns/{project_id}/portal')
    def save(project_id: int, body: Plan, user=Depends(current_user)):
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            project = admin(conn, project_id, user)
            recruiting.ensure_open(conn, project_id)
            previous = get_plan(conn, project)
            if previous['revision'] != body.revision:
                raise HTTPException(409, 'Der Veröffentlichungsplan wurde inzwischen geändert. Bitte neu laden.')
            spent = conn.execute('SELECT COALESCE(SUM(a.spent_cents),0) FROM campaign_actions a JOIN campaign_runs r ON r.id=a.run_id WHERE r.project_id=?',(project_id,)).fetchone()[0]
            if body.budget_cents<spent:
                raise HTTPException(409,'Budget darf simulierte Ausgaben nicht unterschreiten.')
            ends_at = body.ends_at
            if body.ends_on:
                try:
                    ends_at = int(datetime.combine(date.fromisoformat(body.ends_on), datetime.max.time(), ZoneInfo('Europe/Berlin')).timestamp())
                except ValueError:
                    raise HTTPException(422, 'Ungültiges Ablaufdatum.') from None
            if ends_at and ends_at <= int(time.time()):
                raise HTTPException(422, 'Das Ablaufdatum muss in der Zukunft liegen.')
            values = body.model_dump(exclude={'contact_email','privacy_url','retention_days','ends_on'})
            values['ends_at'] = ends_at
            values['project_id'] = project_id
            values['revision'] += 1
            names = ','.join(values)
            update = ','.join(f'{key}=excluded.{key}' for key in values if key != 'project_id')
            conn.execute(f'INSERT INTO job_portal_plans({names}) VALUES({",".join("?" for _ in values)}) ON CONFLICT(project_id) DO UPDATE SET {update}', tuple(values.values()))
            conn.execute('INSERT INTO application_pages(project_id,enabled,contact_email,privacy_url,retention_days) VALUES(?,0,?,?,?) ON CONFLICT(project_id) DO UPDATE SET contact_email=excluded.contact_email,privacy_url=excluded.privacy_url,retention_days=excluded.retention_days', (project_id, body.contact_email, body.privacy_url, body.retention_days))
            campaign_workflow.stop(conn,project_id,'changed')
            history(conn, project["organization_id"], project_id, user["id"], 'portal_plan', 'Veröffentlichungsplan gespeichert')
        return {'ok': True}

    @app.post('/campaigns/{project_id}/portal/publish')
    def publish(project_id: int, body: Publication, user=Depends(current_user)):
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            project = admin(conn, project_id, user)
            if auth.production():
                raise HTTPException(409, 'Lokaler Workflow ist in Produktion deaktiviert.')
            recruiting.ensure_open(conn, project_id)
            plan = get_plan(conn, project)
            if plan['revision'] != body.revision or project['image_revision'] != body.image_revision:
                raise HTTPException(409, 'Der Veröffentlichungsplan wurde inzwischen geändert. Bitte neu laden.')
            if project['status'] != 'Live' or not json.loads(project['generated']).get('jobAd', '').strip():
                raise HTTPException(409, 'Anzeige zuerst freigeben und Stellenanzeigentext speichern.')
            assert_not_expired(conn, project_id)
            if auth.production() and not plan['privacy_url']:
                raise HTTPException(422, 'Datenschutz-URL für die öffentliche Bewerbungsseite erforderlich.')
            if not plan['contact_email']:
                raise HTTPException(422, 'Kontakt für Bewerber erforderlich.')
            conn.execute('UPDATE application_pages SET enabled=1 WHERE project_id=?', (project_id,))
            conn.execute('UPDATE job_portal_plans SET published_at=? WHERE project_id=? AND published_at=0', (int(time.time()),project_id))
            now = int(time.time())
            conn.execute('DELETE FROM job_distribution WHERE project_id=?',(project_id,))
            for channel in ('Instagram', 'Meta'):
                for kind, variant in [('organic','Beitrag')]+([('paid','Anzeige')] if plan['budget_cents'] else [])+([('retargeting','Retargeting')] if plan['budget_cents'] and plan['retargeting'] else []):
                    conn.execute('INSERT OR IGNORE INTO ad_links(id,project_id,organization_id,channel,variant,destination,created_at) VALUES(?,?,?,?,?,\'\',?)', (secrets.token_urlsafe(24), project_id, project['organization_id'], channel, variant, now))
                    link = conn.execute('SELECT id FROM ad_links WHERE project_id=? AND channel=? AND variant=? AND destination=\'\'', (project_id, channel, variant)).fetchone()
                    conn.execute('UPDATE ad_links SET active=1 WHERE id=?',(link['id'],))
                    conn.execute('INSERT OR IGNORE INTO job_distribution(project_id,channel,kind,link_id,created_at) VALUES(?,?,?,?,?)', (project_id, channel, kind, link['id'], now))
            run_id = campaign_workflow.prepare(conn, project, plan, tracking.public_origin())
            campaign_workflow.execute(conn, run_id)
            history(conn, project["organization_id"], project_id, user["id"], 'portal_published', 'Stelle im MH-Jobportal aktiviert; Social-Beiträge und Anzeigen vorbereitet')
            workflow = campaign_workflow.projection(conn,project_id)
        return {'ok': True, 'external_published': False, 'spent_cents': 0, 'workflow': workflow}

    @app.post('/campaigns/{project_id}/portal/unpublish')
    def unpublish(project_id: int, user=Depends(current_user)):
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            project = admin(conn, project_id, user)
            conn.execute('UPDATE application_pages SET enabled=0 WHERE project_id=?',(project_id,))
            conn.execute('UPDATE ad_links SET active=0 WHERE project_id=?',(project_id,))
            campaign_workflow.stop(conn,project_id)
            history(conn,project["organization_id"],project_id,user["id"],'portal_unpublished','Stelle aus dem MH-Jobportal zurückgezogen')
        return {'ok': True}

    @app.post('/campaigns/{project_id}/portal/workflow/retry')
    def retry_workflow(project_id: int, body: WorkflowRequest, user=Depends(current_user)):
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            project = admin(conn,project_id,user)
            if auth.production():
                raise HTTPException(409,'Lokaler Workflow ist in Produktion deaktiviert.')
            run = campaign_workflow.current(conn,project_id)
            if not run or run['id']!=body.run_id or campaign_workflow.valid(conn,run):
                raise HTTPException(409,'Workflow zuerst starten oder aktualisieren.')
            campaign_workflow.execute(conn,run['id'],reconcile=body.reconcile)
            history(conn,project['organization_id'],project_id,user['id'],'workflow_retry','Lokalen Workflow erneut geprüft')
            return campaign_workflow.projection(conn,project_id)

    @app.post('/campaigns/{project_id}/portal/workflow/simulate')
    def simulate_workflow(project_id: int, body: SimulationRequest, user=Depends(current_user)):
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            project = admin(conn,project_id,user)
            if auth.production():
                raise HTTPException(409,'Lokaler Workflow ist in Produktion deaktiviert.')
            run = campaign_workflow.current(conn,project_id)
            if not run or run['id']!=body.run_id:
                raise HTTPException(409,'Workflow zuerst starten oder aktualisieren.')
            result = campaign_workflow.simulate_traffic(conn,project_id,body.request_id)
            history(conn,project['organization_id'],project_id,user['id'],'workflow_simulated','Werbeauslieferung lokal simuliert; keine echten Ausgaben')
            return result

    @app.get('/campaigns/{project_id}/portal/report')
    def report(project_id: int, start: date | None = None, end: date | None = None, user=Depends(current_user)):
        require(user, 'campaigns:read')
        today = datetime.now(timezone.utc).date()
        start = start or today.replace(day=1)
        end = end or today
        if start > end or (end-start).days > 366:
            raise HTTPException(422, 'Ungültiger Analysezeitraum (maximal 367 Tage).')
        with db(user) as conn:
            project_row(conn, project_id, user)
            purge(conn)
            columns = ('requests','consented_views','engaged','form_started','consented_applications','retargeting_eligible','engaged_applications')
            totals = conn.execute('SELECT '+','.join(f'COALESCE(SUM({c}),0) AS {c}' for c in columns)+' FROM job_daily WHERE project_id=? AND day BETWEEN ? AND ?', (project_id,start.isoformat(),end.isoformat())).fetchone()
            begin = int(datetime.combine(start, datetime.min.time(), timezone.utc).timestamp())
            finish = int(datetime.combine(end, datetime.max.time(), timezone.utc).timestamp())
            applications = conn.execute('SELECT COUNT(*) FROM application_receipts WHERE project_id=? AND received_at BETWEEN ? AND ?', (project_id,begin,finish)).fetchone()[0]
            channel_columns = ('consented_views','engaged','form_started','consented_applications','engaged_applications')
            channels = [dict(r) for r in conn.execute('SELECT channel,kind,'+','.join(f'SUM({c}) AS {c}' for c in channel_columns)+' FROM job_channel_daily WHERE project_id=? AND day BETWEEN ? AND ? GROUP BY channel,kind ORDER BY channel,kind',(project_id,start.isoformat(),end.isoformat()))]
            return {'channels': channels, 'workflow': campaign_workflow.projection(conn,project_id), 'totals': dict(totals), 'applications': applications, 'start': start.isoformat(), 'end': end.isoformat(), 'timezone': 'UTC', 'source': 'mh', 'demo': bool(user.get('view_role'))}
