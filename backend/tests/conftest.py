"""
Test Configuration and Fixtures
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import Base, get_db
from app.core.config import settings
from app.models.models import User, StudyProfile, SubjectProgress
from app.core.security import get_password_hash, create_access_token


# Test database URL (in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestAsyncSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def override_get_db():
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create test database tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    """Provide a test database session."""
    async with TestAsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    """Create test client with overridden database."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        role="student",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user):
    """Create authentication headers for test user."""
    token = create_access_token(data={"sub": test_user.id, "email": test_user.email})
    return {"Authorization": f"Bearer {token}", "Cookie": f"access_token={token}"}


@pytest_asyncio.fixture
async def test_profile(db_session, test_user):
    """Create a test study profile."""
    profile = StudyProfile(
        user_id=test_user.id,
        name="Test Student",
        class_level="Class 10",
        stream="Science",
        study_hours_per_day=3,
        subjects=["Math", "Physics", "Chemistry"],
        weak_subjects=["Math"]
    )
    db_session.add(profile)
    
    # Add progress entries
    for subject in ["Math", "Physics", "Chemistry"]:
        progress = SubjectProgress(
            user_id=test_user.id,
            subject=subject,
            mastery_percentage=0,
            completed_topics=[],
            weak_areas=[],
            total_study_minutes=0
        )
        db_session.add(progress)
    
    await db_session.commit()
    await db_session.refresh(profile)
    return profile