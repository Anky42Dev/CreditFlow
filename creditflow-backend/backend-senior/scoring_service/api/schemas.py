"""DOC 5 §7.2: request/response schemas for POST /score."""

from decimal import Decimal

from pydantic import BaseModel, Field


class ScoreRequest(BaseModel):
    application_id: int
    monthly_payment: Decimal = Field(gt=0)
    monthly_income: Decimal | None = Field(default=None, ge=0)
    has_birth_date: bool = False


class ScoreResponse(BaseModel):
    application_id: int
    score: int
    decision: str
    reason: str
