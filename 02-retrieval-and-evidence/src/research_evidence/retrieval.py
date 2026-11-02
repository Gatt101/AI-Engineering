"""Versioned evidence and bounded, inspectable lexical retrieval.

This baseline returns quotations, not model-generated assertions. Retrieved text is
always untrusted data. The instruction heuristic is defense in depth, not a prompt
injection detector or an authorization boundary.
"""

import argparse
import hashlib
import json
import math
import re
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import (
    Column,
    ForeignKeyConstraint,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    and_,
    create_engine,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

CORPUS_VERSION = "synthetic-researchops-v1"
RETRIEVAL_VERSION = "lexical-bm25-v1"
CORPUS_PATH = Path(__file__).resolve().parent / "data" / "documents.json"
CASES_PATH = Path(__file__).resolve().parent / "data" / "retrieval_cases.jsonl"
STOPWORDS = frozenset(
    "a an and are as at be by can do does for from how i in is it me of on or our "
    "please provide research show tell that the their this to what when which who with "
    "would you your about according much many has have will should".split()
)
INSTRUCTION_PATTERN = re.compile(
    r"ignore\s+(all\s+)?(previous|prior|system)|system\s+prompt|"
    r"send\s+(the\s+)?(secret|password|api.?key)|override\s+(permissions|policy)",
    re.IGNORECASE,
)

evidence_metadata = MetaData()
documents = Table(
    "evidence_documents",
    evidence_metadata,
    Column("tenant_id", String(128), primary_key=True),
    Column("source_id", String(128), primary_key=True),
    Column("current_version", Integer, nullable=False),
)
versions = Table(
    "evidence_versions",
    evidence_metadata,
    Column("tenant_id", String(128), primary_key=True),
    Column("source_id", String(128), primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("title", String(400), nullable=False),
    Column("source_uri", String(1000), nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("record_hash", String(64), nullable=False),
    Column("text", Text, nullable=False),
    Column("claims_json", Text, nullable=False),
    Column("expires_at", String(40), nullable=True),
    Column("ingested_at", String(40), nullable=False),
    ForeignKeyConstraint(
        ["tenant_id", "source_id"],
        ["evidence_documents.tenant_id", "evidence_documents.source_id"],
    ),
)
chunks = Table(
    "evidence_chunks",
    evidence_metadata,
    Column("tenant_id", String(128), primary_key=True),
    Column("source_id", String(128), primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("start", Integer, primary_key=True),
    Column("end", Integer, nullable=False),
    Column("text", Text, nullable=False),
    ForeignKeyConstraint(
        ["tenant_id", "source_id", "version"],
        ["evidence_versions.tenant_id", "evidence_versions.source_id", "evidence_versions.version"],
    ),
)


class DocumentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenant_id: str = Field(min_length=1, max_length=128)
    source_id: str = Field(min_length=1, max_length=128, pattern=r"^[\w.-]+$")
    title: str = Field(min_length=1, max_length=400)
    text: str = Field(min_length=1, max_length=200_000)
    source_uri: str = Field(default="synthetic://local", max_length=1000)
    expires_at: str | None = None
    claims: dict[str, str] = Field(default_factory=dict, max_length=20)

    @field_validator("text", "title", "tenant_id")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value must not be blank")
        return value

    @field_validator("source_uri")
    @classmethod
    def allowed_uri(cls, value: str) -> str:
        if not value.startswith(("synthetic://", "https://", "http://")):
            raise ValueError("Source URI must use synthetic, https or http")
        return value

    @field_validator("expires_at")
    @classmethod
    def aware_expiry(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("Expiry must include timezone")
        return parsed.astimezone(UTC).isoformat()

    @field_validator("claims")
    @classmethod
    def bounded_claims(cls, value: dict[str, str]) -> dict[str, str]:
        if any(
            not k.strip() or len(k) > 100 or not v.strip() or len(v) > 200 for k, v in value.items()
        ):
            raise ValueError("Claim keys/values exceed bounds")
        return value


class IngestResult(BaseModel):
    source_id: str
    version: int
    content_hash: str
    chunks: int
    changed: bool


class Passage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    version: int
    title: str
    source_uri: str
    content_hash: str
    ingested_at: str
    start: int
    end: int
    text: str
    score: float = 0
    stale: bool = False
    suspicious: bool = False
    untrusted: Literal[True] = True
    claims: dict[str, str] = Field(default_factory=dict)


class EvidenceAnswer(BaseModel):
    status: Literal["answered", "insufficient_evidence", "conflicting_evidence"]
    answer: str
    citations: list[Passage] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    mode: Literal["extractive"] = "extractive"


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[^\W_]+", text.casefold()) if t not in STOPWORDS]


def _identity(tenant_id: str) -> None:
    if not isinstance(tenant_id, str) or not tenant_id.strip() or len(tenant_id) > 128:
        raise ValueError("Invalid tenant identity")


def _chunks(text: str, size: int):
    """Prefer whitespace boundaries while retaining exact Python-character offsets."""
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + size // 2, end)
            if boundary > start:
                end = boundary + 1
        yield start, end, text[start:end]
        start = end


class EvidenceService:
    def __init__(
        self,
        engine: Engine,
        *,
        max_context_chars: int = 6000,
        chunk_chars: int = 900,
        create_schema: bool = True,
    ):
        if not 128 <= max_context_chars <= 20_000 or not 64 <= chunk_chars <= 4000:
            raise ValueError("Invalid evidence bounds")
        self.engine = engine
        self.max_context_chars = max_context_chars
        self.chunk_chars = chunk_chars
        if create_schema:
            evidence_metadata.create_all(engine)

    def ingest(
        self,
        tenant_id: str,
        source_id: str,
        title: str,
        text: str,
        source_uri: str = "synthetic://local",
        *,
        expires_at: str | None = None,
        claims: dict[str, str] | None = None,
    ) -> IngestResult:
        doc = DocumentInput(
            tenant_id=tenant_id,
            source_id=source_id,
            title=title,
            text=text,
            source_uri=source_uri,
            expires_at=expires_at,
            claims=claims or {},
        )
        digest = hashlib.sha256(doc.text.encode()).hexdigest()
        record_hash = hashlib.sha256(
            json.dumps(doc.model_dump(), sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        pieces = list(_chunks(doc.text, self.chunk_chars))
        key = and_(documents.c.tenant_id == tenant_id, documents.c.source_id == source_id)
        # A unique version key and compare-and-swap protect concurrent writers. The
        # losing transaction rolls back all inserted chunks and retries from the head.
        for attempt in range(3):
            try:
                with self.engine.begin() as conn:
                    head = (
                        conn.execute(select(documents).where(key).with_for_update())
                        .mappings()
                        .first()
                    )
                    current_version = head["current_version"] if head else 0
                    if head:
                        current = (
                            conn.execute(
                                select(versions).where(
                                    versions.c.tenant_id == tenant_id,
                                    versions.c.source_id == source_id,
                                    versions.c.version == current_version,
                                )
                            )
                            .mappings()
                            .one()
                        )
                        if current["record_hash"] == record_hash:
                            return IngestResult(
                                source_id=source_id,
                                version=current_version,
                                content_hash=digest,
                                chunks=len(pieces),
                                changed=False,
                            )
                    version = current_version + 1
                    if not head:
                        conn.execute(
                            insert(documents).values(
                                tenant_id=tenant_id,
                                source_id=source_id,
                                current_version=version,
                            )
                        )
                    conn.execute(
                        insert(versions).values(
                            tenant_id=tenant_id,
                            source_id=source_id,
                            version=version,
                            title=doc.title,
                            source_uri=doc.source_uri,
                            content_hash=digest,
                            record_hash=record_hash,
                            text=doc.text,
                            claims_json=json.dumps(doc.claims, sort_keys=True),
                            expires_at=doc.expires_at,
                            ingested_at=datetime.now(UTC).isoformat(),
                        )
                    )
                    conn.execute(
                        insert(chunks),
                        [
                            {
                                "tenant_id": tenant_id,
                                "source_id": source_id,
                                "version": version,
                                "start": start,
                                "end": end,
                                "text": value,
                            }
                            for start, end, value in pieces
                        ],
                    )
                    if head:
                        changed = conn.execute(
                            update(documents)
                            .where(
                                key,
                                documents.c.current_version == current_version,
                            )
                            .values(current_version=version)
                        )
                        if changed.rowcount != 1:
                            raise IntegrityError("concurrent ingestion", {}, None)
                return IngestResult(
                    source_id=source_id,
                    version=version,
                    content_hash=digest,
                    chunks=len(pieces),
                    changed=True,
                )
            except IntegrityError:
                if attempt == 2:
                    raise ValueError("Concurrent document update; retry ingestion") from None
        raise AssertionError("unreachable")

    @staticmethod
    def _passage(row, start: int, end: int, text: str, score: float = 0) -> Passage:
        expiry = row["expires_at"]
        return Passage(
            source_id=row["source_id"],
            version=row["version"],
            title=row["title"],
            source_uri=row["source_uri"],
            content_hash=row["content_hash"],
            ingested_at=row["ingested_at"],
            start=start,
            end=end,
            text=text,
            score=round(score, 6),
            stale=bool(expiry and datetime.fromisoformat(expiry) <= datetime.now(UTC)),
            suspicious=bool(INSTRUCTION_PATTERN.search(text)),
            claims=json.loads(row["claims_json"]),
        )

    def resolve(
        self, tenant_id: str, source_id: str, version: int, start: int, end: int
    ) -> Passage | None:
        """Resolve immutable old versions too; never reveal another tenant's source."""
        _identity(tenant_id)
        if start < 0 or end <= start or version < 1 or end - start > self.max_context_chars:
            return None
        with self.engine.connect() as conn:
            row = (
                conn.execute(
                    select(versions).where(
                        versions.c.tenant_id == tenant_id,
                        versions.c.source_id == source_id,
                        versions.c.version == version,
                    )
                )
                .mappings()
                .first()
            )
        if row is None or end > len(row["text"]):
            return None
        return self._passage(row, start, end, row["text"][start:end])

    def search(
        self,
        tenant_id: str,
        question: str,
        limit: int = 5,
        *,
        method: Literal["overlap", "bm25"] = "bm25",
        include_stale: bool = False,
    ) -> list[Passage]:
        _identity(tenant_id)
        if not isinstance(question, str) or not question.strip() or len(question) > 8000:
            raise ValueError("Question must contain 1-8000 characters")
        if type(limit) is not int or not 1 <= limit <= 20 or method not in ("overlap", "bm25"):
            raise ValueError("Invalid retrieval parameters")
        query = set(_tokens(question))
        if not query:
            return []
        joined = chunks.join(
            versions,
            and_(
                chunks.c.tenant_id == versions.c.tenant_id,
                chunks.c.source_id == versions.c.source_id,
                chunks.c.version == versions.c.version,
            ),
        ).join(
            documents,
            and_(
                documents.c.tenant_id == versions.c.tenant_id,
                documents.c.source_id == versions.c.source_id,
                documents.c.current_version == versions.c.version,
            ),
        )
        with self.engine.connect() as conn:
            rows = (
                conn.execute(
                    select(
                        versions.c.source_id,
                        versions.c.version,
                        versions.c.title,
                        versions.c.source_uri,
                        versions.c.content_hash,
                        versions.c.ingested_at,
                        versions.c.expires_at,
                        versions.c.claims_json,
                        chunks.c.start,
                        chunks.c.end,
                        chunks.c.text,
                    )
                    .select_from(joined)
                    .where(chunks.c.tenant_id == tenant_id)
                    .limit(10_001)
                )
                .mappings()
                .all()
            )
        if len(rows) > 10_000:
            raise ValueError("Corpus exceeds lexical baseline capacity; use an indexed retriever")
        candidates = [self._passage(r, r["start"], r["end"], r["text"]) for r in rows]
        candidates = [p for p in candidates if include_stale or not p.stale]
        if not candidates:
            return []
        token_counts = [Counter(_tokens(p.text)) for p in candidates]
        frequencies = Counter(t for counts in token_counts for t in counts)
        average_length = sum(sum(c.values()) for c in token_counts) / len(candidates) or 1
        ranked = []
        for passage, counts in zip(candidates, token_counts, strict=True):
            if method == "overlap":
                score = len(query.intersection(counts)) / len(query)
            else:
                length = sum(counts.values())
                score = sum(
                    math.log(1 + (len(candidates) - frequencies[t] + 0.5) / (frequencies[t] + 0.5))
                    * counts[t]
                    * 2.2
                    / (counts[t] + 1.2 * (0.25 + 0.75 * length / average_length))
                    for t in query
                    if counts[t]
                )
            if score > 0:
                ranked.append(passage.model_copy(update={"score": round(score, 6)}))
        ranked.sort(key=lambda p: (-p.score, p.source_id, p.start))
        selected = []
        remaining = self.max_context_chars
        for passage in ranked[:limit]:
            if remaining <= 0:
                break
            text = passage.text[:remaining]
            selected.append(
                passage.model_copy(update={"text": text, "end": passage.start + len(text)})
            )
            remaining -= len(text)
        return selected

    def answer(self, tenant_id: str, question: str, limit: int = 5) -> EvidenceAnswer:
        passages = self.search(tenant_id, question, limit)
        warnings = ["Extractive lexical baseline; semantic answer support has not been assessed."]
        safe = [p for p in passages if not p.suspicious]
        if len(safe) < len(passages):
            warnings.append("Instruction-like source text was excluded from the brief.")
        query = set(_tokens(question))
        # Deliberately conservative lexical coverage, not a confidence probability.
        relevant = [
            p for p in safe if len(query.intersection(_tokens(p.text))) / max(len(query), 1) >= 0.6
        ]
        if not relevant:
            if self.search(tenant_id, question, limit, include_stale=True):
                warnings.append(
                    "Matches may be expired, instruction-like, or only weak lexical matches."
                )
            return EvidenceAnswer(
                status="insufficient_evidence",
                answer="Insufficient current evidence.",
                warnings=warnings,
            )
        values: dict[str, set[str]] = {}
        for passage in relevant:
            for key, value in passage.claims.items():
                values.setdefault(key, set()).add(value)
        conflicting = sorted(key for key, choices in values.items() if len(choices) > 1)
        excerpts = "\n\n".join(
            f"[{p.source_id}@{p.version}:{p.start}-{p.end}]\n{p.text}" for p in relevant
        )
        if conflicting:
            warnings.append("Conflicting declared source claims: " + ", ".join(conflicting))
            return EvidenceAnswer(
                status="conflicting_evidence",
                answer="Sources disagree; review required.\n\n" + excerpts,
                citations=relevant,
                warnings=warnings,
            )
        return EvidenceAnswer(
            status="answered",
            answer="Source excerpts (untrusted data):\n\n" + excerpts,
            citations=relevant,
            warnings=warnings,
        )


def seed_corpus(service: EvidenceService, tenant_id: str = "demo") -> list[IngestResult]:
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    return [service.ingest(tenant_id=tenant_id, **doc) for doc in corpus["documents"]]


def evaluate_retrieval(
    service: EvidenceService | None = None, tenant_id: str = "evaluation"
) -> dict:
    """Measure labeled synthetic cases; never equate quote validity with semantic correctness."""
    owned_engine = None
    if service is None:
        owned_engine = create_engine("sqlite://")
        service = EvidenceService(owned_engine)
    try:
        seed_corpus(service, tenant_id)
        cases = [
            json.loads(line)
            for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        rows = []
        for case in cases:
            started = time.perf_counter()
            overlap = service.search(tenant_id, case["question"], limit=1, method="overlap")
            bm25 = service.search(tenant_id, case["question"], limit=1)
            answer = service.answer(tenant_id, case["question"])
            expected = set(case["relevant_sources"])
            valid_citations = sum(
                (resolved := service.resolve(tenant_id, p.source_id, p.version, p.start, p.end))
                is not None
                and resolved.text == p.text
                and resolved.content_hash == p.content_hash
                for p in answer.citations
            )
            support = all(
                any(label in p.text for p in answer.citations) for label in case["support_quotes"]
            )
            rows.append(
                {
                    "id": case["id"],
                    "split": case["split"],
                    "expected_status": case["expected_status"],
                    "actual_status": answer.status,
                    "task_success": answer.status == case["expected_status"] and support,
                    "overlap_recall_at_1": len(expected & {p.source_id for p in overlap})
                    / len(expected)
                    if expected
                    else None,
                    "bm25_recall_at_1": len(expected & {p.source_id for p in bm25}) / len(expected)
                    if expected
                    else None,
                    "citation_count": len(answer.citations),
                    "valid_citation_count": valid_citations,
                    "citations_valid": valid_citations == len(answer.citations),
                    "support_expected": bool(case["support_quotes"]),
                    "labeled_quote_support": support,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                }
            )
        measured = [r for r in rows if r["bm25_recall_at_1"] is not None]
        durations = sorted(r["duration_ms"] for r in rows)
        return {
            "dataset_version": CORPUS_VERSION,
            "retrieval_version": RETRIEVAL_VERSION,
            "generated_at": datetime.now(UTC).isoformat(),
            "sample_size": len(rows),
            "model": None,
            "usage": None,
            "cost": None,
            "mode": "offline-extractive",
            "summary": {
                "task_success_rate": sum(r["task_success"] for r in rows) / len(rows),
                "overlap_recall_at_1": sum(r["overlap_recall_at_1"] for r in measured)
                / len(measured),
                "bm25_recall_at_1": sum(r["bm25_recall_at_1"] for r in measured) / len(measured),
                "retrieval_sample_size": len(measured),
                "citation_count": sum(r["citation_count"] for r in rows),
                "citation_validity_rate": sum(r["valid_citation_count"] for r in rows)
                / max(sum(r["citation_count"] for r in rows), 1),
                "labeled_quote_support_rate": sum(
                    r["labeled_quote_support"] for r in rows if r["support_expected"]
                )
                / max(sum(r["support_expected"] for r in rows), 1),
                "p50_ms": durations[len(durations) // 2],
                "p95_ms": durations[math.ceil(len(durations) * 0.95) - 1],
            },
            "cases": rows,
            "limitations": [
                "Small synthetic author-labeled dataset; no independent human review "
                "or live model quality measurement.",
                "Quote support checks exact expected spans; it is separate from citation "
                "resolution and is not semantic entailment.",
                "Lexical matching misses paraphrases. Conflict detection uses explicit "
                "claims metadata, not arbitrary contradiction reasoning.",
                "BM25 compared with overlap at k=1 on answerable fresh cases; "
                "exclusion cases are scored separately.",
            ],
        }
    finally:
        if owned_engine:
            owned_engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = evaluate_retrieval()
    output = json.dumps(report, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
