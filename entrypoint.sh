#!/bin/sh
set -e

DB_NAME="${DB_NAME:-assetflow}"

odoo -d "$DB_NAME" -i assetflow --without-demo=all --stop-after-init \
  --db_host="$PGHOST" --db_port="$PGPORT" --db_user="$PGUSER" --db_password="$PGPASSWORD" || true

exec odoo -d "$DB_NAME" \
  --db_host="$PGHOST" --db_port="$PGPORT" --db_user="$PGUSER" --db_password="$PGPASSWORD" \
  --http-port="${PORT:-8069}" --proxy-mode
