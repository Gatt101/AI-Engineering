"""Run a reproducible tool trajectory, or opt into the native provider with --live."""

import argparse
import asyncio
import json

from openai import AsyncOpenAI
from research_evidence.retrieval import EvidenceService, seed_corpus
from research_sdk.config import Settings
from sqlalchemy import create_engine

from research_tools.agent import (
    AgentService,
    AgentTurn,
    OpenAIAgentProvider,
    ScriptedAgentProvider,
    ToolCall,
)
from research_tools.tools import Actor, build_registry


async def run(live=False):
    engine = create_engine("sqlite://")
    evidence = EvidenceService(engine)
    seed_corpus(evidence)
    settings = Settings()
    if live and not settings.configured:
        raise SystemExit("Set OPENAI_API_KEY locally before --live (paid API calls).")
    client = (
        AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.request_timeout_seconds,
            max_retries=settings.openai_max_retries,
        )
        if live
        else None
    )
    provider = (
        OpenAIAgentProvider(client, settings.openai_model)
        if live
        else ScriptedAgentProvider(
            [
                AgentTurn(
                    calls=[
                        ToolCall(
                            "search-1",
                            "evidence_search",
                            json.dumps({"question": "Acme retention deletion", "limit": 3}),
                        )
                    ]
                ),
                AgentTurn(
                    text="See the returned Acme retention passages; offline trajectory fixture."
                ),
            ]
        )
    )
    try:
        result = await AgentService(provider, build_registry(evidence)).run(
            Actor(actor_id="demo", tenant_id="demo", permissions=frozenset({"evidence:read"})),
            "What is Acme's retention policy?",
            "demo-tools",
        )
        return {"mode": "live" if live else "scripted", **result.model_dump()}
    finally:
        if client:
            await client.close()
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    print(json.dumps(asyncio.run(run(parser.parse_args().live)), indent=2))


if __name__ == "__main__":
    main()
