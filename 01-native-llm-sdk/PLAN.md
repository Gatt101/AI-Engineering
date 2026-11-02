# Stage 1: Native LLM SDK research assistant

## Objective

Build a small research-question assistant using one native model SDK and a thin FastAPI API. Prove that requests, streaming, validation, budgets, and failures are handled intentionally.

## Entry requirements

None. This is the first implementation milestone.

## What to design

- Define Pydantic request and response models: question, request ID, answer, completion status, usage when available, and normalized error details.
- Separate the FastAPI route, research service, provider adapter, settings, and logging so tests can replace the model client.
- Provide a health endpoint, a non-streaming research endpoint, and a documented streaming response contract. Handle cancellation and partial streams.
- Set explicit request deadlines, output-token limits, and bounded retry rules for transient failures. Avoid retrying invalid requests or replaying an already-emitted stream blindly.
- Log request IDs, durations, outcomes, model identifiers, and usage without logging credentials or sensitive prompts by default.

## Build sequence

1. Choose one provider and model based on actual access; record the decision and environment variable names without secrets.
2. Create the Python project, dependency lock, application modules, configuration example, and runnable local instructions.
3. Implement one non-streaming happy path, then streaming, structured errors, timeouts, and cancellation.
4. Add deterministic tests with a fake provider and a small versioned evaluation set containing normal, ambiguous, and unanswerable prompts.
5. Run an optional bounded live smoke check when credentials are available; distinguish it from mocked verification.

## Acceptance criteria

- [x] A documented CLI command starts the API, and an API/CLI client can submit a question without a browser.
- [x] Tests cover valid responses, invalid input, empty or malformed provider output, timeout, rate-limit retries, and interrupted streaming.
- [x] Retry attempts and token limits are explicit and testable; failure output does not expose secrets.
- [x] Initial evaluation cases and measured results are saved, or live measurement is explicitly marked pending with its reason.

Implementation and offline acceptance evidence: [verification](evidence/VERIFICATION.md). Live measurement is pending because no API key is configured. Read the [run/learning guide](README.md) for setup and the request walkthrough.

## Portfolio evidence to collect

API request/response examples, provider-mocked test report, redacted success/failure logs, initial evaluation dataset, and a short SDK integration note.

Save generated reports under this stage's `evidence/` folder when available. Include commands, versions, dataset/configuration, date, and limitations. Link evidence from [progress](../docs/PROGRESS.md); do not create placeholder results.

## Handoff to the next stage

A replaceable model adapter, stable research API contract, bounded request behavior, and initial tests/evaluation cases.

## Scope boundary

No retrieval, autonomous tools, durable state, or cloud deployment is required yet.

## Context

Read [master plan](../MASTER_PLAN.md), [root memory](../memory.md), and [stage memory](memory.md). This document describes planned work; check progress and source before assuming any capability exists.


## Implementation layout correction (2026-11-01)

The user requires code, tests and runnable entry points inside this numbered folder. See README.md and pyproject.toml. Earlier shared-root-app references are superseded by D020. Cloud deployment is deferred by the user; local verification does not satisfy cloud deployment gates.
