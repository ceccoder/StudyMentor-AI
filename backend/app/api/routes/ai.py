"""
AI Content Generation API Routes
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_user_optional
from app.models.models import User, SubjectProgress
from app.schemas.schemas import AIContentRequest, AIContentResponse
from app.services.ai_service import ai_service


router = APIRouter(prefix="/ai", tags=["AI Generation"])


def _extract_keys(request: Request):
    return (
        request.headers.get("x-groq-api-key"),
        request.headers.get("x-openai-api-key")
    )


@router.post("/explanation", response_model=AIContentResponse)
async def generate_explanation(
    request_data: AIContentRequest,
    raw_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Generate an AI explanation for a topic (accessible to guests and authenticated users)."""
    mastery = 0
    weak_areas = []
    if current_user and request_data.subject:
        result = await db.execute(
            select(SubjectProgress).where(
                and_(SubjectProgress.user_id == current_user.id, SubjectProgress.subject == request_data.subject)
            )
        )
        progress = result.scalar_one_or_none()
        if progress:
            mastery = progress.mastery_percentage
            weak_areas = progress.weak_areas
    
    context = request_data.context or {}
    context.update({"mastery": mastery, "weak_areas": weak_areas})
    
    groq_k, openai_k = _extract_keys(raw_request)
    ai_result = await ai_service.generate_explanation(
        subject=request_data.subject,
        topic=request_data.topic or "Fundamentals",
        level=context.get("level", "high_school"),
        custom_groq_key=groq_k,
        custom_openai_key=openai_k
    )
    
    return AIContentResponse(
        content=ai_result["explanation"],
        tokens_used=ai_result["tokens_used"],
        model_used=ai_result["model_used"]
    )


@router.post("/practice", response_model=AIContentResponse)
async def generate_practice(
    request_data: AIContentRequest,
    raw_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Generate an AI practice sprint for a topic."""
    mastery = 0
    weak_areas = []
    if current_user and request_data.subject:
        result = await db.execute(
            select(SubjectProgress).where(
                and_(SubjectProgress.user_id == current_user.id, SubjectProgress.subject == request_data.subject)
            )
        )
        progress = result.scalar_one_or_none()
        if progress:
            mastery = progress.mastery_percentage
            weak_areas = progress.weak_areas
    
    groq_k, openai_k = _extract_keys(raw_request)
    ai_result = await ai_service.generate_practice_sprint(
        subject=request_data.subject,
        topic=request_data.topic or "Fundamentals",
        mastery=mastery,
        weak_areas=weak_areas,
        custom_groq_key=groq_k,
        custom_openai_key=openai_k
    )
    
    return AIContentResponse(
        content=ai_result["practice"],
        tokens_used=ai_result["tokens_used"],
        model_used=ai_result["model_used"]
    )


@router.post("/chat")
async def chat_completion(
    request_data: AIContentRequest,
    raw_request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Chat completion with StudyMentor AI tutor."""
    message = request_data.context.get("message", "") if request_data.context else ""
    messages = [{"role": "user", "content": message}]
    
    groq_k, openai_k = _extract_keys(raw_request)
    chat_result = await ai_service.chat(
        messages=messages,
        context=request_data.context,
        custom_groq_key=groq_k,
        custom_openai_key=openai_k
    )
    
    return AIContentResponse(
        content=chat_result["content"],
        tokens_used=chat_result.get("tokens_used", 0),
        model_used=chat_result.get("model_used", "ai-mentor")
    )
