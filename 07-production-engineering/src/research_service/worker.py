"""Separate worker sharing the server-owned permission registry with the API."""

import argparse
import time

from research_evidence.retrieval import EvidenceService
from research_state.db import Database
from research_state.store import WorkflowStore
from research_workflows.workflows import WorkflowWorker

from research_service.auth import IdentityRegistry
from research_service.config import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    config = Settings()
    database = Database(config.database_url)
    database.validate_schema()
    try:
        while True:
            # Reload configuration each tick so removals from the identity file revoke delivery.
            identities = IdentityRegistry(Settings())
            worker = WorkflowWorker(
                WorkflowStore(database.engine),
                EvidenceService(database.engine, create_schema=False),
                authorize=identities.authorize,
            )
            worker.tick()
            if args.once:
                break
            time.sleep(1)
    finally:
        database.close()


if __name__ == "__main__":
    main()
