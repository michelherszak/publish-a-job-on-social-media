"""Durable campaign orchestration with a local-only provider simulator.

Simulator receipts are never represented as external posts, spend or audiences.
No network implementation or live-mode switch exists in this module.
"""
import hashlib
import json
import time

from fastapi import HTTPException
from . import billing


def schema(conn):
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS campaign_runs (
      id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
      fingerprint TEXT NOT NULL, snapshot TEXT NOT NULL, feed BLOB, story BLOB,
      mode TEXT NOT NULL DEFAULT 'simulation', enabled INTEGER NOT NULL DEFAULT 1,
      created_at INTEGER NOT NULL, ads_end_at INTEGER NOT NULL,
      UNIQUE(project_id,fingerprint));
    CREATE TABLE IF NOT EXISTS campaign_run_heads (
      project_id INTEGER PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
      run_id INTEGER NOT NULL REFERENCES campaign_runs(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS campaign_actions (
      id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES campaign_runs(id) ON DELETE CASCADE,
      channel TEXT NOT NULL, kind TEXT NOT NULL, link_id TEXT NOT NULL REFERENCES ad_links(id) ON DELETE CASCADE,
      state TEXT NOT NULL DEFAULT 'queued', reason TEXT NOT NULL DEFAULT '',
      provider_id TEXT NOT NULL DEFAULT '', uncertain INTEGER NOT NULL DEFAULT 0, attempts INTEGER NOT NULL DEFAULT 0,
      allocation_cents INTEGER NOT NULL DEFAULT 0, spent_cents INTEGER NOT NULL DEFAULT 0,
      impressions INTEGER NOT NULL DEFAULT 0, clicks INTEGER NOT NULL DEFAULT 0,
      UNIQUE(run_id,channel,kind));
    CREATE TABLE IF NOT EXISTS campaign_sim_receipts (
      action_id INTEGER NOT NULL REFERENCES campaign_actions(id) ON DELETE CASCADE,
      request_key TEXT NOT NULL, spent_cents INTEGER NOT NULL, occurred_at INTEGER NOT NULL,
      PRIMARY KEY(action_id,request_key));
    ''')
    conn.execute('INSERT OR IGNORE INTO campaign_run_heads SELECT project_id,MAX(id) FROM campaign_runs GROUP BY project_id')
    if 'uncertain' not in {r['name'] for r in conn.execute('PRAGMA table_info(campaign_actions)')}:
        conn.execute('ALTER TABLE campaign_actions ADD COLUMN uncertain INTEGER NOT NULL DEFAULT 0')


def audience(conn, pid):
    # Ephemeral consenting page visits only. No applicant data/cross-visit identity.
    return conn.execute('SELECT COUNT(*) FROM job_flows WHERE project_id=? AND marketing=1 AND engaged=1 AND applied=0 AND expires_at>?',
                        (pid, int(time.time()))).fetchone()[0]


def stop(conn, pid, reason='withdrawn'):
    conn.execute('UPDATE campaign_runs SET enabled=0 WHERE project_id=?', (pid,))
    conn.execute("UPDATE campaign_actions SET state='paused',reason=? WHERE run_id IN (SELECT id FROM campaign_runs WHERE project_id=?)", (reason, pid))
    conn.execute("UPDATE job_distribution SET state='paused' WHERE project_id=?", (pid,))


def valid(conn, run):
    pid = run['project_id']
    snapshot = json.loads(run['snapshot'])
    current = conn.execute('''SELECT p.organization_id,p.status,p.generated,p.image_revision,j.revision,j.ends_at,a.enabled,
      COALESCE(n.state,'open') AS recruiting_state FROM projects p
      JOIN job_portal_plans j ON j.project_id=p.id JOIN application_pages a ON a.project_id=p.id
      LEFT JOIN recruiting_needs n ON n.project_id=p.id WHERE p.id=?''', (pid,)).fetchone()
    if not run['enabled'] or not current or not current['enabled']:
        return 'withdrawn'
    account = billing.account(conn,current['organization_id'])
    if account and not billing.usable(account):
        return 'subscription'
    if current['status'] != 'Live' or current['recruiting_state'] != 'open':
        return 'closed'
    if current['ends_at'] and current['ends_at'] <= int(time.time()):
        return 'expired'
    if (current['revision'] != snapshot['plan']['revision'] or current['image_revision'] != snapshot['image_revision']
            or json.loads(current['generated']) != snapshot['texts']):
        return 'changed'
    return ''


def prepare(conn, project, plan, origin):
    texts = json.loads(project['generated'])
    image = conn.execute('SELECT feed,story FROM campaign_images WHERE project_id=? AND selected=1', (project['id'],)).fetchone()
    snapshot = dict(title=project['role'], location=project['location'], texts=texts, plan=plan,
                    image_revision=project['image_revision'], origin=origin,
                    image_digest=hashlib.sha256(image['feed']+image['story']).hexdigest() if image else '')
    encoded = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
    fingerprint = hashlib.sha256(encoded.encode()).hexdigest()
    old = conn.execute('SELECT * FROM campaign_runs WHERE project_id=? AND fingerprint=?', (project['id'], fingerprint)).fetchone()
    if old:
        # Repeated clicks preserve receipts, allocations and provider identities.
        stop(conn,project['id'],'superseded')
        conn.execute('INSERT INTO campaign_run_heads VALUES(?,?) ON CONFLICT(project_id) DO UPDATE SET run_id=excluded.run_id',(project['id'],old['id']))
        conn.execute('UPDATE campaign_runs SET enabled=1 WHERE id=?', (old['id'],))
        conn.execute("UPDATE campaign_actions SET state=CASE WHEN uncertain=1 THEN 'unknown' WHEN provider_id!='' THEN 'simulated' WHEN attempts>=3 THEN 'failed' ELSE 'queued' END,reason='' WHERE run_id=? AND state='paused'", (old['id'],))
        return old['id']
    stop(conn, project['id'], 'superseded')
    now = int(time.time())
    run_id = conn.execute('INSERT INTO campaign_runs(project_id,fingerprint,snapshot,feed,story,created_at,ads_end_at) VALUES(?,?,?,?,?,?,?)',
                          (project['id'], fingerprint, encoded, image['feed'] if image else None, image['story'] if image else None,
                           now, now+plan['duration_days']*86400)).lastrowid
    conn.execute('INSERT INTO campaign_run_heads VALUES(?,?) ON CONFLICT(project_id) DO UPDATE SET run_id=excluded.run_id',(project['id'],run_id))
    spent = conn.execute('SELECT COALESCE(SUM(a.spent_cents),0) FROM campaign_actions a JOIN campaign_runs r ON r.id=a.run_id WHERE r.project_id=?', (project['id'],)).fetchone()[0]
    remaining = max(0, plan['budget_cents']-spent)
    paid_count = 4 if plan['retargeting'] else 2
    paid_index = 0
    for task in conn.execute('SELECT * FROM job_distribution WHERE project_id=? ORDER BY channel,kind', (project['id'],)).fetchall():
        allocation = 0
        if task['kind'] != 'organic':
            allocation = remaining//paid_count + int(paid_index < remaining % paid_count)
            paid_index += 1
        conn.execute('INSERT INTO campaign_actions(run_id,channel,kind,link_id,allocation_cents) VALUES(?,?,?,?,?)',
                     (run_id, task['channel'], task['kind'], task['link_id'], allocation))
    return run_id


class DeliveryFailure(Exception):
    """Known rejection may be retried; ambiguous delivery must be reconciled."""
    def __init__(self, uncertain=False):
        self.uncertain = uncertain


class LocalProvider:
    def deliver(self, key, payload):
        # The identical immutable request has an identical provider receipt.
        return {'id': 'sim_'+hashlib.sha256(key.encode()).hexdigest()[:24], 'mode': 'simulation'}

    def reconcile(self, key, payload):
        return self.deliver(key, payload)

    def traffic(self, key, maximum):
        return {'spent_cents': min(100, maximum), 'impressions': 10, 'clicks': 1}


PROVIDER = LocalProvider()


def payload(run, action):
    snapshot = json.loads(run['snapshot'])
    return dict(channel=action['channel'], kind=action['kind'], text=snapshot['texts'].get('social' if action['channel']=='Instagram' else 'meta',''),
                landing_url=snapshot['origin']+'/r/'+action['link_id'],
                placement='profile_or_story_link' if action['channel']=='Instagram' and action['kind']=='organic' else 'clickable_ad_or_post',
                feed=run['feed'], story=run['story'], country='DE', category='EMPLOYMENT',
                allocation_cents=action['allocation_cents'], ads_end_at=run['ads_end_at'])


def sync_distribution(conn, pid, run_id):
    for action in conn.execute('SELECT * FROM campaign_actions WHERE run_id=?', (run_id,)):
        conn.execute('UPDATE job_distribution SET state=? WHERE project_id=? AND channel=? AND kind=?',
                     (action['state'], pid, action['channel'], action['kind']))


def execute(conn, run_id, reconcile=False):
    # All local state changes run inside BEGIN IMMEDIATE. No network while locked.
    run = conn.execute('SELECT * FROM campaign_runs WHERE id=?', (run_id,)).fetchone()
    if not run:
        return
    reason = valid(conn, run)
    if reason:
        stop(conn, run['project_id'], reason)
        return
    readers = audience(conn, run['project_id'])
    for action in conn.execute('SELECT * FROM campaign_actions WHERE run_id=? ORDER BY id', (run_id,)).fetchall():
        if action['uncertain'] and not reconcile:
            continue
        snapshot = json.loads(run['snapshot'])
        reason = ''
        if not snapshot['texts'].get('social' if action['channel']=='Instagram' else 'meta','').strip():
            reason = 'missing_text'
        elif action['channel']=='Instagram' and not run['feed']:
            reason = 'missing_image'
        elif action['kind']!='organic' and int(time.time())>=run['ads_end_at']:
            reason = 'duration_ended'
        elif action['kind']!='organic' and action['spent_cents']>=action['allocation_cents']:
            reason = 'budget_exhausted'
        elif action['kind']=='retargeting' and not readers:
            reason = 'no_audience'
        if reason:
            state = 'waiting' if reason=='no_audience' else 'blocked'
            conn.execute('UPDATE campaign_actions SET state=?,reason=? WHERE id=?', (state,reason,action['id']))
            continue
        if action['state']=='unknown' and not reconcile:
            continue
        if action['provider_id']:
            conn.execute("UPDATE campaign_actions SET state='simulated',reason='' WHERE id=?", (action['id'],))
            continue
        if action['attempts']>=3 and action['state']=='failed':
            continue
        key = 'campaign:'+str(run_id)+':'+str(action['id'])
        conn.execute('UPDATE campaign_actions SET attempts=attempts+1 WHERE id=?', (action['id'],))
        try:
            receipt = PROVIDER.reconcile(key,payload(run,action)) if action['uncertain'] else PROVIDER.deliver(key,payload(run,action))
            if receipt.get('mode')!='simulation' or not isinstance(receipt.get('id'),str) or not receipt['id'].startswith('sim_'):
                raise DeliveryFailure(uncertain=True)
            conn.execute("UPDATE campaign_actions SET state='simulated',reason='',uncertain=0,provider_id=? WHERE id=?", (receipt['id'],action['id']))
        except DeliveryFailure as error:
            conn.execute('UPDATE campaign_actions SET state=?,reason=?,uncertain=? WHERE id=?',
                         ('unknown' if error.uncertain else 'failed','uncertain' if error.uncertain else 'provider_rejected',int(error.uncertain),action['id']))
    sync_distribution(conn, run['project_id'], run_id)


def current(conn, pid):
    run = conn.execute('SELECT r.* FROM campaign_runs r JOIN campaign_run_heads h ON h.run_id=r.id WHERE h.project_id=?', (pid,)).fetchone()
    return run


def reconcile_lifecycle(conn, pid):
    run = current(conn, pid)
    if not run:
        return
    reason = valid(conn, run)
    if reason:
        stop(conn, pid, reason)
        return
    readers = audience(conn, pid)
    for task in conn.execute("SELECT * FROM campaign_actions WHERE run_id=? AND kind='retargeting'",(run['id'],)).fetchall():
        if task['state']=='simulated' and not readers:
            conn.execute("UPDATE campaign_actions SET state='waiting',reason='no_audience' WHERE id=?",(task['id'],))
    sync_distribution(conn, pid, run['id'])


def projection(conn, pid):
    reconcile_lifecycle(conn, pid)
    run = current(conn, pid)
    if not run:
        return None
    snapshot = json.loads(run['snapshot'])
    spent = conn.execute('SELECT COALESCE(SUM(a.spent_cents),0) FROM campaign_actions a JOIN campaign_runs r ON r.id=a.run_id WHERE r.project_id=?', (pid,)).fetchone()[0]
    tasks = [dict(r) for r in conn.execute('SELECT id,channel,kind,state,reason,provider_id,attempts,allocation_cents,spent_cents,impressions,clicks,link_id FROM campaign_actions WHERE run_id=? ORDER BY id', (run['id'],))]
    for task in tasks:
        task['url'] = snapshot['origin']+'/r/'+task['link_id']
        task['text'] = snapshot['texts'].get('social' if task['channel']=='Instagram' else 'meta','')
        task['placement'] = 'profile_or_story_link' if task['channel']=='Instagram' and task['kind']=='organic' else 'clickable_ad_or_post'
    return dict(id=run['id'], mode='simulation', enabled=bool(run['enabled']), created_at=run['created_at'], ads_end_at=run['ads_end_at'],
                tasks=tasks, audience=audience(conn,pid) if run['enabled'] else 0,
                budget_cents=snapshot['plan']['budget_cents'], simulated_spent_cents=spent,
                remaining_cents=max(0,snapshot['plan']['budget_cents']-spent), actual_spent_cents=0,
                image=bool(run['feed']), external_published=False)


def simulate_traffic(conn, pid, request_key):
    run = current(conn, pid)
    if not run or valid(conn, run):
        raise HTTPException(409, 'Workflow zuerst starten oder aktualisieren.')
    execute(conn, run['id'])
    cap = json.loads(run['snapshot'])['plan']['budget_cents']
    for task in conn.execute("SELECT * FROM campaign_actions WHERE run_id=? AND kind!='organic' AND state='simulated'", (run['id'],)).fetchall():
        if conn.execute('SELECT 1 FROM campaign_sim_receipts WHERE action_id=? AND request_key=?', (task['id'],request_key)).fetchone():
            continue
        total = conn.execute('SELECT COALESCE(SUM(a.spent_cents),0) FROM campaign_actions a JOIN campaign_runs r ON r.id=a.run_id WHERE r.project_id=?', (pid,)).fetchone()[0]
        maximum = min(task['allocation_cents']-task['spent_cents'], cap-total)
        if maximum<=0:
            continue
        receipt = PROVIDER.traffic(str(task['id'])+':'+request_key,maximum)
        amount = receipt.get('spent_cents')
        impressions, clicks = receipt.get('impressions'), receipt.get('clicks')
        if (type(amount) is not int or not 0<=amount<=maximum or type(impressions) is not int or not 0<=impressions<=1000000
                or type(clicks) is not int or not 0<=clicks<=impressions):
            raise HTTPException(502, 'Simulationsquittung ungültig.')
        conn.execute('INSERT INTO campaign_sim_receipts VALUES(?,?,?,?)', (task['id'],request_key,amount,int(time.time())))
        conn.execute('UPDATE campaign_actions SET spent_cents=spent_cents+?,impressions=impressions+?,clicks=clicks+? WHERE id=?',
                     (amount,impressions,clicks,task['id']))
    execute(conn, run['id'])
    return projection(conn, pid)
