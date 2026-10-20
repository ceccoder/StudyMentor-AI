"""
WebSocket Routes for Real-time Chat and AI Interaction
"""
import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.config import settings
from app.core.security import decode_access_token
from app.models.models import User, AIContentGeneration
from app.services.ai_service import ai_service


router = APIRouter(prefix="/ws", tags=["WebSocket"])


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
    
    async def send_message(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(json.dumps(message))
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_text(json.dumps(message))


manager = ConnectionManager()


async def get_current_user_ws(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Authenticate WebSocket connection using token."""
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token payload")
        return None
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        await websocket.close(code=4001, reason="User not found or inactive")
        return None
    
    return user


@router.websocket("/chat")
async def websocket_chat(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time AI chat.
    
    Connect with: ws://localhost:8000/api/ws/chat?token=<access_token>
    
    Message format:
    {
        "type": "chat",
        "payload": {
            "message": "How do I solve quadratic equations?",
            "context": {"subject": "Math", "topic": "Quadratic Equations"}
        }
    }
    
    Response format (streaming):
    {
        "type": "chat_chunk",
        "payload": {"content": "partial response..."}
    }
    """
    user = await get_current_user_ws(websocket, token, db)
    if not user:
        return
    
    await manager.connect(websocket, user.id)
    
    try:
        # Send welcome message
        await websocket.send_text(json.dumps({
            "type": "connected",
            "payload": {"message": f"Connected as {user.full_name}", "user_id": user.id}
        }))
        
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "payload": {"message": "Invalid JSON format"}
                }))
                continue
            
            msg_type = message.get("type")
            payload = message.get("payload", {})
            
            if msg_type == "chat":
                await handle_chat_message(websocket, user, payload, db)
            
            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "payload": {}}))
            
            elif msg_type == "generate_plan":
                await handle_generate_plan(websocket, user, payload, db)
            
            elif msg_type == "generate_quiz":
                await handle_generate_quiz(websocket, user, payload, db)
            
            elif msg_type == "generate_explanation":
                await handle_generate_explanation(websocket, user, payload, db)
            
            elif msg_type == "generate_practice":
                await handle_generate_practice(websocket, user, payload, db)
            
            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "payload": {"message": f"Unknown message type: {msg_type}"}
                }))
    
    except WebSocketDisconnect:
        manager.disconnect(user.id)
    except Exception as e:
        if settings.DEBUG:
            import traceback
            traceback.print_exc()
        manager.disconnect(user.id)
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "payload": {"message": str(e) if settings.DEBUG else "Internal error"}
            }))
        except:
            pass


async def handle_chat_message(websocket: WebSocket, user: User, payload: dict, db: AsyncSession):
    """Handle regular chat messages with streaming response."""
    message = payload.get("message", "").strip()
    context = payload.get("context")
    
    if not message:
        await websocket.send_text(json.dumps({
            "type": "error",
            "payload": {"message": "Message cannot be empty"}
        }))
        return
    
    # Build context from user profile if available
    if not context:
        from app.models.models import StudyProfile, SubjectProgress
        result = await db.execute(select(StudyProfile).where(StudyProfile.user_id == user.id))
        profile = result.scalar_one_or_none()
        
        if profile:
            result = await db.execute(select(SubjectProgress).where(SubjectProgress.user_id == user.id))
            progress_list = result.scalars().all()
            progress = {p.subject: {"mastery_percentage": p.mastery_percentage} for p in progress_list}
            
            context = {
                "name": profile.name,
                "class_level": profile.class_level,
                "stream": profile.stream,
                "study_hours_per_day": profile.study_hours_per_day,
                "subjects": profile.subjects,
                "weak_subjects": profile.weak_subjects,
                "progress": progress
            }
    
    messages = [{"role": "user", "content": message}]
    
    # Stream response
    await websocket.send_text(json.dumps({
        "type": "chat_start",
        "payload": {}
    }))
    
    full_response = ""
    try:
        async for chunk in ai_service.chat_stream(messages, context):
            full_response += chunk
            await websocket.send_text(json.dumps({
                "type": "chat_chunk",
                "payload": {"content": chunk}
            }))
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "payload": {"message": f"AI error: {str(e)}"}
        }))
        return
    
    await websocket.send_text(json.dumps({
        "type": "chat_end",
        "payload": {"full_response": full_response}
    }))
    
    # Log AI generation
    ai_log = AIContentGeneration(
        user_id=user.id,
        generation_type="chat",
        subject=context.get("subject", "General") if context else "General",
        topic=context.get("topic", "Chat") if context else "Chat",
        prompt=message,
        response=full_response,
        tokens_used=len(full_response) // 4,  # rough estimate
        model_used=settings.OPENAI_MODEL
    )
    db.add(ai_log)
    await db.commit()


