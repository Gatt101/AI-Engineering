# 07-production-engineering

Authenticated FastAPI integration of the earlier project packages. Bearer tokens map SHA256 digests to server-owned actors; tenant identity is never accepted from request bodies. Request sizes, active requests, per-actor rate and pending runs are bounded. Separate API/worker commands, readiness, containers, CI, load sampling and operational runbooks are included.

## Run this project

From this folder in PowerShell:

```powershell
uv sync --locked
uv run python -m research_service.demo
uv run pytest tests -q
```

Python 3.12+ and uv are required. This folder owns `pyproject.toml`, `src/research_service/`, `tests/`, `PLAN.md`, `memory.md`, and `evidence/`. The root uv workspace and lockfile resolve explicit dependencies on earlier numbered projects; no root application or PYTHONPATH modification is needed. Keep sibling projects when cloning or moving the workspace.

## Read the code

Start with [source](src/research_service/), then [tests](tests/) and [acceptance plan](PLAN.md). Tests run without credentials; PostgreSQL cases require `RESEARCHOPS_TEST_DATABASE_URL` pointing to a disposable local database.

## Limits

Synthetic data only. Offline trajectory and exact-quote metrics do not measure live model reasoning or semantic entailment. Real API calls require a local key and incur provider charges. Delivery always uses the fake local outbox. Cloud hosting is deferred by the user's instruction.

See [operations runbook](RUNBOOK.md) for serving the API, separate worker, containers, identity configuration, migrations, backup, rollback and known deployment gaps.
