#!/usr/bin/env bash
set -euo pipefail

backup=${1:?usage: scripts/restore.sh /path/to/backup}
test -f "$backup/SHA256SUMS"
(cd "$backup" && sha256sum -c SHA256SUMS)
read -r -p "This replaces Persona production data. Type RESTORE to continue: " answer
test "$answer" = RESTORE

root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
docker compose down
for volume in persona_workspace persona_falkordb_data persona_postgres_data persona_caddy_data persona_caddy_config; do
  docker volume create "$volume" >/dev/null
  docker run --rm -v "$volume:/target" -v "$backup:/backup:ro" alpine \
    sh -c "rm -rf /target/* /target/.[!.]* /target/..?*; tar -C /target -xzf /backup/$volume.tgz"
done
docker compose up -d
printf 'Restore started. Check: docker compose ps\n'
