"""Save Meta app configuration privately. Does not contact Meta or publish anything."""
import argparse
import getpass
import os
from . import social
from .stripe_test import ENV_FILE, read_env, save_env


def setup():
    values = read_env(ENV_FILE)
    print('Zuerst eine öffentliche HTTPS-Adresse und eine Meta-App einrichten.')
    origin = input('Öffentliche MH-Adresse (https://…): ').strip().rstrip('/')
    app_id = input('Meta-App-ID: ').strip()
    version = input('Graph-API-Version aus dem Meta-App-Dashboard (vXX.0): ').strip()
    callback = input('Exakte OAuth-Rücksprungadresse (https://…/api/social/meta/callback): ').strip()
    secret = getpass.getpass('Meta-App-Secret (unsichtbar; niemals im Chat eingeben): ').strip()
    updated = {**values, 'MH_PUBLIC_URL':origin, 'MH_META_APP_ID':app_id, 'MH_META_APP_SECRET':secret, 'MH_META_GRAPH_VERSION':version, 'MH_META_CALLBACK_URL':callback}
    previous = dict(os.environ)
    try:
        os.environ.update(updated)
        config = social.configuration()
    finally:
        os.environ.clear()
        os.environ.update(previous)
    if not config['ready']:
        raise ValueError('Einrichtung unvollständig: ' + ', '.join(config['missing']))
    save_env(ENV_FILE, updated)
    print('Meta-Konfiguration privat gespeichert. Backend neu starten. Noch keine Meta-Verbindung oder Veröffentlichung geprüft.')


def status():
    os.environ.update(read_env(ENV_FILE))
    config = social.configuration()
    print('Lokale Meta-Konfiguration vollständig; externer Test steht aus.' if config['ready'] else 'Noch einzurichten: ' + ', '.join(config['missing']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('setup','status'))
    args = parser.parse_args()
    try:
        {'setup':setup,'status':status}[args.action]()
    except (ValueError, KeyboardInterrupt, EOFError) as exc:
        print(str(exc) if isinstance(exc, ValueError) else 'Einrichtung abgebrochen.')
        raise SystemExit(1)
