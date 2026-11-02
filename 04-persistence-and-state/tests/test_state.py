"""Durable records and isolation, using real SQL transactions (no database mocks)."""

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from research_state.db import Database, runs, schema_versions
from research_state.store import StateError, WorkflowStore
from sqlalchemy import insert, select, text


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


@pytest.fixture
def store(database):
    return WorkflowStore(database.engine)


def test_idempotency_conflict_and_scope(store):
    run = store.create_run("tenant", "actor", "question", "same-key")
    assert store.create_run("tenant", "actor", "question", "same-key")["id"] == run["id"]
    with pytest.raises(StateError, match="different request"):
        store.create_run("tenant", "actor", "changed question", "same-key")
    assert store.create_run("other", "actor", "question", "same-key")["id"] != run["id"]
    assert store.create_run("tenant", "other", "question", "same-key")["id"] != run["id"]
    for tenant, actor in [("other", "actor"), ("tenant", "other")]:
        with pytest.raises(StateError) as caught:
            store.get_run(tenant, actor, run["id"])
        assert caught.value.status_code == 404


def test_concurrent_duplicate_submissions_and_quota(store):
    def submit(_):
        return store.create_run("tenant", "actor", "question", "same-key")["id"]

    with ThreadPoolExecutor(max_workers=6) as pool:
        assert len(set(pool.map(submit, range(12)))) == 1
    # Existing logical requests remain retrievable even when budget is exhausted.
    store.create_run("tenant", "actor", "question", "same-key", max_pending=1)
    with pytest.raises(StateError) as caught:
        store.create_run("tenant", "another-actor", "question", "new-key", max_pending=1)
    assert caught.value.code == "queue_full"


def test_concurrent_quota_cannot_be_overbooked(store):
    def submit(index):
        try:
            store.create_run("tenant", str(index), "question", str(index), max_pending=2)
            return "accepted"
        except StateError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=6) as pool:
        outcomes = list(pool.map(submit, range(10)))
    assert outcomes.count("accepted") == 2
    assert outcomes.count("queue_full") == 8


def test_version_fence_and_cancel(store):
    run = store.create_run("tenant", "actor", "question", "key")
    with pytest.raises(StateError):
        store.cancel("tenant", "actor", run["id"], run["version"] + 1)
    assert store.cancel("tenant", "actor", run["id"], run["version"])["status"] == "cancelled"
    assert store.claim("worker") is None


def test_failed_transaction_rolls_back(store, monkeypatch):
    def fail(*_):
        raise RuntimeError("test failure")

    monkeypatch.setattr(store, "_event", fail)
    with pytest.raises(RuntimeError):
        store.create_run("tenant", "actor", "question", "key")
    assert store.list_runs("tenant", "actor") == []


def test_restart_and_backup(tmp_path):
    url = f"sqlite:///{tmp_path / 'state.db'}"
    database = Database(url, migrate=True)
    run = WorkflowStore(database.engine).create_run("tenant", "actor", "question", "key")
    backup = database.backup_sqlite(tmp_path / "backup.db")
    database.close()
    for saved_url in (url, f"sqlite:///{backup}"):
        reopened = Database(saved_url)
        assert reopened.validate_schema()
        assert (
            WorkflowStore(reopened.engine).get_run("tenant", "actor", run["id"])["status"]
            == "queued"
        )
        reopened.close()


def test_migration_previous_schema_preserves_records(tmp_path):
    database = Database(f"sqlite:///{tmp_path / 'migration.db'}")
    database.migrate(1)
    row = dict(
        id="old",
        tenant_id="tenant",
        actor_id="actor",
        idempotency_key="old",
        request_hash="0" * 64,
        question="old question",
        status="queued",
        version=1,
        created_at=1.0,
        updated_at=1.0,
        attempts=0,
    )
    with database.engine.begin() as connection:
        connection.execute(insert(runs).values(**row))
    database.migrate()
    assert database.validate_schema()
    with database.engine.connect() as connection:
        assert connection.execute(select(schema_versions.c.version)).scalars().all() == [1, 2, 3]
    assert (
        WorkflowStore(database.engine).get_run("tenant", "actor", "old")["question"]
        == "old question"
    )
    with pytest.raises(ValueError, match="downgrade"):
        database.migrate(1)
    database.close()


def test_list_is_owned_and_bounded(store):
    store.create_run("a", "actor", "question", "one")
    store.create_run("a", "actor", "question", "two")
    store.create_run("a", "other", "question", "three")
    assert len(store.list_runs("a", "actor", limit=1)) == 1
    assert len(store.list_runs("a", "actor")) == 2
    assert store.list_runs("b", "actor") == []


def test_postgresql_integration_is_explicit(database):
    if not os.environ.get("RESEARCHOPS_TEST_DATABASE_URL"):
        pytest.skip("Set RESEARCHOPS_TEST_DATABASE_URL to run these tests against PostgreSQL")
    assert database.engine.dialect.name == "postgresql"
    assert database.validate_schema()
