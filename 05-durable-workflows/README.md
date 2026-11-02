# 05-durable-workflows

Database-backed worker checkpoints, leases and fencing, approval hash/version/expiry binding, cancellation/rejection, bounded retries, fake delivery receipts and uncertainty reconciliation. The demo crashes after a fake side effect, reopens the database and resolves the existing receipt.

## Run this project

From this folder in PowerShell:

```powershell
uv sync --locked
uv run python -m research_workflows
uv run pytest tests -q
```

Python 3.12+ and uv are required. This folder owns `pyproject.toml`, `src/research_workflows/`, `tests/`, `PLAN.md`, `memory.md`, and `evidence/`. The root uv workspace and lockfile resolve explicit dependencies on earlier numbered projects; no root application or PYTHONPATH modification is needed. Keep sibling projects when cloning or moving the workspace.

## Read the code

Start with [source](src/research_workflows/), then [tests](tests/) and [acceptance plan](PLAN.md). Tests run without credentials; PostgreSQL cases require `RESEARCHOPS_TEST_DATABASE_URL` pointing to a disposable local database.

## Limits

Synthetic data only. Offline trajectory and exact-quote metrics do not measure live model reasoning or semantic entailment. Real API calls require a local key and incur provider charges. Delivery always uses the fake local outbox. Cloud hosting is deferred by the user's instruction.
