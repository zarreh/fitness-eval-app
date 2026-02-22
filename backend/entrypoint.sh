#!/bin/sh
# Always sync static seed data (i18n, norms) from the image into the
# volume-mounted /app/data directory.  This ensures that rebuilding the
# image updates these files even though /app/data is a persisted Docker
# volume.  Runtime files (fitness.db, clients.json, etc.) are not touched.
set -e

echo "Syncing static data from image seed..."
cp -r /app/seed_data/i18n/. /app/data/i18n/
cp -r /app/seed_data/norms/. /app/data/norms/
echo "Static data sync complete."

exec "$@"
