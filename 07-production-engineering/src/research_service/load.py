"""Bounded local ASGI throughput sample; excludes network and model latency."""

import argparse
import json
import math
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

from research_service.config import Settings
from research_service.main import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("evidence/load.json"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        config = Settings(
            _env_file=None,
            demo_mode=True,
            requests_per_minute=1000,
            database_url=f"sqlite:///{Path(directory) / 'load.db'}",
        )
        with TestClient(create_app(config)) as client:

            def request(_):
                started = time.perf_counter()
                result = client.post(
                    "/v1/answers",
                    headers={"Authorization": "Bearer local-demo-token"},
                    json={"question": "Acme retention deletion"},
                )
                return (time.perf_counter() - started) * 1000, result.status_code

            started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(request, range(40)))
            duration = time.perf_counter() - started
        durations = sorted(ms for ms, _ in results)
        report = {
            "workload": "40 in-process ASGI extractive answers, SQLite",
            "concurrency": 4,
            "requests": 40,
            "duration_seconds": duration,
            "error_rate": sum(status != 200 for _, status in results) / 40,
            "p95_ms": durations[math.ceil(0.95 * len(durations)) - 1],
            "limitations": "Local regression sample; no deployment SLO or network/model benchmark.",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))


if __name__ == "__main__":
    main()
