> Historical 2026-10-28 evidence below used the old root layout. Current source is ../src/research_sdk/ and current commands are in ../README.md; current folder-local tests.xml replaces its test run.

# Stage 01 verification

Date: 2026-10-28. Environment: Windows, Python 3.14.0, OpenAI SDK 3.40.0, FastAPI 0.162.0, pytest 9.2.0. Exact dependencies: root `uv.lock`.

## Automated results

- `.venv\Scripts\python.exe -m pytest -q --junitxml=01-native-llm-sdk/evidence/tests.xml`: **26 passed**, 4.76 seconds. The XML contains the individual cases.
- `.venv\Scripts\ruff.exe check app tests evals`: passed.
- `.venv\Scripts\ruff.exe format --check app tests evals`: passed (10 files).
- Temporary localhost Uvicorn server: health returned `ok` and `provider_configured: false`. `python -m app.cli "What is an LLM?"` returned exit code 1 and `not_configured`, as intended. See `local-smoke.json`. The server was stopped afterward.

Tests use the real OpenAI SDK with fake HTTP responses, including native request parameters, SDK retries, rate-limit recovery/exhaustion, non-retryable auth/input errors, provider failures, malformed/empty output, refusal, incomplete status, total deadline including backoff, connection failure, streaming interruption/error, cancellation cleanup, redacted structured logs, input validation, missing-key behavior, API serialization, and SSE serialization.

Illustrative structured log from a mocked success (usage is synthetic):

```json
{"request_id":"id","duration_ms":1.0,"outcome":"completed","model":"configured-model","usage":{"input_tokens":10,"output_tokens":6,"total_tokens":16}}
```

The logging test verifies parseable JSON fields and absence of the private test question. Exact durations are environment-dependent and are not a model latency benchmark.

## Evaluation status and limits

`evals/cases.jsonl` is dataset `cases-v1`, five examples. Prompt version: `stage01-v1`. The initial live evaluation is **pending because no API key is configured**. `python -m evals.run` is an opt-in runner with token/deadline/retry limits that saves answers and leaves rubric scores pending human review.

No live provider authentication, model access, generated-answer quality, live token usage, API latency, or dollar cost has been measured. Offline tests verify integration behavior and do not establish model quality. No paid API calls were made.

Official quickstart, streaming, and library pages were fetched through CLI HTTPS; links and learning instructions are in `../README.md`. Installed SDK source was inspected for current types/retries. This release is a local learning service; authentication, retrieval, persistence, and deployment belong to later stages.
