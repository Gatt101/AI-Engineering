> Structure correction, 2026-11-01: the user requires separately runnable numbered projects. The historical cumulative-app language below describes conceptual progression only; D020 and project READMEs govern physical layout. Cloud hosting is deferred by the user.

# Master plan: Applied and Agentic AI Engineering Portfolio

## Outcome

Build a reproducible, deployed flagship application demonstrating applied AI, agentic engineering, FastAPI backend development, and production deployment. Add a small inference-engine project for LLM internals and an evaluation workbench for deeper specialization. Present ten portfolio stages with working behavior, automated checks, measured results, and explanations of design tradeoffs.

The source is the user's pasted analysis of an eight-stage roadmap. Stages 01-08 follow that sequence with concrete deliverables and completion gates. Stages 09-10 are additions explicitly requested by the user after discussing inference fundamentals and evaluation specialization; they are not attributed to the video. This is a proposed engineering plan, not a claim that the original video specifies every detail here.

## Product to build

Working title: **ResearchOps Assistant**. A user submits a research question; the application retrieves evidence, produces a cited brief, uses authorized tools to inspect synthetic company/lead records, drafts a follow-up, and tracks a workflow through review and completion. External delivery starts with a fake adapter and may later use an explicitly authorized test destination.

This theme keeps retrieval, tools, state, approvals, and failure recovery in one coherent product. The user can change the domain before implementation; the eight engineering milestones remain applicable. Do not infer the user's proficiency or existing projects from commentary in the supplied analysis.

## System design to evolve toward

```text
User / API client
      |
FastAPI: authentication, validation, request and tenant context
      |
Application services: research, retrieval, tools, workflow execution
      |                 |                   |
Native model SDK    Evidence store     Policy + approval checks
      |                 |                   |
      +---------- PostgreSQL ---------- Tool adapters / worker
                        |
              Runs, business state, approvals, action ledger

Cross-cutting: automated tests, evaluation datasets, traces,
resource budgets, deployment checks, and operational runbooks
```

This is a target architecture. Implement only the part needed by the active stage. Conversation summaries, trusted business state, and workflow checkpoints serve different purposes and must not be conflated.

## Milestone sequence

| Stage | New capability | Depends on | Completion evidence |
| --- | --- | --- | --- |
| [1](01-native-llm-sdk/PLAN.md) | Bounded native-SDK requests and streaming through a small API | None | Runnable app, provider-mocked tests, initial evaluation cases |
| [2](02-retrieval-and-evidence/PLAN.md) | Ingestion, retrieval, supported answers, citations | 1 | Reproducible corpus, retrieval results, citation checks |
| [3](03-tool-calling-agent/PLAN.md) | Agent loop, validated tools, deterministic permissions | 1-2 | Tool trajectories, denial tests, bounded execution |
| [4](04-persistence-and-state/PLAN.md) | Durable business records and resumable requests | 1-3 | Migrations, restart tests, concurrency and ownership checks |
| [5](05-durable-workflows/PLAN.md) | Checkpoints, approvals, worker recovery, action deduplication | 1-4 | Crash/retry/replay demonstrations and recovery reports |
| [6](06-evaluation-and-observability/PLAN.md) | Regression evaluation and correlated traces | 1-5 | Versioned evaluation baseline, CI gates, redacted failure traces |
| [7](07-production-engineering/PLAN.md) | Secure, observable deployment and operations | 1-6 | Deployment, tenant tests, load report, rollback/restore rehearsal |
| [8](08-engineering-portfolio/PLAN.md) | Reproducible portfolio and engineering narrative | 1-7 | Fresh-clone walkthrough, case study, evidence index, final demo |
| [9](09-llm-inference-engine/PLAN.md) | Small custom inference engine and LLM internals | Stage 1 concepts and tensor fundamentals; recommended after 1-2 | Reference-logit parity, KV-cache correctness, latency/throughput/memory report |
| [10](10-ai-evaluation-specialization/PLAN.md) | Reusable evaluation workbench and specialization | Stage 6 assets; deep work after core portfolio; stage 9 optional | Dataset/rubric, judge calibration, paired comparisons, uncertainty, failure analysis |

Proceed by completion gates rather than a fixed calendar. For each stage: review its memory, design the smallest useful increment, implement, test failure paths, collect evidence, and update the handoff. Stages 01-08 are separately runnable projects in numbered folders, with explicit dependencies where needed. Stages 09-10 remain companion projects.

Suggested learning order: **01-02 -> 09 -> 03-07 -> 08 initial portfolio -> 10 specialization -> 08 portfolio refresh**. Folder numbering is organizational, not a strict dependency chain. Collect evaluation cases from stage 01 throughout; do not postpone evaluation until stage 10. Stage 08 can complete its initial flagship release before stage 10 and later receive a documented portfolio update, avoiding a circular prerequisite.

Stage 06 establishes application-specific evaluation and observability. Stage 10 extends those assets into reusable tooling and deeper evaluation methodology, including label quality, judge reliability, held-out experiments, and uncertainty. Stage 09 is an educational engine, not a prerequisite for deploying the flagship.

## Repository organization

```text
AGENTS.md                         AI context-loading instructions
README.md                         Entry point and stage index
memory.md                         Compact persistent project context
MASTER_PLAN.md                    Overall scope and completion gates
docs/
  PROGRESS.md                     Actual status and evidence links
  DECISIONS.md                    Proposed and accepted architecture choices
  SOURCE_NOTES.md                 Provenance and interpretation
  source-video-analysis.md        Preserved user-provided analysis
01-native-llm-sdk/                 PLAN.md + memory.md
02-retrieval-and-evidence/         PLAN.md + memory.md
03-tool-calling-agent/             PLAN.md + memory.md
04-persistence-and-state/          PLAN.md + memory.md
05-durable-workflows/              PLAN.md + memory.md
06-evaluation-and-observability/   PLAN.md + memory.md
07-production-engineering/        PLAN.md + memory.md
08-engineering-portfolio/          PLAN.md + memory.md
09-llm-inference-engine/           PLAN.md + memory.md
10-ai-evaluation-specialization/   PLAN.md + memory.md
```

