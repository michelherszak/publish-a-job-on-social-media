"""Explicit Facebook Page publishing; Instagram account discovery is the next stage.

Provider tokens remain encrypted on the server. A claimed publication is never
automatically retried: a lost response can still mean Facebook created the post.
"""
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import ssl
import time
from urllib import error, parse, request as http

import certifi
from cryptography.fernet import InvalidToken
from fastapi import Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from . import auth

FACEBOOK_SCOPES = {'pages_show_list', 'pages_read_engagement', 'pages_manage_posts'}
INSTAGRAM_SCOPES = {'instagram_basic', 'instagram_content_publish'}


def schema(conn):
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS meta_oauth_states (
      state_hash TEXT PRIMARY KEY, organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, session_hash TEXT NOT NULL,
      instagram INTEGER NOT NULL, expires_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS meta_pending_pages (
      organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, session_hash TEXT NOT NULL,
      payload TEXT NOT NULL, expires_at INTEGER NOT NULL,
      PRIMARY KEY(organization_id,user_id,session_hash));
    CREATE TABLE IF NOT EXISTS meta_connections (
      organization_id INTEGER PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
      page_id TEXT NOT NULL, page_name TEXT NOT NULL, token TEXT NOT NULL,
      instagram_id TEXT NOT NULL DEFAULT '', instagram_name TEXT NOT NULL DEFAULT '',
      expires_at INTEGER NOT NULL, connected_at INTEGER NOT NULL, revision TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS social_publications (
      id TEXT PRIMARY KEY, organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
      project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
      actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
      platform TEXT NOT NULL DEFAULT 'facebook', page_id TEXT NOT NULL, page_name TEXT NOT NULL,
      connection_revision TEXT NOT NULL, project_digest TEXT NOT NULL, link_id TEXT NOT NULL,
      message TEXT NOT NULL, link_url TEXT NOT NULL, state TEXT NOT NULL,
      post_id TEXT NOT NULL DEFAULT '', post_url TEXT NOT NULL DEFAULT '',
      created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
      UNIQUE(project_id,platform));
    ''')


def public_https(value):
    try:
        url = parse.urlsplit(value)
        _ = url.port  # Reject malformed or out-of-range ports.
        host = url.hostname or ''
        if url.scheme != 'https' or not host or url.username or url.password or url.fragment or any(ord(c) < 33 for c in value):
            return False
        if host in {'localhost', 'localhost.localdomain'} or host.endswith(('.local', '.localhost', '.test', '.invalid')):
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return '.' in host
    except ValueError:
        return False


def configuration():
    origin = os.getenv('MH_PUBLIC_URL', '').rstrip('/')
    callback = os.getenv('MH_META_CALLBACK_URL', '')
    version = os.getenv('MH_META_GRAPH_VERSION', '')
    missing = []
    if not os.getenv('MH_META_APP_ID', '').isdigit(): missing.append('Meta-App-ID')
    if not os.getenv('MH_META_APP_SECRET'): missing.append('Meta-App-Secret')
    if not public_https(origin) or parse.urlsplit(origin).path or parse.urlsplit(origin).query: missing.append('Öffentliche HTTPS-Adresse')
    if not public_https(callback) or parse.urlsplit(callback).query or parse.urlsplit(callback).path not in {'/social/meta/callback', '/api/social/meta/callback'}: missing.append('Meta-Rücksprungadresse')
    if public_https(origin) and public_https(callback) and parse.urlsplit(origin).netloc != parse.urlsplit(callback).netloc:
        missing.append('Rücksprungadresse auf derselben Domain')
    if not re.fullmatch(r'v\d+\.0', version): missing.append('Meta-API-Version')
    return {'ready': not missing, 'missing': missing, 'origin': origin, 'callback': callback, 'version': version}


def configured():
    config = configuration()
    if not config['ready']:
        raise HTTPException(503, 'Die Meta-Verbindung benötigt eine öffentliche HTTPS-Adresse und die Meta-App-Einrichtung.')
    return config


class ProviderError(Exception):
    def __init__(self, rejected=False):
        self.rejected = rejected


class NoRedirect(http.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def graph(method, path, token='', data=None):
    """Fixed provider host, bounded responses and errors without provider secrets."""
    config = configured()
    if not re.fullmatch(r'[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*', path):
        raise ProviderError()
    values = dict(data or {})
    if token:
        values['appsecret_proof'] = hmac.new(os.environ['MH_META_APP_SECRET'].encode(), token.encode(), hashlib.sha256).hexdigest()
    payload = parse.urlencode(values).encode()
    url = 'https://graph.facebook.com/' + config['version'] + '/' + path
    headers = {'Accept': 'application/json'}
    if token: headers['Authorization'] = 'Bearer ' + token
    if method == 'GET':
        if payload: url += '?' + payload.decode()
        payload = None
    else:
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    req = http.Request(url, data=payload, headers=headers, method=method)
    opener = http.build_opener(NoRedirect(), http.HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where())))
    try:
        with opener.open(req, timeout=30) as response:
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024: raise ProviderError()
        result = json.loads(raw)
        if not isinstance(result, dict): raise ProviderError()
        if 'error' in result: raise ProviderError(rejected=True)
        return result
    except error.HTTPError as exc:
        # Only a structured Graph 4xx rejection establishes that no post was made.
        rejected = False
        if 400 <= exc.code < 500:
            try:
                rejected = isinstance(json.loads(exc.read(65536)).get('error'), dict)
            except (ValueError, AttributeError):
                pass
        exc.close()
        raise ProviderError(rejected=rejected) from None
    except (OSError, ValueError):
        raise ProviderError() from None


def seal(value):
    return auth.cipher().encrypt(json.dumps(value).encode()).decode()


def unseal(value):
    try:
        return json.loads(auth.cipher().decrypt(value.encode()))
    except (InvalidToken, ValueError):
        raise HTTPException(503, 'Gespeicherte Meta-Verbindung kann nicht gelesen werden. Bitte erneut verbinden.') from None


class ConnectBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    instagram: bool = False


class PageBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    page_id: str = Field(pattern=r'^\d+$', max_length=50)


class PreviewBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    message: str = Field(min_length=1, max_length=10000)
    link_id: str = Field(min_length=20, max_length=64)


class PublishBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    preview_id: str = Field(min_length=20, max_length=64)
    confirmed: bool


class VerifyBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    post_id: str = Field(pattern=r'^\d+_\d+$', max_length=110)


def projection(row):
    return {key: row[key] for key in ('id', 'platform', 'page_name', 'message', 'link_url', 'state', 'post_id', 'post_url', 'created_at', 'updated_at')}


def fingerprint(project):
    return hashlib.sha256((project['generated'] + project['briefing'] + project['status']).encode()).hexdigest()


def install(app, db, current_user, require, project_row, log_history):
    def company(user, admin=False, write=False):
        if user.get('view_role') or user.get('base_role') == 'platform_admin' or not user.get('organization_id') or user['role'] not in ({'firmen_admin'} if admin else {'firmen_admin', 'user'}):
            raise HTTPException(403, 'Social-Veröffentlichung ist nur für das echte Firmenteam verfügbar.')
        if write: require(user, 'campaigns:write')

    def connection(conn, org):
        row = conn.execute('SELECT * FROM meta_connections WHERE organization_id=?', (org,)).fetchone()
        if not row or row['expires_at'] <= int(time.time()):
            raise HTTPException(409, 'Bitte die Facebook-Seite in Settings verbinden oder die Verbindung erneuern.')
        return row

    def valid_link(conn, project, link_id):
        link = conn.execute("SELECT * FROM ad_links WHERE id=? AND organization_id=? AND project_id=? AND channel IN ('Facebook','Meta') AND active=1", (link_id, project['organization_id'], project['id'])).fetchone()
        if not link:
            raise HTTPException(422, 'Bitte einen aktiven Facebook-Bewerbungslink dieser Kampagne auswählen.')
        if not link['destination']:
            page = conn.execute('SELECT * FROM application_pages WHERE project_id=? AND enabled=1', (project['id'],)).fetchone()
            if not page or not json.loads(project['generated']).get('jobAd', '').strip():
                raise HTTPException(409, 'Die MH-Bewerbungsseite muss zuerst eingerichtet und aktiviert werden.')
        return configuration()['origin'] + '/r/' + link['id']

    @app.get('/social/meta/status')
    def status(request: Request, user=Depends(current_user)):
        company(user)
        config = configuration()
        with db() as conn:
            row = conn.execute('SELECT * FROM meta_connections WHERE organization_id=?', (user['organization_id'],)).fetchone()
            pending = conn.execute('SELECT payload FROM meta_pending_pages WHERE organization_id=? AND user_id=? AND session_hash=? AND expires_at>?', (user['organization_id'], user['id'], request.state.session_hash, int(time.time()))).fetchone()
        selected = None if not row else {'page_id': row['page_id'], 'page_name': row['page_name'], 'instagram_id': row['instagram_id'], 'instagram_name': row['instagram_name'], 'expired': row['expires_at'] <= int(time.time()), 'connected_at': row['connected_at']}
        pages = [] if not pending or user['role'] != 'firmen_admin' else [{key: p[key] for key in ('id', 'name', 'instagram_id', 'instagram_name')} for p in unseal(pending['payload'])['pages']]
        return {'ready': config['ready'], 'missing': config['missing'], 'connection': selected, 'pages': pages, 'facebook_stage': 'implemented_unverified', 'instagram_stage': 'connection_prepared'}

    @app.post('/social/meta/connect')
    def connect(body: ConnectBody, request: Request, user=Depends(current_user)):
        company(user, admin=True, write=True)
        config = configured()
        auth.rate(db, request, 'meta-connect', str(user['id']), limit=10, seconds=600)
        state = secrets.token_urlsafe(32)
        with db() as conn:
            conn.execute('DELETE FROM meta_oauth_states WHERE expires_at<=?', (int(time.time()),))
            conn.execute('DELETE FROM meta_pending_pages WHERE expires_at<=?', (int(time.time()),))
            conn.execute('INSERT INTO meta_oauth_states VALUES(?,?,?,?,?,?)', (auth.digest(state), user['organization_id'], user['id'], request.state.session_hash, int(body.instagram), int(time.time()) + 600))
        scopes = FACEBOOK_SCOPES | (INSTAGRAM_SCOPES if body.instagram else set())
        return {'url': 'https://www.facebook.com/' + config['version'] + '/dialog/oauth?' + parse.urlencode({'client_id': os.environ['MH_META_APP_ID'], 'redirect_uri': config['callback'], 'state': state, 'scope': ','.join(sorted(scopes)), 'response_type': 'code', 'auth_type': 'rerequest'})}

    @app.get('/social/meta/callback')
    def callback(request: Request, state: str = Query('', max_length=128), code: str = Query('', max_length=4096), error: str = Query('', max_length=200), user=Depends(current_user)):
        company(user, admin=True, write=True)
        config = configured()
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT * FROM meta_oauth_states WHERE state_hash=? AND organization_id=? AND user_id=? AND session_hash=? AND expires_at>?', (auth.digest(state), user['organization_id'], user['id'], request.state.session_hash, int(time.time()))).fetchone()
            if not row:
                raise HTTPException(403, 'Facebook-Anmeldung ist abgelaufen oder gehört zu einer anderen Sitzung.')
            conn.execute('DELETE FROM meta_oauth_states WHERE state_hash=?', (auth.digest(state),))
        if error or not code:
            return RedirectResponse(config['origin'] + '/app?social=cancelled', status_code=303)
        try:
            short = graph('POST', 'oauth/access_token', data={'client_id': os.environ['MH_META_APP_ID'], 'client_secret': os.environ['MH_META_APP_SECRET'], 'redirect_uri': config['callback'], 'code': code})
            extended = graph('POST', 'oauth/access_token', data={'grant_type': 'fb_exchange_token', 'client_id': os.environ['MH_META_APP_ID'], 'client_secret': os.environ['MH_META_APP_SECRET'], 'fb_exchange_token': short['access_token']})
            token = extended['access_token']
            expires = int(time.time()) + int(extended['expires_in'])
            permissions = graph('GET', 'me/permissions', token)['data']
            granted = {p['permission'] for p in permissions if p.get('status') == 'granted'}
            if not FACEBOOK_SCOPES <= granted: raise ProviderError(rejected=True)
            include_ig = bool(row['instagram'] and INSTAGRAM_SCOPES <= granted)
            fields = 'id,name,access_token,tasks' + (',instagram_business_account{id,username}' if include_ig else '')
            pages, after = [], ''
            for _ in range(10):
                data = {'fields': fields, 'limit': 100}
                if after: data['after'] = after
                result = graph('GET', 'me/accounts', token, data)
                for p in result['data']:
                    tasks = set(p.get('tasks', []))
                    if not tasks & {'CREATE_CONTENT', 'MANAGE', 'PROFILE_PLUS_CREATE_CONTENT', 'PROFILE_PLUS_FULL_CONTROL', 'PROFILE_PLUS_MANAGE', 'PROFILE_PLUS_FACEBOOK_ACCESS'}: continue
                    if not str(p.get('id', '')).isdigit() or not p.get('access_token'): continue
                    ig = p.get('instagram_business_account', {}) if include_ig else {}
                    pages.append({'id': p['id'], 'name': str(p['name'])[:200], 'token': p['access_token'], 'instagram_id': str(ig.get('id', '')), 'instagram_name': str(ig.get('username', ''))[:200]})
                if not result.get('paging', {}).get('next'): break
                after = result.get('paging', {}).get('cursors', {}).get('after', '')
                if not after: break
            if not pages: raise ProviderError(rejected=True)
            with db() as conn:
                conn.execute('INSERT OR REPLACE INTO meta_pending_pages VALUES(?,?,?,?,?)', (user['organization_id'], user['id'], request.state.session_hash, seal({'pages': pages, 'token_expires': expires}), int(time.time()) + 1200))
        except (ProviderError, KeyError, TypeError, ValueError):
            return RedirectResponse(config['origin'] + '/app?social=failed', status_code=303)
        return RedirectResponse(config['origin'] + '/app?social=select', status_code=303)

    @app.post('/social/meta/page')
    def select_page(body: PageBody, request: Request, user=Depends(current_user)):
        company(user, admin=True, write=True)
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT * FROM meta_pending_pages WHERE organization_id=? AND user_id=? AND session_hash=? AND expires_at>?', (user['organization_id'], user['id'], request.state.session_hash, int(time.time()))).fetchone()
            if not row: raise HTTPException(409, 'Bitte zuerst über Facebook anmelden und die Seiten freigeben.')
            payload = unseal(row['payload'])
            page = next((p for p in payload['pages'] if p['id'] == body.page_id), None)
            if not page: raise HTTPException(404, 'Seite wurde für diese Verbindung nicht freigegeben.')
            if payload['token_expires'] <= int(time.time()): raise HTTPException(409, 'Bitte die Facebook-Verbindung erneuern.')
            conn.execute('INSERT OR REPLACE INTO meta_connections VALUES(?,?,?,?,?,?,?,?,?)', (user['organization_id'], page['id'], page['name'], seal(page['token']), page['instagram_id'], page['instagram_name'], payload['token_expires'], int(time.time()), secrets.token_urlsafe(24)))
            conn.execute('DELETE FROM meta_pending_pages WHERE organization_id=?', (user['organization_id'],))
            conn.execute('DELETE FROM meta_oauth_states WHERE organization_id=?', (user['organization_id'],))
        return {'connected': True, 'page_name': page['name']}

    @app.delete('/social/meta/connection')
    def disconnect(user=Depends(current_user)):
        company(user, admin=True)
        with db() as conn:
            for table in ('meta_connections', 'meta_pending_pages', 'meta_oauth_states'):
                conn.execute('DELETE FROM ' + table + ' WHERE organization_id=?', (user['organization_id'],))
        return {'disconnected': True}

    @app.get('/campaigns/{project_id}/social/publication')
    def publication(project_id: int, user=Depends(current_user)):
        company(user)
        with db() as conn:
            project_row(conn, project_id, user)
            row = conn.execute("SELECT * FROM social_publications WHERE project_id=? AND platform='facebook'", (project_id,)).fetchone()
        return {'publication': projection(row) if row else None}

    @app.post('/campaigns/{project_id}/social/facebook/preview')
    def preview(project_id: int, body: PreviewBody, user=Depends(current_user)):
        company(user, write=True)
        configured()
        if not body.message.strip(): raise HTTPException(422, 'Bitte den Beitragstext prüfen.')
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            project = project_row(conn, project_id, user)
            from .recruiting import ensure_open
            ensure_open(conn, project_id)
            if project['status'] != 'Live': raise HTTPException(409, 'Die Kampagne muss zuerst intern freigegeben werden.')
            target = connection(conn, user['organization_id'])
            link = valid_link(conn, project, body.link_id)
            existing = conn.execute("SELECT state FROM social_publications WHERE project_id=? AND platform='facebook'", (project_id,)).fetchone()
            if existing and existing['state'] not in {'preview', 'failed'}:
                raise HTTPException(409, 'Eine Veröffentlichung liegt bereits vor oder muss zuerst auf Facebook geprüft werden.')
            conn.execute("DELETE FROM social_publications WHERE project_id=? AND platform='facebook'", (project_id,))
            ident, now = secrets.token_urlsafe(24), int(time.time())
            message = body.message.strip() + '\n\n' + link
            conn.execute('INSERT INTO social_publications(id,organization_id,project_id,actor_id,page_id,page_name,connection_revision,project_digest,link_id,message,link_url,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,\'preview\',?,?)', (ident, user['organization_id'], project_id, user['id'], target['page_id'], target['page_name'], target['revision'], fingerprint(project), body.link_id, message, link, now, now))
            return projection(conn.execute('SELECT * FROM social_publications WHERE id=?', (ident,)).fetchone())

    @app.post('/campaigns/{project_id}/social/facebook/publish')
    def publish(project_id: int, body: PublishBody, user=Depends(current_user)):
        company(user, write=True)
        configured()
        if not body.confirmed: raise HTTPException(422, 'Bitte die öffentliche Veröffentlichung ausdrücklich bestätigen.')
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            project = project_row(conn, project_id, user)
            row = conn.execute('SELECT * FROM social_publications WHERE id=? AND project_id=? AND organization_id=?', (body.preview_id, project_id, user['organization_id'])).fetchone()
            if not row: raise HTTPException(404, 'Vorschau nicht gefunden.')
            if row['state'] == 'published': return projection(row)
            from .recruiting import ensure_open
            ensure_open(conn, project_id)
            if row['state'] != 'preview': raise HTTPException(409, 'Veröffentlichungsstatus zuerst auf Facebook prüfen. Kein automatischer Wiederholungsversuch.')
            target = connection(conn, user['organization_id'])
            if project['status'] != 'Live' or row['project_digest'] != fingerprint(project) or row['connection_revision'] != target['revision'] or row['created_at'] < int(time.time()) - 1200:
                raise HTTPException(409, 'Vorschau ist nicht mehr aktuell. Bitte erneut prüfen.')
            if valid_link(conn, project, row['link_id']) != row['link_url']:
                raise HTTPException(409, 'Bewerbungslink hat sich geändert. Bitte eine neue Vorschau erstellen.')
            token = unseal(target['token'])
            conn.execute("UPDATE social_publications SET state='publishing',updated_at=? WHERE id=?", (int(time.time()), row['id']))
        state, post_id, post_url = 'unknown', '', ''
        try:
            result = graph('POST', target['page_id'] + '/feed', token, {'message': row['message'], 'link': row['link_url']})
            ident = result.get('id', '')
            if not isinstance(ident, str) or not re.fullmatch(re.escape(target['page_id']) + r'_\d+', ident): raise ProviderError()
            post_id = ident
            post_url = 'https://www.facebook.com/' + target['page_id'] + '/posts/' + ident.split('_')[1]
            state = 'published'
        except ProviderError as exc:
            state = 'failed' if exc.rejected else 'unknown'
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('UPDATE social_publications SET state=?,post_id=?,post_url=?,updated_at=? WHERE id=?', (state, post_id, post_url, int(time.time()), row['id']))
            log_history(conn, user['organization_id'], project_id, user['id'], 'facebook_' + state, 'Facebook: ' + {'published': 'Beitrag veröffentlicht', 'failed': 'Veröffentlichung abgewiesen', 'unknown': 'Ergebnis unklar; auf Facebook prüfen'}[state])
            return projection(conn.execute('SELECT * FROM social_publications WHERE id=?', (row['id'],)).fetchone())

    @app.post('/campaigns/{project_id}/social/facebook/verify')
    def verify(project_id: int, body: VerifyBody, user=Depends(current_user)):
        company(user, admin=True, write=True)
        with db() as conn:
            project_row(conn, project_id, user)
            row = conn.execute("SELECT * FROM social_publications WHERE project_id=? AND platform='facebook'", (project_id,)).fetchone()
            if not row or row['state'] not in {'unknown', 'publishing'} or row['updated_at'] > int(time.time()) - 120:
                raise HTTPException(409, 'Ein unklarer Veröffentlichungsstatus kann nach zwei Minuten geprüft werden.')
            target = connection(conn, user['organization_id'])
            if target['page_id'] != row['page_id'] or not body.post_id.startswith(row['page_id'] + '_'):
                raise HTTPException(422, 'Beitrag gehört nicht zur ursprünglichen Facebook-Seite.')
            token = unseal(target['token'])
        try:
            post = graph('GET', body.post_id, token, {'fields': 'id,message'})
        except ProviderError:
            raise HTTPException(502, 'Facebook-Beitrag konnte nicht überprüft werden.') from None
        if post.get('id') != body.post_id or post.get('message') != row['message']:
            raise HTTPException(409, 'Facebook-Beitrag stimmt nicht mit der gespeicherten Vorschau überein.')
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            result = conn.execute("UPDATE social_publications SET state='published',post_id=?,post_url=?,updated_at=? WHERE id=? AND state IN ('unknown','publishing')", (body.post_id, 'https://www.facebook.com/' + row['page_id'] + '/posts/' + body.post_id.split('_')[1], int(time.time()), row['id']))
            if result.rowcount: log_history(conn, user['organization_id'], project_id, user['id'], 'facebook_verified', 'Facebook-Veröffentlichung nachträglich bestätigt')
            return projection(conn.execute('SELECT * FROM social_publications WHERE id=?', (row['id'],)).fetchone())
