# Stage 5 memory

Updated: 2026-11-01
Status: complete (see remaining gates below).

## Implemented

Database-backed worker checkpoints, leases and fencing, approval hash/version/expiry binding, cancellation/rejection, bounded retries, fake delivery receipts and uncertainty reconciliation. The demo crashes after a fake side effect, reopens the database and resolves the existing receipt.

Source: `src/research_workflows/`. Tests: `tests/`. Setup and exact run command: [README](README.md).

## Structure decision

User explicitly corrected the structure: each project owns its implementation inside its numbered folder. D020 supersedes the old shared-root-app plan. Dependencies on earlier projects are declared in pyproject.toml; code is not copied between project runtimes. Original root source is backed up locally under `.migration-backup/`.

## Validation and next action

Run `uv run pytest tests -q` from this folder. Consolidated results are in stage08/evidence/tests.xml; live provider behavior is unmeasured. PostgreSQL and container results must be checked in the final verification record, never inferred from SQLite tests. Complete remaining external gates before claiming the original deployment acceptance criteria are met.

## Measured validation (2026-11-01)

14 passed in 2.98s. Tests were run from this project folder with no PYTHONPATH overrides. Demo command exited 0. See evidence/tests.xml and evidence/cli-smoke.json. Validate a real outbound provider only after explicit authorization and adapter design.
