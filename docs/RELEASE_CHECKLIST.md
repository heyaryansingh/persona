# Release checklist

## Verified locally

- [x] Evidence-first core: exact-span claims, replayable sessions, offline GEO artifact, provenance, and human-gated anchors.
- [x] FalkorDB live claim-write regression.
- [x] Public tenant boundary: OIDC session, owner-filtered list, cross-tenant 404, CSRF, quota, and rate-limit tests.
- [x] Provider-key ciphertext/redaction/revocation tests and explicit Anthropic/OpenAI-compatible provider boundaries.
- [x] Blinded reviewer enrollment, fixed assignment ordering, duplicate refusal, append-only labels, and ledger verification.
- [x] `350` Python tests, renderer checks, compilation, whitespace check, Compose-template validation, and shell-script validation.
- [x] No-worker browser smoke through Work → GEO replay → Review dossier.
- [x] `persona:0.3.0` container image build.

## Run on the VPS before publishing

- [ ] Rotate any local credentials that were ever present in `.env`; create fresh Google OAuth, session, encryption, Postgres, and provider secrets.
- [ ] Set DNS A/AAAA records and verify Caddy HTTPS issuance at the real domain.
- [ ] Sign in with a real Google account; confirm an account sees only its own workspace.
- [ ] Add, rotate, and revoke Anthropic/OpenAI/Hugging Face keys through `/settings`; confirm no plaintext is returned or logged.
- [ ] Confirm the $5 public workspace cap, one-workspace quota, and rate-limit response.
- [ ] Rehearse `scripts/backup.sh` and `scripts/restore.sh` on a disposable VPS, then inspect a known replayable session after restore.

## Hackathon presentation

Use [HACKATHON_DEMO.md](HACKATHON_DEMO.md) with `PERSONA_WORKERS=0` and
`PERSONA_START_SCHEDULER=0`. The demo is intentionally read-only and shows the
system’s real artifacts rather than spending money or mutating shared evidence live.
