from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.models import User, StudyProfile, SubjectProgress, StudyPlan, StudyPlanBlock, UserStreak
from app.schemas.schemas import (
    StudyProfileCreate, StudyProfileUpdate, StudyProfileResponse,
    SubjectProgressResponse, StudyPlanResponse, DailyPlanResponse
)
from app.services.ai_service import ai_service

router = APIRouter(prefix="/profile", tags=["Study Profile"])


@router.post("", response_model=StudyProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: StudyProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create study profile."""
    # Check if profile exists
    result = await db.execute(
        select(StudyProfile).where(StudyProfile.user_id == current_user.id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Profile already exists. Use PUT to update.")
    
    # Create profile
    profile = StudyProfile(
        user_id=current_user.id,
        **profile_data.model_dump()
    )
    db.add(profile)
    
    # Initialize progress for each subject
    for subject in profile_data.subjects:
        progress = SubjectProgress(
            user_id=current_user.id,
            subject=subject,
            mastery_percentage=0,
            completed_topics=[],
            weak_areas=[],
            total_study_minutes=0
        )
        db.add(progress)
    
    await db.commit()
    await db.refresh(profile)
    
    return profile


@router.get("", response_model=StudyProfileResponse)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get study profile."""
    result = await db.execute(
        select(StudyProfile).where(StudyProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Create one first.")
    
    return profile


@router.put("", response_model=StudyProfileResponse)
async def update_profile(
    profile_data: StudyProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update study profile."""
    result = await db.execute(
        select(StudyProfile).where(StudyProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    profile.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(profile)
    
    return profile


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete study profile."""
    result = await db.execute(
        select(StudyProfile).where(StudyProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    await db.delete(profile)
    await db.commit()


# Progress routes
progress_router = APIRouter(prefix="/progress", tags=["Progress"])


@progress_router.get("", response_model=List[SubjectProgressResponse])
async def get_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all subject progress."""
    result = await db.execute(
        select(SubjectProgress).where(SubjectProgress.user_id == current_user.id)
    )
    return result.scalars().all()


@progress_router.get("/{subject}", response_model=SubjectProgressResponse)
async def get_subject_progress(
    subject: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get progress for a specific subject."""
    result = await db.execute(
        select(SubjectProgress).where(
            and_(SubjectProgress.user_id == current_user.id, SubjectProgress.subject == subject)
        )
    )
    progress = result.scalar_one_or_none()
    
    if not progress:
        # Create default progress
        progress = SubjectProgress(
            user_id=current_user.id,
            subject=subject,
            mastery_percentage=0,
            completed_topics=[],
            weak_areas=[],
            total_study_minutes=0
        )
        db.add(progress)
        await db.commit()
        await db.refresh(progress)
    
    return progress


@progress_router.put("/{subject}", response_model=SubjectProgressResponse)
async def update_subject_progress(
    subject: str,
    progress_data: SubjectProgressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update subject progress."""
    result = await db.execute(
        select(SubjectProgress).where(
            and_(SubjectProgress.user_id == current_user.id, SubjectProgress.subject == subject)
        )
    )
    progress = result.scalar_one_or_none()
    
    if not progress:
        progress = SubjectProgress(
            user_id=current_user.id,
            subject=subject,
            mastery_percentage=0,
            completed_topics=[],
            weak_areas=[],
            total_study_minutes=0
        )
        db.add(progress)
    
    update_data = progress_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(progress, field, value)
    
    progress.updated_at = datetime.utcnow()
    if progress_data.last_studied is not None:
        progress.last_studied = progress_data.last_studied
    elif "mastery_percentage" in update_data or "completed_topics" in update_data:
        progress.last_studied = datetime.utcnow()
    
    await db.commit()
    await db.refresh(progress)
    
    return progress


# Study Plan routes
plan_router = APIRouter(prefix="/plan", tags=["Study Plan"])


@plan_router.post("/generate", response_model=StudyPlanResponse)
async def generate_plan(
    target_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate AI study plan for a date."""
    if target_date is None:
        target_date = date.today()
    
    # Get profile
    result = await db.execute(
        select(StudyProfile).where(StudyProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=400, detail="Create a study profile first")
    
    # Get progress
    result = await db.execute(
        select(SubjectProgress).where(SubjectProgress.user_id == current_user.id)
    )
    progress_list = result.scalars().all()
    progress = {p.subject: {"mastery_percentage": p.mastery_percentage} for p in progress_list}
    
    # Generate AI plan
    ai_result = await ai_service.generate_study_plan(
        profile=profile.__dict__,
        progress=progress,
        weak_subjects=profile.weak_subjects
    )
    
    # Deactivate old plans for this date
    await db.execute(
        select(StudyPlan).where(
            and_(
                StudyPlan.user_id == current_user.id,
                func.date(StudyPlan.date) == target_date,
                StudyPlan.is_active == True
            )
        ).update({"is_active": False})
    )
    
    # Create new plan
    plan = StudyPlan(
        user_id=current_user.id,
        date=datetime.combine(target_date, datetime.min.time()),
        plan_data=ai_result["plan"],
        generated_by_ai=True
    )
    db.add(plan)
    await db.flush()
    
    # Create plan blocks
    blocks = []
    for idx, block_data in enumerate(ai_result["plan"].get("blocks", [])):
        block = StudyPlanBlock(
            plan_id=plan.id,
            subject=block_data["subject"],
            topic=block_data["topic"],
            minutes=block_data["minutes"],
            task_description=block_data["task_description"],
            is_weak_subject=block_data.get("is_weak_subject", False),
            order_index=idx
        )
        db.add(block)
        blocks.append(block)
    
    await db.commit()
    await db.refresh(plan)
    
    # Log AI generation
    from app.models.models import AIContentGeneration
    ai_log = AIContentGeneration(
        user_id=current_user.id,
        generation_type="plan",
        subject=", ".join(profile.subjects),
        topic="Daily Plan",
        prompt="Generated daily study plan",
        response=str(ai_result["plan"]),
        tokens_used=ai_result["tokens_used"],
        model_used=ai_result["model_used"]
    )
    db.add(ai_log)
    await db.commit()
    
    # Build response
    plan.blocks = blocks
    return plan


@plan_router.get("/today", response_model=DailyPlanResponse)
async def get_today_plan(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get today's study plan."""
    today = date.today()
    
    result = await db.execute(
        select(StudyPlan).where(
            and_(
                StudyPlan.user_id == current_user.id,
                func.date(StudyPlan.date) == today,
                StudyPlan.is_active == True
            )
        ).order_by(StudyPlan.created_at.desc())
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        # Auto-generate if none exists
        return await generate_plan(today, db, current_user)
    
    # Get blocks
    result = await db.execute(
        select(StudyPlanBlock).where(StudyPlanBlock.plan_id == plan.id).order_by(StudyPlanBlock.order_index)
    )
    blocks = result.scalars().all()
    
    total_minutes = sum(b.minutes for b in blocks)
    
    return DailyPlanResponse(
        date=today.isoformat(),
        total_minutes=total_minutes,
        blocks=blocks
    )


@plan_router.get("/{plan_date}", response_model=DailyPlanResponse)
async def get_plan_by_date(
    plan_date: date,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get study plan for specific date."""
    result = await db.execute(
        select(StudyPlan).where(
            and_(
                StudyPlan.user_id == current_user.id,
                func.date(StudyPlan.date) == plan_date,
                StudyPlan.is_active == True
            )
        ).order_by(StudyPlan.created_at.desc())
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="No plan found for this date")
    
    result = await db.execute(
        select(StudyPlanBlock).where(StudyPlanBlock.plan_id == plan.id).order_by(StudyPlanBlock.order_index)
    )
    blocks = result.scalars().all()
    
    total_minutes = sum(b.minutes for b in blocks)
    
    return DailyPlanResponse(
        date=plan_date.isoformat(),
        total_minutes=total_minutes,
        blocks=blocks
    )


@plan_router.put("/blocks/{block_id}/complete")
async def complete_plan_block(
    block_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a plan block as completed."""
    result = await db.execute(
        select(StudyPlanBlock)
        .join(StudyPlan)
        .where(
            and_(
                StudyPlanBlock.id == block_id,
                StudyPlan.user_id == current_user.id
            )
        )
    )
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(status_code=404, detail="Plan block not found")
    
    block.is_completed = True
    block.completed_at = datetime.utcnow()
    
    # Update subject progress
    result = await db.execute(
        select(SubjectProgress).where(
            and_(
                SubjectProgress.user_id == current_user.id,
                SubjectProgress.subject == block.subject
            )
        )
    )
    progress = result.scalar_one_or_none()
    
    if progress:
        progress.total_study_minutes += block.minutes
        progress.mastery_percentage = min(100, progress.mastery_percentage + 5)
        if block.topic not in progress.completed_topics:
            progress.completed_topics.append(block.topic)
        progress.last_studied = datetime.utcnow()
        progress.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Block marked complete", "block_id": block_id}