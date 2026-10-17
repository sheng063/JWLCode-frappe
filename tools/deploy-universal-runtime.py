#!/usr/bin/env python3
"""One-time platform deployment; subsequent game uploads never call this tool."""
import argparse
import json
from pathlib import Path
import secrets
import subprocess
import time
import urllib.request
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publish_game', ROOT/'tools/deploy-game.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--port', type=int, default=2572)
parser.add_argument('--site', default='school.localhost')
args = parser.parse_args()
# Platform maintenance must not interrupt active rooms.
try:
    with urllib.request.urlopen(f'http://localhost:{args.port}/readyz', timeout=3) as response:
        current = json.load(response)
    if current.get('rooms', 0):
        raise SystemExit('Universal relay still has active rooms. Wait for them to finish before maintenance.')
except (OSError, ValueError):
    pass
subprocess.run(['docker', 'build', '-f', 'services/game-runtime/Dockerfile', '-t', 'jwlcode/game-universal:1', '.'], cwd=ROOT, check=True)
image = subprocess.check_output(['docker', 'image', 'inspect', 'jwlcode/game-universal:1', '--format', '{{.Id}}'], text=True).strip()
directory = ROOT/'docker/.game-runtime'/'universal'
directory.mkdir(parents=True, exist_ok=True)
env_path = directory/'runtime.env'
previous = dict(line.split('=', 1) for line in env_path.read_text().splitlines()) if env_path.exists() else {}
secret = previous.get('GAME_SERVICE_KEY') or secrets.token_hex(32)
secret_path = directory/'service-key'
secret_path.write_text(secret)
secret_path.chmod(0o600)
base = ['docker', 'compose', '-f', str(ROOT/'docker/docker-compose.yml')]
container_secret = '/tmp/universal-key-' + secrets.token_hex(12)
subprocess.run(base + ['cp', str(secret_path), 'frappe:'+container_secret], check=True)
subprocess.run(base + ['exec', '-T', 'frappe', 'chown', 'frappe:frappe', container_secret], check=True)
endpoint = f'http://localhost:{args.port}'
try:
    helper.bench('lms.lms.game_runtime.configure_runtime', {'endpoint': endpoint, 'service_key_path': container_secret}, args.site)
finally:
    subprocess.run(base + ['exec', '-T', 'frappe', 'rm', '-f', container_secret], check=True)
    secret_path.unlink(missing_ok=True)
values = {'GAME_IMAGE': image, 'GAME_SERVICE_KEY': secret, 'GAME_PORT': str(args.port), 'FRAPPE_SITE': args.site}
env_path.write_text('\n'.join(f'{key}={value}' for key,value in values.items())+'\n')
env_path.chmod(0o600)
subprocess.run(['docker', 'compose', '--env-file', str(env_path), '-f', str(ROOT/'docker/game-runtime.compose.yml'), 'up', '-d'], check=True)
for _ in range(45):
    try:
        with urllib.request.urlopen(endpoint+'/readyz', timeout=3) as response:
            status = json.load(response)
        if status.get('roomTypes') == ['universal'] and status.get('ready'):
            print(json.dumps({'endpoint': endpoint, 'image': image, 'roomTypes': ['universal']}, indent=2))
            break
    except Exception:
        pass
    time.sleep(1)
else:
    raise SystemExit('Universal runtime did not become ready')
