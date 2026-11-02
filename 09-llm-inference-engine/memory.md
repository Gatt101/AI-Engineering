# Stage 9 memory: Small LLM inference engine

Updated: 2026-10-28
Status: not started

## Purpose

Understand LLM internals by implementing inference for one small existing model and proving forward-pass and KV-cache correctness with reference comparisons.

## Inputs and dependencies

Python/tensor fundamentals and stage 1 concepts. Recommended after stages 1-2; completion of stage 8 is not a prerequisite. Hardware capacity, checkpoint access, model choice, and numerical tolerances remain unresolved.

## Current facts

- The user explicitly requested a small inference-engine project as folder 09.
- Only planning documents exist. No engine, downloaded weights, parity results, tests, or benchmarks exist.
- This is a separate educational project; it does not replace the flagship's native SDK integration.

## Design context to preserve

- Use existing weights and PyTorch tensor operations for the custom forward/generation path; begin with one architecture and one device.
- A tokenizer and a reference model may be reused for tokenization and comparison, but a wrapper around reference inference does not satisfy the project objective.
- Establish uncached numerical parity before KV caching and performance work. Never infer correctness from plausible generated text.
- Model training, custom GPU kernels, and production serving are optional extensions.

## Required output

A runnable small engine, reference-parity and cache correctness reports, reproducible latency/throughput/memory measurements, and an explanation of LLM internals linked into stage 8's portfolio.

## Validation state

Not run. [PLAN.md](PLAN.md) contains the acceptance criteria. Future results must include checkpoint/configuration, dtype/device, tolerance, commands, and actual outcomes.

## Open choices / blockers

Choose the model and dependency versions after inspecting hardware. No implementation blocker is established. No paid compute or model download is authorized merely by this planning document.

## Next action

When implementation is requested, inspect hardware and select a small supported architecture; define the reference comparison and tensor shapes before coding the forward pass.

## Session handoff template

- Date and scope:
- Implemented behavior and changed paths:
- Decisions accepted or revised (link `../docs/DECISIONS.md`):
- Validation commands and outcomes:
- Evidence/report locations:
- Known failures or blockers:
- Exact next action:

Keep this file factual and update [root memory](../memory.md) and [progress](../docs/PROGRESS.md) when state changes.
