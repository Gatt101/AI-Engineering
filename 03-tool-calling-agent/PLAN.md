# Stage 3: Tool-calling agent and permissions

## Objective

Allow the assistant to select and call tools while deterministic application code validates inputs, controls permissions, and bounds execution.

## Entry requirements

Stages 1-2 research service and retrieval tools.

## What to design

- Define a tool registry with strict argument schemas, output schemas, timeout policy, side-effect classification, and permission requirements.
- Start with evidence search, synthetic company/lead lookup, and draft creation. Represent external delivery as a fake adapter or proposed action.
- Build an explicit loop: model proposal, schema validation, policy check, execution, tool result, then next model step or final response.
- Use trusted actor/tenant context from the application boundary. Never accept a model-supplied identity, role, or tenant as authority.
- Cap tool iterations, total tokens, execution time, and result size. Audit requested, denied, failed, and completed tool calls.
- Keep approval checks outside prompts. MCP may be added only if a real integration needs interoperability.

## Build sequence

1. Write the tool catalog and actor/action/resource permission matrix before enabling tool execution.
2. Implement the registry, executor, fake adapters, and policy enforcement independently of the model loop.
3. Connect native SDK tool calls to the executor and normalize tool failures for the next model turn.
4. Add trajectory fixtures for successful tool selection, incorrect arguments, denial, and bounded repeated calls.
5. Document the boundary between drafting an action and actually executing an external side effect.

## Acceptance criteria

- [x] Malformed or unknown tool calls are rejected before adapter invocation.
- [x] Unauthorized requests and prompt-injection attempts cannot bypass tested policy boundaries.
- [x] An iteration/time budget terminates a looping agent with a structured incomplete result.
- [x] Tests verify allowed calls, denied calls, invalid arguments, tool timeouts, and correct handling of tool output as untrusted data.
- [x] No real email or other external write occurs during default tests or demos.

## Portfolio evidence to collect

Tool catalog, permission matrix, redacted tool trajectories, authorization tests, and an injection/denial demonstration.

Save generated reports under this stage's `evidence/` folder when available. Include commands, versions, dataset/configuration, date, and limitations. Link evidence from [progress](../docs/PROGRESS.md); do not create placeholder results.

## Handoff to the next stage

Validated tools, deterministic policy checks, and traceable agent runs ready for durable storage.

## Scope boundary

No mandatory MCP, A2A, multi-agent system, or live outbound integration.

## Context

Read [master plan](../MASTER_PLAN.md), [root memory](../memory.md), and [stage memory](memory.md). This document describes planned work; check progress and source before assuming any capability exists.


## Implementation layout correction (2026-11-01)

The user requires code, tests and runnable entry points inside this numbered folder. See README.md and pyproject.toml. Earlier shared-root-app references are superseded by D020. Cloud deployment is deferred by the user; local verification does not satisfy cloud deployment gates.
