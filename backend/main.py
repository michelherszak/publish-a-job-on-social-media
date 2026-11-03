from __future__ import annotations

import hashlib
import html
import io
import zipfile
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Literal, Annotated
from urllib.parse import urlparse

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

try:
    from . import billing, auth, ai, mail_templates, status_mail, tracking, social, recruiting, campaign_images, job_portal, account_recovery
    from .security import RequestSizeLimit
except ImportError:
    import billing, auth, ai, mail_templates, status_mail, tracking, social, recruiting, campaign_images, job_portal, account_recovery
    from security import RequestSizeLimit

DB = Path(__file__).parent / "mh.db"
DEMO_DB = Path(__file__).parent / "mh_demo.db"
CREDENTIALS = Path(__file__).parent / "demo_credentials.txt"
INTEGRATION_SETTINGS = Path(__file__).parent / "integration_settings.json"
SETTINGS_LOCK = threading.Lock()
INTEGRATIONS = {"openai": "OpenAI", "meta": "Meta", "linkedin": "LinkedIn", "xing": "XING"}
COMPANY_INTEGRATIONS = ("meta", "linkedin", "xing")
app = FastAPI(title="MH API", version="0.2.0", docs_url=None if auth.production() else "/docs", redoc_url=None if auth.production() else "/redoc", openapi_url=None if auth.production() else "/openapi.json")
app.add_middleware(
    CORSMiddleware,
    allow_origins=([] if auth.production() else ["http://127.0.0.1:5181", "http://localhost:5181", "http://127.0.0.1:4181"]) + ([os.environ["MH_PUBLIC_URL"].rstrip("/")] if os.getenv("MH_PUBLIC_URL") else []),
    allow_methods=["GET", "POST", "PATCH", "DELETE", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "Idempotency-Key", "X-CSRF-Token", "Accept-Language"],
    allow_credentials=True,
)

# Permissions are checked on every route. Company users never receive another
# organization's data, including when a foreign ID is supplied directly.
PERMISSIONS = {
    "platform_admin": {"organizations:read", "campaigns:read", "campaigns:write", "users:manage"},
    "firmen_admin": {"organizations:read", "campaigns:read", "campaigns:write", "campaigns:approve", "users:manage"},
    "user": {"organizations:read", "campaigns:read", "campaigns:write", "campaigns:approve"},
    "kunde": {"organizations:read", "campaigns:read"},
}


def db(user: dict | None = None):
    database = DEMO_DB if user and user.get("view_role") else DB
    conn = sqlite3.connect(database, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    hashed = hashlib.scrypt(password.encode(), salt=salt, n=2**17, r=8, p=1, maxmem=256 * 1024 * 1024)
    return f"scrypt2:{salt.hex()}:{hashed.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        if stored.startswith("scrypt2:"):
            _, salt_hex, digest = stored.split(":")
            actual = password_hash(password, bytes.fromhex(salt_hex)).rsplit(":", 1)[1]
        else:
            salt_hex, digest = stored.split(":", 1)
            actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1).hex()
        return hmac.compare_digest(actual, digest)
    except (ValueError, TypeError):
        return False


