# Stage 2: Retrieval and evidence

## Objective

Answer questions from an explicit document corpus with verifiable citations and an abstention path when evidence is insufficient.

## Entry requirements

Stage 1 model adapter, API, error handling, and evaluation scaffold.

## What to design

- Create a reproducible ingestion pipeline with document identity, provenance, content hash, version, chunk offsets, and ingestion timestamps.
- Use PostgreSQL plus pgvector as the initial candidate; record embedding model, vector dimensions, index configuration, and migration strategy.
- Separate ingestion, retrieval/ranking, context assembly, and answer generation. Start with a simple baseline before adding hybrid search or a reranker.
- Represent citations with source ID and passage/offset information so links can be checked against the stored evidence.
- Treat retrieved text as untrusted data; bound context size, filter by ownership when applicable, and preserve source provenance.

## Build sequence

1. Choose a small synthetic or redistributable corpus and create answerable, unanswerable, conflicting, and stale-evidence questions.
2. Implement idempotent ingestion, chunking, embeddings, storage, and an inspectable retrieval interface.
3. Add retrieval to the research service and return cited answers with source excerpts and an insufficient-evidence result.
4. Compare a simple retrieval baseline with one justified improvement using the same versioned question set.
5. Add ingestion and retrieval tests, citation checks, and groundedness review criteria.

## Acceptance criteria

- [x] Re-ingesting unchanged documents does not create duplicate active chunks; document updates have defined replacement/version behavior.
- [x] Every citation resolves to an ingested source passage; citation support is evaluated separately from link validity.
- [x] Tests cover missing evidence, conflicting passages, malicious instructions inside documents, and bounded context assembly.
- [x] A report records retrieval recall at the chosen k, citation validity/support, dataset size, and observed failure cases without invented targets.

## Portfolio evidence to collect

Corpus manifest, ingestion commands, data schema, cited answer examples, retrieval comparison report, and groundedness failure examples.

Save generated reports under this stage's `evidence/` folder when available. Include commands, versions, dataset/configuration, date, and limitations. Link evidence from [progress](../docs/PROGRESS.md); do not create placeholder results.

## Handoff to the next stage

An evidence service and cited research output that tools and later workflows can reuse.

## Scope boundary

Do not add complex reranking or a second database without evidence that the baseline needs it.

## Context

Read [master plan](../MASTER_PLAN.md), [root memory](../memory.md), and [stage memory](memory.md). This document describes planned work; check progress and source before assuming any capability exists.


## Implementation layout correction (2026-11-01)

The user requires code, tests and runnable entry points inside this numbered folder. See README.md and pyproject.toml. Earlier shared-root-app references are superseded by D020. Cloud deployment is deferred by the user; local verification does not satisfy cloud deployment gates.
