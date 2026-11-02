# Stage 5: Durable workflows and failure recovery

## Objective

Execute research-to-draft workflows across interruptions, approvals, retries, and worker crashes with explicit handling of external-action uncertainty.

## Entry requirements

Stages 1-4 stored runs, approvals/actions, tool policy, and transactions.

## What to design

- Define a workflow: intake, retrieve, generate brief, validate, draft, await approval, execute permitted action, reconcile, complete/fail.
- Select one orchestration approach after comparing the required checkpoint, scheduling, retry, and operational semantics; record the choice.
- Persist workflow identifiers, checkpoints, pending work, and action attempts; keep these consistent with business records.
- Bind approvals to actor, tenant, action ID, payload hash/version, expiry, and consumed state. Re-check permission and payload at execution.
- Use stable idempotency keys, action deduplication, and an outbox/dispatch design where appropriate. When the provider lacks idempotency, reconcile uncertain outcomes before resending.
- Define retryable versus permanent failures, retry budgets, cancellation, dead-letter/manual recovery, and worker ownership/leases.

## Build sequence

1. Write the state machine and a failure matrix identifying crashes before, during, and after each side effect.
2. Implement durable workflow execution over the stage 4 state model with a fake external provider.
3. Add approval pause/resume, rejection, expiry, cancellation, and stale-payload handling.
4. Implement idempotent dispatch and explicit uncertain-action reconciliation behavior.
5. Run controlled crash/restart, duplicate delivery, and approval replay scenarios, then document recovery procedures.

## Acceptance criteria

- [x] A worker stopped mid-workflow resumes from durable state without losing accepted work.
- [x] Duplicate requests/events and replayed approvals do not create duplicate logical actions in the test scenarios.
- [x] A simulated external success followed by a crash before local recording is safely deduplicated or held for reconciliation.
- [x] Tests cover revoked authorization, changed action payload, rejected/expired approvals, and exhausted retries.
- [x] A recovery report distinguishes guaranteed internal invariants from limitations of the external provider.

## Portfolio evidence to collect

Workflow diagram, orchestration decision, crash matrix, replay/recovery test report, approval trace, and reconciliation runbook.

Save generated reports under this stage's `evidence/` folder when available. Include commands, versions, dataset/configuration, date, and limitations. Link evidence from [progress](../docs/PROGRESS.md); do not create placeholder results.

## Handoff to the next stage

Recoverable end-to-end workflows and failure fixtures for systematic evaluation.

## Scope boundary

Do not claim checkpoints or a workflow engine alone guarantee exactly-once external side effects.

## Context

Read [master plan](../MASTER_PLAN.md), [root memory](../memory.md), and [stage memory](memory.md). This document describes planned work; check progress and source before assuming any capability exists.


## Implementation layout correction (2026-11-01)

The user requires code, tests and runnable entry points inside this numbered folder. See README.md and pyproject.toml. Earlier shared-root-app references are superseded by D020. Cloud deployment is deferred by the user; local verification does not satisfy cloud deployment gates.