def init_db():
    with db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
                industry TEXT NOT NULL DEFAULT '', location TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL, password_hash TEXT NOT NULL,
                role TEXT NOT NULL, organization_id INTEGER REFERENCES organizations(id)
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
                expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY, organization_id INTEGER NOT NULL REFERENCES organizations(id),
                role TEXT NOT NULL, location TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Draft',
                channels TEXT NOT NULL DEFAULT '[]', briefing TEXT NOT NULL DEFAULT '{}',
                generated TEXT NOT NULL DEFAULT '{}', change_request TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY, organization_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER REFERENCES projects(id), actor_id INTEGER REFERENCES users(id),
                message TEXT NOT NULL, created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS integration_credentials (
                organization_id INTEGER NOT NULL REFERENCES organizations(id),
                provider TEXT NOT NULL, api_key TEXT NOT NULL,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY(organization_id,provider)
            );
            CREATE TABLE IF NOT EXISTS campaign_metrics (
                project_id INTEGER NOT NULL REFERENCES projects(id), channel TEXT NOT NULL,
                impressions INTEGER NOT NULL DEFAULT 0, clicks INTEGER NOT NULL DEFAULT 0,
                applications INTEGER NOT NULL DEFAULT 0, source TEXT NOT NULL DEFAULT 'manual',
                updated_at INTEGER NOT NULL, PRIMARY KEY(project_id,channel)
            );
            CREATE TABLE IF NOT EXISTS campaign_history (
                id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id),
                organization_id INTEGER NOT NULL REFERENCES organizations(id),
                actor_id INTEGER REFERENCES users(id), action TEXT NOT NULL,
                message TEXT NOT NULL DEFAULT '', snapshot TEXT,
                created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS history_project_idx ON campaign_history(project_id,id);
            CREATE INDEX IF NOT EXISTS projects_org_idx ON projects(organization_id);
            CREATE INDEX IF NOT EXISTS activity_org_idx ON activity(organization_id);
        """)
        conn.execute("""CREATE TABLE IF NOT EXISTS ai_usage (
            id INTEGER PRIMARY KEY, organization_id INTEGER NOT NULL, project_id INTEGER NOT NULL,
            request_key TEXT NOT NULL, model TEXT NOT NULL, response_id TEXT NOT NULL,
            input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL, cached_tokens INTEGER NOT NULL,
            mh_tokens INTEGER NOT NULL, created_at INTEGER NOT NULL,
            UNIQUE(organization_id,request_key))""")
        billing.schema(conn)
        auth.schema(conn)
        status_mail.schema(conn)
        tracking.schema(conn)
        social.schema(conn)
        recruiting.schema(conn)
        campaign_images.schema(conn)
        job_portal.schema(conn)
        if "generation_mode" not in {row["name"] for row in conn.execute("PRAGMA table_info(projects)")}:
            conn.execute("ALTER TABLE projects ADD COLUMN generation_mode TEXT NOT NULL DEFAULT ''")
        org_columns = {row["name"] for row in conn.execute("PRAGMA table_info(organizations)")}
        for field in ("brand_description", "benefits", "tone", "contact_name", "contact_email", "website"):
            if field not in org_columns:
                conn.execute(f"ALTER TABLE organizations ADD COLUMN {field} TEXT NOT NULL DEFAULT ''")
        session_columns = {row["name"] for row in conn.execute("PRAGMA table_info(sessions)")}
        if "view_role" not in session_columns:
            conn.execute("ALTER TABLE sessions ADD COLUMN view_role TEXT")
        if "view_org_id" not in session_columns:
            conn.execute("ALTER TABLE sessions ADD COLUMN view_org_id INTEGER REFERENCES organizations(id)")
        conn.execute("CREATE TABLE IF NOT EXISTS deleted_demo_companies (name TEXT PRIMARY KEY)")
        companies = [
            ("Müller Elektrotechnik", "Handwerk", "Berlin"),
            ("Autohaus König", "Automotive", "Potsdam"),
            ("Pflegezentrum Sonnenhof", "Pflege", "Berlin"),
            ("Bäckerei Morgenrot", "Lebensmittel", "Berlin"),
        ]
        for name, industry, location in (companies if not auth.production() else []):
            if conn.execute("SELECT 1 FROM deleted_demo_companies WHERE name=?", (name,)).fetchone():
                continue
            conn.execute("INSERT OR IGNORE INTO organizations(name,industry,location) VALUES(?,?,?)", (name, industry, location))
        if conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0:
            existing = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='campaigns'").fetchone()
            if existing:
                for row in conn.execute("SELECT customer,role,location,status,channels FROM campaigns"):
                    org = conn.execute("SELECT id FROM organizations WHERE name=?", (row["customer"],)).fetchone()
                    if org:
                        now = int(time.time())
                        conn.execute("INSERT INTO projects(organization_id,role,location,status,channels,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (org["id"], row["role"], row["location"], row["status"], json.dumps(row["channels"].split(",")), now, now))
        for project in conn.execute("SELECT id,role,location,channels FROM projects WHERE briefing='{}'").fetchall():
            starter = {"role": project["role"], "location": project["location"], "employment_type": "Vollzeit", "tasks": "", "requirements": "", "benefits": "", "salary": "", "tone": "Freundlich und direkt", "channels": json.loads(project["channels"])}
            conn.execute("UPDATE projects SET briefing=? WHERE id=?", (json.dumps(starter), project["id"]))
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0 and not auth.production():
            accounts = [("admin@flh.local", "FLH Admin", "platform_admin", None)]
            for org in conn.execute("SELECT id,name FROM organizations"):
                slug = {"Müller Elektrotechnik":"mueller", "Autohaus König":"autohaus", "Pflegezentrum Sonnenhof":"pflege", "Bäckerei Morgenrot":"baeckerei"}[org["name"]]
                accounts.append((f"admin@{slug}.local", org["name"] + " Admin", "firmen_admin", org["id"]))
            credentials = []
            for email, name, role, org_id in accounts:
                password = secrets.token_urlsafe(18)
                conn.execute("INSERT INTO users(email,name,password_hash,role,organization_id) VALUES(?,?,?,?,?)", (email, name, password_hash(password), role, org_id))
                credentials.append(f"{email}  {password}")
            fd = os.open(CREDENTIALS, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as file:
                file.write("MH local demo accounts (keep private)\n" + "\n".join(credentials) + "\n")
        for project in conn.execute("SELECT p.id,p.briefing,o.name FROM projects p JOIN organizations o ON o.id=p.organization_id WHERE p.status IN ('Review','Live') AND p.generated='{}'").fetchall():
            conn.execute("UPDATE projects SET generated=? WHERE id=?", (json.dumps(make_content(json.loads(project["briefing"]), project["name"])), project["id"]))
        for project in conn.execute("SELECT id,organization_id,generated,created_at FROM projects WHERE NOT EXISTS (SELECT 1 FROM campaign_history h WHERE h.project_id=projects.id)").fetchall():
            snapshot = project["generated"] if project["generated"] != "{}" else None
            conn.execute("INSERT INTO campaign_history(project_id,organization_id,action,message,snapshot,created_at) VALUES(?,?,?,?,?,?)", (project["id"], project["organization_id"], "imported", "Bestehende Kampagne übernommen", snapshot, project["created_at"]))
    os.chmod(DB, 0o600)
    # Persisted role previews can predate an additive project-column migration.
    if DEMO_DB.exists():
        with sqlite3.connect(DEMO_DB) as preview:
            preview.row_factory = sqlite3.Row
            recruiting.schema(preview)
            campaign_images.schema(preview)
            job_portal.schema(preview)
        os.chmod(DEMO_DB, 0o600)




class LoginBody(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=128)


class DemoContext(BaseModel):
    role: Literal["platform_admin", "firmen_admin", "user", "kunde"]
    organization_id: int | None = None


class OrganizationBody(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    industry: str = Field(default="", max_length=160)
    location: str = Field(default="", max_length=160)


class OrganizationProfile(BaseModel):
    industry: str = Field(default="", max_length=160)
    location: str = Field(default="", max_length=160)
    brand_description: str = Field(default="", max_length=2000)
    benefits: str = Field(default="", max_length=2000)
    tone: str = Field(default="", max_length=500)
    contact_name: str = Field(default="", max_length=160)
    contact_email: str = Field(default="", max_length=320)
    website: str = Field(default="", max_length=500)


class Briefing(BaseModel):
    role: str = Field(min_length=2, max_length=180)
    location: str = Field(default="", max_length=180)
    learnable_requirements: str = Field(default="", max_length=4000)
    working_hours: str = Field(default="", max_length=500)
    employment_type: str = Field(default="Vollzeit", max_length=180)
    tasks: str = Field(default="", max_length=4000)
    requirements: str = Field(default="", max_length=4000)
    benefits: str = Field(default="", max_length=4000)
    salary: str = Field(default="", max_length=300)
    tone: str = Field(default="Freundlich und direkt", max_length=500)
    channels: list[Annotated[str, Field(max_length=80)]] = Field(default_factory=list, max_length=12)


class ProjectBody(BaseModel):
    organization_id: int
    briefing: Briefing


class ProjectPatch(BaseModel):
    image_edit: campaign_images.ImageEdit | None = None
    image_revision: int | None = Field(default=None, ge=0)
    briefing: Briefing | None = None
    generated: dict[Annotated[str, Field(max_length=80)], Annotated[str, Field(max_length=30000)]] | None = Field(default=None, max_length=12)
    reviewed_briefing: str | None = Field(default=None, min_length=64, max_length=64)
    status: Literal["Draft", "Review", "Live"] | None = None
    change_request: str | None = Field(default=None, max_length=4000)


class CommentBody(BaseModel):
    channel: str = Field(default="Allgemein", max_length=80)
    message: str = Field(min_length=1, max_length=2000)


class IntegrationBody(BaseModel):
    api_key: str | None = Field(default=None, max_length=2000)
    model: str | None = Field(default=None, max_length=120)


class MetricsBody(BaseModel):
    channel: str = Field(min_length=2, max_length=80)
    impressions: int = Field(ge=0)
    clicks: int = Field(ge=0)
    applications: int = Field(ge=0)
    source: str = Field(default="manual", max_length=100)


class UserBody(BaseModel):
    email: str = Field(max_length=320)
    name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=15, max_length=128)
    role: Literal["firmen_admin", "user", "kunde"]
    organization_id: int


def current_user(request: Request):
    token = request.cookies.get(auth.SESSION)
    if not token:
        raise HTTPException(401, "Sign in required")
    token_hash = auth.digest(token)
    with db() as conn:
        row = conn.execute("""SELECT u.id,u.email,u.name,u.role AS base_role,u.email_verified,u.security_required,u.mfa_recovery_required,
            (u.mfa_secret!='') AS mfa_enabled,s.mfa_ok,s.csrf_hash,s.last_seen,
            COALESCE(s.view_role,u.role) AS role, s.view_role AS view_role,
            CASE WHEN s.view_role IS NULL THEN u.organization_id ELSE s.view_org_id END AS organization_id
            FROM sessions s JOIN users u ON u.id=s.user_id
            WHERE s.token_hash=? AND s.expires_at>?""", (token_hash, int(time.time()))).fetchone()
        if row and row["last_seen"] and row["last_seen"] < int(time.time()) - 1800:
            conn.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))
            row = None
        if row:
            conn.execute("UPDATE sessions SET last_seen=? WHERE token_hash=?", (int(time.time()), token_hash))
    if not row:
        raise HTTPException(401, "Session expired")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and not hmac.compare_digest(row["csrf_hash"], auth.digest(request.headers.get("x-csrf-token", ""))):
        raise HTTPException(403, "Sicherheitsprüfung fehlgeschlagen. Bitte neu anmelden.")
    result = dict(row)
    result.pop("csrf_hash")
    result.pop("last_seen")
    result["mfa_required"] = bool(result["mfa_enabled"] or result["mfa_recovery_required"] or ((result["security_required"] or auth.production()) and result["base_role"] in {"firmen_admin", "platform_admin"}))
    result["security_pending"] = bool(not result["email_verified"] or (result["mfa_required"] and (not result["mfa_enabled"] or not result["mfa_ok"])))
    if result["security_pending"] and request.url.path not in {"/auth/me", "/auth/session", "/onboarding", "/auth/mfa/setup", "/auth/mfa/reconnect", "/auth/mfa/confirm", "/auth/mfa/challenge"}:
        raise HTTPException(403, "Bitte E-Mail-Bestätigung und Sicherheitsprüfung abschließen.")
    request.state.session_hash = token_hash
    return result


def require(user: dict, permission: str):
    if permission not in PERMISSIONS.get(user["role"], set()):
        raise HTTPException(403, "Insufficient permissions")
    if permission in {"campaigns:write", "campaigns:approve"} and user.get("organization_id") and not user.get("view_role"):
        with db() as conn:
            account = billing.account(conn, user["organization_id"])
            if account and not billing.usable(account):
                raise HTTPException(402, "Dein Konto benötigt ein aktives, bezahltes Abo. Bitte Abo & Tokens öffnen.")


def org_scope(user: dict, org_id: int):
    if user["role"] != "platform_admin" and user["organization_id"] != org_id:
        raise HTTPException(404, "Not found")


def project_row(conn, project_id: int, user: dict):
    row = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    org_scope(user, row["organization_id"])
    if user["role"] == "kunde" and row["status"] == "Draft":
        raise HTTPException(404, "Not found")
    return row


def serialize_project(row):
    value = dict(row)
    value["channels"] = json.loads(value["channels"])
    value["briefing"] = json.loads(value["briefing"])
    value["generated"] = json.loads(value["generated"])
    value["briefing_fingerprint"] = recruiting.fingerprint(value["briefing"])
    value["briefing_stale"] = bool(value["generated"] and value.get("generated_briefing") != value["briefing_fingerprint"])
    return value


def image_changed(conn, project, user, action, message, notify=True):
    status = 'Draft' if project['status'] == 'Review' else project['status']
    conn.execute('UPDATE projects SET image_revision=image_revision+1,status=?,updated_at=? WHERE id=?', (status, int(time.time()), project['id']))
    log_history(conn, project['organization_id'], project['id'], user['id'], action, message)
    if notify and status != project['status'] and not user.get('view_role'):
        updated = conn.execute('SELECT * FROM projects WHERE id=?', (project['id'],)).fetchone()
        status_mail.queue(conn, updated, project['status'], status, user['id'], secrets.token_hex(16))


def log_activity(conn, org_id, project_id, actor_id, message):
    conn.execute("INSERT INTO activity(organization_id,project_id,actor_id,message,created_at) VALUES(?,?,?,?,?)", (org_id, project_id, actor_id, message, int(time.time())))


def log_history(conn, org_id, project_id, actor_id, action, message="", snapshot=None):
    conn.execute("INSERT INTO campaign_history(project_id,organization_id,actor_id,action,message,snapshot,created_at) VALUES(?,?,?,?,?,?,?)",
                 (project_id, org_id, actor_id, action, message, json.dumps(snapshot) if snapshot is not None else None, int(time.time())))


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/auth/me")
def me(user: dict = Depends(current_user)):
    return user


@app.get("/auth/session")
def session_status(request: Request):
    # Anonymous/expired sessions are normal when opening the sign-in page.
    # Protected routes retain their existing 401 behavior.
    try:
        user = current_user(request)
    except HTTPException as error:
        if error.status_code != 401:
            raise
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": user}


def require_demo_admin(user: dict, request: Request):
    local_client = request.client and request.client.host in {"127.0.0.1", "::1", "testclient"}
    if os.getenv("MH_DEMO_SWITCHER", "1") != "1" or not local_client:
        raise HTTPException(404, "Not found")
    if user["base_role"] != "platform_admin":
        raise HTTPException(403, "Platform admin required")


@app.get("/demo/options")
def demo_options(request: Request, user: dict = Depends(current_user)):
    require_demo_admin(user, request)
    with db() as conn:
        companies = [dict(row) for row in conn.execute("SELECT id,name FROM organizations ORDER BY name")]
    return {"organizations": companies, "roles": ["firmen_admin", "user", "kunde"]}


@app.post("/demo/context")
def demo_context(body: DemoContext, request: Request, user: dict = Depends(current_user)):
    require_demo_admin(user, request)
    if body.role == "platform_admin":
        if body.organization_id is not None:
            raise HTTPException(422, "Platform Admin has no company scope")
        view_role, view_org_id = None, None
    else:
        if body.organization_id is None:
            raise HTTPException(422, "Choose a company")
        with db() as conn:
            if not conn.execute("SELECT id FROM organizations WHERE id=?", (body.organization_id,)).fetchone():
                raise HTTPException(404, "Company not found")
        view_role, view_org_id = body.role, body.organization_id
        if not user["view_role"] or not DEMO_DB.exists():
            with sqlite3.connect(DB) as source, sqlite3.connect(DEMO_DB) as target:
                source.backup(target)
            os.chmod(DEMO_DB, 0o600)
    token_hash = request.state.session_hash
    with db() as conn:
        conn.execute("UPDATE sessions SET view_role=?,view_org_id=? WHERE token_hash=? AND user_id=?", (view_role, view_org_id, token_hash, user["id"]))
    return {"ok": True, "role": body.role, "organization_id": body.organization_id}


def read_integration_settings():
    if not INTEGRATION_SETTINGS.exists():
        return {}
    try:
        with INTEGRATION_SETTINGS.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        raise HTTPException(500, "Integration settings could not be read")


def write_integration_settings(data: dict):
    temporary = INTEGRATION_SETTINGS.with_name(INTEGRATION_SETTINGS.name + "." + secrets.token_hex(6) + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(data, file)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, INTEGRATION_SETTINGS)
        os.chmod(INTEGRATION_SETTINGS, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


def integration_status(provider: str, configured: bool, model: str = ""):
    return {"provider": provider, "label": INTEGRATIONS[provider], "configured": configured, "model": model if provider == "openai" else ""}


def integration_scope(user: dict, provider: str):
    if provider not in INTEGRATIONS:
        raise HTTPException(404, "Integration not found")
    if provider == "openai":
        if user["role"] != "platform_admin":
            raise HTTPException(403, "Platform admin required")
    elif user["role"] != "firmen_admin" or user["organization_id"] is None:
        raise HTTPException(403, "Company admin required")


@app.get("/admin/email-previews")
def email_previews(request: Request, user: dict = Depends(current_user)):
    if user["base_role"] != "platform_admin" or user["role"] != "platform_admin" or user.get("view_role"):
        raise HTTPException(403, "Platform admin required")
    return {"previews": mail_templates.previews(mail_templates.request_language(request))}


@app.get("/settings/integrations")
def get_integrations(user: dict = Depends(current_user)):
    if user["role"] == "platform_admin":
        with SETTINGS_LOCK:
            entry = read_integration_settings().get("openai", {})
        return [integration_status("openai", bool(entry.get("api_key")), entry.get("model", ""))]
    if user["role"] == "firmen_admin" and user["organization_id"] is not None:
        with db(user) as conn:
            rows = conn.execute("SELECT provider FROM integration_credentials WHERE organization_id=?", (user["organization_id"],)).fetchall()
        configured = {row["provider"] for row in rows}
        return [integration_status(provider, provider in configured) for provider in COMPANY_INTEGRATIONS]
    raise HTTPException(403, "Admin role required")


@app.put("/settings/integrations/{provider}")
def set_integration(provider: str, body: IntegrationBody, user: dict = Depends(current_user)):
    integration_scope(user, provider)
    if provider == "openai":
        with SETTINGS_LOCK:
            data = read_integration_settings()
            entry = dict(data.get("openai", {}))
            if body.api_key is not None and body.api_key.strip():
                entry["api_key"] = body.api_key.strip()
            if body.model is not None:
                entry["model"] = body.model.strip()
            if not entry.get("api_key") and not entry.get("model"):
                raise HTTPException(422, "Enter a key or model")
            write_integration_settings({"openai": entry})
            return integration_status("openai", bool(entry.get("api_key")), entry.get("model", ""))
    if not body.api_key or not body.api_key.strip():
        raise HTTPException(422, "Enter a key")
    with db(user) as conn:
        conn.execute("""INSERT INTO integration_credentials(organization_id,provider,api_key,updated_at) VALUES(?,?,?,?)
            ON CONFLICT(organization_id,provider) DO UPDATE SET api_key=excluded.api_key,updated_at=excluded.updated_at""",
            (user["organization_id"], provider, body.api_key.strip(), int(time.time())))
    return integration_status(provider, True)


@app.delete("/settings/integrations/{provider}")
def delete_integration(provider: str, user: dict = Depends(current_user)):
    integration_scope(user, provider)
    if provider == "openai":
        with SETTINGS_LOCK:
            write_integration_settings({})
    else:
        with db(user) as conn:
            conn.execute("DELETE FROM integration_credentials WHERE organization_id=? AND provider=?", (user["organization_id"], provider))
    return integration_status(provider, False)


@app.get("/organizations")
def organizations(user: dict = Depends(current_user)):
    require(user, "organizations:read")
    with db(user) as conn:
        if user["role"] == "platform_admin":
            rows = conn.execute("SELECT * FROM organizations ORDER BY name").fetchall()
        else:
            rows = conn.execute("SELECT * FROM organizations WHERE id=?", (user["organization_id"],)).fetchall()
    return [dict(row) for row in rows]


@app.post("/organizations", status_code=201)
def create_organization(body: OrganizationBody, user: dict = Depends(current_user)):
    if user["role"] != "platform_admin":
        raise HTTPException(403, "Platform admin required")
    with db(user) as conn:
        try:
            cursor = conn.execute("INSERT INTO organizations(name,industry,location) VALUES(?,?,?)", (body.name.strip(), body.industry.strip(), body.location.strip()))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Organization already exists")
        return dict(conn.execute("SELECT * FROM organizations WHERE id=?", (cursor.lastrowid,)).fetchone())


@app.patch("/organizations/{org_id}")
def update_organization(org_id: int, body: OrganizationProfile, user: dict = Depends(current_user)):
    if user["role"] != "platform_admin":
        raise HTTPException(403, "Platform admin required")
    with db(user) as conn:
        if not conn.execute("SELECT id FROM organizations WHERE id=?", (org_id,)).fetchone():
            raise HTTPException(404, "Organization not found")
        values = body.model_dump()
        assignments = ",".join(f"{key}=?" for key in values)
        conn.execute(f"UPDATE organizations SET {assignments} WHERE id=?", (*[value.strip() for value in values.values()], org_id))
        return dict(conn.execute("SELECT * FROM organizations WHERE id=?", (org_id,)).fetchone())


def remove_organization(conn, org_id: int):
    user_ids = [row["id"] for row in conn.execute("SELECT id FROM users WHERE organization_id=?", (org_id,))]
    if user_ids:
        placeholders = ",".join("?" * len(user_ids))
        conn.execute(f"DELETE FROM sessions WHERE user_id IN ({placeholders})", user_ids)
        conn.execute(f"DELETE FROM auth_links WHERE user_id IN ({placeholders})", user_ids)
        conn.execute(f"DELETE FROM recovery_codes WHERE user_id IN ({placeholders})", user_ids)
    conn.execute("UPDATE sessions SET view_role=NULL, view_org_id=NULL WHERE view_org_id=?", (org_id,))
    conn.execute("DELETE FROM campaign_metrics WHERE project_id IN (SELECT id FROM projects WHERE organization_id=?)", (org_id,))
    conn.execute("DELETE FROM campaign_history WHERE organization_id=? OR project_id IN (SELECT id FROM projects WHERE organization_id=?)", (org_id, org_id))
    conn.execute("DELETE FROM activity WHERE organization_id=? OR project_id IN (SELECT id FROM projects WHERE organization_id=?)", (org_id, org_id))
    conn.execute("DELETE FROM ai_usage WHERE organization_id=?", (org_id,))
    conn.execute("DELETE FROM projects WHERE organization_id=?", (org_id,))
    conn.execute("DELETE FROM integration_credentials WHERE organization_id=?", (org_id,))
    conn.execute("DELETE FROM invitations WHERE organization_id=?", (org_id,))
    conn.execute("DELETE FROM users WHERE organization_id=?", (org_id,))
    conn.execute("DELETE FROM organizations WHERE id=?", (org_id,))


def organization_deletion_preview(conn, org_id: int):
    org = conn.execute("SELECT id,name FROM organizations WHERE id=?", (org_id,)).fetchone()
    if not org:
        raise HTTPException(404, "Organization not found")
    counts = {
        "users": conn.execute("SELECT COUNT(*) FROM users WHERE organization_id=?", (org_id,)).fetchone()[0],
        "campaigns": conn.execute("SELECT COUNT(*) FROM projects WHERE organization_id=?", (org_id,)).fetchone()[0],
        "history": conn.execute("SELECT COUNT(*) FROM campaign_history WHERE organization_id=?", (org_id,)).fetchone()[0],
        "metrics": conn.execute(
            "SELECT COUNT(*) FROM campaign_metrics WHERE project_id IN "
            "(SELECT id FROM projects WHERE organization_id=?)", (org_id,)
        ).fetchone()[0],
        "invitations": conn.execute("SELECT COUNT(*) FROM invitations WHERE organization_id=?", (org_id,)).fetchone()[0],
        "credentials": conn.execute(
            "SELECT COUNT(*) FROM integration_credentials WHERE organization_id=?", (org_id,)
        ).fetchone()[0],
    }
    billing_tables = ("billing_accounts", "billing_orders", "token_ledger", "invoice_deliveries")
    billing_records = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table} WHERE organization_id=?", (org_id,)).fetchone()[0]
        for table in billing_tables
    }
    return {
        "id": org["id"],
        "name": org["name"],
        "counts": counts,
        "billing_blocked": any(billing_records.values()),
        "billing_records": billing_records,
    }


class DeleteOrganizationBody(BaseModel):
    confirmation_name: str = Field(min_length=2, max_length=160)


@app.get("/organizations/{org_id}/deletion-preview")
def deletion_preview(org_id: int, user: dict = Depends(current_user)):
    if user["role"] != "platform_admin" or user.get("view_role"):
        raise HTTPException(403, "Platform admin required")
    with db(user) as conn:
        return organization_deletion_preview(conn, org_id)


@app.delete("/organizations/{org_id}")
def delete_organization(org_id: int, body: DeleteOrganizationBody, user: dict = Depends(current_user)):
    if user["role"] != "platform_admin" or user.get("view_role"):
        raise HTTPException(403, "Platform admin required")
    with db(user) as conn:
        conn.execute("BEGIN IMMEDIATE")
        org = conn.execute("SELECT id,name FROM organizations WHERE id=?", (org_id,)).fetchone()
        if not org:
            raise HTTPException(404, "Organization not found")
        if body.confirmation_name != org["name"]:
            raise HTTPException(409, "Bitte den Firmennamen exakt bestätigen.")
        if organization_deletion_preview(conn, org_id)["billing_blocked"]:
            raise HTTPException(409, "Kunden mit Abrechnungsdaten können hier nicht gelöscht werden. Abos und Abrechnungsdaten müssen separat geprüft und aufbewahrt werden.")
        # Keep deletion atomic and local; never cancel subscriptions through this action.
        conn.execute("INSERT OR IGNORE INTO deleted_demo_companies(name) VALUES(?)", (org["name"],))
        conn.execute("UPDATE activity SET actor_id=NULL WHERE actor_id IN (SELECT id FROM users WHERE organization_id=?)", (org_id,))
        conn.execute("UPDATE campaign_history SET actor_id=NULL WHERE actor_id IN (SELECT id FROM users WHERE organization_id=?)", (org_id,))
        remove_organization(conn, org_id)
    return {"ok": True}


@app.get("/users")
def users(user: dict = Depends(current_user)):
    require(user, "users:manage")
    with db(user) as conn:
        if user["role"] == "platform_admin":
            rows = conn.execute("SELECT id,email,name,role,organization_id FROM users ORDER BY name").fetchall()
        else:
            rows = conn.execute("SELECT id,email,name,role,organization_id FROM users WHERE organization_id=? ORDER BY name", (user["organization_id"],)).fetchall()
    return [dict(row) for row in rows]


@app.post("/users", status_code=201)
def create_user(body: UserBody, user: dict = Depends(current_user)):
    require(user, "users:manage")
    if not user.get("view_role") and user["role"] == "firmen_admin":
        with db() as conn:
            if billing.account(conn, user["organization_id"]):
                raise HTTPException(403, "Bitte neue Teammitglieder per Einladung hinzufügen.")
    org_scope(user, body.organization_id)
    with db(user) as conn:
        conn.execute("BEGIN IMMEDIATE")
        if not conn.execute("SELECT id FROM organizations WHERE id=?", (body.organization_id,)).fetchone():
            raise HTTPException(404, "Organization not found")
        if not user.get("view_role"):
            billing.enforce_seats(conn, body.organization_id, body.role)
        try:
            cursor = conn.execute("INSERT INTO users(email,name,password_hash,role,organization_id) VALUES(?,?,?,?,?)", (body.email.strip().lower(), body.name.strip(), password_hash(body.password), body.role, body.organization_id))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Email already in use")
    return {"id": cursor.lastrowid, "email": body.email.strip().lower(), "name": body.name.strip(), "role": body.role, "organization_id": body.organization_id}


@app.get("/campaigns")
def campaigns(user: dict = Depends(current_user)):
    require(user, "campaigns:read")
    with db(user) as conn:
        if user["role"] == "platform_admin":
            rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC,id DESC").fetchall()
        elif user["role"] == "kunde":
            rows = conn.execute("SELECT * FROM projects WHERE organization_id=? AND status IN ('Review','Live') ORDER BY updated_at DESC,id DESC", (user["organization_id"],)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM projects WHERE organization_id=? ORDER BY updated_at DESC,id DESC", (user["organization_id"],)).fetchall()
    return [serialize_project(row) for row in rows]


@app.post("/campaigns", status_code=201)
def create_campaign(body: ProjectBody, user: dict = Depends(current_user)):
    require(user, "campaigns:write")
    org_scope(user, body.organization_id)
    with db(user) as conn:
        if not conn.execute("SELECT id FROM organizations WHERE id=?", (body.organization_id,)).fetchone():
            raise HTTPException(404, "Organization not found")
        now = int(time.time())
        cursor = conn.execute("""INSERT INTO projects(organization_id,role,location,status,channels,briefing,created_at,updated_at)
            VALUES(?,?,?,'Draft',?,?,?,?)""", (body.organization_id, body.briefing.role, body.briefing.location, json.dumps(body.briefing.channels), body.briefing.model_dump_json(), now, now))
        log_activity(conn, body.organization_id, cursor.lastrowid, user["id"], "Campaign created")
        log_history(conn, body.organization_id, cursor.lastrowid, user["id"], "created", "Briefing angelegt")
        return serialize_project(conn.execute("SELECT * FROM projects WHERE id=?", (cursor.lastrowid,)).fetchone())


@app.get("/campaigns/{project_id}")
def get_campaign(project_id: int, user: dict = Depends(current_user)):
    require(user, "campaigns:read")
    with db(user) as conn:
        return serialize_project(project_row(conn, project_id, user))


@app.get("/campaigns/{project_id}/history")
def campaign_history(project_id: int, user: dict = Depends(current_user)):
    require(user, "campaigns:read")
    with db(user) as conn:
        project_row(conn, project_id, user)
        rows = conn.execute("SELECT h.id,h.action,h.message,h.snapshot,h.created_at,u.name AS actor FROM campaign_history h LEFT JOIN users u ON u.id=h.actor_id WHERE h.project_id=? ORDER BY h.id DESC", (project_id,)).fetchall()
    return [{**dict(row), "snapshot": json.loads(row["snapshot"]) if row["snapshot"] else None} for row in rows]


def creative_svg(project: dict, company: str):
    title = html.escape(project["role"][:95])
    location = html.escape(project["location"][:95])
    company = html.escape(company[:95])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080" role="img" aria-label="Recruiting-Motiv für {title}">
<rect width="1080" height="1080" fill="#101d2e"/>
<rect x="64" y="64" width="952" height="952" rx="40" fill="#223653"/>
<rect x="96" y="96" width="888" height="12" rx="6" fill="#8b7cff"/>
<text x="110" y="225" fill="#aab9cf" font-family="Arial,sans-serif" font-size="36">{company}</text>
<text x="110" y="390" fill="white" font-family="Arial,sans-serif" font-size="70" font-weight="bold">Wir suchen</text>
<foreignObject x="110" y="425" width="850" height="300"><div xmlns="http://www.w3.org/1999/xhtml" style="font-family:Arial,sans-serif;font-size:82px;line-height:1.12;font-weight:bold;color:white;overflow-wrap:anywhere">{title}</div></foreignObject>
<text x="110" y="790" fill="#b9d9d2" font-family="Arial,sans-serif" font-size="42">{location}</text>
<rect x="110" y="850" width="455" height="90" rx="20" fill="#8b7cff"/>
<text x="145" y="910" fill="white" font-family="Arial,sans-serif" font-size="42" font-weight="bold">Jetzt bewerben</text>
</svg>'''


@app.post("/campaigns/{project_id}/comments", status_code=201)
def add_campaign_comment(project_id: int, body: CommentBody, user: dict = Depends(current_user)):
    require(user, "campaigns:write")
    with db(user) as conn:
        project = project_row(conn, project_id, user)
        message = body.message.strip()
        if not message:
            raise HTTPException(422, "Comment cannot be empty")
        channel = body.channel.strip() or "Allgemein"
        log_history(conn, project["organization_id"], project_id, user["id"], "commented", f"{channel}: {message}")
        row = conn.execute("SELECT h.id,h.action,h.message,h.snapshot,h.created_at,u.name AS actor FROM campaign_history h LEFT JOIN users u ON u.id=h.actor_id WHERE h.id=last_insert_rowid()").fetchone()
        return dict(row)


def make_content(b: dict, customer: str):
    role, location = b["role"], b["location"]
    tasks, requirements, benefits = b.get("tasks", ""), b.get("requirements", ""), b.get("benefits", "")
    benefit_line = ", ".join([x.strip() for x in benefits.replace("\n", ",").split(",") if x.strip()][:4])
    return {
        "jobAd": f"# {role}\n\n**{customer} · {location} · {b.get('employment_type','Vollzeit')}**\n\n## Deine Aufgaben\n{tasks}\n\n## Notwendige Voraussetzungen\n{requirements}\n\n## Bei uns lernbar\n{b.get('learnable_requirements', '')}\n\n## Arbeitszeiten\n{b.get('working_hours', '')}\n\n## Vergütung\n{b.get('salary', '')}\n\n## Das bieten wir\n{benefits}\n\nInteresse? Dann bewirb dich unkompliziert bei {customer}.",
        "social": f"Variante A · Direkt\nWir suchen Verstärkung: {role} in {location}.\n\nWas dich erwartet:\n• {benefit_line or 'Vorteile noch zu klären'}\n\nJetzt kennenlernen und bewerben.\n\nVariante B · Persönlich\nDein nächster Job wartet in {location}: {role} bei {customer}. {benefit_line}. Bewirb dich jetzt.",
        "meta": f"Variante A\nPrimary Text: Neuer Job in {location}: {role} bei {customer}. {benefit_line}. Jetzt unkompliziert bewerben.\nHeadline: {role} gesucht\nDescription: Jetzt in wenigen Schritten bewerben.\n\nVariante B\nPrimary Text: Starte als {role} in {location} bei {customer}. {benefit_line}.\nHeadline: Dein neuer Job in {location}\nDescription: Jetzt kennenlernen und bewerben.",
    }


def local_test_generation_allowed(account):
    # Sandbox payments alone never authorize simulated production generation.
    return bool(account and account["mode"] == "test"
                and os.getenv("MH_ENV") != "production"
                and os.getenv("STRIPE_SECRET_KEY", "").startswith("sk_test_")
                and urlparse(billing.configuration()["site"]).hostname in {"localhost", "127.0.0.1", "::1"})


@app.post("/campaigns/{project_id}/generate")
def generate(project_id: int, user: dict = Depends(current_user), idempotency_key: str | None = Header(default=None), test_package: bool = False):
    require(user, "campaigns:write")
    with db(user) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = project_row(conn, project_id, user)
        recruiting.ensure_open(conn, project_id)
        if len(json.loads(row["briefing"]).get("location", "").strip()) < 2:
            raise HTTPException(422, "Vor der Texterstellung den tatsächlichen Arbeitsort ergänzen.")
        if row["status"] == "Live":
            raise HTTPException(409, "Live campaigns cannot be edited")
        managed = not user.get("view_role") and billing.account(conn, row["organization_id"])
        if test_package and not local_test_generation_allowed(managed):
            raise HTTPException(403, "Testpakete sind nur für lokale Stripe-Testkonten verfügbar.")
        if not user.get("view_role") and not billing.debit_generation(conn, row["organization_id"], idempotency_key, project_id):
            return serialize_project(row)
        org = conn.execute("SELECT name FROM organizations WHERE id=?", (row["organization_id"],)).fetchone()
        mode = "local_test" if test_package else "openai" if managed else "demo"
        if managed and not test_package:
            with SETTINGS_LOCK:
                settings = read_integration_settings().get("openai", {})
            content, usage = ai.generate(json.loads(row["briefing"]), org["name"], settings)
            conn.execute("INSERT INTO ai_usage(organization_id,project_id,request_key,model,response_id,input_tokens,output_tokens,cached_tokens,mh_tokens,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (row["organization_id"],project_id,idempotency_key,usage["model"],usage["response_id"],usage["input_tokens"],usage["output_tokens"],usage["cached_tokens"],50,int(time.time())))
        else:
            content = make_content(json.loads(row["briefing"]), org["name"])
        conn.execute("UPDATE projects SET generated=?,generated_briefing=?,generation_mode=?,updated_at=? WHERE id=?", (json.dumps(content), recruiting.fingerprint(row["briefing"]), mode, int(time.time()), project_id))
        log_activity(conn, row["organization_id"], project_id, user["id"], "Content generated")
        log_history(conn, row["organization_id"], project_id, user["id"], "generated", "Lokales Testpaket aus Vorlagen" if test_package else "Kanaltexte erzeugt", content)
        return serialize_project(conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())


@app.get("/campaigns/{project_id}/creative.svg")
def campaign_creative(project_id: int, user: dict = Depends(current_user)):
    require(user, "campaigns:read")
    with db(user) as conn:
        row = project_row(conn, project_id, user)
        org = conn.execute("SELECT name FROM organizations WHERE id=?", (row["organization_id"],)).fetchone()
        svg = creative_svg(dict(row), org["name"])
    return Response(svg, media_type="image/svg+xml", headers={"Content-Disposition": f'attachment; filename="campaign-{project_id}-creative.svg"'})


@app.get("/campaigns/{project_id}/export")
def campaign_export(project_id: int, user: dict = Depends(current_user)):
    require(user, "campaigns:read")
    with db(user) as conn:
        row = project_row(conn, project_id, user)
        org = conn.execute("SELECT name FROM organizations WHERE id=?", (row["organization_id"],)).fetchone()
        campaign = serialize_project(row)
        image_files = campaign_images.export(conn, project_id)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("README.txt", ("MH TESTPAKET · lokale Vorlagen, keine KI-Generierung.\n" if campaign.get("generation_mode") == "local_test" else "") + "MH Kampagnenpaket\nDie Dateien sind zum Prüfen und manuellen Veröffentlichen bestimmt. Der Status 'Live' veröffentlicht nicht automatisch.\n")
        package.writestr("briefing.json", json.dumps(campaign["briefing"], ensure_ascii=False, indent=2))
        for channel, content in campaign["generated"].items():
            if channel.isalnum():
                package.writestr(f"content/{channel}.txt", content)
        package.writestr("creative.svg", creative_svg(campaign, org["name"]))
        for name, data in image_files.items():
            package.writestr(name, data)
    return Response(archive.getvalue(), media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="campaign-{project_id}.zip"'})


@app.get("/campaigns/{project_id}/metrics")
def get_campaign_metrics(project_id: int, user: dict = Depends(current_user)):
    require(user, "campaigns:read")
    with db(user) as conn:
        project_row(conn, project_id, user)
        return [dict(row) for row in conn.execute("SELECT channel,impressions,clicks,applications,source,updated_at FROM campaign_metrics WHERE project_id=? ORDER BY channel", (project_id,))]


@app.put("/campaigns/{project_id}/metrics")
def put_campaign_metrics(project_id: int, body: MetricsBody, user: dict = Depends(current_user)):
    require(user, "campaigns:write")
    with db(user) as conn:
        project = project_row(conn, project_id, user)
        conn.execute("""INSERT INTO campaign_metrics(project_id,channel,impressions,clicks,applications,source,updated_at)
            VALUES(?,?,?,?,?,?,?) ON CONFLICT(project_id,channel) DO UPDATE SET impressions=excluded.impressions,clicks=excluded.clicks,applications=excluded.applications,source=excluded.source,updated_at=excluded.updated_at""",
            (project_id, body.channel.strip(), body.impressions, body.clicks, body.applications, body.source.strip() or "manual", int(time.time())))
        log_history(conn, project["organization_id"], project_id, user["id"], "metrics_updated", f"Kennzahlen für {body.channel.strip()} aktualisiert")
        return dict(conn.execute("SELECT channel,impressions,clicks,applications,source,updated_at FROM campaign_metrics WHERE project_id=? AND channel=?", (project_id, body.channel.strip())).fetchone())


@app.patch("/campaigns/{project_id}")
def update_campaign(project_id: int, body: ProjectPatch, background_tasks: BackgroundTasks, user: dict = Depends(current_user)):
    require(user, "campaigns:write")
    with db(user) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = project_row(conn, project_id, user)
        recruiting.ensure_open(conn, project_id)
        values = {}
        if body.image_edit is not None:
            if row['status'] == 'Live':
                raise HTTPException(409, 'Live campaigns cannot be edited')
            if body.status is not None:
                raise HTTPException(422, 'Bildausschnitte zuerst speichern, danach zur Prüfung geben.')
            campaign_images.edit(conn, row, body.image_edit)
            image_changed(conn, row, user, 'image_saved', 'Bildausschnitte gespeichert', notify=False)
        if body.status in {'Review', 'Live'} and row['image_revision'] and body.image_revision != row['image_revision']:
            raise HTTPException(409, 'Die Kampagnenbilder wurden inzwischen geändert. Bitte die aktuelle Fassung erneut prüfen.')
        if body.reviewed_briefing is not None:
            if row["status"] == "Live" or body.reviewed_briefing != recruiting.fingerprint(row["briefing"]) or body.briefing is not None or not json.loads(row["generated"]):
                raise HTTPException(409, "Aktuelles Briefing und gespeicherte Texte zuerst erneut prüfen.")
            values["generated_briefing"] = body.reviewed_briefing
        if body.briefing is not None:
            if row["status"] == "Live":
                raise HTTPException(409, "Live campaigns cannot be edited")
            values.update(briefing=body.briefing.model_dump_json(), role=body.briefing.role, location=body.briefing.location, channels=json.dumps(body.briefing.channels))
        if body.generated is not None:
            if row["status"] == "Live":
                raise HTTPException(409, "Live campaigns cannot be edited")
            values["generated"] = json.dumps(body.generated)
        if body.status is not None:
            if row["status"] == "Live" and body.status != "Live":
                raise HTTPException(409, "Live campaigns cannot be reopened")
            if body.status == "Live":
                require(user, "campaigns:approve")
                if row["status"] != "Review":
                    raise HTTPException(409, "Submit for review first")
                if not json.loads(row["generated"]):
                    raise HTTPException(409, "Generate content first")
                # Legacy material may be approved after human review; new tracked material must match.
                expected = values.get("briefing", row["briefing"])
                reviewed = values.get("generated_briefing", row["generated_briefing"])
                if reviewed and reviewed != recruiting.fingerprint(expected):
                    raise HTTPException(409, "Briefing wurde geändert. Gespeicherte Texte zuerst damit abgleichen und die Prüfung bestätigen.")
            elif body.status == "Review" and not json.loads(row["generated"]):
                raise HTTPException(409, "Generate content first")
            values["status"] = body.status
        if body.change_request is not None:
            if body.change_request.strip():
                require(user, "campaigns:approve")
            if body.change_request.strip() and row["status"] != "Review":
                raise HTTPException(409, "Changes can only be requested during review")
            values["change_request"] = body.change_request.strip()
            if body.change_request.strip():
                values["status"] = "Draft"
        if values:
            values["updated_at"] = int(time.time())
            assignments = ",".join(f"{key}=?" for key in values)
            conn.execute(f"UPDATE projects SET {assignments} WHERE id=?", (*values.values(), project_id))
            log_activity(conn, row["organization_id"], project_id, user["id"], "Campaign updated")
            if body.change_request and body.change_request.strip():
                action, message = "changes_requested", body.change_request.strip()
            elif body.status == "Live":
                action, message = "approved", "Kampagne freigegeben"
            elif body.status == "Review":
                action, message = "submitted", "Zur Prüfung eingereicht"
            elif body.reviewed_briefing is not None:
                action, message = "materials_reviewed", "Gespeicherte Texte mit aktuellem Briefing abgeglichen"
            elif body.generated is not None:
                action, message = "content_saved", "Kanaltext bearbeitet"
            else:
                action, message = "briefing_updated", "Briefing bearbeitet"
            log_history(conn, row["organization_id"], project_id, user["id"], action, message, body.generated)
        updated = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if updated['status'] != row['status'] and not user.get('view_role'):
            status_mail.queue(conn, updated, row['status'], updated['status'], user['id'], secrets.token_hex(16))
        result = serialize_project(updated)
    if not user.get('view_role'):
        background_tasks.add_task(status_mail.drain, db)
    return result


@app.get("/activity")
def activity(user: dict = Depends(current_user)):
    require(user, "campaigns:read")
    with db(user) as conn:
        if user["role"] == "platform_admin":
            rows = conn.execute("SELECT a.*,u.name AS actor FROM activity a LEFT JOIN users u ON u.id=a.actor_id ORDER BY a.id DESC LIMIT 20").fetchall()
        elif user["role"] == "kunde":
            rows = conn.execute("SELECT a.*,u.name AS actor FROM activity a JOIN projects p ON p.id=a.project_id LEFT JOIN users u ON u.id=a.actor_id WHERE a.organization_id=? AND p.status IN ('Review','Live') ORDER BY a.id DESC LIMIT 20", (user["organization_id"],)).fetchall()
        else:
            rows = conn.execute("SELECT a.*,u.name AS actor FROM activity a LEFT JOIN users u ON u.id=a.actor_id WHERE a.organization_id=? ORDER BY a.id DESC LIMIT 20", (user["organization_id"],)).fetchall()
    return [dict(row) for row in rows]


@app.get("/analytics")
def analytics(user: dict = Depends(current_user)):
    require(user, "campaigns:read")
    with db(user) as conn:
        if user["role"] == "platform_admin":
            rows = conn.execute("SELECT status,COUNT(*) AS count FROM projects GROUP BY status").fetchall()
        elif user["role"] == "kunde":
            rows = conn.execute("SELECT status,COUNT(*) AS count FROM projects WHERE organization_id=? AND status IN ('Review','Live') GROUP BY status", (user["organization_id"],)).fetchall()
        else:
            rows = conn.execute("SELECT status,COUNT(*) AS count FROM projects WHERE organization_id=? GROUP BY status", (user["organization_id"],)).fetchall()
        if user["role"] == "platform_admin":
            metrics = conn.execute("SELECT m.project_id,m.channel,m.impressions,m.clicks,m.applications,m.source FROM campaign_metrics m JOIN projects p ON p.id=m.project_id ORDER BY p.updated_at DESC").fetchall()
        elif user["role"] == "kunde":
            metrics = conn.execute("SELECT m.project_id,m.channel,m.impressions,m.clicks,m.applications,m.source FROM campaign_metrics m JOIN projects p ON p.id=m.project_id WHERE p.organization_id=? AND p.status IN ('Review','Live') ORDER BY p.updated_at DESC", (user["organization_id"],)).fetchall()
        else:
            metrics = conn.execute("SELECT m.project_id,m.channel,m.impressions,m.clicks,m.applications,m.source FROM campaign_metrics m JOIN projects p ON p.id=m.project_id WHERE p.organization_id=? ORDER BY p.updated_at DESC", (user["organization_id"],)).fetchall()
    counts = {row["status"]: row["count"] for row in rows}
    metrics = [dict(row) for row in metrics]
    return {"campaigns": sum(counts.values()), "draft": counts.get("Draft", 0), "review": counts.get("Review", 0), "live": counts.get("Live", 0), "impressions": sum(row["impressions"] for row in metrics), "clicks": sum(row["clicks"] for row in metrics), "applications": sum(row["applications"] for row in metrics), "metrics": metrics}


init_db()
billing.install(app, db, current_user, password_hash)
auth.install(app, db, current_user, password_hash, verify_password, LoginBody, OrganizationProfile)
account_recovery.install(app, db, current_user, password_hash)


@app.get("/tokens/wallet")
def token_wallet(user: dict = Depends(current_user)):
    org = user.get("organization_id")
    if not org or user.get("view_role"):
        return {"managed":False,"included":0,"purchased":0,"available":0,"active":False,"ledger":[]}
    with db(user) as conn:
        conn.execute("BEGIN IMMEDIATE")
        a = billing.reconcile_included(conn, billing.account(conn, org))
        if not a: return {"managed":False,"included":0,"purchased":0,"available":0,"active":False,"ledger":[]}
        included = a["included"] if a["period_end"] > int(time.time()) else 0
        entries = [dict(row) for row in conn.execute("SELECT included_delta,purchased_delta,description,created_at FROM token_ledger WHERE organization_id=? ORDER BY id DESC LIMIT 10", (org,))]
        _, credit_end = billing.credit_window(a)
        with SETTINGS_LOCK:
            settings = read_integration_settings().get("openai", {})
        configured = bool(os.getenv("OPENAI_API_KEY") or settings.get("api_key"))
        mode = "openai" if configured else "local_test" if local_test_generation_allowed(a) else "unavailable"
        return {"managed":True,"generation_mode":mode,"included":included,"purchased":a["purchased"],"available":included+a["purchased"] if billing.usable(a) else 0,"active":bool(billing.usable(a)),"period_end":a["period_end"],"credit_period_end":credit_end,"ledger":entries}

# Installed last so oversized bodies are rejected before auth and JSON parsing.
app.add_middleware(RequestSizeLimit)

status_mail.install(app, db)

tracking.install(app, db, current_user, require, project_row)
social.install(app, db, current_user, require, project_row, log_history)

recruiting.install(app, db, current_user, require, project_row, log_history, serialize_project)

campaign_images.install(app, db, current_user, require, project_row, image_changed)

job_portal.install(app, db, current_user, require, project_row, log_history)
