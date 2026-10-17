#!/usr/bin/env python3
"""Publish front-end game data through Bench. Never builds or restarts the relay."""
import argparse
import json
import re
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def bench(method, kwargs, site):
    command = ['docker', 'compose', '-f', str(ROOT/'docker/docker-compose.yml'), 'exec', '-T', '-u', 'frappe', '-w', '/home/frappe/bench-data/frappe-bench', 'frappe', 'bench', '--site', site, 'execute', method, '--kwargs', repr(kwargs)]
    try:
        result = run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as error:
        details = re.sub(r'[a-f0-9]{64}', '<redacted>', error.stderr or error.stdout or '')
        raise RuntimeError(f'Bench {method} failed: {details[-4000:]}') from None
    lines = result.stdout.strip().splitlines()
    return json.loads(lines[-1]) if lines else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--client', required=True, type=Path)
    parser.add_argument('--site', default='school.localhost')
    parser.add_argument('--game')
    parser.add_argument('--title')
    args = parser.parse_args()
    # Stage under the read-only source mount: these are public browser assets, never secrets.
    import secrets
    directory = ROOT/'docker/.game-runtime'/'uploads'/secrets.token_hex(8)
    directory.mkdir(parents=True)
    (directory/'game.manifest.json').write_bytes(args.manifest.read_bytes())
    (directory/args.client.name).write_bytes(args.client.read_bytes())
    base = '/workspace/lms/' + str(directory.relative_to(ROOT))
    result = bench('lms.lms.game_publish.publish_from_files', {'manifest_path': base+'/game.manifest.json', 'client_path': base+'/'+args.client.name, 'game': args.game, 'title': args.title}, args.site)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
