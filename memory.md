# Persistent project memory

Updated: 2026-11-01

## User objective and explicit preferences

Build the AI engineering portfolio through stages01–08, plus planned09 inference and10 evaluation specialization. Work inside G:/Projects/Agentic-AI. Do not use browser tools or browser automation.

The user explicitly rejected the shared root app/ layout. **Each numbered project must own its source, tests, setup, runnable commands and documentation inside that folder.** This supersedes prior shared-app plans. See D020. Do not recreate a root application.

## Actual implementation

Eight project packages now live under their numbered folders' src/: research_sdk, research_evidence, research_tools, research_state, research_workflows, research_evaluation, research_service and research_portfolio. Each has tests and pyproject.toml. The root only holds uv workspace tooling, shared lockfile and context/index documents. Later packages declare explicit dependencies on earlier projects. Original root source and pre-migration archive are preserved under ignored .migration-backup/.

All project-folder tests and demo commands passed. Combined suite: 106 passed, 21 PostgreSQL-dependent skips. Lint/format pass. Reports and per-project commands: docs/PROGRESS.md and project READMEs. Stage02/03/05/06 local acceptance complete. Stage04 retains real-PostgreSQL verification; stage07 retains container/production verification; stage08 retains final release evidence. Do not describe all original deployment gates as complete.

No live provider measurement has run. OpenAI native SDK is implemented; configure a local key only for opt-in live commands. Retrieval answers are extractive quotes; scripted agent trajectories are labeled. Delivery is fake only; authorization comes from trusted actor permissions and exact stored approval records. Stages09–10 remain planned.

The user chose local preparation and cloud hosting later. Docker Engine was unavailable during final verification; container build, PostgreSQL checks and hosted rollback/restore remain pending. SQLite restart/concurrency/backup, workflow crash-after-side-effect recovery, API ownership, denial/replay and trace redaction have offline tests.

## Next action

Read the chosen project's README, PLAN and memory. Run its command from its numbered folder. Complete outstanding PostgreSQL/container gates when a working server/engine is available; choose cloud hosting only when the user resumes that scope. Preserve the project-owned layout and accurately distinguish local tests from live/deployed evidence.
