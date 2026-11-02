"""Explicit worker process; no outbound provider is configured."""

import argparse
import time

from research_evidence.retrieval import EvidenceService
from research_state.db import Database
from research_state.store import WorkflowStore

from research_workflows.workflows import WorkflowWorker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default="sqlite:///researchops.db")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    database = Database(args.database_url)
    database.validate_schema()
    worker = WorkflowWorker(
        WorkflowStore(database.engine), EvidenceService(database.engine, create_schema=False)
    )
    try:
        while True:
            worker.tick()
            if args.once:
                break
            time.sleep(1)
    finally:
        database.close()


if __name__ == "__main__":
    main()
