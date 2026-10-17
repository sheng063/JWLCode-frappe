#!/usr/bin/env python3
"""Build the versioned browser artifact and immutable demo runtime image."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--release', default='1.0.0')
args = parser.parse_args()
service = ROOT/'services/game-runtime'
subprocess.run(['npm', 'ci'], cwd=service, check=True)
subprocess.run(['npm', 'run', 'build:demo'], cwd=service, check=True)
subprocess.run(['docker', 'build', '-f', 'services/game-runtime/Dockerfile', '-t', 'jwlcode/game-runtime:colyseus-v1', '.'], cwd=ROOT, check=True)
image = subprocess.check_output(['docker', 'image', 'inspect', 'jwlcode/game-runtime:colyseus-v1', '--format', '{{.Id}}'], text=True).strip()
out = service/'dist'
with zipfile.ZipFile(out/'client.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    entry = zipfile.ZipInfo('index.html', date_time=(2026, 1, 1, 0, 0, 0))
    entry.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(entry, (out/'index.html').read_bytes())
manifest = {'manifestVersion': 1, 'gameKey': 'colyseus-demo', 'release': args.release, 'platformApi': '1', 'runtimeProfile': 'colyseus-web-v1', 'client': {'artifact': 'client.zip', 'entry': 'index.html', 'sha256': hashlib.sha256((out/'client.zip').read_bytes()).hexdigest()}, 'server': {'image': 'jwlcode/game-runtime@'+image, 'protocolVersion': '1'}, 'rooms': [{'key': 'arena', 'maxClients': 4, 'visibility': 'public'}], 'limits': {'maxRooms': 20, 'maxConnections': 80, 'memoryMiB': 512}}
(out/'game.manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(json.dumps({'manifest': str(out/'game.manifest.json'), 'client': str(out/'client.zip'), 'image': image}, indent=2))
