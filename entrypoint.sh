#!/bin/sh
set -e

export DB_NAME="${DB_NAME:-assetflow}"
export PORT="${PORT:-8069}"

mkdir -p /var/lib/odoo/filestore /var/lib/odoo/sessions
chown -R odoo:odoo /var/lib/odoo

su -p odoo -s /bin/sh -c '
  odoo -d "$DB_NAME" -i assetflow --without-demo=all --stop-after-init \
    --db_host="$PGHOST" --db_port="$PGPORT" --db_user="$PGUSER" --db_password="$PGPASSWORD"
' || true

exec su -p odoo -s /bin/sh -c '
  exec odoo -d "$DB_NAME" \
    --db_host="$PGHOST" --db_port="$PGPORT" --db_user="$PGUSER" --db_password="$PGPASSWORD" \
    --http-port="$PORT" --proxy-mode
'
