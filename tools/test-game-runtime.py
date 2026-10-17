#!/usr/bin/env python3
"""Run the local browser acceptance check with temporary student accounts."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('deploy_game', ROOT/'tools/deploy-game.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--game', required=True)
parser.add_argument('--site', default='school.localhost')
parser.add_argument('--output', type=Path, default=ROOT/'docs/qa/game-colyseus-20261017')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
fixture = deploy.bench('lms.tests.test_game_runtime.prepare_browser_smoke', {'game_name': args.game}, args.site)
process = None
try:
    with tempfile.TemporaryDirectory(prefix='game-runtime-smoke-') as temp:
        directory = Path(temp)
        fixture_path = directory/'fixture.json'
        fixture_path.write_text(json.dumps(fixture))
        fixture_path.chmod(0o600)
        with (args.output/'browser.log').open('w') as log:
            process = subprocess.Popen(['node', str(ROOT/'tools/game-runtime-browser-smoke.cjs'), str(fixture_path), str(args.output.resolve())], stdout=log, stderr=subprocess.STDOUT)
            for _ in range(80):
                if (directory/'live.json').exists():
                    deploy.bench('lms.lms.game.set_game_availability', {'name': args.game, 'enabled': 0}, args.site)
                    (directory/'revoked').write_text('revoked')
                    break
                if process.poll() is not None:
                    break
                time.sleep(1)
            code = process.wait(timeout=50)
        print((args.output/'browser.log').read_text())
        if code:
            raise SystemExit(code)
finally:
    if process and process.poll() is None:
        process.terminate()
        process.wait(timeout=10)
    deploy.bench('lms.tests.test_game_runtime.cleanup_browser_smoke', {'fixture': fixture}, args.site)
