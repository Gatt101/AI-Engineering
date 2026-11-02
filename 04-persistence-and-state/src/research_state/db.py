"""Small explicit SQLAlchemy migrations, shared by API and worker processes.

SQLite is the zero-service development database. PostgreSQL uses the same Core
schema and transactions; run its integration suite before deploying it.
"""

import argparse
import sqlite3
from pathlib import Path

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    insert,
    select,
    text,
)
from sqlalchemy.pool import StaticPool

metadata = MetaData()
schema_versions = Table("schema_versions", metadata, Column("version", Integer, primary_key=True))
runs = Table(
    "workflow_runs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("tenant_id", String(100), nullable=False),
    Column("actor_id", String(100), nullable=False),
    Column("idempotency_key", String(128), nullable=False),
    Column("request_hash", String(64), nullable=False),
    Column("question", Text, nullable=False),
    Column("status", String(40), nullable=False),
    Column("version", Integer, nullable=False),
    Column("brief", JSON),
    Column("draft", JSON),
    Column("created_at", Float, nullable=False),
    Column("updated_at", Float, nullable=False),
    Column("attempts", Integer, nullable=False, default=0),
    Column("lease_owner", String(36)),
    Column("lease_until", Float),
    Column("error_code", String(80)),
    UniqueConstraint("tenant_id", "actor_id", "idempotency_key", name="uq_run_request"),
)
Index("ix_runs_pending", runs.c.status, runs.c.lease_until)
actions = Table(
    "workflow_actions",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("run_id", String(36), ForeignKey("workflow_runs.id"), nullable=False, unique=True),
    Column("tenant_id", String(100), nullable=False),
    Column("actor_id", String(100), nullable=False),
    Column("payload", JSON, nullable=False),
    Column("payload_hash", String(64), nullable=False),
    Column("version", Integer, nullable=False),
    Column("status", String(40), nullable=False),
    Column("receipt", String(100)),
    Column("created_at", Float, nullable=False),
)
approvals = Table(
    "workflow_approvals",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("action_id", String(36), ForeignKey("workflow_actions.id"), nullable=False),
    Column("tenant_id", String(100), nullable=False),
    Column("actor_id", String(100), nullable=False),
    Column("action_version", Integer, nullable=False),
    Column("payload_hash", String(64), nullable=False),
    Column("expires_at", Float, nullable=False),
    Column("consumed", Boolean, nullable=False),
    Column("created_at", Float, nullable=False),
    UniqueConstraint("action_id", "action_version", name="uq_approval_version"),
)
attempts = Table(
    "workflow_attempts",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("action_id", String(36), ForeignKey("workflow_actions.id"), nullable=False),
    Column("outcome", String(40), nullable=False),
    Column("created_at", Float, nullable=False),
)
audit_events = Table(
    "workflow_audit",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("run_id", String(36), ForeignKey("workflow_runs.id"), nullable=False),
    Column("event", String(80), nullable=False),
    Column("created_at", Float, nullable=False),
)
fake_receipts = Table(
    "fake_delivery_receipts",
    metadata,
    Column("action_id", String(36), primary_key=True),
    Column("payload_hash", String(64), nullable=False),
    Column("receipt", String(100), nullable=False),
)
MIGRATIONS = {1: [runs], 2: [actions, approvals, attempts, audit_events, fake_receipts], 3: []}
SCHEMA_VERSION = max(MIGRATIONS)


class Database:
    def __init__(self, url: str = "sqlite:///researchops.db", *, migrate: bool = False):
        options = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            options["connect_args"] = {"check_same_thread": False, "timeout": 15}
            if url in ("sqlite://", "sqlite:///:memory:"):
                options["poolclass"] = StaticPool
        else:
            options.update(pool_size=5, max_overflow=5, pool_timeout=15)
        self.engine = create_engine(url, **options)
        if self.engine.dialect.name == "sqlite":

            @event.listens_for(self.engine, "connect")
            def sqlite_options(connection, _record):
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("PRAGMA busy_timeout=15000")

        if migrate:
            self.migrate()

    def migrate(self, target_version: int = SCHEMA_VERSION) -> int:
        if target_version not in MIGRATIONS:
            raise ValueError("Unknown schema version")
        with self.engine.begin() as connection:
            if self.engine.dialect.name == "postgresql":
                connection.execute(text("SELECT pg_advisory_xact_lock(72403628)"))
            schema_versions.create(connection, checkfirst=True)
            applied = set(connection.execute(select(schema_versions.c.version)).scalars())
            if applied and max(applied) > target_version:
                raise ValueError("Schema downgrade refused; restore a compatible backup")
            for version, tables in MIGRATIONS.items():
                if version <= target_version and version not in applied:
                    metadata.create_all(connection, tables=tables)
                    if version == 3:
                        from research_evidence.retrieval import evidence_metadata

                        evidence_metadata.create_all(connection)
                    connection.execute(insert(schema_versions).values(version=version))
        return target_version

    def ready(self) -> bool:
        with self.engine.connect() as connection:
            versions = connection.execute(select(schema_versions.c.version)).scalars().all()
            return max(versions, default=0) == SCHEMA_VERSION

    def validate_schema(self):
        if not self.ready():
            raise ValueError("Database schema is not current; run the migration command")
        with self.engine.connect() as connection:
            connection.execute(select(runs.c.id).limit(1))
            connection.execute(select(approvals.c.id).limit(1))
            from research_evidence.retrieval import documents

            connection.execute(select(documents).limit(1))
        return True

    def backup_sqlite(self, destination: str | Path) -> Path:
        """SQLite backup API gives a consistent snapshot, including committed WAL data."""
        if self.engine.dialect.name != "sqlite":
            raise ValueError("Use pg_dump and a protected target for PostgreSQL backups")
        destination = Path(destination).resolve()
        source = self.engine.url.database
        if source and source != ":memory:" and Path(source).resolve() == destination:
            raise ValueError("Backup destination must differ from the live database")
        if destination.exists():
            raise ValueError("Backup destination already exists")
        with self.engine.connect() as connection:
            raw = connection.connection.driver_connection
            with sqlite3.connect(destination) as target:
                raw.backup(target)
        return destination

    def close(self):
        self.engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default="sqlite:///researchops.db")
    parser.add_argument("--backup")
    args = parser.parse_args()
    database = Database(args.database_url, migrate=True)
    try:
        if args.backup:
            database.backup_sqlite(args.backup)
        print(f"Schema {SCHEMA_VERSION} ready")
    finally:
        database.close()


if __name__ == "__main__":
    main()
