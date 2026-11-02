# Stage 10: AI evaluation engineering specialization

## Objective

Build an evaluation workbench for AI applications and agents, using the flagship as its first real target. Specialize in designing trustworthy evaluations, explaining failures, and comparing versions with defensible evidence.

## Entry requirements

Stage 6 evaluation datasets, runner, baselines, and traces provide the foundation. Deep specialization is recommended after the core flagship and stage 8's initial portfolio release. Collect failures and evaluation cases from stage 1 onward. Stage 9 is an optional additional evaluation target, not a dependency.

## What to design

- Define reusable target adapters, versioned dataset schemas, run manifests, scorers, result storage, comparison reports, and regression gates. Reuse stage 6 fixtures and contracts instead of maintaining a competing copy.
- Evaluate answer correctness, abstention, retrieval, citation validity/support, tool selection/arguments, task completion, permissions, prompt injection, recovery, latency, and cost per successful task where measurable.
- Separate deterministic checks, human judgments, and model-based scoring. Use explicit rubrics and failure categories; preserve raw outcomes and score explanations for inspection.
- Version labels, provenance, splits, prompts, judge configurations, and target configurations. Separate development/calibration data from held-out evaluation; use entity/task grouping where near-duplicate cases would leak across splits.
- Design a human annotation and adjudication process. Measure disagreement; if only one annotator is available, report that limitation rather than claiming inter-annotator agreement.
- Calibrate model judges against human-labeled examples and test for position/order bias, verbosity bias, self-preference where applicable, and instruction injection inside evaluated outputs. Freeze judge/rubric choices before held-out comparisons.
- Support paired version comparisons on the same cases, repeated trials for stochastic behavior, task-level uncertainty estimates, and slices by failure type/difficulty. Avoid treating repeated samples from one case as independent tasks.
- Maintain an experiment ledger linking a hypothesis, change, dataset/configuration, result, and failure analysis. Preserve the difference between a quality improvement and a latency/cost tradeoff.

## Build sequence

1. Audit stage 6 assets and define which contracts can be generalized into a reusable workbench. Start with a CLI and machine-readable reports; a dashboard is optional.
2. Build a small human-reviewed dataset from synthetic cases and redacted flagship failures, with explicit rubrics, provenance, development/calibration/held-out splits, and failure labels.
3. Implement deterministic scorers and target adapters before model judges. Include fixtures with deliberately known defects to verify that scorers detect them.
4. Add an optional judge adapter and perform calibration and bias checks against human judgments. Report disagreement and avoid treating judge scores as ground truth.
5. Run a baseline and a candidate on paired cases, report per-slice results and uncertainty, and investigate regressions rather than publishing only a combined score.
6. Add versioned regression policies and CI checks with a fast offline tier and a separately configured, cost-bounded live tier. Record retries, missing results, and judge failures explicitly.
7. Repeat the experiment workflow on another target or task suite to demonstrate reuse; stage 9 can supply an optional correctness/performance adapter.
8. Publish an evaluation methodology case study, reproducible reports, limitations, and the updated stage 8 portfolio evidence index.

## Acceptance criteria

- [ ] A documented CLI command runs a versioned dataset against a target adapter and emits both structured results and a readable report with complete run metadata.
- [ ] The workbench reuses stage 6 assets and runs a second target/task suite without copying the evaluator implementation.
- [ ] Dataset provenance and split boundaries are documented; held-out cases are not used to tune prompts, judges, or thresholds for the reported comparison.
- [ ] Scorer tests detect known planted answer, citation, tool, and policy failures; missing/error outcomes are visible and cannot silently improve scores.
- [ ] Model-judge calibration is compared with human labels, disagreement is analyzed, and bias/injection tests are reported. If live calibration cannot run, that criterion remains pending.
- [ ] Reports include paired comparisons, relevant slices, sample sizes, repeat counts, an appropriate uncertainty method and its assumptions, and quality/latency/cost tradeoffs. Small datasets are labeled accordingly.
- [ ] At least one experiment links a measured regression to a concrete failure cause and validates a proposed fix on development data before reporting its held-out result.
- [ ] CI detects an intentionally introduced meaningful regression; thresholds are set before the candidate's evaluation and stochastic gate behavior is documented.
- [ ] The portfolio explains the evaluation system's own limitations, including label quality, judge errors, coverage gaps, and uncertainty. It does not claim universal reliability from benchmark scores.

## Portfolio evidence to collect

Dataset cards, annotation rubric, label/disagreement audit, judge-calibration and bias report, run manifests, paired comparison reports, uncertainty calculations, failure taxonomy, experiment ledger, CI regression example, and a methodological case study. Save measured artifacts in this folder's eventual `evidence/` directory and link them from [progress](../docs/PROGRESS.md).

## Handoff to the portfolio

A specialization project showing how to evaluate systems and evaluate the evaluators themselves. Update stage 8 with a separate evaluation case study, the inference project when complete, and a ten-stage skill-to-evidence index. The intended positioning is an AI engineer focused on evaluation and reliable agent systems, with hands-on inference understanding.

## Scope boundary

Stage 6 proves that the flagship is tested and observable; stage 10 develops reusable evaluation methodology and tooling across targets. A dashboard, many model integrations, or a single aggregate judge score cannot substitute for trustworthy labels and experiments. No frontend, paid annotation service, or large live benchmark is required for the initial workbench.

## Context

Read [master plan](../MASTER_PLAN.md), [root memory](../memory.md), [stage memory](memory.md), and [stage 6 plan](../06-evaluation-and-observability/PLAN.md). All capabilities and evidence are planned until verified.
