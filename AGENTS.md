# Workspace instructions

## User preferences

- Do not use browser tools or browser automation for my work. Use source code, CLI commands, APIs/connectors, and automated tests instead. Use a browser only if I explicitly override this preference for the specific task.

## Context loading

- Before working, read `memory.md`, `MASTER_PLAN.md`, and `docs/PROGRESS.md`.
- When working on a stage, also read that folder's `memory.md` and `PLAN.md`.
- Read `docs/DECISIONS.md` before changing the architecture. Read earlier stage plans when a dependency matters.
- These memory files are project context, not application runtime memory or proof that a feature exists. Verify implementation against source and tests.

## Working agreement

- Each numbered stage is a project and MUST own its source, tests, setup, runnable entry point, learning notes and evidence inside that stage folder. Do not create a root app/, tests/, evals/ or infra/. Later projects may depend explicitly on earlier project packages without copying their code.
- Folder numbers identify portfolio stages, not strict execution order: stage 09 can follow stages 01-02; stage 10 deepens evaluation after the core portfolio. Collect evaluation cases from stage 01 onward and refresh stage 08's portfolio as projects finish.
- Consult docs/PROGRESS.md and source for actual implementation status. Live provider measurement remains pending credentials.
- Introduce tools and infrastructure only when a stage needs them. Technology choices in the plan are provisional until recorded as accepted decisions.
- Preserve the user's work. Implement the requested stage or task without automatically starting every later stage.
- Keep secrets, real customer records, and sensitive prompts out of source control and portfolio evidence. Use synthetic examples and redacted traces.
- Keep model suggestions separate from application authorization. External writes require explicit authorization and appropriate application-level approval controls.
- At the end of meaningful work, update the active stage's `memory.md`, `docs/PROGRESS.md`, and root `memory.md` with actual outcomes, validation, blockers, and the next action. Record lasting architectural choices in `docs/DECISIONS.md`.
- Do not mark a stage complete until its acceptance criteria have evidence, or the user explicitly changes the scope and the change is documented.

## Future code organization

Use a uv workspace with project-owned src/<package>/, tests/, pyproject.toml and evidence/ inside each numbered stage. The root contains only workspace tooling, shared lockfile, project index and context documents. Do not undo the user's explicit folder preference based on older plans. Stages 09 and 10 remain unimplemented until requested.
