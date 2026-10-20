import json
import os
from typing import Optional
from openai import AsyncOpenAI
from app.core.config import settings


class AIService:
    def __init__(self):
        # Use Groq as primary (fast, free tier), fallback to OpenAI if available
        if settings.GROQ_API_KEY:
            self.client = AsyncOpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1"
            )
            self.model = settings.GROQ_MODEL
            self.max_tokens = settings.GROQ_MAX_TOKENS
            self.temperature = settings.GROQ_TEMPERATURE
            self.provider = "groq"
        elif settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.OPENAI_MODEL
            self.max_tokens = settings.OPENAI_MAX_TOKENS
            self.temperature = settings.OPENAI_TEMPERATURE
            self.provider = "openai"
        else:
            self.client = None
            self.model = "fallback"
            self.max_tokens = 4096
            self.temperature = 0.7
            self.provider = "fallback"

    async def _chat_completion(self, messages: list[dict], response_format: dict = None, temperature: float = None) -> dict:
        """Internal method to handle chat completions with fallback."""
        if not self.client:
            return {"content": None, "tokens_used": 0, "model_used": "fallback"}

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=temperature if temperature is not None else self.temperature,
                response_format=response_format
            )
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            return {"content": content, "tokens_used": tokens_used, "model_used": self.model}
        except Exception as e:
            print(f"AI generation failed ({self.provider}): {e}")
            return {"content": None, "tokens_used": 0, "model_used": "fallback"}
    
    async def generate_study_plan(
            self,
            profile: dict,
            progress: dict,
            weak_subjects: list[str]
        ) -> dict:
            """Generate a personalized daily study plan."""

            subjects_info = []
            for subject in profile.get("subjects", []):
                mastery = progress.get(subject, {}).get("mastery_percentage", 0)
                is_weak = subject in weak_subjects
                subjects_info.append({
                    "subject": subject,
                    "mastery": mastery,
                    "is_weak": is_weak
                })

            prompt = f"""You are an expert AI study planner. Create a personalized daily study plan.

    Student Profile:
    - Name: {profile.get('name', 'Student')}
    - Class: {profile.get('class_level', 'Class 10')}
    - Stream: {profile.get('stream', 'Science')}
    - Study hours per day: {profile.get('study_hours_per_day', 3)}
    - Subjects: {', '.join(profile.get('subjects', []))}
    - Weak subjects: {', '.join(weak_subjects) if weak_subjects else 'None'}

    Current Progress:
    {json.dumps(subjects_info, indent=2)}

    Create a study plan with these requirements:
    1. Total time = study_hours_per_day * 60 minutes
    2. Allocate more time to weak subjects and low-mastery subjects
    3. Each block should have: subject, topic (specific), minutes (15-90), task_description, is_weak_subject
    4. Include 3-5 study blocks
    5. Make tasks specific and actionable (e.g., "Revise quadratic equations with 5 practice problems" not "Study math")

    Return ONLY valid JSON in this exact format:
    {{
      "blocks": [
        {{"subject": "Math", "topic": "Quadratic Equations", "minutes": 45, "task_description": "Revise factorization method, solve 5 practice problems", "is_weak_subject": true}},
        ...
      ]
    }}"""

            result = await self._chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert AI study planner. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            if result["content"]:
                try:
                    plan_data = json.loads(result["content"])
                    return {
                        "plan": plan_data,
                        "tokens_used": result["tokens_used"],
                        "model_used": result["model_used"]
                    }
                except json.JSONDecodeError:
                    pass

            # Fallback plan
            return self._fallback_plan(profile, progress, weak_subjects)
    
    async def generate_quiz(
            self,
            subject: str,
            topic: str,
            difficulty: str = "medium",
            num_questions: int = 5,
            context: Optional[dict] = None
        ) -> dict:
            """Generate a quiz for a specific topic."""

            difficulty_prompts = {
                "easy": "basic recall and fundamental concepts",
                "medium": "application and understanding",
                "hard": "analysis, synthesis, and complex problem-solving"
            }

            prompt = f"""Generate a {difficulty} difficulty quiz for {subject} - {topic}.

    Focus: {difficulty_prompts.get(difficulty, 'understanding and application')}
    Number of questions: {num_questions}

    Requirements:
    1. Each question: question text, 4 options (A-D), correct answer index (0-3), brief explanation
    2. Questions should test {difficulty_prompts.get(difficulty, 'understanding')}
    3. Make questions specific to the topic, not generic
    4. Include a mix of conceptual and application questions

    Return ONLY valid JSON:
    {{
      "questions": [
        {{"question": "...", "options": ["A", "B", "C", "D"], "answer": 0, "explanation": "..."}},
        ...
      ]
    }}"""

            result = await self._chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert quiz creator. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            if result["content"]:
                try:
                    quiz_data = json.loads(result["content"])
                    return {
                        "quiz": quiz_data,
                        "tokens_used": result["tokens_used"],
                        "model_used": result["model_used"]
                    }
                except json.JSONDecodeError:
                    pass

            return self._fallback_quiz(subject, topic, difficulty, num_questions)
    
    async def generate_explanation(
            self,
            subject: str,
            topic: str,
            level: str = "high_school"
        ) -> dict:
            """Generate a clear explanation for a topic."""

            prompt = f"""Explain {topic} in {subject} for a {level} student.

    Structure:
    1. Brief overview (2-3 sentences)
    2. Key concepts (3-5 bullet points)
    3. Important formulas/rules (if applicable)
    4. Common mistakes to avoid
    5. Quick practice tip

    Keep it concise, clear, and encouraging. Use simple language with examples.

    Return ONLY valid JSON:
    {{
      "overview": "...",
      "key_concepts": ["...", "..."],
      "formulas_rules": ["...", "..."],
      "common_mistakes": ["...", "..."],
      "practice_tip": "..."
    }}"""

            result = await self._chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert teacher. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.5
            )

            if result["content"]:
                try:
                    return {
                        "explanation": json.loads(result["content"]),
                        "tokens_used": result["tokens_used"],
                        "model_used": result["model_used"]
                    }
                except json.JSONDecodeError:
                    pass

            return self._fallback_explanation(subject, topic)
    
    async def generate_practice_sprint(
            self,
            subject: str,
            topic: str,
            mastery: int,
            weak_areas: list[str]
        ) -> dict:
            """Generate a focused practice sprint."""

            prompt = f"""Create a focused practice sprint for {subject} - {topic}.

    Student mastery: {mastery}%
    Weak areas: {', '.join(weak_areas) if weak_areas else 'None'}

    Create a 15-30 minute practice session with:
    1. Warm-up (2-3 quick recall questions)
    2. Main practice (3-5 problems/exercises)
    3. Challenge problem (1 harder problem)
    4. Self-check criteria

    Return ONLY valid JSON:
    {{
      "warmup": ["...", "..."],
      "main_practice": [
        {{"type": "problem", "description": "...", "hint": "..."}},
        ...
      ],
      "challenge": {{"description": "...", "hint": "..."}},
      "self_check": ["...", "..."]
    }}"""

            result = await self._chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert tutor. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.6
            )

            if result["content"]:
                try:
                    return {
                        "practice": json.loads(result["content"]),
                        "tokens_used": result["tokens_used"],
                        "model_used": result["model_used"]
                    }
                except json.JSONDecodeError:
                    pass

            return self._fallback_practice(subject, topic)
    
    async def chat_stream(
            self,
            messages: list[dict],
            context: Optional[dict] = None
        ):
            """Stream chat response for real-time interaction."""

            system_prompt = """You are StudyMentor AI, an expert study assistant.
    Help students with explanations, study strategies, motivation, and answering questions.
    Be encouraging, clear, and concise. Use examples."""

            if context:
                system_prompt += f"\n\nStudent Context: {json.dumps(context)}"

            full_messages = [{"role": "system", "content": system_prompt}] + messages

            if not self.client:
                # Fallback streaming
                fallback_msg = "AI service not configured. Please set GROQ_API_KEY or OPENAI_API_KEY in your environment."
                for word in fallback_msg.split():
                    yield word + " "
                return

            try:
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=full_messages,
                    max_tokens=self.max_tokens,
                    temperature=0.7,
                    stream=True
                )

                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            except Exception as e:
                print(f"Chat streaming failed: {e}")
                fallback_msg = "AI service temporarily unavailable. Using offline mode."
                for word in fallback_msg.split():
                    yield word + " "
    
    # Fallback methods for when AI fails
    def _fallback_plan(self, profile: dict, progress: dict, weak_subjects: list[str]) -> dict:
        subjects = profile.get("subjects", [])
        total_minutes = profile.get("study_hours_per_day", 3) * 60
        blocks = []
        
        for i, subject in enumerate(subjects[:4]):
            minutes = max(20, total_minutes // len(subjects))
            is_weak = subject in weak_subjects
            blocks.append({
                "subject": subject,
                "topic": f"{subject} Fundamentals",
                "minutes": minutes,
                "task_description": f"Review {subject} basics and complete practice exercises",
                "is_weak_subject": is_weak
            })
        
        return {"plan": {"blocks": blocks}, "tokens_used": 0, "model_used": "fallback"}
    
    def _fallback_quiz(self, subject: str, topic: str, difficulty: str, num_questions: int) -> dict:
        questions = []
        for i in range(num_questions):
            questions.append({
                "question": f"Sample {subject} question about {topic} #{i+1}",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "answer": 0,
                "explanation": "This is a fallback question. AI generation failed."
            })
        return {"quiz": {"questions": questions}, "tokens_used": 0, "model_used": "fallback"}
    
    def _fallback_explanation(self, subject: str, topic: str) -> dict:
        return {
            "explanation": {
                "overview": f"{topic} is an important concept in {subject}.",
                "key_concepts": ["Concept 1", "Concept 2", "Concept 3"],
                "formulas_rules": ["Rule 1", "Rule 2"],
                "common_mistakes": ["Mistake 1", "Mistake 2"],
                "practice_tip": "Practice regularly and review mistakes."
            },
            "tokens_used": 0,
            "model_used": "fallback"
        }
    
    def _fallback_practice(self, subject: str, topic: str) -> dict:
        return {
            "practice": {
                "warmup": ["Quick recall question 1", "Quick recall question 2"],
                "main_practice": [
                    {"type": "problem", "description": "Practice problem 1", "hint": "Hint 1"},
                    {"type": "problem", "description": "Practice problem 2", "hint": "Hint 2"}
                ],
                "challenge": {"description": "Challenge problem", "hint": "Think step by step"},
                "self_check": ["Can I explain this to someone else?", "Did I avoid common mistakes?"]
            },
            "tokens_used": 0,
            "model_used": "fallback"
        }


ai_service = AIService()