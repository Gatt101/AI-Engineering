# Stage 4 memory

Updated: 2026-11-01
Status: in progress (see remaining gates below).

## Implemented

SQLAlchemy repositories and explicit schema migrations for runs, drafts, actions, approvals and action attempts. Tenant/actor ownership, request idempotency, queue admission, optimistic versions, rollback and consistent SQLite snapshots are enforced in the store. PostgreSQL uses the same schema with transaction locks.

Source: `src/research_state/`. Tests: `tests/`. Setup and exact run command: [README](README.md).

## Structure decision

User explicitly corrected the structure: each project owns its implementation inside its numbered folder. D020 supersedes the old shared-root-app plan. Dependencies on earlier projects are declared in pyproject.toml; code is not copied between project runtimes. Original root source is backed up locally under `.migration-backup/`.

## Validation and next action

Run `uv run pytest tests -q` from this folder. Consolidated results are in stage08/evidence/tests.xml; live provider behavior is unmeasured. PostgreSQL and container results must be checked in the final verification record, never inferred from SQLite tests. Complete remaining external gates before claiming the original deployment acceptance criteria are met.

## Measured validation (2026-11-01)

8 passed, 1 skipped in 2.45s. Tests were run from this project folder with no PYTHONPATH overrides. Demo command exited 0. See evidence/tests.xml and evidence/cli-smoke.json. Run real PostgreSQL transaction/migration/concurrency checks when Docker/server is available.
