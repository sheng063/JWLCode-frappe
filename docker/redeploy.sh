#!/usr/bin/env bash

# Redeploy the local LMS source into the running Frappe Bench container.
# Usage: ./docker/redeploy.sh
# Optional: SITE_NAME=another.localhost ./docker/redeploy.sh

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
SITE_NAME="${SITE_NAME:-school.localhost}"
BENCH_DIR="/home/frappe/bench-data/frappe-bench"
APP_DIR="${BENCH_DIR}/apps/lms"

require_command() {
	command -v "$1" >/dev/null 2>&1 || {
		echo "Required command is unavailable: $1" >&2
		exit 1
	}
}

require_command docker
require_command tar

compose() {
	docker compose -f "${COMPOSE_FILE}" "$@"
}

cd "${REPO_ROOT}"

echo "==> Starting required containers"
compose up -d

echo "==> Syncing workspace source into the Bench application"
# Generated frontend assets are deliberately retained until the following
# production build replaces them. Host-only metadata and dependencies are omitted.
COPYFILE_DISABLE=1 tar \
	--exclude='.git' \
	--exclude='.idea' \
	--exclude='*/__pycache__' \
	--exclude='*/node_modules' \
	--exclude='./lms/public/frontend' \
	-cf - . \
| compose exec -T frappe tar -xf - -C "${APP_DIR}"

echo "==> Installing LMS dependencies, building, migrating site, and clearing cache"
compose exec -T -e SITE_NAME="${SITE_NAME}" frappe bash -lc '
	chown -R frappe:frappe /home/frappe/bench-data/frappe-bench/apps/lms
	runuser -u frappe -- bash -lc "
		cd /home/frappe/bench-data/frappe-bench &&
		env/bin/pip install -e apps/lms &&
		cd apps/lms/frontend &&
		yarn install --frozen-lockfile --non-interactive &&
		NODE_OPTIONS=--max-old-space-size=4096 yarn build &&
		cd /home/frappe/bench-data/frappe-bench &&
		bench compile-po-to-mo --app lms &&
		bench --site \"\$SITE_NAME\" migrate &&
		bench --site \"\$SITE_NAME\" clear-cache
	"
'

echo "==> Restarting Frappe"
compose restart frappe

container_id="$(compose ps -q frappe)"
if [[ -z "${container_id}" ]]; then
	echo "Frappe container was not found after restart." >&2
	exit 1
fi

echo "==> Waiting for the health check"
for _attempt in {1..30}; do
	health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${container_id}")"
	if [[ "${health}" == "healthy" ]]; then
		echo "Deployment complete: http://${SITE_NAME}:8000/lms/"
		exit 0
	fi
	sleep 2
done

echo "Frappe did not become healthy in time. Recent logs:" >&2
compose logs --tail 80 frappe >&2
exit 1
