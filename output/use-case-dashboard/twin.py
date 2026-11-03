"""Source-only inventory and deletion prompts. Never imports the product or reads its DB."""
import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'docs/requirements/use_case_status.json'
SUITES = ['security', 'billing', 'stripe_setup', 'auth', 'ai', 'gmail', 'tracking', 'social', 'recruiting', 'campaign_images', 'job_portal', 'campaign_workflow']
CHECKS = [(['python3', '-m', 'unittest', *['backend/test_' + n + '.py' for n in SUITES]], ''),
          (['npm', 'run', 'build'], 'frontend'), (['npm', 'run', 'test:seo'], 'frontend'),
          (['npm', 'run', 'test:language'], 'frontend'), (['npm', 'run', 'test:job-seo'], 'frontend'), (['npm', 'run', 'test:onboarding'], 'frontend')]


def source_files(root=ROOT):
    """Explicit code/document locations, no private configuration, databases or outboxes."""
    allowed = {'.py', '.tsx', '.ts', '.css', '.html', '.mjs', '.md'}
    files = list(root.glob('*.md'))
    for directory in ('backend', 'frontend/src', 'frontend/scripts', 'docs/requirements', 'output/use-case-dashboard'):
        for path in (root / directory).rglob('*'):
            parts = path.relative_to(root / directory).parts
            if any(p in ('runs', '__pycache__', 'mail_outbox', 'node_modules', 'dist') or p.startswith('.') for p in parts):
                continue
            if path.suffix in allowed and path.is_file() and not path.is_symlink():
                files.append(path)
    files.extend(p for p in (root / 'frontend').glob('*') if p.suffix in ('.ts', '.html') or
                 p.name.startswith('tsconfig') and p.suffix == '.json')
    files.extend(root / name for name in ('start.sh', 'frontend/package.json', 'frontend/package-lock.json',
                 'frontend/src/translations.json', 'backend/requirements.txt', 'docs/requirements/use_case_status.json'))
    return {str(p.relative_to(root)): p for p in sorted(set(files))
            if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(root.resolve())}


def hashes(root=ROOT):
    return {name: hashlib.sha256(p.read_bytes()).hexdigest() for name, p in source_files(root).items()}


def fingerprint(root=ROOT):
    return hashlib.sha256(json.dumps(hashes(root), sort_keys=True).encode()).hexdigest()


def inventory(data, root=ROOT):
    routes, tables = [], []
    files = source_files(root)
    linked = {f for c in data['cases'] for f in c['evidence']}
    for name, path in files.items():
        if not name.startswith('backend/') or not name.endswith('.py') or path.name.startswith('test_'):
            continue
        try:
            tree = ast.parse(path.read_text())
        except (SyntaxError, UnicodeError):
            continue
        cases = [c['id'] for c in data['cases'] if name in c['evidence']]
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                            and dec.func.attr in ('get', 'post', 'patch', 'put', 'delete') and dec.args
                            and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str)):
                        routes.append(dict(method=dec.func.attr.upper(), path=dec.args[0].value,
                                           function=node.name, file=name, line=node.lineno, cases=cases))
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for table in re.findall(r'CREATE TABLE(?: IF NOT EXISTS)?\s+([\w]+)', node.value, re.I):
                    tables.append(dict(name=table, file=name))
    nfa_path = root / 'docs/requirements/NICHTFUNKTIONALE_ANFORDERUNGEN.md'
    quality = re.findall(r'^### (NFA-\d+) (.+)$', nfa_path.read_text(), re.M) if nfa_path.is_file() else []
    return dict(file_count=len(files), route_count=len(routes), routes=routes,
                tables=list({(t['name'], t['file']): t for t in tables}.values()),
                unlinked_files=[f for f in files if f not in linked],
                quality=[dict(id=i, title=t) for i, t in quality])


def status(root=ROOT):
    data = json.loads((root / 'docs/requirements/use_case_status.json').read_text())
    current = hashes(root)
    reviewed = data.get('reviewed_sources', {})
    changed = [f for f, digest in reviewed.items() if current.get(f) != digest]
    unreviewed = [f for f in current if f not in reviewed and f not in
                  ('docs/requirements/use_case_status.json', 'output/use-case-dashboard/index.html',
                   'output/use-case-dashboard/before.html')]
    data.update(changed_sources=changed, unreviewed_sources=unreviewed,
                verification_stale=bool(changed or unreviewed), fingerprint=fingerprint(root),
                inventory=inventory(data, root), project_path=str(root))
    data['prompts'] = {c['id']: deletion_prompt(c, data) for c in data['cases']}
    data['batch_header'] = batch_prompt([], data)
    return data


