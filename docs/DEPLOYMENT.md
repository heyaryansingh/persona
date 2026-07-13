# Production deployment

Persona runs on one Ubuntu VPS. Caddy is the only exposed service; the web API,
worker, FalkorDB, and PostgreSQL remain on the Docker network. The worker is off
by default, so a public launch cannot begin autonomous paid work accidentally.

## Prerequisites

1. An Ubuntu VPS with Docker Engine and the Docker Compose plugin.
2. DNS control: create an `A` record for `persona.aryansingh.org` to the VPS IPv4
   address (and an `AAAA` record only when IPv6 routing/firewall is working).
3. Allow inbound TCP 80 and 443. Do not expose 8137, 6379, or 5432.
4. Google OAuth production credentials, provider credentials, and independently
   generated encryption and session secrets.

## Launch

```bash
git clone <your-release-repository> persona && cd persona
cp .env.production.example .env.production
chmod 600 .env.production
# edit .env.production; set every required secret and the real DOMAIN
docker compose --env-file .env.production config # validates interpolation without starting services
docker compose --env-file .env.production up -d --build
docker compose --env-file .env.production ps
curl -fsS https://persona.aryansingh.org/ >/dev/null
```

Caddy obtains and renews TLS after DNS resolves and ports 80/443 are reachable.
`docker compose --env-file .env.production logs -f caddy web` is the first diagnostic if certificate issuance
or startup fails. The API health check uses `/readyz`, which probes FalkorDB; the deployment is ready
only when `docker compose ps` reports Caddy and web healthy.

## Workers and spend

The stack deliberately sets both `PERSONA_WORKERS=0` and
`PERSONA_START_SCHEDULER=0`. Do not add a separate worker container until the
tenant-aware queue dispatcher is implemented and has passed its isolation test;
the existing worker command only knows the legacy default workspace. Do not put
provider keys in Compose arguments, shell history, Git, browser storage, logs, or
backups shared outside the trusted recovery path.

## Backup and restore rehearsal

Run backups from the release checkout. They include the workspace, FalkorDB,
PostgreSQL, and Caddy certificate/config volumes; encrypt and copy the resulting
directory off-host.

```bash
chmod +x scripts/backup.sh scripts/restore.sh
scripts/backup.sh /srv/persona-backups/$(date -u +%Y%m%dT%H%M%SZ)
scripts/restore.sh /srv/persona-backups/<timestamp>
```

Restore intentionally stops the stack, validates checksums, asks for `RESTORE`,
replaces all named volumes, then starts the stack. Rehearse this on a separate VPS
before release and verify HTTPS sign-in plus a known tenant's data afterwards.

## Release gate

Before tagging an image or demoing publicly: run the full test suite and browser
smoke with workers disabled, build the compose stack, verify HTTPS sign-in and
tenant isolation, exercise provider add/rotate/revoke without plaintext leakage,
exercise bounded HF trial failures, and complete the restore rehearsal above.
