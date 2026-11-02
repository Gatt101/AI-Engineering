"""Create a durable request, close the database, then verify the stored identifier."""

import json
import tempfile
from pathlib import Path

from research_state.db import Database
from research_state.store import WorkflowStore


def main():
    with tempfile.TemporaryDirectory() as directory:
        url = f"sqlite:///{Path(directory) / 'demo.db'}"
        database = Database(url, migrate=True)
        run = WorkflowStore(database.engine).create_run(
            "demo", "researcher", "Acme retention", "demo"
        )
        database.close()
        database = Database(url)
        try:
            restored = WorkflowStore(database.engine).get_run("demo", "researcher", run["id"])
            assert restored["id"] == run["id"]
            print(json.dumps({"restart_verified": True, "run": restored}, indent=2))
        finally:
            database.close()


if __name__ == "__main__":
    main()
