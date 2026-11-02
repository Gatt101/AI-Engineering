# AI engineering projects

Each numbered folder owns its implementation, tests, setup, run commands and evidence. The root is workspace tooling only.

```powershell
uv sync --locked --all-packages
uv run --all-packages pytest -q
```

Open a project folder and follow its README to run it individually:

- [01-native-llm-sdk](01-native-llm-sdk/README.md) — `research_sdk`
- [02-retrieval-and-evidence](02-retrieval-and-evidence/README.md) — `research_evidence`
- [03-tool-calling-agent](03-tool-calling-agent/README.md) — `research_tools`
- [04-persistence-and-state](04-persistence-and-state/README.md) — `research_state`
- [05-durable-workflows](05-durable-workflows/README.md) — `research_workflows`
- [06-evaluation-and-observability](06-evaluation-and-observability/README.md) — `research_evaluation`
- [07-production-engineering](07-production-engineering/README.md) — `research_service`
- [08-engineering-portfolio](08-engineering-portfolio/README.md) — `research_portfolio`

Stages09–10 remain planned. [Progress](docs/PROGRESS.md), [portfolio case study](08-engineering-portfolio/CASE_STUDY.md), and [decisions](docs/DECISIONS.md) distinguish implemented behavior from pending live/cloud validation.

The pre-migration implementation is preserved in a local ignored `.migration-backup/` archive. Credentials and real data belong outside source control.
