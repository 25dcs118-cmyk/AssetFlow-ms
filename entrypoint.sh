#!/bin/sh
set -e

export DB_NAME="${DB_NAME:-assetflow}"
export PORT="${PORT:-8069}"

mkdir -p /var/lib/odoo/filestore /var/lib/odoo/sessions
chown -R odoo:odoo /var/lib/odoo

# Lock down the database manager: single-tenant deploy, no reason to expose
# create/duplicate/delete/restore over the web at all.
echo "list_db = False" >> /etc/odoo/odoo.conf
if [ -n "$ADMIN_PASSWORD" ]; then
  echo "admin_passwd = $ADMIN_PASSWORD" >> /etc/odoo/odoo.conf
fi

# su -p preserves root's HOME, which makes libpq look for TLS client certs at
# /root/.postgresql/ (unreadable by the odoo user) and hard-fail every DB
# connection. Force HOME to the odoo user's own home to avoid that lookup.
su -p odoo -s /bin/sh -c '
  export HOME=/var/lib/odoo
  odoo -d "$DB_NAME" -i assetflow --without-demo=all --stop-after-init \
    --db_host="$PGHOST" --db_port="$PGPORT" --db_user="$PGUSER" --db_password="$PGPASSWORD"
' || true

# -i is a no-op once the module is already installed, so code/view changes on
# every subsequent deploy would otherwise never actually reach the live site.
# Always run -u too to pick up updates.
su -p odoo -s /bin/sh -c '
  export HOME=/var/lib/odoo
  odoo -d "$DB_NAME" -u assetflow --stop-after-init \
    --db_host="$PGHOST" --db_port="$PGPORT" --db_user="$PGUSER" --db_password="$PGPASSWORD"
' || true

exec su -p odoo -s /bin/sh -c '
  export HOME=/var/lib/odoo
  exec odoo -d "$DB_NAME" \
    --db_host="$PGHOST" --db_port="$PGPORT" --db_user="$PGUSER" --db_password="$PGPASSWORD" \
    --http-port="$PORT" --proxy-mode
'
