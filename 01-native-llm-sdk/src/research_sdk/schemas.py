"""The public API contract; provider objects never escape directly to clients."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ResearchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    question: str = Field(min_length=1, max_length=8000)


class Usage(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class ResearchResult(BaseModel):
    request_id: str
    answer: str
    status: Literal["completed", "incomplete"]
    model: str
    usage: Usage | None = None


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    request_id: str
    error: ErrorDetail
