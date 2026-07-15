"""DOC 5 §7.2: POST /score and GET /health."""

from fastapi import APIRouter

from ..domain.scoring import ScoringEngine, ScoringInput
from .schemas import ScoreRequest, ScoreResponse

router = APIRouter()


@router.post("/score", response_model=ScoreResponse)
async def score(payload: ScoreRequest) -> ScoreResponse:
    result = ScoringEngine.evaluate(
        ScoringInput(
            application_id=payload.application_id,
            monthly_payment=payload.monthly_payment,
            monthly_income=payload.monthly_income,
            has_birth_date=payload.has_birth_date,
        )
    )
    return ScoreResponse(
        application_id=result.application_id,
        score=result.score,
        decision=result.decision,
        reason=result.reason,
    )


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}
