"""Company recruiting workflow. Human evidence, no messages or hiring decisions."""
import hashlib
import json
import time
from datetime import date, datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from . import auth, tracking


def schema(conn):
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS recruiting_needs (
        project_id INTEGER PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
        owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        response_owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        state TEXT NOT NULL DEFAULT 'open', desired_start TEXT NOT NULL DEFAULT '',
        open_questions TEXT NOT NULL DEFAULT '', response_hours INTEGER,
        close_reason TEXT NOT NULL DEFAULT '', version INTEGER NOT NULL DEFAULT 0,
        updated_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS recruiting_cases (
        receipt_id INTEGER PRIMARY KEY REFERENCES application_receipts(id) ON DELETE CASCADE,
        owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        state TEXT NOT NULL DEFAULT 'new', due_at INTEGER, first_response_at INTEGER,
        scheduled_at INTEGER, confirmed_at INTEGER, outcome_at INTEGER,
        payload TEXT NOT NULL DEFAULT '', version INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS recruiting_events (
        id INTEGER PRIMARY KEY, receipt_id INTEGER NOT NULL REFERENCES application_receipts(id) ON DELETE CASCADE,
        actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL, kind TEXT NOT NULL,
        occurred_at INTEGER NOT NULL, recorded_at INTEGER NOT NULL,
        payload TEXT NOT NULL, request_key TEXT NOT NULL, request_digest TEXT NOT NULL,
        UNIQUE(receipt_id,request_key));
    CREATE TABLE IF NOT EXISTS recruiting_publications (
        id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL, channel TEXT NOT NULL,
        variant TEXT NOT NULL, proof_url TEXT NOT NULL DEFAULT '', posted_at INTEGER NOT NULL,
        recorded_at INTEGER NOT NULL, request_key TEXT NOT NULL, request_digest TEXT NOT NULL,
        UNIQUE(project_id,request_key));
    CREATE TABLE IF NOT EXISTS recruiting_effort (
        id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL, day TEXT NOT NULL,
        minutes INTEGER NOT NULL, support_minutes INTEGER NOT NULL, baseline_minutes INTEGER,
        comparison TEXT NOT NULL DEFAULT '', spend_cents INTEGER,
        learning TEXT NOT NULL DEFAULT '', request_key TEXT NOT NULL, request_digest TEXT NOT NULL,
        UNIQUE(project_id,request_key));
    CREATE TABLE IF NOT EXISTS recruiting_reuse (
        source_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        request_key TEXT NOT NULL, new_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        PRIMARY KEY(source_id,request_key));
    ''')
    columns = {r['name'] for r in conn.execute('PRAGMA table_info(projects)')}
    if 'generated_briefing' not in columns:
        conn.execute("ALTER TABLE projects ADD COLUMN generated_briefing TEXT NOT NULL DEFAULT ''")


def fingerprint(briefing):
    value = json.loads(briefing) if isinstance(briefing, str) else briefing
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def ensure_open(conn, project_id):
    row = conn.execute('SELECT state FROM recruiting_needs WHERE project_id=?', (project_id,)).fetchone()
    if row and row['state'] != 'open':
        raise HTTPException(409, 'Die Suche ist pausiert oder abgeschlossen. Für einen neuen Bedarf einen neuen Entwurf anlegen.')


def encrypt(value):
    return auth.cipher().encrypt(json.dumps(value, ensure_ascii=False).encode()).decode()


def decrypt(value):
    return json.loads(auth.cipher().decrypt(value.encode())) if value else {}


def create_case(conn, receipt_id):
    row = conn.execute('SELECT r.received_at,n.response_owner_id,n.response_hours FROM application_receipts r LEFT JOIN recruiting_needs n ON n.project_id=r.project_id WHERE r.id=?', (receipt_id,)).fetchone()
    conn.execute('INSERT OR IGNORE INTO recruiting_cases(receipt_id,owner_id,due_at,payload) VALUES(?,?,?,?)', (receipt_id, row['response_owner_id'], row['received_at']+row['response_hours']*3600 if row['response_hours'] else None, encrypt({'next_action':'Erste Rückmeldung','next_action_system':True})))


def purge(conn):
    """Personal workflow notes share the application's original retention deadline."""
    now = int(time.time())
    conn.execute("UPDATE hosted_applications SET payload='' WHERE expires_at<=?", (now,))
    expired = 'SELECT receipt_id FROM hosted_applications WHERE expires_at<=?'
    conn.execute(f"UPDATE recruiting_events SET payload='',request_digest='' WHERE receipt_id IN ({expired})", (now,))
    conn.execute(f"UPDATE recruiting_cases SET payload='',owner_id=NULL,due_at=NULL,scheduled_at=NULL WHERE receipt_id IN ({expired})", (now,))


class StrictBody(BaseModel):
    model_config = ConfigDict(extra='forbid')


class NeedBody(StrictBody):
    version: int = Field(ge=0)
    owner_id: int | None = None
    response_owner_id: int | None = None
    desired_start: str = Field(default='', max_length=180)
    open_questions: str = Field(default='', max_length=4000)
    response_hours: int | None = Field(default=None, ge=1, le=8760)
    state: Literal['open', 'paused', 'closed'] = 'open'
    close_reason: str = Field(default='', max_length=1000)


class EventBody(StrictBody):
    version: int = Field(ge=0)
    request_key: str = Field(min_length=20, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    kind: Literal['assign', 'task', 'response', 'proposal', 'confirmation', 'cancelled', 'held', 'no_show']
    owner_id: int | None = None
    occurred_at: int | None = Field(default=None, ge=946684800)
    due_at: int | None = Field(default=None, ge=946684800)
    next_action: str = Field(default='', max_length=1000)
    note: str = Field(default='', max_length=4000)
    contact_way: str = Field(default='', max_length=180)
    scheduled_at: int | None = Field(default=None, ge=946684800)
    timezone: str = Field(default='Europe/Berlin', max_length=80)
    place: str = Field(default='', max_length=500)
    confirmed: bool = False

    @field_validator('timezone')
    @classmethod
    def zone(cls, value):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError:
            raise ValueError('Unknown timezone')
        return value


class PublicationBody(StrictBody):
    request_key: str = Field(min_length=20, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    channel: str
    variant: str = Field(default='A', min_length=1, max_length=80)
    proof_url: str = Field(default='', max_length=2000)
    posted_at: int = Field(ge=946684800)
    confirmed: bool
    link_id: str = Field(min_length=20, max_length=64)

    @field_validator('channel')
    @classmethod
    def channel_valid(cls, value):
        return tracking.LinkBody.valid_channel(value)

    @field_validator('proof_url')
    @classmethod
    def proof(cls, value):
        return tracking.LinkBody.valid_destination(value)


class EffortBody(StrictBody):
    request_key: str = Field(min_length=20, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    day: date
    minutes: int = Field(ge=0, le=100000)
    support_minutes: int = Field(default=0, ge=0, le=100000)
    baseline_minutes: int | None = Field(default=None, ge=0, le=100000)
    comparison: str = Field(default='', max_length=2000)
    spend_cents: int | None = Field(default=None, ge=0, le=100000000)
    learning: str = Field(default='', max_length=4000)


class ReuseBody(StrictBody):
    request_key: str = Field(min_length=20, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')


def install(app, db, current_user, require, project_row, log_history, serialize_project):
    def team(user, write=False):
        if user.get('view_role') or user['role'] not in {'firmen_admin', 'user'} or not user.get('organization_id'):
            raise HTTPException(403, 'Recruiting ist nur für das berechtigte Firmenteam zugänglich.')
        require(user, 'campaigns:write' if write else 'campaigns:read')

    def valid_owner(conn, owner, org):
        if owner is not None and not conn.execute("SELECT 1 FROM users WHERE id=? AND organization_id=? AND role IN ('firmen_admin','user')", (owner, org)).fetchone():
            raise HTTPException(422, 'Zuständigkeit nur an berechtigte Mitglieder derselben Firma vergeben.')
        return owner

    def members(conn, org):
        return [dict(r) for r in conn.execute("SELECT id,name FROM users WHERE organization_id=? AND role IN ('firmen_admin','user') ORDER BY name", (org,))]

    def need(conn, project):
        row = conn.execute('SELECT * FROM recruiting_needs WHERE project_id=?', (project['id'],)).fetchone()
        if row:
            value = dict(row)
        else:
            value = dict(project_id=project['id'], owner_id=None, response_owner_id=None, state='open', desired_start='', open_questions='', response_hours=None, close_reason='', version=0, updated_at=project['updated_at'])
        valid = {r['id'] for r in members(conn, project['organization_id'])}
        for key in ('owner_id', 'response_owner_id'):
            if value[key] not in valid:
                value[key] = None
        b = json.loads(project['briefing'])
        value['missing'] = [label for label, value_ in [('Arbeitsort', b.get('location')), ('Beschäftigungsumfang', b.get('employment_type')), ('Gewünschter Start', value['desired_start']), ('Verantwortliche Person', value['owner_id']), ('Erste Bewerberreaktion', value['response_owner_id'])] if not value_]
        value['questions'] = []
        for phrase in ('flexibel', 'attraktiv', 'familiär', 'modern'):
            if phrase in b.get('benefits', '').lower():
                value['questions'].append(f'Was bedeutet „{phrase}“ bei dieser Stelle konkret? Bitte ein belegbares Beispiel ergänzen.')
        return value

    def case_value(conn, receipt, org):
        row = conn.execute('SELECT * FROM recruiting_cases WHERE receipt_id=?', (receipt['id'],)).fetchone()
        if row:
            value = dict(row)
            value.update(decrypt(value.pop('payload')))
        else:
            project = conn.execute('SELECT * FROM projects WHERE id=?', (receipt['project_id'],)).fetchone()
            n = need(conn, project)
            value = dict(receipt_id=receipt['id'], owner_id=n['response_owner_id'], state='new', due_at=None, first_response_at=None, scheduled_at=None, confirmed_at=None, outcome_at=None, version=0, next_action='Erste Rückmeldung', next_action_system=True)
        if value['owner_id'] is not None:
            valid = conn.execute("SELECT name FROM users WHERE id=? AND organization_id=? AND role IN ('firmen_admin','user')", (value['owner_id'], org)).fetchone()
            value['owner'] = valid['name'] if valid else None
            if not valid:
                value['owner_id'] = None
        else:
            value['owner'] = None
        active = bool(receipt['payload'] and receipt['expires_at'] > int(time.time()))
        value.update(id=receipt['id'], received_at=receipt['received_at'], expires_at=receipt['expires_at'], channel=receipt['channel'], variant=receipt['variant'], contact=decrypt(receipt['payload']) if active else None)
        value['overdue'] = active and bool(value.get('next_action')) and value['due_at'] is not None and value['due_at'] < int(time.time())
        if not active:
            value.update(next_action='', due_at=None, owner=None, owner_id=None)
        return value

    def receipts(conn, project_id):
        return conn.execute('''SELECT r.*,h.payload,h.expires_at,l.channel,l.variant FROM application_receipts r
            JOIN hosted_applications h ON h.receipt_id=r.id LEFT JOIN ad_links l ON l.id=r.link_id
            WHERE r.project_id=? ORDER BY r.received_at DESC,r.id DESC''', (project_id,)).fetchall()

    def duplicate(conn, table, scope, identity, key, digest):
        row = conn.execute(f'SELECT * FROM {table} WHERE {scope}=? AND request_key=?', (identity, key)).fetchone()
        if row and row['request_digest'] != digest:
            raise HTTPException(409, 'Anfrage bereits mit anderen Daten dokumentiert.')
        return row

    @app.get('/campaigns/{project_id}/recruiting')
    def workspace(project_id: int, user=Depends(current_user)):
        team(user)
        with db() as conn:
            p = project_row(conn, project_id, user)
            purge(conn)
            cases = [case_value(conn, r, p['organization_id']) for r in receipts(conn, project_id)]
            publications = [dict(r) for r in conn.execute("SELECT p.*,u.name AS actor,'manual' AS source FROM recruiting_publications p LEFT JOIN users u ON u.id=p.actor_id WHERE project_id=? ORDER BY posted_at DESC", (project_id,))]
            return dict(need=need(conn, p), team=members(conn, p['organization_id']), applications=cases, publications=publications, updated_at=int(time.time()))

    @app.post('/campaigns/{project_id}/recruiting/need')
    def save_need(project_id: int, body: NeedBody, user=Depends(current_user)):
        team(user, True)
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            p = project_row(conn, project_id, user)
            n = need(conn, p)
            if body.version != n['version']:
                raise HTTPException(409, 'Der Bedarf wurde inzwischen geändert. Neu laden und erneut prüfen.')
            if n['state'] == 'closed' and body.state != 'closed':
                raise HTTPException(409, 'Abgeschlossene Suche als neuen Entwurf wiederverwenden.')
            for owner in (body.owner_id, body.response_owner_id):
                valid_owner(conn, owner, p['organization_id'])
            if body.state != 'open' and not body.close_reason.strip():
                raise HTTPException(422, 'Grund für Pause oder Abschluss angeben.')
            values = body.model_dump()
            values['version'] += 1
            conn.execute('''INSERT INTO recruiting_needs(project_id,owner_id,response_owner_id,state,desired_start,open_questions,response_hours,close_reason,version,updated_at)
                VALUES(:project_id,:owner_id,:response_owner_id,:state,:desired_start,:open_questions,:response_hours,:close_reason,:version,:updated_at)
                ON CONFLICT(project_id) DO UPDATE SET owner_id=excluded.owner_id,response_owner_id=excluded.response_owner_id,state=excluded.state,
                desired_start=excluded.desired_start,open_questions=excluded.open_questions,response_hours=excluded.response_hours,close_reason=excluded.close_reason,version=excluded.version,updated_at=excluded.updated_at''', {**values, 'project_id': project_id, 'updated_at': int(time.time())})
            if body.state != 'open':
                conn.execute('UPDATE application_pages SET enabled=0 WHERE project_id=?', (project_id,))
                from .campaign_workflow import stop
                stop(conn,project_id,'closed')
                conn.execute('UPDATE ad_links SET active=0 WHERE project_id=?', (project_id,))
            log_history(conn, p['organization_id'], project_id, user['id'], 'recruiting_need', f'Personalbedarf: {body.state}; Zuständigkeiten aktualisiert')
            return need(conn, p)

    @app.get('/campaigns/{project_id}/recruiting/applications/{receipt_id}/events')
    def events(project_id: int, receipt_id: int, user=Depends(current_user)):
        team(user)
        with db() as conn:
            project_row(conn, project_id, user)
            if not conn.execute('SELECT 1 FROM application_receipts WHERE id=? AND project_id=?', (receipt_id, project_id)).fetchone():
                raise HTTPException(404, 'Not found')
            purge(conn)
            return [dict(id=r['id'], kind=r['kind'], occurred_at=r['occurred_at'], recorded_at=r['recorded_at'], actor=r['actor'], evidence='manual', details=decrypt(r['payload']) if r['payload'] else None) for r in conn.execute('SELECT e.*,u.name AS actor FROM recruiting_events e LEFT JOIN users u ON u.id=e.actor_id WHERE receipt_id=? ORDER BY e.id', (receipt_id,))]

    @app.post('/campaigns/{project_id}/recruiting/applications/{receipt_id}/events')
    def record_event(project_id: int, receipt_id: int, body: EventBody, user=Depends(current_user)):
        team(user, True)
        digest = fingerprint(body.model_dump())
        now = int(time.time())
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            p = project_row(conn, project_id, user)
            purge(conn)
            r = next((r for r in receipts(conn, project_id) if r['id'] == receipt_id), None)
            if r is None:
                raise HTTPException(404, 'Not found')
            c = case_value(conn, r, p['organization_id'])
            if not c['contact']:
                raise HTTPException(410, 'Die Aufbewahrungsfrist ist abgelaufen. Persönliche Bearbeitung ist beendet.')
            if duplicate(conn, 'recruiting_events', 'receipt_id', receipt_id, body.request_key, digest):
                return c
            if body.version != c['version']:
                raise HTTPException(409, 'Die Bewerbung wurde inzwischen bearbeitet. Neu laden und erneut prüfen.')
            occurred = body.occurred_at or now
            if occurred < r['received_at'] or occurred > now:
                raise HTTPException(422, 'Tatsächlicher Zeitpunkt muss zwischen Bewerbungseingang und jetzt liegen.')
            details = {k: c.get(k, '') for k in ('next_action', 'note', 'contact_way', 'timezone', 'place')}
            details['next_action_system'] = c.get('next_action_system', False)
            if body.kind == 'assign':
                c['owner_id'] = valid_owner(conn, body.owner_id, p['organization_id'])
            elif body.kind == 'task':
                if not body.note.strip():
                    raise HTTPException(422, 'Änderung der Aufgabe oder Frist begründen.')
                c['due_at'] = body.due_at
                details['next_action'] = body.next_action.strip()
                details['next_action_system'] = False
            else:
                if c['owner_id'] is None:
                    raise HTTPException(422, 'Zuerst eine zuständige Person festlegen.')
                if body.kind == 'response':
                    if not body.confirmed or not body.contact_way.strip() or not body.note.strip():
                        raise HTTPException(422, 'Tatsächlichen Kontakt, Kontaktweg und Nachweis ausdrücklich bestätigen.')
                    c['first_response_at'] = min(c['first_response_at'], occurred) if c['first_response_at'] else occurred
                    if c['state'] == 'new':
                        c['state'] = 'contacted'
                    details.update(contact_way=body.contact_way.strip(), next_action=body.next_action.strip(), next_action_system=False)
                    c['due_at'] = body.due_at
                elif body.kind == 'proposal':
                    if not body.scheduled_at or body.scheduled_at <= now or not body.place.strip() or not body.contact_way.strip() or not body.confirmed:
                        raise HTTPException(422, 'Zukünftigen Termin, Ort/Kontaktweg und tatsächlich übermittelten Vorschlag bestätigen.')
                    c.update(state='proposed', scheduled_at=body.scheduled_at, confirmed_at=None, outcome_at=None, due_at=body.due_at)
                    details.update(place=body.place.strip(), timezone=body.timezone, contact_way=body.contact_way.strip(), next_action=body.next_action.strip() or 'Terminbestätigung abwarten', next_action_system=not bool(body.next_action.strip()))
                    c['first_response_at'] = min(c['first_response_at'], occurred) if c['first_response_at'] else occurred
                elif body.kind == 'confirmation':
                    proposal_time = conn.execute("SELECT MAX(occurred_at) FROM recruiting_events WHERE receipt_id=? AND kind='proposal'", (receipt_id,)).fetchone()[0]
                    if proposal_time is not None and occurred < proposal_time:
                        raise HTTPException(422, 'Die Bestätigung darf nicht vor dem übermittelten Vorschlag liegen.')
                    if c['state'] != 'proposed' or not body.confirmed or not body.note.strip():
                        raise HTTPException(422, 'Bestätigung des vorgeschlagenen Termins durch den Bewerber dokumentieren.')
                    c.update(state='confirmed', confirmed_at=occurred, due_at=None)
                    details['next_action'] = 'Gespräch durchführen'
                    details['next_action_system'] = True
                elif body.kind in {'held', 'no_show'}:
                    if c['state'] != 'confirmed' or c['scheduled_at'] > occurred or not body.confirmed:
                        raise HTTPException(422, 'Ergebnis erst nach dem bestätigten Termin dokumentieren.')
                    c.update(state=body.kind, outcome_at=occurred, due_at=body.due_at)
                    details['next_action'] = body.next_action.strip()
                    details['next_action_system'] = False
                elif body.kind == 'cancelled':
                    if c['state'] not in {'proposed', 'confirmed'} or not body.confirmed or not body.note.strip():
                        raise HTTPException(422, 'Absage eines offenen Termins mit Grund bestätigen.')
                    c.update(state='cancelled', scheduled_at=None, confirmed_at=None, due_at=body.due_at)
                    details['next_action'] = body.next_action.strip()
                    details['next_action_system'] = False
            if body.note:
                details['note'] = body.note.strip()
            conn.execute('''INSERT INTO recruiting_cases(receipt_id,owner_id,state,due_at,first_response_at,scheduled_at,confirmed_at,outcome_at,payload,version)
                VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(receipt_id) DO UPDATE SET owner_id=excluded.owner_id,state=excluded.state,due_at=excluded.due_at,
                first_response_at=excluded.first_response_at,scheduled_at=excluded.scheduled_at,confirmed_at=excluded.confirmed_at,outcome_at=excluded.outcome_at,payload=excluded.payload,version=excluded.version''', (receipt_id, c['owner_id'], c['state'], c['due_at'], c['first_response_at'], c['scheduled_at'], c['confirmed_at'], c['outcome_at'], encrypt(details), c['version']+1))
            # Avoid personal content in campaign history, activity, or request keys.
            conn.execute('INSERT INTO recruiting_events(receipt_id,actor_id,kind,occurred_at,recorded_at,payload,request_key,request_digest) VALUES(?,?,?,?,?,?,?,?)', (receipt_id, user['id'], body.kind, occurred, now, encrypt(body.model_dump()), body.request_key, digest))
            return case_value(conn, r, p['organization_id'])

    @app.post('/campaigns/{project_id}/recruiting/publications', status_code=201)
    def publication(project_id: int, body: PublicationBody, user=Depends(current_user)):
        team(user, True)
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            p = project_row(conn, project_id, user)
            old = duplicate(conn, 'recruiting_publications', 'project_id', project_id, body.request_key, fingerprint(body.model_dump()))
            if old:
                return {**dict(old), 'source': 'manual'}
            ensure_open(conn, project_id)
            if p['status'] != 'Live' or not body.confirmed or body.posted_at > int(time.time()):
                raise HTTPException(422, 'Freigabe und tatsächlich erfolgte Veröffentlichung bestätigen.')
            link = conn.execute('SELECT * FROM ad_links WHERE id=? AND project_id=? AND active=1 AND channel=? AND variant=?', (body.link_id, project_id, body.channel, body.variant)).fetchone()
            if not link or (not link['destination'] and not conn.execute('SELECT 1 FROM application_pages WHERE project_id=? AND enabled=1', (project_id,)).fetchone()):
                raise HTTPException(409, 'Aktiven Bewerbungslink desselben Kanals prüfen.')
            if not need(conn, p)['response_owner_id']:
                raise HTTPException(422, 'Zuständigkeit für die erste Bewerberreaktion festlegen.')
            identifier = conn.execute('INSERT INTO recruiting_publications(project_id,actor_id,channel,variant,proof_url,posted_at,recorded_at,request_key,request_digest) VALUES(?,?,?,?,?,?,?,?,?)', (project_id, user['id'], body.channel, body.variant, body.proof_url, body.posted_at, int(time.time()), body.request_key, fingerprint(body.model_dump()))).lastrowid
            log_history(conn, p['organization_id'], project_id, user['id'], 'manual_publication', f'{body.channel}: Veröffentlichung manuell dokumentiert; keine Anbieterbestätigung')
            return {**dict(conn.execute('SELECT * FROM recruiting_publications WHERE id=?', (identifier,)).fetchone()), 'source': 'manual'}

    @app.post('/campaigns/{project_id}/recruiting/effort', status_code=201)
    def effort(project_id: int, body: EffortBody, user=Depends(current_user)):
        team(user, True)
        values = body.model_dump(mode='json')
        if body.day > datetime.now(timezone.utc).date() or (body.baseline_minutes is not None and not body.comparison.strip()):
            raise HTTPException(422, 'Vergleich begründen; Aufwand nur für vergangene oder heutige Tage erfassen.')
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            project_row(conn, project_id, user)
            old = duplicate(conn, 'recruiting_effort', 'project_id', project_id, body.request_key, fingerprint(values))
            if old:
                return dict(old)
            values.update(project_id=project_id, actor_id=user['id'], request_digest=fingerprint(values))
            identifier = conn.execute('''INSERT INTO recruiting_effort(project_id,actor_id,day,minutes,support_minutes,baseline_minutes,comparison,spend_cents,learning,request_key,request_digest)
                VALUES(:project_id,:actor_id,:day,:minutes,:support_minutes,:baseline_minutes,:comparison,:spend_cents,:learning,:request_key,:request_digest)''', values).lastrowid
            return dict(conn.execute('SELECT * FROM recruiting_effort WHERE id=?', (identifier,)).fetchone())

    @app.get('/campaigns/{project_id}/recruiting/results')
    def results(project_id: int, start: date | None = None, end: date | None = None, user=Depends(current_user)):
        team(user)
        today = datetime.now(timezone.utc).date()
        start, end = start or today.replace(day=1), end or today
        if start > end:
            raise HTTPException(422, 'Invalid date range')
        lower = int(datetime.combine(start, datetime.min.time(), timezone.utc).timestamp())
        upper = int(datetime.combine(end, datetime.min.time(), timezone.utc).timestamp()) + 86400
        with db() as conn:
            project_row(conn, project_id, user)
            rows = conn.execute('SELECT r.received_at,c.first_response_at FROM application_receipts r LEFT JOIN recruiting_cases c ON c.receipt_id=r.id WHERE r.project_id=? AND r.received_at>=? AND r.received_at<?', (project_id, lower, upper)).fetchall()
            connected = bool(rows or conn.execute('SELECT 1 FROM application_pages WHERE project_id=?', (project_id,)).fetchone() or conn.execute('SELECT 1 FROM application_connectors a JOIN projects p ON p.organization_id=a.organization_id WHERE p.id=? AND a.last_seen IS NOT NULL', (project_id,)).fetchone())
            delays = [max(0, r['first_response_at']-r['received_at']) for r in rows if r['first_response_at'] is not None and r['first_response_at'] < upper]
            counts = {kind: conn.execute('SELECT COUNT(DISTINCT e.receipt_id) FROM recruiting_events e JOIN application_receipts r ON r.id=e.receipt_id WHERE r.project_id=? AND e.kind=? AND e.occurred_at>=? AND e.occurred_at<?', (project_id, kind, lower, upper)).fetchone()[0] for kind in ('confirmation', 'held', 'no_show')}
            hits = conn.execute('SELECT SUM(h.count) FROM ad_link_hits h JOIN ad_links l ON l.id=h.link_id WHERE l.project_id=? AND h.day>=? AND h.day<=?', (project_id, str(start), str(end))).fetchone()[0]
            has_links = conn.execute('SELECT 1 FROM ad_links WHERE project_id=?', (project_id,)).fetchone()
            efforts = [dict(r) for r in conn.execute('SELECT * FROM recruiting_effort WHERE project_id=? AND day>=? AND day<=? ORDER BY day,id', (project_id, str(start), str(end)))]
            baseline_rows = [r for r in efforts if r['baseline_minutes'] is not None]
            return dict(start=str(start), end=str(end), timezone='UTC', updated_at=int(time.time()), connected=connected, link_requests=(hits or 0) if has_links else None, applications=len(rows) if connected else None, responses=len(delays) if connected else None, mean_response_hours=sum(delays)/len(delays)/3600 if delays else None, confirmed=counts['confirmation'] if connected else None, held=counts['held'] if connected else None, no_show=counts['no_show'] if connected else None, effort=efforts, work_minutes=sum(r['minutes'] for r in efforts) if efforts else None, support_minutes=sum(r['support_minutes'] for r in efforts) if efforts else None, spend_cents=sum(r['spend_cents'] for r in efforts if r['spend_cents'] is not None) if any(r['spend_cents'] is not None for r in efforts) else None, comparison_difference_minutes=sum(r['baseline_minutes']-r['minutes']-r['support_minutes'] for r in baseline_rows) if baseline_rows else None, source='server_receipts_and_manual_evidence')

    @app.post('/campaigns/{project_id}/recruiting/reuse', status_code=201)
    def reuse(project_id: int, body: ReuseBody, user=Depends(current_user)):
        team(user, True)
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            p = project_row(conn, project_id, user)
            old = conn.execute('SELECT new_id FROM recruiting_reuse WHERE source_id=? AND request_key=?', (project_id, body.request_key)).fetchone()
            if old:
                return serialize_project(conn.execute('SELECT * FROM projects WHERE id=?', (old['new_id'],)).fetchone())
            b = json.loads(p['briefing'])
            now = int(time.time())
            new_id = conn.execute("INSERT INTO projects(organization_id,role,location,status,channels,briefing,generated,created_at,updated_at) VALUES(?,?,?,'Draft',?,?,?,?,?)", (p['organization_id'], p['role'], p['location'], p['channels'], json.dumps(b, ensure_ascii=False), p['generated'], now, now)).lastrowid
            conn.execute("INSERT INTO recruiting_needs(project_id,owner_id,response_owner_id,open_questions,updated_at) VALUES(?,?,?,?,?)", (new_id, user['id'], user['id'], 'Vergütung, Arbeitszeiten, Standort, Vorteile und Ansprechpartner erneut bestätigen.', now))
            conn.execute('INSERT INTO recruiting_reuse(source_id,request_key,new_id) VALUES(?,?,?)', (project_id, body.request_key, new_id))
            log_history(conn, p['organization_id'], new_id, user['id'], 'reused', 'Arbeitsgrundlagen als ungeprüften Entwurf übernommen; keine Bewerbungen oder Freigaben kopiert', json.loads(p['generated']))
            return serialize_project(conn.execute('SELECT * FROM projects WHERE id=?', (new_id,)).fetchone())
