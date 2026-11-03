"""Durable, tenant-scoped campaign status notifications with retryable delivery."""
import logging
import os
import threading
import time
from . import auth, mail_templates

logger = logging.getLogger(__name__)


def schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS status_deliveries (
        id INTEGER PRIMARY KEY,
        event_id TEXT NOT NULL,
        organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        recipient TEXT NOT NULL, language TEXT NOT NULL,
        company TEXT NOT NULL, title TEXT NOT NULL, actor TEXT NOT NULL,
        old_status TEXT NOT NULL, new_status TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
        next_attempt INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL, sent_at INTEGER,
        UNIQUE(event_id,user_id)
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS status_delivery_due ON status_deliveries(state,next_attempt)")


def queue(conn, project, old_status, new_status, actor_id, event_id):
    if old_status == new_status:
        return
    company = conn.execute("SELECT name FROM organizations WHERE id=?", (project['organization_id'],)).fetchone()[0]
    actor = conn.execute("SELECT name FROM users WHERE id=?", (actor_id,)).fetchone()[0]
    # Include every existing company role, including the actor, with a verified mailbox.
    for recipient in conn.execute("SELECT id,email,email_language FROM users WHERE organization_id=? AND email_verified=1 AND role IN ('firmen_admin','user','kunde')", (project['organization_id'],)).fetchall():
        conn.execute("""INSERT OR IGNORE INTO status_deliveries
            (event_id,organization_id,project_id,user_id,recipient,language,company,title,actor,old_status,new_status,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (event_id, project['organization_id'], project['id'], recipient['id'], recipient['email'], recipient['email_language'], company, project['role'], actor, old_status, new_status, int(time.time())))


def drain(db, limit=50):
    """Claim each delivery before SMTP; never hold the status transaction during I/O."""
    for _ in range(limit):
        now = int(time.time())
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute("SELECT * FROM status_deliveries WHERE state IN ('pending','sending') AND next_attempt<=? ORDER BY id LIMIT 1", (now,)).fetchone()
            if not row:
                return
            eligible = conn.execute("SELECT 1 FROM users WHERE id=? AND organization_id=? AND email=? AND email_verified=1 AND role IN ('firmen_admin','user','kunde')", (row['user_id'],row['organization_id'],row['recipient'])).fetchone()
            if not eligible:
                conn.execute("UPDATE status_deliveries SET state='cancelled' WHERE id=?", (row['id'],))
                continue
            conn.execute("UPDATE status_deliveries SET state='sending', attempts=attempts+1,next_attempt=? WHERE id=?", (now+300,row['id']))
        try:
            message = mail_templates.status_message(os.getenv('MH_MAIL_FROM','MH <noreply@mh.local>'),row['recipient'],row['company'],row['title'],row['actor'],row['old_status'],row['new_status'],os.getenv('MH_PUBLIC_URL','http://127.0.0.1:5181'),row['language'])
            auth.deliver_message(message)
        except Exception:
            # No message bodies, addresses or provider exceptions in logs.
            logger.warning('Campaign status delivery %s failed; retry queued',row['id'])
            with db() as conn:
                conn.execute("UPDATE status_deliveries SET state='pending',next_attempt=? WHERE id=?", (int(time.time())+min(3600,30*2**min(row['attempts'],7)),row['id']))
        else:
            with db() as conn:
                conn.execute("UPDATE status_deliveries SET state='sent',sent_at=? WHERE id=?", (int(time.time()),row['id']))


def install(app, db):
    stop = threading.Event()
    worker = None

    def run():
        while not stop.is_set():
            try:
                drain(db)
            except Exception:
                logger.warning('Campaign status delivery worker will retry')
            stop.wait(30)

    @app.on_event('startup')
    def start():
        nonlocal worker
        stop.clear()
        worker = threading.Thread(target=run,daemon=True,name='mh-status-mail')
        worker.start()

    @app.on_event('shutdown')
    def shutdown():
        stop.set()
        if worker:
            worker.join(timeout=20)
