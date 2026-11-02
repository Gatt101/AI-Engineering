# Local operations and deferred deployment

## API and worker

From this folder:

```powershell
uv sync --locked
Copy-Item .env.example .env
# Set DEMO_MODE=true only for local synthetic examples.
uv run python -m uvicorn research_service.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

With local demo mode, authenticate with `Authorization: Bearer local-demo-token`. Readiness is GET /ready. Use POST /v1/answers, POST /v1/runs, GET /v1/runs/{id}, POST /v1/runs/{id}/advance, GET /v1/actions/{id}, and POST /v1/actions/{id}/approve. Each approval body contains expected_version from the current stored action. Run `uv run python -m research_service.demo` for executable examples.

A separate terminal may run `uv run python -m research_service.worker`. The worker rechecks configured permissions, and always uses fake delivery. API and worker must share DATABASE_URL and identity configuration. Stop with Ctrl+C; pending work survives. A killed worker's lease must expire before another worker resumes it.

## Identity and secrets

API_PRINCIPALS is a JSON object mapping SHA256 bearer-token digests to objects with actor_id, tenant_id and permissions. Generate random high-entropy tokens locally, hash with hashlib.sha256, store the original token in a secret manager/client, and store the mapping in protected environment configuration. Tokens, prompts and real records must not enter evidence. Permission names are in research_service.auth.DEMO_PERMISSIONS; grant the minimum required subset. Never use the public demo token beyond localhost. Restart/reload API configuration after revocation; the worker reloads its configuration each tick.

Production mode requires PostgreSQL, nonempty configured principals, DEMO_MODE=false and AUTO_MIGRATE=false. A hosting provider, TLS termination, SSO strategy and managed secret store remain deferred. Quotas and active-request bounds currently apply per process; distributed rate limiting must be added when scaling replicas.

## Migrations, backup and recovery

Run `uv run python -m research_state.db --database-url <URL>` as a separate release step before starting workers or the API with AUTO_MIGRATE=false. Migration IDs are recorded in schema_versions. Downgrades are refused. Back up before migration; deploy only releases compatible with the recorded schema. There is no automatic destructive down migration.

For SQLite, use `uv run python -m research_state.db --database-url sqlite:///researchops.db --backup backups/snapshot.db` (create backups/ first). The backup API takes a consistent snapshot; destination must be new. Restore into a new file, point DATABASE_URL at it, run readiness and the stored-record checks before switching traffic. Automated snapshot/reopen evidence is in stage04/tests/test_state.py.

For PostgreSQL, use pg_dump to a protected destination; restore with pg_restore into a separate empty database. Verify migrations, owned records, readiness and pending-work recovery before promotion. A PostgreSQL restore rehearsal has NOT run in this environment.

Roll back application code/image only if its schema compatibility is known. Otherwise restore the pre-migration snapshot into a separate database and verify before switching traffic. Quiesce workers during the transition. No deployed image rollback rehearsal is claimed.

## Local containers

```powershell
docker compose -f infra/compose.yaml up --build -d
docker compose -f infra/compose.yaml logs --tail 100 api worker
docker compose -f infra/compose.yaml down
```

Compose starts PostgreSQL, runs migrations once, then starts separate API and worker processes. The API binds to localhost; the DB volume persists after down. It uses synthetic-only local credentials. Docker Engine is required. Container startup/build and PostgreSQL integration verification remain pending because the engine was unavailable during the final verification.

## Diagnostics and retention

Allowlisted JSON logs correlate request IDs and durable run IDs. Unknown tools appear as mode=unknown and outcome=unknown_tool. A representative failure trace is exported by the stage08 portfolio demo. Local evidence contains synthetic data. Production operators must restrict log access and set retention/deletion before real data use. Inspect manual_review actions and reconcile with a provider receipt; never blindly resend uncertain actions.

## Measurements

`uv run python -m research_service.load` writes evidence/load.json. This is a bounded, in-process ASGI/SQLite sample with 40 extractive-answer requests and concurrency 4; it does not establish hosted capacity, provider latency or an availability SLO. No cloud resources or operating cost commitments were made.
