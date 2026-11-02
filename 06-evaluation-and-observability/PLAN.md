# Stage 6: Evaluation and observability

## Objective

Make quality, failures, latency, and resource use measurable, and gate changes with reproducible evaluation.

## Entry requirements

Stages 1-5 evaluation cases, traces, tool trajectories, and recovery fixtures.

## What to design

- Build a versioned evaluation suite covering answer quality, retrieval, citations, tool selection/arguments, authorization, prompt injection, and recovery.
- Separate deterministic invariants from probabilistic model quality. Use human-labeled references and documented rubrics; calibrate any model-based judge.
- Keep tuning/development examples separate from held-out regression cases and prevent sensitive production content from entering fixtures.
- Correlate API requests, model calls, retrieval, tools, workflow runs, and action attempts with trace/run IDs.
- Record latency, token usage, failures, and cost estimates with model/configuration versions; label unavailable usage rather than guessing.
- Choose a tracing backend and define redaction, sampling, retention, and access controls.

## Build sequence

1. Consolidate earlier stage fixtures and add adversarial, edge, and recovery cases with expected outcomes.
2. Implement an evaluation runner that emits machine-readable results plus a concise human-readable report.
3. Measure the first baseline with dataset/model/prompt versions and sample sizes.
4. Set justified quality and performance thresholds before subsequent comparison; add CI gates for deterministic and regression checks.
5. Instrument correlated traces and demonstrate how a failed task can be diagnosed from its redacted trace.

## Acceptance criteria

- [x] A documented command reproduces the offline evaluation report; live-model evaluation is a separately configured bounded run.
- [x] The report includes task success, retrieval/citation quality, tool correctness, denial/recovery results, latency, and usage where available.
- [x] CI fails when a deliberately introduced regression breaks a meaningful gate.
- [x] Authorization tests contain zero successful forbidden actions; no metric is represented as a universal security guarantee.
- [x] At least one failure trace connects API input through retrieval/model/tool/workflow events and supports a concrete diagnosis.

## Portfolio evidence to collect

Versioned datasets, evaluation runner, baseline/comparison reports, CI gate results, redacted traces, and documented limitations.

Save generated reports under this stage's `evidence/` folder when available. Include commands, versions, dataset/configuration, date, and limitations. Link evidence from [progress](../docs/PROGRESS.md); do not create placeholder results.

## Handoff to the next stage

Quality gates and operational signals ready for deployment monitoring and final portfolio claims.

## Scope boundary

Do not inflate confidence from a small sample or rely only on an LLM judging its own output.

## Context

Read [master plan](../MASTER_PLAN.md), [root memory](../memory.md), and [stage memory](memory.md). This document describes planned work; check progress and source before assuming any capability exists.


## Implementation layout correction (2026-11-01)

The user requires code, tests and runnable entry points inside this numbered folder. See README.md and pyproject.toml. Earlier shared-root-app references are superseded by D020. Cloud deployment is deferred by the user; local verification does not satisfy cloud deployment gates.
