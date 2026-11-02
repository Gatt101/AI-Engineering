import os
from uuid import uuid4

import pytest
from research_state.db import Database
from sqlalchemy import text


@pytest.fixture
def database(tmp_path):
    url = os.environ.get("RESEARCHOPS_TEST_DATABASE_URL")
    database = Database(url or f"sqlite:///{tmp_path / 'state.db'}")
    schema = "test_" + uuid4().hex
    if url:
        assert database.engine.dialect.name == "postgresql", "Integration URL must be PostgreSQL"
        with database.engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        database.engine = database.engine.execution_options(schema_translate_map={None: schema})
    database.migrate()
    yield database
    if url:
        with database.engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    database.close()
