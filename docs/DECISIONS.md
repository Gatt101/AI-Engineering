# Architecture decision ledger

Updated: 2026-10-28

Distinguish confirmed user requirements from provisional planning defaults. Change a proposal to accepted only when resolved during implementation or explicitly chosen by the user.

| ID | Status | Decision | Reason / revisit trigger |
| --- | --- | --- | --- |
| D001 | confirmed requirement | Demonstrate applied AI, agentic AI, FastAPI development, and deployment | User's portfolio goal |
| D002 | confirmed requirement | Eight stage folders, individual plans/memory, and a master plan | User's requested organization |
| D003 | planning default | Build one cumulative flagship with eight demonstrable milestones | Matches the source's progression; revisit if user wants separate products |
| D004 | proposed | ResearchOps Assistant as the working domain | Covers research, evidence, tools, drafts, approvals, and recovery; confirm before coding |
| D005 | planning default | Shared application code; stage folders hold plans and evidence | Avoid divergent implementations and duplicated maintenance |
| D006 | proposed | One native provider SDK first | Keeps stage 1 focused; select provider based on access and requirements |
| D007 | proposed | PostgreSQL and pgvector | Fits relational state and evidence retrieval; validate corpus needs in stage 2 |
| D008 | open | Workflow engine | Compare actual durability needs at stage 5; do not adopt both by default |
| D009 | open | Tracing backend | Resolve at stage 6 based on privacy, deployment, and cost constraints |
| D010 | open | Hosting, identity provider, operating budget | Resolve before stage 7 deployment |
| D011 | confirmed requirement | Extend the original eight-folder scope (D002) with 09 inference engine and 10 AI evaluation specialization | User explicitly requested both additions; original stages retained |
| D012 | planning default | Keep stages 01-08 as the flagship; scope 09 and 10 as companion projects | Refines D003/D005 without duplicating the flagship; reuse stage 06 evaluation assets |
| D013 | planning default | Stage 09 after 01-02; deep stage 10 after core portfolio; refresh stage 08 afterward | Separates folder order from learning order and avoids circular dependencies |
| D014 | proposed | Existing small-model weights, PyTorch tensor inference, reference parity before optimization | Keeps inference project focused on internals; architecture/hardware unresolved |
| D015 | confirmed requirement | AI evaluation engineering as the intended specialization | User wants deeper eval mastery after the core work |
| D016 | proposed | Reusable evaluation workbench with calibration, held-out comparisons, and uncertainty | Expands stage 06 application checks into a specialization project |

For substantial decisions add: context, alternatives, chosen option, tradeoffs, consequences, affected paths, acceptance date, and evidence. Preserve superseded decisions with their replacement references.

## D017 - Native OpenAI SDK (accepted 2026-10-28)

The user selected OpenAI for stage 01. This resolves D006. Use AsyncOpenAI's Responses API directly, one shared client per lifespan, native HTTP retries, and a total application deadline. OpenAI SDK 3.40.0 is locked. Model is configurable; the quickstart's `gpt-6-astra` is an example/default, not a verified account entitlement. No live credential configured. See `app/provider.py`, `app/service.py`, and stage 01 verification.

## D018 - Local FastAPI and learning scope (accepted 2026-10-28)

FastAPI 0.162.0, native SSE, JSON/Pydantic contracts, a terminal client, commented code, and fake-transport SDK tests satisfy the requested first project. Keep the research-assistant domain as the existing working default. Stage 01 remains local; API deployment/security is future work.

## D019 - Offline completion and live evaluation separation (accepted 2026-10-28)

All four stage 01 acceptance gates are met with 26 offline tests, a localhost smoke, a learning guide, and five evaluation cases. The final gate explicitly allows live measurement to be marked pending with its reason. No API key is configured, so live authentication, availability, quality, usage, cost, and latency are pending. Do not reinterpret the offline test count as live model-quality evidence.

## D020 — Project-owned implementation (accepted 2026-11-01)

The user explicitly rejected the root app/ structure and asked for each project inside its own numbered folder. This supersedes D003/D005/D012 and all shared-root implementation guidance. Each of 01–08 now owns a named Python package under src/, tests, pyproject.toml, executable commands, and documentation. A uv workspace shares dependency resolution only. Later packages depend on earlier packages explicitly. Original source was backed up before migration.

## D021 — Local evidence-first implementation (2026-11-01)

Use inspectable BM25 lexical retrieval before paid embeddings; PostgreSQL is supported through SQLAlchemy/psycopg, with SQLite for zero-service learning. Exact quotations and declared conflict metadata have limited semantic coverage. Use an explicit transactional workflow state machine: LangGraph adds graph execution abstractions and Temporal adds a server/worker operational model; neither is necessary for the current small checkpoint/approval flow. The action ledger and fake provider receipt reconciliation are explicit and tested. No exactly-once external delivery claim is made.

## D022 — Deployment scope and tracing (2026-11-01)

User selected local preparation and deferred cloud hosting. Stage07 includes local API, containers and operations tooling; hosted validation remains pending. Server-configured machine tokens are adequate for local staging; production SSO, gateway-wide quotas, TLS and managed secrets must be selected with hosting. Trace backend is allowlisted JSON logging, with local synthetic evidence exported under stage08. No prompts, credentials or tool arguments enter trace metadata. Production log retention/access remains an operator responsibility.
