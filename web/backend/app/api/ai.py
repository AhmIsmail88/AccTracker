# -*- coding: utf-8 -*-
"""API تحليل الصيانة بالذكاء الاصطناعي (§11/§14/§16)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.services.ai_analysis import analyze_asset, list_suggestions, review_suggestion
from app.services.llm import LLMUnavailable, get_client

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ReviewIn(BaseModel):
    status: str


@router.get("/status")
def ai_status():
    client = get_client()
    available = client.available()
    models = []
    if available:
        try:
            models = client.list_models() or []
        except LLMUnavailable:
            models = []
    return {
        "available": available,
        "model": getattr(client, "model", None),
        "models": models,
    }


@router.post("/analyze/{asset_code}")
def analyze(asset_code: str, db: Session = Depends(get_db)):
    try:
        return {"suggestion": analyze_asset(db, asset_code)}
    except LookupError:
        raise HTTPException(status_code=404, detail="asset not found")
    except LLMUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/suggestions")
def suggestions(
    asset_code: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    safe_limit = max(1, min(limit, 200))
    return list_suggestions(db, asset_code=asset_code, status=status, limit=safe_limit)


@router.patch("/suggestions/{suggestion_id}")
def review(suggestion_id: int, payload: ReviewIn, db: Session = Depends(get_db)):
    try:
        return review_suggestion(db, suggestion_id, payload.status.upper())
    except LookupError:
        raise HTTPException(status_code=404, detail="suggestion not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
