# Stage 7 memory

Updated: 2026-11-01
Status: in progress (see remaining gates below).

## Implemented

Authenticated FastAPI integration of the earlier project packages. Bearer tokens map SHA256 digests to server-owned actors; tenant identity is never accepted from request bodies. Request sizes, active requests, per-actor rate and pending runs are bounded. Separate API/worker commands, readiness, containers, CI, load sampling and operational runbooks are included.

Source: `src/research_service/`. Tests: `tests/`. Setup and exact run command: [README](README.md).

## Structure decision

User explicitly corrected the structure: each project owns its implementation inside its numbered folder. D020 supersedes the old shared-root-app plan. Dependencies on earlier projects are declared in pyproject.toml; code is not copied between project runtimes. Original root source is backed up locally under `.migration-backup/`.

## Validation and next action

Run `uv run pytest tests -q` from this folder. Consolidated results are in stage08/evidence/tests.xml; live provider behavior is unmeasured. PostgreSQL and container results must be checked in the final verification record, never inferred from SQLite tests. Complete remaining external gates before claiming the original deployment acceptance criteria are met.

## Measured validation (2026-11-01)

5 passed in 5.58s. Tests were run from this project folder with no PYTHONPATH overrides. Demo command exited 0. See evidence/tests.xml and evidence/cli-smoke.json. Validate container build/PostgreSQL and rollback/restore; cloud deferred by user.