Each stage owns src/<package>/, tests/, pyproject.toml, data and infrastructure inside its numbered folder. There is no root application. Reuse earlier projects through declared package dependencies. Store stage-specific reports under that stage's eventual `evidence/` directory. When Git is initialized, use milestone tags to preserve runnable historical versions, with their dependency locks and setup instructions.

Companion implementations may live in separately scoped packages under a future `projects/` directory; create them only when coding begins and record their paths in stage memory. Keep stage 09's inference dependencies separate from the flagship. Stage 10 should reuse or extract stage 06 evaluation contracts and assets with documented compatibility instead of creating a divergent evaluator.

## Technology and scope

- **Python + FastAPI:** begin with a thin API in stage 1; mature validation, dependency injection, background execution, and API contracts across later stages.
- **Native model SDK:** select one provider initially; capture timeouts, retry behavior, streaming, output validation, usage, and errors without hiding the underlying mechanics.
- **PostgreSQL:** introduce it for retrieval in stage 2 if using pgvector; expand to business state and transactional migrations in stage 4. Retrieval storage is not a substitute for business-state design.
- **Agent tools:** implement a small explicit tool registry and policy boundary before adding orchestration abstractions. MCP is optional; A2A is outside the initial scope unless a concrete need emerges.
- **Workflow engine:** evaluate LangGraph or Temporal at stage 5 and select one based on the required durability and operating model. Neither choice removes the need for idempotency and reconciliation.
- **Evaluation and traces:** begin with a small local dataset; decide on a tracing backend such as Langfuse when stage 6 requirements are clear.
- **Inference fundamentals:** stage 09 starts with one small existing checkpoint, PyTorch tensor operations, reference comparisons, and KV caching. Training, CUDA kernels, and production serving are optional extensions.
- **Evaluation specialization:** stage 10 prioritizes datasets/rubrics, deterministic scorers, calibrated judges, reusable target adapters, paired experiments, and regression gates. A dashboard is optional.
- **Deployment:** plan Docker and GitHub Actions; choose a hosting platform and managed database before stage 7. Do not provision paid resources as part of planning.
- **UI:** optional after a useful API exists. A polished web frontend, Kubernetes, multiple model providers, and multi-agent coordination are not initial completion requirements.

## Engineering requirements across stages

1. Keep a deterministic, offline test suite with fake model/tool adapters. Run live-provider checks separately when credentials and a cost budget are available.
2. Version prompts, schemas, corpus snapshots, and evaluation cases alongside code. Keep train/tuning examples separate from final evaluation cases.
3. Validate model outputs and tool arguments. Bound request duration, tool rounds, concurrency, output tokens, and retries. Classify failures before retrying.
4. Enforce permissions in application code using trusted identity and resource ownership. Treat retrieved text and model output as untrusted data.
5. Bind approval to a specific actor, tenant, action, and payload/version; re-check authorization at execution. Reject stale or replayed approvals.
6. Use transactions, stable action identifiers, unique constraints, and provider idempotency when available. If external completion is ambiguous, reconcile before retrying. Do not claim exactly-once side effects from checkpoints alone.
7. Redact secrets and sensitive inputs from logs and portfolio evidence. Define retention and deletion behavior before handling real data.
8. Every stage must include a happy path, at least one meaningful failure case, and a repeatable verification procedure.

## Measurement plan

Track task success, grounded-answer quality, retrieval recall at a chosen k, citation validity/support, tool selection and argument correctness, unauthorized-action blocks, recovery success, p50/p95 latency, and token/cost usage where applicable.

For stage 09, measure reference-logit error, cached/uncached agreement, time to first token, decode throughput, and memory under declared hardware/dtype/workloads. For stage 10, report label/judge disagreement, paired version differences, sample sizes, repeated trials, per-task slices, uncertainty assumptions, and scorer failures. Keep development/calibration separate from held-out comparisons.

For each report, record dataset version, model and prompt version, configuration, sample size, environment, date, and limitations. Agree on thresholds after the first measured baseline and before evaluating subsequent changes. Authorization and tenant-isolation test suites must have zero successful forbidden actions. Report that as a test result, not a universal security guarantee. Never invent benchmark values or pricing.

## Final definition of done

- A documented deployment completes the research-to-review workflow through the API.
- Offline setup and tests are reproducible; live-provider setup and costs are explained separately.
- Retrieval citations, permissions, tenant boundaries, restart recovery, approval integrity, and retry behavior have automated evidence.
- Evaluation reports show measured results and known failures, with regression gates in CI.
- Deployment documentation covers configuration, secrets, migrations, health checks, logs, rollback, and backup restoration.
- The expanded portfolio contains an architecture diagram, ten stage summaries, API examples, a concise demo, failure/recovery case studies, and an honest limitations section. Stage 08's initial release may cover the original eight before being refreshed.
- The inference project demonstrates a custom forward/generation path, reference parity, KV-cache correctness, and reproducible performance measurements.
- The evaluation specialization demonstrates reusable tooling, human-label methodology, judge calibration, held-out paired experiments, uncertainty, and failure analysis beyond the flagship's stage 06 checks.
- Every capability claimed by the final case study links to source, tests, reports, or a demonstrable deployment.
