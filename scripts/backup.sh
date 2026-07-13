#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
target=${1:-"$root/backups/$(date -u +%Y%m%dT%H%M%SZ)"}
mkdir -p "$target"

docker compose exec -T postgres pg_dump -U persona persona >"$target/postgres.sql"
docker compose exec -T falkordb redis-cli SAVE >/dev/null
for volume in persona_workspace persona_falkordb_data persona_postgres_data persona_caddy_data persona_caddy_config; do
  docker run --rm -v "$volume:/source:ro" -v "$target:/backup" alpine \
    tar -C /source -czf "/backup/$volume.tgz" .
done
sha256sum "$target"/* >"$target/SHA256SUMS"
printf 'Backup written to %s\n' "$target"
