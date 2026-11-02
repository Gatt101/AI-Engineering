# Stage 8: Final engineering portfolio

## Objective

Package the complete system into a clear, reproducible engineering portfolio proving applied AI, agentic AI, FastAPI, and deployment skills.

## Entry requirements

Stages 1-7 completed with linked implementation, tests, reports, and deployment evidence.

These are the prerequisites for the initial flagship portfolio release. Stages [09](../09-llm-inference-engine/PLAN.md) and [10](../10-ai-evaluation-specialization/PLAN.md) are added to this portfolio when complete; they do not block its initial release.

## What to design

- Create a flagship case study explaining the problem, users, architecture, constraints, decisions, measured results, failures, and limitations.
- Present eight milestone summaries linked to project source modules, automated checks, evidence folders, and runnable Git versions when available.
- Provide architecture, data/state, and workflow diagrams that match the implemented system.
- Publish a skill-to-evidence index covering model integration, RAG, tool authorization, persistence, durable execution, evaluation, API design, and operations.
- Design a concise demo that shows a useful result, a denied unsafe action, and recovery from interruption.
- Keep portfolio materials free of credentials, private records, unverified performance claims, and unsupported security promises.

## Build sequence

1. Audit every claimed capability against source, automated tests, measured reports, and deployment behavior.
2. Write the main README, environment/setup guide, API examples, architecture narrative, and engineering case study.
3. Collect representative evaluation reports and redacted failure/recovery traces with their limitations.
4. Create a scripted API/CLI demo and optionally record a video; a separate portfolio website is optional.
5. Validate installation and the demo from a clean checkout/environment using only the documented instructions.
6. Complete a final evidence-gap review and record remaining limitations or explicitly deferred scope.

## Acceptance criteria

- [ ] A reviewer can understand the problem and architecture, reproduce offline tests, and run the documented API demo.
- [ ] All eight stage summaries identify the capability added, design choices, validation, and associated evidence.
- [ ] The portfolio shows measured quality, latency, cost where known, security-boundary tests, and failure recovery without fabricated values.
- [ ] FastAPI contracts, persistence design, CI/CD, deployment, rollback, and restoration evidence are easy to locate.
- [ ] Setup prerequisites, provider requirements, access constraints, known failures, and operating costs are disclosed.
- [ ] The final case study links every major claim to a source file, test, report, or demonstrable deployed behavior.

## Portfolio evidence to collect

Final README and case study, architecture diagrams, skill/evidence matrix, fresh-environment verification report, release reference, and demo script/recording.

Save generated reports under this stage's `evidence/` folder when available. Include commands, versions, dataset/configuration, date, and limitations. Link evidence from [progress](../docs/PROGRESS.md); do not create placeholder results.

## Handoff to the next stage

A complete flagship engineering portfolio with eight defensible milestones and an explicit maintenance/backlog plan.

## Portfolio expansion for stages 09-10

After the companion projects finish, refresh this portfolio with ten stage summaries and three coherent project narratives: the flagship application, the small inference engine, and the evaluation workbench. Link inference parity/cache benchmarks and evaluation calibration/comparison reports in the skill-to-evidence index. Record the refresh separately from the initial eight-stage release.

- [ ] Add the inference-engine case study with correctness and performance evidence.
- [ ] Add the evaluation-specialization case study with dataset methodology, judge calibration, uncertainty, and failure analysis.
- [ ] Verify the expanded ten-stage index and companion-project setup instructions; clearly identify pending work until these refresh criteria are met.

## Scope boundary

This stage packages verified engineering work; presentation polish cannot substitute for missing implementation or evidence.

## Context

Read [master plan](../MASTER_PLAN.md), [root memory](../memory.md), and [stage memory](memory.md). This document describes planned work; check progress and source before assuming any capability exists.


## Implementation layout correction (2026-11-01)

The user requires code, tests and runnable entry points inside this numbered folder. See README.md and pyproject.toml. Earlier shared-root-app references are superseded by D020. Cloud deployment is deferred by the user; local verification does not satisfy cloud deployment gates.
