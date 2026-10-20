"""
Quiz API Routes for StudyMentor AI
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.models import User, Quiz, QuizAttempt, SubjectProgress
from app.schemas.schemas import (
    QuizCreate, QuizResponse, QuizAttemptCreate, QuizAttemptResponse,
    QuizResultResponse, QuizQuestionCreate
)
from app.services.ai_service import ai_service


router = APIRouter(prefix="/quiz", tags=["Quiz"])


@router.post("", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def create_quiz(
    quiz_data: QuizCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a quiz (admin or AI-generated)."""
    quiz = Quiz(
        subject=quiz_data.subject,
        topic=quiz_data.topic,
        difficulty=quiz_data.difficulty,
        questions=[q.model_dump() for q in quiz_data.questions],
        generated_by_ai=quiz_data.generated_by_ai,
        source_material=quiz_data.source_material
    )
    db.add(quiz)
    await db.commit()
    await db.refresh(quiz)
    return quiz


@router.post("/generate", response_model=QuizResponse)
async def generate_quiz(
    subject: str,
    topic: str,
    difficulty: str = "medium",
    num_questions: int = 5,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a quiz using AI for a specific topic."""
    
    # Get user's progress for context
    result = await db.execute(
        select(SubjectProgress).where(
            and_(SubjectProgress.user_id == current_user.id, SubjectProgress.subject == subject)
        )
    )
    progress = result.scalar_one_or_none()
    mastery = progress.mastery_percentage if progress else 0
    weak_areas = progress.weak_areas if progress else []
    
    # Generate quiz with AI
    ai_result = await ai_service.generate_quiz(
        subject=subject,
        topic=topic,
        difficulty=difficulty,
        num_questions=num_questions,
        context={"mastery": mastery, "weak_areas": weak_areas}
    )
    
    # Save quiz
    quiz = Quiz(
        subject=subject,
        topic=topic,
        difficulty=difficulty,
        questions=ai_result["quiz"]["questions"],
        generated_by_ai=True
    )
    db.add(quiz)
    await db.flush()
    
    # Log AI generation
    from app.models.models import AIContentGeneration
    ai_log = AIContentGeneration(
        user_id=current_user.id,
        generation_type="quiz",
        subject=subject,
        topic=topic,
        prompt=f"Generate {difficulty} quiz for {topic}",
        response=str(ai_result["quiz"]),
        tokens_used=ai_result["tokens_used"],
        model_used=ai_result["model_used"]
    )
    db.add(ai_log)
    
    await db.commit()
    await db.refresh(quiz)
    
    return quiz


@router.get("", response_model=List[QuizResponse])
async def list_quizzes(
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List available quizzes, optionally filtered by subject/topic."""
    query = select(Quiz)
    if subject:
        query = query.where(Quiz.subject == subject)
    if topic:
        query = query.where(Quiz.topic == topic)
    query = query.order_by(Quiz.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific quiz (without answers for taking)."""
    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalar_one_or_none()
    
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    return quiz


@router.post("/{quiz_id}/attempt", response_model=QuizResultResponse)
async def attempt_quiz(
    quiz_id: int,
    attempt_data: QuizAttemptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit a quiz attempt and get results."""
    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalar_one_or_none()
    
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Calculate score
    questions = quiz.questions
    answers = attempt_data.answers
    
    if len(answers) != len(questions):
        raise HTTPException(status_code=400, detail="Number of answers must match number of questions")
    
    correct_count = 0
    results = []
    
    for i, (question, user_answer) in enumerate(zip(questions, answers)):
        correct_answer = question.get("answer", 0)
        is_correct = user_answer == correct_answer
        if is_correct:
            correct_count += 1
        
        results.append({
            "question": question.get("question", ""),
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "explanation": question.get("explanation", "")
        })
    
    score = int((correct_count / len(questions)) * 100) if questions else 0
    
    # Save attempt
    attempt = QuizAttempt(
        user_id=current_user.id,
        quiz_id=quiz_id,
        subject=quiz.subject,
        answers=answers,
        score=score,
        correct_count=correct_count,
        total_questions=len(questions),
        time_taken_seconds=attempt_data.time_taken_seconds
    )
    db.add(attempt)
    
    # Update subject progress
    progress_result = await db.execute(
        select(SubjectProgress).where(
            and_(SubjectProgress.user_id == current_user.id, SubjectProgress.subject == quiz.subject)
        )
    )
    progress = progress_result.scalar_one_or_none()
    
    progress_updated = False
    if progress:
        # Increase mastery based on score
        mastery_increase = 3 if score >= 70 else 1
        progress.mastery_percentage = min(100, progress.mastery_percentage + mastery_increase)
        progress.total_study_minutes += attempt_data.time_taken_seconds // 60
        if quiz.topic not in progress.completed_topics:
            progress.completed_topics.append(quiz.topic)
        progress.last_studied = datetime.utcnow()
        progress.updated_at = datetime.utcnow()
        progress_updated = True
    else:
        # Create progress entry
        progress = SubjectProgress(
            user_id=current_user.id,
            subject=quiz.subject,
            mastery_percentage=3 if score >= 70 else 1,
            completed_topics=[quiz.topic] if score >= 70 else [],
            weak_areas=[],
            total_study_minutes=attempt_data.time_taken_seconds // 60,
            last_studied=datetime.utcnow()
        )
        db.add(progress)
        progress_updated = True
    
    await db.commit()
    
    return QuizResultResponse(
        score=score,
        correct_count=correct_count,
        total_questions=len(questions),
        results=results,
        progress_updated=progress_updated
    )


@router.get("/attempts/history", response_model=List[QuizAttemptResponse])
async def get_quiz_history(
    subject: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's quiz attempt history."""
    query = select(QuizAttempt).where(QuizAttempt.user_id == current_user.id)
    if subject:
        query = query.where(QuizAttempt.subject == subject)
    query = query.order_by(QuizAttempt.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/subjects/available", response_model=List[str])
async def get_available_subjects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get subjects that have quizzes available."""
    result = await db.execute(select(Quiz.subject).distinct())
    return [row[0] for row in result.all()]