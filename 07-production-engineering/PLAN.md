# Stage 7: Production FastAPI service and deployment

## Objective

Deploy and operate the system with secure identity, tenant isolation, bounded resources, observability, and tested recovery.

## Entry requirements

Stages 1-6 working service, durable workflows, tests, and evaluation gates.

## What to design

- Harden FastAPI contracts, authentication, authorization, tenant-scoped queries, validation, error handling, and readiness/liveness behavior.
- Separate API and worker lifecycles where needed; bound concurrency, queues, database pools, timeouts, retries, and per-tenant resource budgets.
- Package repeatable Docker builds with pinned dependencies, appropriate runtime privileges, and environment-based configuration.
- Design CI/CD for tests, evaluation gates, image creation, schema migration, deployment smoke checks, and rollback.
- Use platform secret management and a managed database if appropriate; define backup, retention, restore, and release compatibility requirements.
- Choose a hosting target, identity provider, operating budget, and availability/performance targets based on actual requirements.

## Build sequence

1. Record deployment architecture, environment requirements, cloud costs/budget, and identity/tenant model before provisioning.
2. Implement production authentication and authorization end to end; carry trusted tenant context through workers, retrieval, and tool adapters.
3. Create containers, CI workflow, deployment configuration, health endpoints, and API/CLI smoke checks.
4. Deploy a staging environment, run isolation and representative concurrency/load checks, then resolve observed bottlenecks.
5. Exercise worker recovery, migration failure handling, application rollback, and database backup restoration in a safe environment.
6. Publish operating instructions and release the approved deployment with measured limitations.

## Acceptance criteria

- [ ] A documented authenticated API flow works on the deployment, including a durable workflow and result retrieval.
- [ ] Tests prove the selected tenant model prevents tested cross-tenant reads, writes, retrieval, and background-action access.
- [ ] CI validates code and evaluation gates before deployment; deployed health/readiness and smoke checks pass.
- [ ] A load report states workload, concurrency, duration, error rate, p95 latency, and resource bottlenecks against agreed targets.
- [ ] Rollback and backup restoration have recorded rehearsal evidence, including migration compatibility considerations.
- [ ] Secrets are absent from source, images, and sample traces; logs and alerts are sufficient to diagnose a failed run.

## Portfolio evidence to collect

Deployment URL/API access instructions, Docker/CI configuration, security/isolation tests, load report, cost estimate, and rollback/restore runbooks.

Save generated reports under this stage's `evidence/` folder when available. Include commands, versions, dataset/configuration, date, and limitations. Link evidence from [progress](../docs/PROGRESS.md); do not create placeholder results.

## Handoff to the next stage

An operable deployment and reproducible release process that the portfolio can demonstrate.

## Scope boundary

No Kubernetes or multi-region complexity unless measured requirements justify it. No unrestricted public write endpoints for demonstration.

## Context

Read [master plan](../MASTER_PLAN.md), [root memory](../memory.md), and [stage memory](memory.md). This document describes planned work; check progress and source before assuming any capability exists.


## Implementation layout correction (2026-11-01)

The user requires code, tests and runnable entry points inside this numbered folder. See README.md and pyproject.toml. Earlier shared-root-app references are superseded by D020. Cloud deployment is deferred by the user; local verification does not satisfy cloud deployment gates.
