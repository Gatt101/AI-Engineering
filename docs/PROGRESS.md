# Progress and evidence ledger

Updated: 2026-11-01

The user corrected the architecture: projects own their source/tests inside numbered folders. Root app/tests/evals/infra were moved into a protected local backup after source relocation and testing. No root runtime remains. A uv workspace supplies shared dependency resolution.

Local implementation is present for 01–08. The original external acceptance gates are tracked separately. All eight projects passed their own folder-local tests and demos; full suite: **106 passed, 21 skipped** (PostgreSQL-dependent cases). Ruff lint and formatting pass.

| Project | Status | Evidence | Next action |
| --- | --- | --- | --- |
| 1. 01-native-llm-sdk | complete | [26 passed in 3.94s](../01-native-llm-sdk/evidence/tests.xml), [run guide](../01-native-llm-sdk/README.md) | Optional live provider measurement with a local API key. |
| 2. 02-retrieval-and-evidence | complete | [22 passed, 20 skipped in 2.03s](../02-retrieval-and-evidence/evidence/tests.xml), [run guide](../02-retrieval-and-evidence/README.md) | Review paraphrase miss; add embeddings only when justified. |
| 3. 03-tool-calling-agent | complete | [29 passed in 3.28s](../03-tool-calling-agent/evidence/tests.xml), [run guide](../03-tool-calling-agent/README.md) | Optional live tool-choice evaluation with a local API key. |
| 4. 04-persistence-and-state | in progress | [8 passed, 1 skipped in 2.45s](../04-persistence-and-state/evidence/tests.xml), [run guide](../04-persistence-and-state/README.md) | Run real PostgreSQL transaction/migration/concurrency checks when Docker/server is available. |
| 5. 05-durable-workflows | complete | [14 passed in 2.98s](../05-durable-workflows/evidence/tests.xml), [run guide](../05-durable-workflows/README.md) | Validate a real outbound provider only after explicit authorization and adapter design. |
| 6. 06-evaluation-and-observability | complete | [1 passed in 3.57s](../06-evaluation-and-observability/evidence/tests.xml), [run guide](../06-evaluation-and-observability/README.md) | Keep gates fixed for subsequent changes; live model evaluation remains pending. |
| 7. 07-production-engineering | in progress | [5 passed in 5.58s](../07-production-engineering/evidence/tests.xml), [run guide](../07-production-engineering/README.md) | Validate container build/PostgreSQL and rollback/restore; cloud deferred by user. |
| 8. 08-engineering-portfolio | in progress | [1 passed in 4.72s](../08-engineering-portfolio/evidence/tests.xml), [run guide](../08-engineering-portfolio/README.md) | Complete remaining production evidence before declaring the original full release gate complete. |
| 9. LLM inference engine | not started | Plan only | User has not requested implementation in this task |
| 10. Evaluation specialization | not started | Plan only | User has not requested implementation in this task |

## Measurements

Stage02/06 synthetic dataset: nine questions, six retrieval-labeled cases. Task success 8/9; BM25 recall@1 0.9167 versus term overlap 0.5833 (fractional recall for multi-source cases). All seven returned citations resolve; expected-quote support is 5/6. One paraphrase miss is documented. These are authored synthetic exact-quote checks, not live model/semantic entailment scores.

Stage07 local ASGI load: 40 requests, concurrency4, zero errors, p95 87.09ms in the recorded run. See its load.json for exact workload/duration; this excludes network, hosted hardware and provider latency.

## Evidence and external limitations

- [Per-project verification](../08-engineering-portfolio/evidence/project-verification.json): each tests/demo command ran from its own folder.
- [Combined JUnit](../08-engineering-portfolio/evidence/tests.xml): 106 pass, 21 PostgreSQL-dependent skips.
- [Evaluation](../06-evaluation-and-observability/evidence/offline-report.json): all deterministic gates pass; deliberate citation regression is rejected by tests.
- [API/recovery demo](../08-engineering-portfolio/evidence/demo.json), [correlated failure trace](../08-engineering-portfolio/evidence/demo.trace.jsonl), [case study](../08-engineering-portfolio/CASE_STUDY.md).
- Docker executable exists, but Docker Engine was unavailable on final verification and startup did not establish a usable engine. No new container/PostgreSQL pass or image rollback/PG restore rehearsal is claimed.
- Cloud hosting was explicitly deferred by the user. No paid resources provisioned. No live model calls made.
- Fresh locked dependencies were installed; all project-folder tests and demos ran afterward. No Git release/tag or hosted CI run exists.

## Work log

2026-11-01: Corrected prior unfinished shared-root implementation following user feedback. Created project-owned packages, migrated existing tested code, split authoritative state from orchestration, added standalone commands, evaluation gates, API tenant/resource tests, operational worker, load sampler, portfolio demo/trace and guides. Preserved old source in ignored .migration-backup/. Updated AGENTS, plans, decisions and memories. Validation commands: `python -m pytest -q --junitxml=08-engineering-portfolio/evidence/tests.xml`; `python -m ruff check .`; `python -m ruff format --check .`; and each project's `python -m pytest tests -q` plus README demo.

2026-10-28 historical: stage01 native provider integration and 26 offline checks initially lived in root app/. That layout is superseded; historical raw evidence may retain old paths.
