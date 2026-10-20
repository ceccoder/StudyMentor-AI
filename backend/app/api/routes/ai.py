"""
AI Content Generation API Routes
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.models import User, SubjectProgress
from app.schemas.schemas import AIContentRequest, AIContentResponse
from app.services.ai_service import ai_service


router = APIRouter(prefix="/ai", tags=["AI Generation"])


@router.post("/explanation", response_model=AIContentResponse)
async def generate_explanation(
    request: AIContentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate an AI explanation for a topic."""
    
    # Get user's progress for context
    mastery = 0
    weak_areas = []
    if request.subject:
        result = await db.execute(
            select(SubjectProgress).where(
                and_(SubjectProgress.user_id == current_user.id, SubjectProgress.subject == request.subject)
            )
        )
        progress = result.scalar_one_or_none()
        if progress:
            mastery = progress.mastery_percentage
            weak_areas = progress.weak_areas
    
    context = request.context or {}
    context.update({"mastery": mastery, "weak_areas": weak_areas})
    
    ai_result = await ai_service.generate_explanation(
        subject=request.subject,
        topic=request.topic or "General",
        level=context.get("level", "high_school")
    )
    
    return AIContentResponse(
        content=ai_result["explanation"],
        tokens_used=ai_result["tokens_used"],
        model_used=ai_result["model_used"]
    )


@router.post("/practice", response_model=AIContentResponse)
async def generate_practice(
    request: AIContentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate an AI practice sprint for a topic."""
    
    mastery = 0
    weak_areas = []
    if request.subject:
        result = await db.execute(
            select(SubjectProgress).where(
                and_(SubjectProgress.user_id == current_user.id, SubjectProgress.subject == request.subject)
            )
        )
        progress = result.scalar_one_or_none()
        if progress:
            mastery = progress.mastery_percentage
            weak_areas = progress.weak_areas
    
    ai_result = await ai_service.generate_practice_sprint(
        subject=request.subject,
        topic=request.topic or "General",
        mastery=mastery,
        weak_areas=weak_areas
    )
    
    return AIContentResponse(
        content=ai_result["practice"],
        tokens_used=ai_result["tokens_used"],
        model_used=ai_result["model_used"]
    )


@router.post("/chat")
async def chat_completion(
    request: AIContentRequest,
    current_user: User = Depends(get_current_user)
):
    """Non-streaming chat completion (for simple requests)."""
    from app.schemas.schemas import WSChatMessage
    
    messages = [{"role": "user", "content": request.context.get("message", "") if request.context else ""}]
    
    # For non-streaming, we'll use a simple completion
    import json
    response = await ai_service.client.chat.completions.create(
        model=ai_service.model,
        messages=[
            {"role": "system", "content": "You are StudyMentor AI, an expert study assistant. Be encouraging, clear, and concise. Use examples."},
            *messages
        ],
        max_tokens=ai_service.max_tokens,
        temperature=0.7
    )
    
    content = response.choices[0].message.content
    tokens_used = response.usage.total_tokens if response.usage else 0
    
    return AIContentResponse(
        content=content,
        tokens_used=tokens_used,
        model_used=ai_service.model
    )