async def handle_generate_plan(websocket: WebSocket, user: User, payload: dict, db: AsyncSession):
    """Handle AI study plan generation."""
    from app.models.models import StudyProfile, SubjectProgress
    
    result = await db.execute(select(StudyProfile).where(StudyProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    
    if not profile:
        await websocket.send_text(json.dumps({
            "type": "error",
            "payload": {"message": "Create a study profile first"}
        }))
        return
    
    result = await db.execute(select(SubjectProgress).where(SubjectProgress.user_id == user.id))
    progress_list = result.scalars().all()
    progress = {p.subject: {"mastery_percentage": p.mastery_percentage} for p in progress_list}
    
    await websocket.send_text(json.dumps({
        "type": "plan_generation_start",
        "payload": {}
    }))
    
    ai_result = await ai_service.generate_study_plan(
        profile=profile.__dict__,
        progress=progress,
        weak_subjects=profile.weak_subjects
    )
    
    await websocket.send_text(json.dumps({
        "type": "plan_generation_complete",
        "payload": {"plan": ai_result["plan"]}
    }))
    
    # Log AI generation
    ai_log = AIContentGeneration(
        user_id=user.id,
        generation_type="plan",
        subject=", ".join(profile.subjects),
        topic="Daily Plan",
        prompt="WebSocket: Generated daily study plan",
        response=str(ai_result["plan"]),
        tokens_used=ai_result["tokens_used"],
        model_used=ai_result["model_used"]
    )
    db.add(ai_log)
    await db.commit()


async def handle_generate_quiz(websocket: WebSocket, user: User, payload: dict, db: AsyncSession):
    """Handle AI quiz generation."""
    subject = payload.get("subject")
    topic = payload.get("topic")
    difficulty = payload.get("difficulty", "medium")
    num_questions = payload.get("num_questions", 5)
    
    if not subject or not topic:
        await websocket.send_text(json.dumps({
            "type": "error",
            "payload": {"message": "Subject and topic are required"}
        }))
        return
    
    from app.models.models import SubjectProgress
    result = await db.execute(
        select(SubjectProgress).where(
            SubjectProgress.user_id == user.id, SubjectProgress.subject == subject
        )
    )
    progress = result.scalar_one_or_none()
    mastery = progress.mastery_percentage if progress else 0
    weak_areas = progress.weak_areas if progress else []
    
    await websocket.send_text(json.dumps({
        "type": "quiz_generation_start",
        "payload": {}
    }))
    
    ai_result = await ai_service.generate_quiz(
        subject=subject,
        topic=topic,
        difficulty=difficulty,
        num_questions=num_questions,
        context={"mastery": mastery, "weak_areas": weak_areas}
    )
    
    await websocket.send_text(json.dumps({
        "type": "quiz_generation_complete",
        "payload": {"quiz": ai_result["quiz"]}
    }))
    
    # Log AI generation
    ai_log = AIContentGeneration(
        user_id=user.id,
        generation_type="quiz",
        subject=subject,
        topic=topic,
        prompt=f"WebSocket: Generate {difficulty} quiz for {topic}",
        response=str(ai_result["quiz"]),
        tokens_used=ai_result["tokens_used"],
        model_used=ai_result["model_used"]
    )
    db.add(ai_log)
    await db.commit()


async def handle_generate_explanation(websocket: WebSocket, user: User, payload: dict, db: AsyncSession):
    """Handle AI explanation generation."""
    subject = payload.get("subject")
    topic = payload.get("topic")
    level = payload.get("level", "high_school")
    
    if not subject or not topic:
        await websocket.send_text(json.dumps({
            "type": "error",
            "payload": {"message": "Subject and topic are required"}
        }))
        return
    
    await websocket.send_text(json.dumps({
        "type": "explanation_generation_start",
        "payload": {}
    }))
    
    ai_result = await ai_service.generate_explanation(subject, topic, level)
    
    await websocket.send_text(json.dumps({
        "type": "explanation_generation_complete",
        "payload": {"explanation": ai_result["explanation"]}
    }))
    
    # Log AI generation
    ai_log = AIContentGeneration(
        user_id=user.id,
        generation_type="explanation",
        subject=subject,
        topic=topic,
        prompt=f"WebSocket: Explain {topic} for {level} student",
        response=str(ai_result["explanation"]),
        tokens_used=ai_result["tokens_used"],
        model_used=ai_result["model_used"]
    )
    db.add(ai_log)
    await db.commit()


async def handle_generate_practice(websocket: WebSocket, user: User, payload: dict, db: AsyncSession):
    """Handle AI practice sprint generation."""
    subject = payload.get("subject")
    topic = payload.get("topic")
    
    if not subject or not topic:
        await websocket.send_text(json.dumps({
            "type": "error",
            "payload": {"message": "Subject and topic are required"}
        }))
        return
    
    from app.models.models import SubjectProgress
    result = await db.execute(
        select(SubjectProgress).where(
            SubjectProgress.user_id == user.id, SubjectProgress.subject == subject
        )
    )
    progress = result.scalar_one_or_none()
    mastery = progress.mastery_percentage if progress else 0
    weak_areas = progress.weak_areas if progress else []
    
    await websocket.send_text(json.dumps({
        "type": "practice_generation_start",
        "payload": {}
    }))
    
    ai_result = await ai_service.generate_practice_sprint(
        subject=subject,
        topic=topic,
        mastery=mastery,
        weak_areas=weak_areas
    )
    
    await websocket.send_text(json.dumps({
        "type": "practice_generation_complete",
        "payload": {"practice": ai_result["practice"]}
    }))
    
    # Log AI generation
    ai_log = AIContentGeneration(
        user_id=user.id,
        generation_type="practice",
        subject=subject,
        topic=topic,
        prompt=f"WebSocket: Generate practice sprint for {topic}",
        response=str(ai_result["practice"]),
        tokens_used=ai_result["tokens_used"],
        model_used=ai_result["model_used"]
    )
    db.add(ai_log)
    await db.commit()