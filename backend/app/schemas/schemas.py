from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from enum import Enum


# Auth schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None


class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# Study Profile schemas
class StudyProfileBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    class_level: str = Field(pattern="^(Class 9|Class 10|Class 11|Class 12)$")
    stream: str = Field(pattern="^(Science|Commerce|Arts|General|Engineering)$")
    study_hours_per_day: int = Field(ge=1, le=12, default=3)
    subjects: list[str] = Field(default_factory=list, min_length=1)
    weak_subjects: list[str] = Field(default_factory=list)


class StudyProfileCreate(StudyProfileBase):
    pass


class StudyProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    class_level: Optional[str] = Field(default=None, pattern="^(Class 9|Class 10|Class 11|Class 12)$")
    stream: Optional[str] = Field(default=None, pattern="^(Science|Commerce|Arts|General|Engineering)$")
    study_hours_per_day: Optional[int] = Field(default=None, ge=1, le=12)
    subjects: Optional[list[str]] = None
    weak_subjects: Optional[list[str]] = None


class StudyProfileResponse(StudyProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Subject Progress schemas
class SubjectProgressBase(BaseModel):
    subject: str
    mastery_percentage: int = Field(ge=0, le=100, default=0)
    completed_topics: list[str] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)
    total_study_minutes: int = Field(ge=0, default=0)


class SubjectProgressCreate(SubjectProgressBase):
    pass


class SubjectProgressUpdate(BaseModel):
    mastery_percentage: Optional[int] = Field(default=None, ge=0, le=100)
    completed_topics: Optional[list[str]] = None
    weak_areas: Optional[list[str]] = None
    total_study_minutes: Optional[int] = Field(default=None, ge=0)
    last_studied: Optional[datetime] = None


class SubjectProgressResponse(SubjectProgressBase):
    id: int
    user_id: int
    last_studied: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Study Plan schemas
class StudyPlanBlockBase(BaseModel):
    subject: str
    topic: str
    minutes: int = Field(ge=5, le=180)
    task_description: str
    is_weak_subject: bool = False
    order_index: int


class StudyPlanBlockCreate(StudyPlanBlockBase):
    pass


class StudyPlanBlockResponse(StudyPlanBlockBase):
    id: int
    plan_id: int
    is_completed: bool
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class StudyPlanBase(BaseModel):
    date: datetime
    plan_data: dict


class StudyPlanCreate(StudyPlanBase):
    pass


class StudyPlanResponse(StudyPlanBase):
    id: int
    user_id: int
    is_active: bool
    generated_by_ai: bool
    created_at: datetime
    blocks: list[StudyPlanBlockResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class DailyPlanResponse(BaseModel):
    date: str
    total_minutes: int
    blocks: list[StudyPlanBlockResponse]


# Quiz schemas
class QuizQuestionBase(BaseModel):
    question: str
    options: list[str] = Field(min_length=2, max_length=6)
    answer: int = Field(ge=0)
    explanation: Optional[str] = None


class QuizQuestionCreate(QuizQuestionBase):
    pass


class QuizQuestionResponse(QuizQuestionBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)


class QuizBase(BaseModel):
    subject: str
    topic: str
    difficulty: str = Field(pattern="^(easy|medium|hard)$", default="medium")
    questions: list[QuizQuestionCreate]
    generated_by_ai: bool = True
    source_material: Optional[str] = None


class QuizCreate(QuizBase):
    pass


class QuizResponse(QuizBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class QuizAttemptBase(BaseModel):
    quiz_id: int
    answers: list[int]
    time_taken_seconds: int = Field(ge=0, default=0)


class QuizAttemptCreate(QuizAttemptBase):
    pass


class QuizAttemptResponse(BaseModel):
    id: int
    user_id: int
    quiz_id: int
    subject: str
    answers: list[int]
    score: int
    correct_count: int
    total_questions: int
    time_taken_seconds: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class QuizResultResponse(BaseModel):
    score: int
    correct_count: int
    total_questions: int
    results: list[dict]  # [{question, user_answer, correct_answer, is_correct, explanation}]
    progress_updated: bool


# Streak schemas
class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    last_active_date: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# AI Generation schemas
class AIContentRequest(BaseModel):
    generation_type: str = Field(pattern="^(plan|quiz|explanation|practice)$")
    subject: str
    topic: Optional[str] = None
    context: Optional[dict] = None  # Additional context like profile, progress, etc.


class AIContentResponse(BaseModel):
    content: str
    tokens_used: int
    model_used: str


# Dashboard schemas
class DashboardStatsResponse(BaseModel):
    focus_blocks: int
    weak_focus_count: int
    planned_minutes: int
    streak: int
    subjects_count: int
    avg_mastery: float


class WeakSubjectAlert(BaseModel):
    subject: str
    progress: int
    message: str
    priority: str  # high, medium, low


# WebSocket schemas
class WSMessage(BaseModel):
    type: str
    payload: dict


class WSChatMessage(BaseModel):
    message: str
    context: Optional[dict] = None