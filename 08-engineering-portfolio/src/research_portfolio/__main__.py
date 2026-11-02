"""Reproduce the portfolio's API and failure-recovery demonstrations."""

import argparse
import json
import logging
from pathlib import Path

from research_service.demo import run_demo
from research_workflows.__main__ import run_demo as recovery_demo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("evidence/demo.json"))
    args = parser.parse_args()
    events = []

    class Capture(logging.Handler):
        def emit(self, record):
            events.append(json.loads(record.getMessage()))

    handler = Capture()
    logger = logging.getLogger("researchops.trace")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    report = {
        "api": run_demo(),
        "crash_recovery": recovery_demo(),
        "cloud_deployment": "deferred by user",
        "live_provider": "not measured",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.removeHandler(handler)
    args.output.with_suffix(".trace.jsonl").write_text(
        "\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
