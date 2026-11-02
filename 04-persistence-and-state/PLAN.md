# Stage 4: Persistence and business state

## Objective

Persist authoritative business records and pending work so state survives process restarts and concurrent requests remain consistent.

## Entry requirements

Stages 1-3 tool contracts, identities, and run behavior.

## What to design

- Model tenants/actors, research runs, briefs, drafts, proposed actions, approvals, and action attempts as needed; avoid unused entities.
- Define statuses and legal transitions, ownership constraints, timestamps, schema versions, and optimistic concurrency or locking rules.
- Use migrations, transactions, foreign keys, and unique constraints to enforce invariants. Keep network calls outside long database transactions.
- Separate conversation history and summaries from authoritative approval/action records. Never infer action completion from a chat message.
- Define request idempotency, durable pending-work records, and audit-event persistence. Workflow orchestration is completed in stage 5.

## Build sequence

1. Document entity relationships and invariants such as one logical request per idempotency key and approval tied to an exact action version.
2. Introduce migration tooling and database-backed repositories while retaining testable service boundaries.
3. Add API operations to create a run, inspect status, retrieve results, and list owned records.
4. Persist intermediate business outcomes and pending work; verify their visibility after a process restart.
5. Add real PostgreSQL integration tests for transactions, concurrent writes, ownership filtering, and migrations.

## Acceptance criteria

- [ ] After restart, stored runs, drafts, and pending actions can be queried with the same identifiers and correct status.
- [ ] Duplicate submissions and concurrent updates cannot silently create conflicting records; behavior is documented and tested.
- [ ] Tests verify cross-owner/tenant denial, rollback on failed writes, stale version rejection, and migration from the previous schema.
- [ ] Action status is derived from trusted stored records, and deleting conversation memory does not erase business truth.

## Portfolio evidence to collect

Entity diagram, migration instructions, restart demonstration, transactional/concurrency tests, and state-transition examples.

Save generated reports under this stage's `evidence/` folder when available. Include commands, versions, dataset/configuration, date, and limitations. Link evidence from [progress](../docs/PROGRESS.md); do not create placeholder results.

## Handoff to the next stage

Versioned durable entities, transactional repositories, stable run/action IDs, and ownership boundaries for workflow execution.

## Scope boundary

Surviving a restart as stored data does not yet prove automatic workflow recovery or exactly-once external effects.

## Context

Read [master plan](../MASTER_PLAN.md), [root memory](../memory.md), and [stage memory](memory.md). This document describes planned work; check progress and source before assuming any capability exists.


## Implementation layout correction (2026-11-01)

The user requires code, tests and runnable entry points inside this numbered folder. See README.md and pyproject.toml. Earlier shared-root-app references are superseded by D020. Cloud deployment is deferred by the user; local verification does not satisfy cloud deployment gates.
