# Stage 10 memory: AI evaluation engineering specialization

Updated: 2026-10-28
Status: not started

## Purpose

Make AI evaluation engineering the user's specialization through a reusable evaluation workbench, calibrated scoring, careful experiments, and failure analysis.

## Inputs and dependencies

Reuse stage 6 datasets, runner, traces, and baselines; begin collecting failures in stage 1. Deep work follows the core flagship and initial stage 8 portfolio. Stage 9 is an optional evaluation target.

## Current facts

- The user explicitly requested a separate AI evals project as folder 10 and wants to specialize in evals after the core work.
- Only the plan and this memory exist; no workbench, annotated dataset, calibrated judge, measured report, or passing test exists.
- Stage 6 remains application-specific evaluation and observability. This project expands it into reusable tooling and evaluation methodology.

## Design context to preserve

- Evaluate target-system behavior and evaluator reliability separately. Human labels and model judges both have limitations.
- Prefer a CLI, explicit schemas, adapters, scorers, and reproducible reports before UI work.
- Separate development/calibration and held-out evaluation; freeze rubrics and thresholds before reported comparisons.
- Report paired results, slices, sample sizes, repeat counts, uncertainty, and failed/missing runs. Do not hide regressions behind one average.
- Reuse stage 6 assets; demonstrate another target/task suite without duplicating the evaluator.

## Required output

A reusable workbench, versioned datasets/rubrics, calibrated judge report, failure analysis, comparison experiments, regression gates, and a specialization case study integrated into stage 8.

## Validation state

Not run. [PLAN.md](PLAN.md) defines acceptance gates. Dataset sizes, thresholds, model versions, prices, and quality scores are not yet established.

## Open choices / blockers

Dataset scope, annotator availability, judge/provider choice, statistical method, and live-evaluation budget remain open. A single-annotator setup must be disclosed. No implementation blocker is established.

## Next action

Collect real failure cases throughout earlier stages. When specialization work starts, audit stage 6 assets, define the first target/task contract, and design the labeling rubric and split policy.

## Session handoff template

- Date and scope:
- Implemented behavior and changed paths:
- Decisions accepted or revised (link `../docs/DECISIONS.md`):
- Validation commands and outcomes:
- Evidence/report locations:
- Known failures or blockers:
- Exact next action:

Keep this file factual and update [root memory](../memory.md) and [progress](../docs/PROGRESS.md) when state changes.