def deletion_prompt(c, data):
    shared = [x['id'] for x in data['cases'] if x['id'] != c['id'] and set(x['evidence']) & set(c['evidence'])]
    return (f"Ich möchte den Use Case {c['id']} – {c['title']} aus dieser Anwendung entfernen.\n"
            f"Beschreibung: {c['present']}\nOffene Teile: {c['gap'] or 'Keine dokumentiert.'}\n"
            f"Stand: {c['status']} · Herkunft: {c['source_kind']}\n"
            f"Einstiegspunkte zur Untersuchung (keine pauschale Dateilöschung): {', '.join(c['evidence'])}.\n"
            f"Mögliche Überlappungen nach gemeinsamen Nachweisdateien: {', '.join(shared) or 'Keine erfasst'}. "
            "Das ist eine Untersuchungshilfe, kein belegter Aufrufgraph.\n"
            "Entferne nur Verhalten, Oberfläche, API und ausschließlich hierfür benötigten Code. "
            "Erhalte gemeinsam genutzte Bausteine für nicht ausgewählte Use Cases. "
            "Bei noch nicht implementierten Teilen ändere Planung/Katalog und vermeide unnötige Codeänderungen.")


def batch_prompt(ids, data, note=''):
    chosen = [c for c in data['cases'] if c['id'] in ids]
    head = ("LÖSCHAUFTRAG FÜR MH · ausgewählte Produktfunktionen\n"
            f"Projekt: {ROOT}\nAusgewählte Use Cases: {', '.join(c['id'] for c in chosen)}\n"
            "Die Person hat diesen gesamten Batch im lokalen Dashboard geprüft und seine Umsetzung gestartet.\n"
            "Lies zuerst AGENTS.md und PROJECT_CONTEXT.md sowie README.md, AUTH_SETUP.md, BILLING_SETUP.md. "
            "Behandle die folgenden Use Cases als einen gemeinsamen Auftrag, löse Überschneidungen zusammen auf.\n"
            "Entferne die ausgewählten Funktionen vollständig aus dem Produkt und aktualisiere Tests, "
            "Navigation, Texte, Dokumentation und docs/requirements/use_case_status.json. "
            "Lass entfernte Einträge mit status=removed und Begründung sichtbar. "
            "Erhalte alle nicht ausgewählten Use Cases und deren Sicherheits-, Mandanten- und Zahlungsregeln. "
            "Wenn eine ausgewählte Funktion zwingend für verbleibende Funktionen benötigt wird, "
            "berichte den Konflikt statt deren Verhalten stillschweigend zu entfernen.\n"
            "Dieser Auftrag betrifft Quellcode/Planung, keine Kunden-, Bewerber- oder Abrechnungsdaten. "
            "Kein DROP/DELETE in bestehenden Datenbanken, keine Migration mit Datenverlust, "
            "keine Stripe-/Meta-/Mail-Aktion und keine Veröffentlichung. "
            "Lies keine privaten .env-Dateien, Auth-Schlüssel, Credentials, Mail-Outboxes oder Datenbanken. "
            "Gib keine Geheimnisse aus. Bereits laufende Produktserver nicht stoppen. "
            "Bearbeite keine Dashboard-Ausführung, Backups oder Laufprotokolle.\n"
            "Prüfe jede verbleibende Funktion mit geeigneter Regression; erfülle die Vollprüfung in AGENTS.md "
            "sowie Tracking/Social/Recruiting und Sprachprüfung. Aktualisiere den Quellabgleich erst nach Tests. "
            "Erstelle zuletzt die HTML-Snapshot-Datei mit python3 output/use-case-dashboard/build.py. "
            "Berichte entfernte und blockierte Use Cases, Änderungen und tatsächliche Tests.\n")
    if note:
        head += '\nZusätzlicher Änderungswunsch der Person:\n' + note.strip() + '\n'
    return head + '\n\n' + '\n\n'.join(deletion_prompt(c, data) for c in chosen)
