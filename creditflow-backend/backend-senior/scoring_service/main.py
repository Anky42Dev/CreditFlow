"""DOC 5 §7.2: CreditFlow Scoring Service — standalone FastAPI app.

Run: uvicorn scoring_service.main:app --host 0.0.0.0 --port 9000
"""

from fastapi import FastAPI

from .api.routes import router

app = FastAPI(title="CreditFlow Scoring Service", version="1.0.0")
app.include_router(router)
