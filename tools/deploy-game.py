#!/usr/bin/env python3
"""Publish a trusted game artifact to the local Compose/Bench environment."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import secrets
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def bench(method, kwargs, site):
    # A Python literal (bench execute format) is passed as one argv value; never interpolated into a shell.
    command = ['docker', 'compose', '-f', str(ROOT/'docker/docker-compose.yml'), 'exec', '-T', '-u', 'frappe', '-w', '/home/frappe/bench-data/frappe-bench', 'frappe', 'bench', '--site', site, 'execute', method, '--kwargs', repr(kwargs)]
    try:
        result = run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as error:
        details = re.sub(r'[a-f0-9]{64}', '<redacted>', error.stderr or error.stdout or '')
        raise RuntimeError(f'Bench {method} failed: {details[-5000:]}') from None
    lines = result.stdout.strip().splitlines()
    return json.loads(lines[-1]) if lines else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--client', required=True, type=Path)
    parser.add_argument('--image', required=True, help='Immutable local image ID or registry image@sha256 digest')
    parser.add_argument('--port', type=int, default=2567)
    parser.add_argument('--site', default='school.localhost')
    parser.add_argument('--game')
    parser.add_argument('--title')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if hashlib.sha256(args.client.read_bytes()).hexdigest() != manifest['client']['sha256']:
        raise SystemExit('Client checksum mismatch')
    if args.image.split('@')[-1] != manifest['server']['image'].split('@')[-1]:
        raise SystemExit('Runtime image does not match manifest digest')
    if not (args.image.startswith('sha256:') or '@sha256:' in args.image):
        raise SystemExit('Use an immutable image ID or digest')
    endpoint = f'http://localhost:{args.port}'
    service_key = secrets.token_hex(32)
    # Copy only artifacts into a private staging directory shared read-only with Bench.
    directory = ROOT/'docker/.game-runtime'/secrets.token_hex(8)
    directory.mkdir(parents=True, mode=0o755)
    (directory/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    (directory/'client.zip').write_bytes(args.client.read_bytes())
    staged = '/workspace/lms/' + str(directory.relative_to(ROOT))
    # Approve only this local loopback origin, preserving previously registered origins.
    bench('lms.lms.game_publish.approve_local_origin', {'endpoint': endpoint}, args.site)
    secret_file = directory/'service-key'
    secret_file.write_text(service_key)
    secret_file.chmod(0o600)
    container_secret = '/tmp/game-publish-' + secrets.token_hex(16)
    base = ['docker', 'compose', '-f', str(ROOT/'docker/docker-compose.yml')]
    run(base + ['cp', str(secret_file), 'frappe:'+container_secret], stdout=subprocess.DEVNULL)
    run(base + ['exec', '-T', 'frappe', 'chown', 'frappe:frappe', container_secret])
    try:
        registered = bench('lms.lms.game_publish.publish_release', {'manifest_path': staged+'/manifest.json', 'client_path': staged+'/client.zip', 'endpoint': endpoint, 'service_key_path': container_secret, 'game': args.game, 'title': args.title}, args.site)
    finally:
        run(base + ['exec', '-T', 'frappe', 'rm', '-f', container_secret])
        secret_file.unlink(missing_ok=True)
    env = {'GAME_IMAGE': args.image, 'GAME_DEPLOYMENT': registered['deployment'], 'GAME_RELEASE': registered['release'], 'GAME_ID': registered['game'], 'GAME_SERVICE_KEY': service_key, 'GAME_DEPLOY_DIR': str(directory), 'GAME_PORT': str(args.port), 'FRAPPE_SITE': args.site, 'GAME_MEMORY_MIB': str(manifest['limits']['memoryMiB'])}
    env_path = directory/'runtime.env'
    env_path.write_text('\n'.join(f'{key}={value}' for key, value in env.items())+'\n')
    env_path.chmod(0o600)
    project = 'jwl-game-' + registered['deployment']
    compose = ['docker', 'compose', '--env-file', str(env_path), '-p', project, '-f', str(ROOT/'docker/game-runtime.compose.yml')]
    try:
        run(compose + ['up', '-d'])
        for _ in range(40):
            try:
                with urllib.request.urlopen(endpoint+'/readyz', timeout=3) as response:
                    state = json.load(response)
                if state.get('deployment') == registered['deployment'] and state.get('release') == registered['release']:
                    break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError('Candidate runtime did not become ready')
        bench('lms.lms.game_publish.activate_release', {'deployment': registered['deployment']}, args.site)
        with urllib.request.urlopen(endpoint+'/readyz', timeout=5) as response:
            state = json.load(response)
        if state.get('status') != 'Ready':
            raise RuntimeError('Activated runtime did not accept new connections')
    except Exception:
        bench('lms.lms.game_publish.stop_deployment', {'deployment': registered['deployment']}, args.site)
        run(compose + ['down'])
        raise
    result = {**registered, 'endpoint': endpoint, 'project': project, 'env_file': str(env_path), 'game_url': f'http://localhost:8000/lms/game/{registered["game"]}'}
    (directory/'deployment.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
