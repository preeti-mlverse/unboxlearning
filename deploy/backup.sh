#!/usr/bin/env bash
# Nightly database backup for both environments (installed by server-setup.sh as /usr/local/bin/unboxed-backup).
# Keeps 14 days in /var/backups/unboxed. Restore one with:
#   gunzip -c FILE.sql.gz | sudo docker compose -p unboxed-production -f /srv/unboxed/docker-compose.prod.yml \
#     --env-file /etc/unboxed/production.env exec -T db psql -U unboxed unboxed
set -euo pipefail
OUT=/var/backups/unboxed
mkdir -p "$OUT"
for TARGET in production staging; do
  ENV=/etc/unboxed/$TARGET.env
  [ -f "$ENV" ] || continue
  docker compose -p "unboxed-$TARGET" -f /srv/unboxed/docker-compose.prod.yml --env-file "$ENV" ps --status running db -q | grep -q . || continue
  F="$OUT/$TARGET-$(date +%Y%m%d-%H%M).sql.gz"
  docker compose -p "unboxed-$TARGET" -f /srv/unboxed/docker-compose.prod.yml --env-file "$ENV" exec -T db pg_dump -U unboxed unboxed | gzip > "$F"
  echo "$(date -Is) backed up $TARGET -> $F"
done
find "$OUT" -name '*.sql.gz' -mtime +14 -delete
