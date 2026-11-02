# Stage 1 memory

Updated: 2026-11-01
Status: complete (see remaining gates below).

## Implemented

Native OpenAI Responses API integration, JSON and SSE endpoints, provider error normalization, total deadlines, retry and token budgets. Tests use the real SDK with HTTP transport fixtures.

Source: `src/research_sdk/`. Tests: `tests/`. Setup and exact run command: [README](README.md).

## Structure decision

User explicitly corrected the structure: each project owns its implementation inside its numbered folder. D020 supersedes the old shared-root-app plan. Dependencies on earlier projects are declared in pyproject.toml; code is not copied between project runtimes. Original root source is backed up locally under `.migration-backup/`.

## Validation and next action

Run `uv run pytest tests -q` from this folder. Consolidated results are in stage08/evidence/tests.xml; live provider behavior is unmeasured. PostgreSQL and container results must be checked in the final verification record, never inferred from SQLite tests. Complete remaining external gates before claiming the original deployment acceptance criteria are met.

## Measured validation (2026-11-01)

26 passed in 3.94s. Tests were run from this project folder with no PYTHONPATH overrides. See evidence/tests.xml and README.md. Optional live provider measurement with a local API key.
