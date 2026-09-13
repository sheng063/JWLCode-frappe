#!/usr/bin/env bash

set -Eeuo pipefail

BENCH_DATA_DIR="/home/frappe/bench-data"
BENCH_DIR="${BENCH_DATA_DIR}/frappe-bench"

if [[ "$(id -u)" == "0" ]]; then
	mkdir -p "${BENCH_DATA_DIR}"
	chown -R frappe:frappe "${BENCH_DATA_DIR}"
	exec runuser -u frappe -- "$0" "$@"
fi
SITE_NAME="${SITE_NAME:-school.localhost}"
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-123}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
FRAPPE_BRANCH="${FRAPPE_BRANCH:-develop}"
PAYMENTS_BRANCH="${PAYMENTS_BRANCH:-develop}"
LMS_SOURCE="${LMS_SOURCE:-/workspace/lms}"


if [[ ! -d "${BENCH_DIR}/apps/frappe" ]]; then
	echo "[init] Creating Frappe Bench (${FRAPPE_BRANCH})"
	bench init \
		--frappe-branch "${FRAPPE_BRANCH}" \
		--skip-redis-config-generation \
		"${BENCH_DIR}"
fi

cd "${BENCH_DIR}"

bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis:6379
bench set-redis-queue-host redis://redis:6379
bench set-redis-socketio-host redis://redis:6379
bench set-config -g socketio_port 9000

# Redis is supplied by Compose. Asset watching is not needed for this packaged run.
sed -i '/^redis_/d; /^watch:/d' Procfile
# Keep interactive judge dispatch available while the general worker indexes courses.
if ! grep -q '^worker_short:' Procfile; then
	printf '\nworker_short: bench worker --queue short 1>> logs/worker-short.log 2>> logs/worker-short.error.log\n' >> Procfile
fi
sed -i -E 's#^web: bench serve.*#web: bench serve --port 8000 --host 0.0.0.0#' Procfile

if [[ ! -d apps/payments ]]; then
	echo "[init] Installing Payments source (${PAYMENTS_BRANCH})"
	bench get-app --branch "${PAYMENTS_BRANCH}" payments
fi

if [[ ! -d apps/lms ]]; then
	echo "[init] Importing local Learning source from ${LMS_SOURCE}"
	bench get-app "${LMS_SOURCE}"
fi

if [[ ! -d "sites/${SITE_NAME}" ]]; then
	echo "[init] Creating site ${SITE_NAME}"
	bench new-site "${SITE_NAME}" \
		--mariadb-root-password "${DB_ROOT_PASSWORD}" \
		--admin-password "${ADMIN_PASSWORD}" \
		--mariadb-user-host-login-scope='%'
fi

if ! bench --site "${SITE_NAME}" list-apps --format text | awk '{print $1}' | grep -qx payments; then
	echo "[init] Installing Payments on ${SITE_NAME}"
	bench --site "${SITE_NAME}" install-app payments
fi

if ! bench --site "${SITE_NAME}" list-apps --format text | awk '{print $1}' | grep -qx lms; then
	echo "[init] Installing Learning on ${SITE_NAME}"
	bench --site "${SITE_NAME}" install-app lms
fi

bench --site "${SITE_NAME}" set-config developer_mode 1
bench --site "${SITE_NAME}" set-config host_name "http://${SITE_NAME}:8000"
bench --site "${SITE_NAME}" clear-cache
bench use "${SITE_NAME}"

echo "[init] Learning is available at http://${SITE_NAME}:8000/lms"
bench start
