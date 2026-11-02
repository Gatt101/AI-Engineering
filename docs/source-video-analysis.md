# Video Analysis: Agentic Engineering Roadmap For Beginners

[Learn AI Agents For FREE From These Github Repos | by Ramakrushna Mohapatra | Medium](https://images.openai.com/static-rsc-4/b0w5KSDMNTDIihzUaaimzz_rEsCrT0OPfh1PVhqJOiI9VwtKx_ASzKZZjihtjf4vRFaQm10hSF3TvnFFaY0cVXd2VPpSKy6o5z1hJQsT2n55kOesSDORgPG3lfK76-lcNq-YNqyDx2DsixVyPwDSfbHUjfKj03eXsMQeWlG2uto?purpose=inline)

Creator: Ayush Singh

Published: October 26, 2026

Duration: 16 minutes, 43 seconds

[Watch original video](https://www.youtube.com/watch?v=dt1eK_4rCAM\&utm_source=chatgpt.com)

I've reviewed the video's transcript, including its eight-project learning roadmap.

My assessment: This is a strong roadmap for learning how to engineer reliable AI agents, rather than merely learning agent frameworks. Its biggest strength is that it emphasizes engineering fundamentals, failure recovery, evaluation, and production deployment.

The central argument is that knowing LangGraph, MCP, vector databases, or an LLM SDK individually does not automatically make someone a competent Agentic AI Engineer.

Instead, the presenter proposes building one application that evolves through eight stages, introducing each engineering concept when the system needs it.

## 1. The eight-stage roadmap explained

1

Native LLM SDK

1:14

Build a basic research assistant using the OpenAI or Anthropic SDK. Understand requests, responses, token limits, streaming, timeouts, retries, and structured logging.

Python · Model SDK · Logging · Tests

2

Retrieval and evidence

3:16

Connect the assistant to external knowledge, retrieve relevant passages, rank evidence, provide citations, and test whether answers are grounded.

Search · Embeddings · PostgreSQL · pgvector

3

Tool-calling agent

5:02

Allow the assistant to search companies, query lead records, draft emails, and request actions. Validate arguments and enforce permissions before execution.

Function calling · MCP · Authorization

4

Persistence and state

7:33

Store business state, completed work, and pending actions so the system can resume after users leave or servers restart.

PostgreSQL · Transactions · Pydantic

5

Durable workflows

9:21

Create multi-step processes with branching, checkpoints, interruption handling, retries, and human approval before external actions.

LangGraph · Temporal · Checkpointing

6

Evaluation and observability

10:37

Test factual accuracy, retrieval, citations, tool selection, unauthorized actions, prompt injection, latency, and token cost. Add tracing.

Evaluation datasets · Langfuse · Tracing

7

Production engineering

12:14

Deploy a secure service with authentication, tenant isolation, validation, secret management, CI/CD, monitoring, and operational recovery.

FastAPI · Docker · GitHub Actions

8

Final engineering portfolio

13:40

Combine the entire system into a documented, reproducible project with automated tests, evaluation baselines, architecture diagrams, and failure traces.

GitHub · Architecture docs · Test reports

Notice that stage 8 is primarily about demonstrating engineering quality, rather than introducing another technical capability.

The learning model is sensible: each stage adds something that the previous version of the agent cannot reliably accomplish.

## 2. What the video gets right

The strongest point is at [6:19](https://www.youtube.com/watch?v=dt1eK_4rCAM\&t=379s\&utm_source=chatgpt.com): the model proposes an action, but the application determines whether that action is permitted.

This is fundamental to production agent engineering. An LLM should not be trusted to enforce its own permissions. Authorization, argument validation, approval integrity, and tenant boundaries belong in deterministic application code.

Three other particularly valuable ideas are:

- Evidence quality matters more than the vector database. RAG effectiveness depends on retrieving correct, relevant, current information, not simply generating embeddings.
- Agent memory is not the same as business state. A conversation summary might remember what a customer said, but a persisted workflow record determines whether an email was actually sent or an approval was granted.
- A successful demo is not proof of reliability. An agent needs reproducible tests, failure traces, monitoring, and measurable performance before deployment.

I especially agree with the presenter's recommendation not to introduce Kubernetes or complex infrastructure merely to make an architecture look sophisticated.

## 3. What I would improve in this roadmap

| Area              | My assessment                                                                                                                    |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Evaluation        | Should begin at stage 1 and mature throughout development, not first appear at stage 6                                           |
| Security          | Authorization and tool boundaries should be designed before enabling actions, rather than treated mainly as production hardening |
| MCP and A2A       | Useful interoperability protocols, but neither is mandatory to build a reliable agent                                            |
| Durable execution | Checkpointing alone does not prevent duplicate external actions                                                                  |
| Scalability       | Needs more concrete discussion of concurrency, queues, worker isolation, backpressure, and resource budgets                      |

One important technical nuance: LangGraph checkpointing and Temporal durable execution are not interchangeable with exactly-once side-effect guarantees. If a worker successfully sends an email but crashes before recording success, retrying can send the email again. You need idempotency, deduplication, or reconciliation strategies. Both frameworks document the importance of handling repeated execution.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://langchain-ai.github.io\&sz=32)

Docs by LangChain+1



Similarly, MCP standardizes access to tools and resources, while A2A is designed for communication between independent agents. They address different requirements.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://a2a-protocol.org\&sz=32)

a2a-protocol.org



The video also doesn't provide a complete coding tutorial. It describes what to build, why to build it, and what technologies to explore, but it doesn't demonstrate all the implementations.

## 4. How useful is this roadmap for your current level?

Given your existing work with FastAPI, PostgreSQL, AI agent harnesses, healthcare agents, and the certification platform, I wouldn't recommend following the entire roadmap from zero.

You already have practical exposure to several of its foundational stages. Your biggest opportunity is to demonstrate that the systems you've built are measurably reliable, recoverable, secure, and observable.

## Suggested priorities for you

Agent evaluation engineering

Highest

Build automated datasets, trajectory tests, tool-call checks, hallucination assessments, and regression gates.

Durable execution and failure recovery

Highest

Practice checkpoint semantics, idempotency, transaction boundaries, worker crashes, and restart recovery.

Production backend fundamentals

High

Continue PostgreSQL transactions, connection pooling, queues, background workers, auth, and observability.

Agent security

High

Test prompt injection, permission escalation, approval replay, cross-tenant access, and tool misuse.

Native LLM SDK and RAG foundations

Refresh

Revisit implementation details where needed rather than rebuilding introductory demos.

Relative learning priorities based on your projects, not measured skill scores.

## 5. One practical project I'd recommend

Instead of building the video's sales assistant, you could apply the same engineering principles to your AI certification assessment workflow.

### Production-grade assessment agent

Candidate intake

Assessment generation

Validation and approval

Sandbox execution

Evidence evaluation

Certificate decision

Then prove the architecture through reproducible tests. For example, kill the worker halfway through assessment generation and verify that it resumes correctly; submit the same request twice and verify that duplicate assessments aren't created; attempt an unauthorized approval and verify that the action is blocked.

Finally, measure task success rate, tool-call correctness, recovery success, p95 latency, and cost per completed assessment.

That is stronger evidence of engineering capability than simply demonstrating a multi-agent application.

## Final verdict

# 8.5/10

My rating as a learning roadmap

Excellent architectural direction, particularly for engineers transitioning from basic LLM integrations to reliable agent systems. Limited implementation depth.

My recommendation: Use this video's eight stages as an engineering checklist, not as eight new projects you must complete. For your progression toward Applied AI Engineer roles, stages 5–7—durability, evaluation, and production reliability—offer the greatest immediate value.

The most important change in mindset is this: don't ask only “Can my agent complete the task?” Ask “Can I prove it completes the task correctly, handles failures, respects permissions, and remains reliable under real operating conditions?”&#x20;