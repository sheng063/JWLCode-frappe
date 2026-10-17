#!/usr/bin/env python3
"""Build front-end-only relay examples. Does not build any server image."""
import argparse
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--release', default='1.0.0')
args = parser.parse_args()
service = ROOT/'services/game-runtime'
subprocess.run(['npm', 'run', 'build:demo'], cwd=service, check=True)
out = service/'dist'
for kind, maximum in [('gomoku',2),('race',4)]:
    for client_type in ('html','zip'):
        entry = f'{kind}.html' if client_type == 'html' else 'index.html'
        manifest = {'manifestVersion':1,'gameKey':'relay-'+kind,'release':args.release,'platformApi':'1','client':{'entry':entry,'type':client_type},'multiplayer':{'enabled':True,'mode':'relay','minPlayers':2,'maxPlayers':maximum,'allowPrivateRoom':True,'allowQuickMatch':True}}
        (out/f'{kind}-{client_type}.manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        if client_type == 'zip':
            with zipfile.ZipFile(out/f'{kind}.zip','w',zipfile.ZIP_DEFLATED) as archive:
                for file in sorted((out/kind).iterdir()):
                    info=zipfile.ZipInfo(file.name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;archive.writestr(info,file.read_bytes())
                archive.writestr('game.manifest.json',json.dumps(manifest))
print('Built gomoku/race HTML and ZIP artifacts under services/game-runtime/dist (no Docker operations).')
