"""Opt-in live evaluation: five bounded calls; outputs answers for human rubric review."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from openai import AsyncOpenAI

from research_sdk.config import Settings
from research_sdk.provider import PROMPT_VERSION, OpenAIProvider, ResearchError
from research_sdk.service import ResearchService


async def main():
    settings = Settings()
    if not settings.configured:
        raise SystemExit(
            "Set OPENAI_API_KEY locally first. This command makes five paid API calls."
        )
    rows = []
    async with AsyncOpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
        timeout=settings.request_timeout_seconds,
        max_retries=settings.openai_max_retries,
        _strict_response_validation=True,
    ) as client:
        service = ResearchService(OpenAIProvider(settings, client))
        for line in Path(__file__).with_name("cases.jsonl").read_text().splitlines():
            case = json.loads(line)
            try:
                result = await service.answer(case["question"], case["id"])
                rows.append({**case, "result": result.model_dump(), "rubric_pass": None})
            except ResearchError as exc:
                rows.append({**case, "error": exc.code, "rubric_pass": None})
    report = {
        "date": datetime.now(UTC).isoformat(),
        "dataset": "cases-v1",
        "prompt": PROMPT_VERSION,
        "model": settings.openai_model,
        "max_output_tokens": settings.max_output_tokens,
        "max_retries": settings.openai_max_retries,
        "deadline_seconds": settings.request_timeout_seconds,
        "review_status": "pending human rubric review",
        "cases": rows,
    }
    output = Path("evidence/live-evaluation.json")
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved {output}. Review each answer against its rubric; no quality score is inferred.")


if __name__ == "__main__":
    asyncio.run(main())
