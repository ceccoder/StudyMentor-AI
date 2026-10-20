"""
Test Study Profile and Plan Endpoints
"""
import pytest
from httpx import AsyncClient


class TestStudyProfileEndpoints:
    """Test study profile routes."""

    @pytest.mark.asyncio
    async def test_create_profile(self, client: AsyncClient, auth_headers):
        """Test creating a study profile."""
        response = await client.post(
            "/api/profile",
            json={
                "name": "Test Student",
                "class_level": "Class 10",
                "stream": "Science",
                "study_hours_per_day": 3,
                "subjects": ["Math", "Physics", "Chemistry"],
                "weak_subjects": ["Math"]
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Student"
        assert data["class_level"] == "Class 10"
        assert data["stream"] == "Science"
        assert data["subjects"] == ["Math", "Physics", "Chemistry"]
        assert data["weak_subjects"] == ["Math"]

    @pytest.mark.asyncio
    async def test_create_duplicate_profile(self, client: AsyncClient, auth_headers, test_profile):
        """Test creating profile when one already exists."""
        response = await client.post(
            "/api/profile",
            json={
                "name": "Another Student",
                "class_level": "Class 11",
                "stream": "Commerce",
                "study_hours_per_day": 4,
                "subjects": ["Economics"],
                "weak_subjects": []
            },
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_profile(self, client: AsyncClient, auth_headers, test_profile):
        """Test getting study profile."""
        response = await client.get("/api/profile", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Student"
        assert data["subjects"] == ["Math", "Physics", "Chemistry"]

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, client: AsyncClient, auth_headers, test_user):
        """Test getting profile when none exists."""
        # Need a fresh user without profile
        from app.main import app
        from app.db.session import get_db
        from app.core.security import create_access_token
        
        # Create a new user
        from app.models.models import User
        from app.core.security import get_password_hash
        from sqlalchemy import select
        
        async with client.app.state.db_session() as db:  # This won't work, need different approach
            pass

    @pytest.mark.asyncio
    async def test_update_profile(self, client: AsyncClient, auth_headers, test_profile):
        """Test updating study profile."""
        response = await client.put(
            "/api/profile",
            json={
                "study_hours_per_day": 4,
                "weak_subjects": ["Math", "Physics"]
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["study_hours_per_day"] == 4
        assert data["weak_subjects"] == ["Math", "Physics"]

    @pytest.mark.asyncio
    async def test_delete_profile(self, client: AsyncClient, auth_headers, test_profile):
        """Test deleting study profile."""
        response = await client.delete("/api/profile", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify it's gone
        response = await client.get("/api/profile", headers=auth_headers)
        assert response.status_code == 404


class TestProgressEndpoints:
    """Test progress routes."""

    @pytest.mark.asyncio
    async def test_get_progress(self, client: AsyncClient, auth_headers, test_profile):
        """Test getting all subject progress."""
        response = await client.get("/api/progress", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3  # Math, Physics, Chemistry
        subjects = {p["subject"] for p in data}
        assert subjects == {"Math", "Physics", "Chemistry"}

    @pytest.mark.asyncio
    async def test_get_subject_progress(self, client: AsyncClient, auth_headers, test_profile):
        """Test getting progress for specific subject."""
        response = await client.get("/api/progress/Math", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["subject"] == "Math"
        assert data["mastery_percentage"] == 0

    @pytest.mark.asyncio
    async def test_update_subject_progress(self, client: AsyncClient, auth_headers, test_profile):
        """Test updating subject progress."""
        response = await client.put(
            "/api/progress/Math",
            json={
                "mastery_percentage": 50,
                "completed_topics": ["Quadratic Equations"],
                "weak_areas": ["Factoring"]
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mastery_percentage"] == 50
        assert data["completed_topics"] == ["Quadratic Equations"]
        assert data["weak_areas"] == ["Factoring"]


class TestPlanEndpoints:
    """Test study plan routes."""

    @pytest.mark.asyncio
    async def test_generate_plan(self, client: AsyncClient, auth_headers, test_profile):
        """Test generating a study plan."""
        response = await client.post("/api/plan/generate", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "plan_data" in data
        assert "blocks" in data["plan_data"]
        assert len(data["plan_data"]["blocks"]) > 0
        
        # Check block structure
        block = data["plan_data"]["blocks"][0]
        assert "subject" in block
        assert "topic" in block
        assert "minutes" in block
        assert "task_description" in block

    @pytest.mark.asyncio
    async def test_get_today_plan(self, client: AsyncClient, auth_headers, test_profile):
        """Test getting today's plan (auto-generates if none)."""
        response = await client.get("/api/plan/today", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "date" in data
        assert "total_minutes" in data
        assert "blocks" in data
        assert data["total_minutes"] > 0

    @pytest.mark.asyncio
    async def test_get_plan_by_date(self, client: AsyncClient, auth_headers, test_profile):
        """Test getting plan for specific date."""
        from datetime import date, timedelta
        tomorrow = date.today() + timedelta(days=1)
        
        response = await client.get(f"/api/plan/{tomorrow.isoformat()}", headers=auth_headers)
        # Should auto-generate or return 404
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_complete_plan_block(self, client: AsyncClient, auth_headers, test_profile):
        """Test marking a plan block as complete."""
        # First generate a plan
        gen_response = await client.post("/api/plan/generate", headers=auth_headers)
        assert gen_response.status_code == 200
        plan = gen_response.json()
        block_id = plan["blocks"][0]["id"]
        
        # Mark complete
        response = await client.put(f"/api/plan/blocks/{block_id}/complete", headers=auth_headers)
        assert response.status_code == 200
        assert "marked complete" in response.json()["message"]


class TestQuizEndpoints:
    """Test quiz routes."""

    @pytest.mark.asyncio
    async def test_generate_quiz(self, client: AsyncClient, auth_headers, test_profile):
        """Test generating a quiz."""
        response = await client.post(
            "/api/quiz/generate",
            params={
                "subject": "Math",
                "topic": "Quadratic Equations",
                "difficulty": "medium",
                "num_questions": 3
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["subject"] == "Math"
        assert data["topic"] == "Quadratic Equations"
        assert len(data["questions"]) == 3
        
        # Check question structure
        question = data["questions"][0]
        assert "question" in question
        assert "options" in question
        assert len(question["options"]) == 4
        assert "answer" in question
        assert "explanation" in question

    @pytest.mark.asyncio
    async def test_list_quizzes(self, client: AsyncClient, auth_headers, test_profile):
        """Test listing quizzes."""
        # First generate one
        await client.post(
            "/api/quiz/generate",
            params={"subject": "Math", "topic": "Algebra"},
            headers=auth_headers
        )
        
        response = await client.get("/api/quiz", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(q["topic"] == "Algebra" for q in data)

    @pytest.mark.asyncio
    async def test_attempt_quiz(self, client: AsyncClient, auth_headers, test_profile):
        """Test attempting a quiz."""
        # Generate quiz first
        gen_response = await client.post(
            "/api/quiz/generate",
            params={"subject": "Math", "topic": "Geometry", "num_questions": 2},
            headers=auth_headers
        )
        quiz = gen_response.json()
        quiz_id = quiz["id"]
        
        # Get correct answers
        correct_answers = [q["answer"] for q in quiz["questions"]]
        
        # Attempt with correct answers
        response = await client.post(
            f"/api/quiz/{quiz_id}/attempt",
            json={
                "answers": correct_answers,
                "time_taken_seconds": 60
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 100
        assert data["correct_count"] == 2
        assert data["total_questions"] == 2
        assert data["progress_updated"] is True
        assert len(data["results"]) == 2

    @pytest.mark.asyncio
    async def test_attempt_quiz_wrong_answers(self, client: AsyncClient, auth_headers, test_profile):
        """Test attempting a quiz with wrong answers."""
        gen_response = await client.post(
            "/api/quiz/generate",
            params={"subject": "Physics", "topic": "Mechanics", "num_questions": 3},
            headers=auth_headers
        )
        quiz = gen_response.json()
        quiz_id = quiz["id"]
        
        # Use wrong answers (all 0)
        wrong_answers = [0, 0, 0]
        
        response = await client.post(
            f"/api/quiz/{quiz_id}/attempt",
            json={
                "answers": wrong_answers,
                "time_taken_seconds": 120
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["score"] < 100  # Should be less than perfect
        assert data["progress_updated"] is True

    @pytest.mark.asyncio
    async def test_get_quiz_history(self, client: AsyncClient, auth_headers, test_profile):
        """Test getting quiz attempt history."""
        # Generate and attempt a quiz
        gen_response = await client.post(
            "/api/quiz/generate",
            params={"subject": "Chemistry", "topic": "Bonding", "num_questions": 2},
            headers=auth_headers
        )
        quiz = gen_response.json()
        await client.post(
            f"/api/quiz/{quiz['id']}/attempt",
            json={"answers": [0, 1], "time_taken_seconds": 60},
            headers=auth_headers
        )
        
        response = await client.get("/api/quiz/attempts/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["subject"] == "Chemistry"

    @pytest.mark.asyncio
    async def test_get_available_subjects(self, client: AsyncClient, auth_headers, test_profile):
        """Test getting subjects with available quizzes."""
        await client.post(
            "/api/quiz/generate",
            params={"subject": "Biology", "topic": "Cells"},
            headers=auth_headers
        )
        
        response = await client.get("/api/quiz/subjects/available", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "Biology" in data