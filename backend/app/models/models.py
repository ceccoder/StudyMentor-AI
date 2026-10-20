import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, 
    Enum as SQLEnum, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.session import Base


class UserRole(str, enum.Enum):
    STUDENT = "student"
    ADMIN = "admin"


class SubjectCategory(str, enum.Enum):
    MATH = "Math"
    PHYSICS = "Physics"
    CHEMISTRY = "Chemistry"
    BIOLOGY = "Biology"
    ENGLISH = "English"
    ECONOMICS = "Economics"
    HISTORY = "History"
    GEOGRAPHY = "Geography"
    COMPUTER_SCIENCE = "Computer Science"
    ACCOUNTANCY = "Accountancy"
    # Engineering subjects
    MATHEMATICS_1 = "Mathematics 1"
    MATHEMATICS_2 = "Mathematics 2"
    ENGINEERING_PHYSICS = "Engineering Physics"
    ENGINEERING_CHEMISTRY = "Engineering Chemistry"
    BASIC_ELECTRICAL = "Basic Electrical Engineering"
    BASIC_ELECTRONICS = "Basic Electronics Engineering"
    PROGRAMMING_C = "Programming in C"
    PROGRAMMING_PYTHON = "Programming in Python"
    DATA_STRUCTURES = "Data Structures & Algorithms"
    ENGINEERING_DRAWING = "Engineering Drawing"
    ENGINEERING_MECHANICS = "Engineering Mechanics"
    THERMODYNAMICS = "Thermodynamics"
    FLUID_MECHANICS = "Fluid Mechanics"
    STRENGTH_OF_MATERIALS = "Strength of Materials"
    CONTROL_SYSTEMS = "Control Systems"
    SIGNALS_SYSTEMS = "Signals & Systems"
    MICROPROCESSORS = "Microprocessors & Microcontrollers"
    DIGITAL_ELECTRONICS = "Digital Electronics"
    COMMUNICATION_SYSTEMS = "Communication Systems"
    POWER_SYSTEMS = "Power Systems"
    MACHINE_DESIGN = "Machine Design"
    MANUFACTURING_PROCESSES = "Manufacturing Processes"


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.STUDENT)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    profile: Mapped["StudyProfile"] = relationship("StudyProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    progress: Mapped[list["SubjectProgress"]] = relationship("SubjectProgress", back_populates="user", cascade="all, delete-orphan")
    plans: Mapped[list["StudyPlan"]] = relationship("StudyPlan", back_populates="user", cascade="all, delete-orphan")
    quiz_attempts: Mapped[list["QuizAttempt"]] = relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    streak: Mapped["UserStreak"] = relationship("UserStreak", back_populates="user", uselist=False, cascade="all, delete-orphan")


class StudyProfile(Base):
    __tablename__ = "study_profiles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Profile info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    class_level: Mapped[str] = mapped_column(String(50), nullable=False)  # Class 9, 10, 11, 12
    stream: Mapped[str] = mapped_column(String(100), nullable=False)  # Science, Commerce, Arts, General
    study_hours_per_day: Mapped[int] = mapped_column(Integer, default=3)
    
    # Subjects as JSON arrays
    subjects: Mapped[list[str]] = mapped_column(JSON, default=list)
    weak_subjects: Mapped[list[str]] = mapped_column(JSON, default=list)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="profile")


class SubjectProgress(Base):
    __tablename__ = "subject_progress"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    mastery_percentage: Mapped[int] = mapped_column(Integer, default=0)
    completed_topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    weak_areas: Mapped[list[str]] = mapped_column(JSON, default=list)
    last_studied: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_study_minutes: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="progress")
    
    __table_args__ = (
        UniqueConstraint("user_id", "subject", name="uq_user_subject_progress"),
        Index("ix_user_subject", "user_id", "subject"),
    )


class StudyPlan(Base):
    __tablename__ = "study_plans"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    plan_data: Mapped[dict] = mapped_column(JSON, nullable=False)  # Full plan with blocks
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    generated_by_ai: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="plans")
    
    __table_args__ = (
        Index("ix_user_date_active", "user_id", "date", "is_active"),
    )


class StudyPlanBlock(Base):
    __tablename__ = "study_plan_blocks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("study_plans.id", ondelete="CASCADE"), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    task_description: Mapped[str] = mapped_column(Text, nullable=False)
    is_weak_subject: Mapped[bool] = mapped_column(Boolean, default=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Quiz(Base):
    __tablename__ = "quizzes"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subject: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(50), default="medium")  # easy, medium, hard
    questions: Mapped[list[dict]] = mapped_column(JSON, nullable=False)  # [{question, options, answer, explanation}]
    generated_by_ai: Mapped[bool] = mapped_column(Boolean, default=True)
    source_material: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    quiz_id: Mapped[int] = mapped_column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    answers: Mapped[list[int]] = mapped_column(JSON, nullable=False)  # Selected option indices
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # Percentage
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    time_taken_seconds: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="quiz_attempts")
    quiz: Mapped["Quiz"] = relationship("Quiz")
    
    __table_args__ = (
        Index("ix_user_subject_date", "user_id", "subject", "created_at"),
    )


class UserStreak(Base):
    __tablename__ = "user_streaks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_active_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="streak")


class AIContentGeneration(Base):
    __tablename__ = "ai_content_generations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    generation_type: Mapped[str] = mapped_column(String(50), nullable=False)  # plan, quiz, explanation, practice
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_user_generation_type", "user_id", "generation_type"),
    )