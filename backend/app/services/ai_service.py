import json
import os
from typing import Optional, AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings


class AIService:
    def __init__(self):
        self._init_primary_client()

    def _init_primary_client(self):
        if settings.GROQ_API_KEY:
            self.client = AsyncOpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1"
            )
            self.model = settings.GROQ_MODEL or "llama-3.3-70b-versatile"
            self.fallback_model = "llama-3.1-8b-instant"
            self.max_tokens = settings.GROQ_MAX_TOKENS
            self.temperature = settings.GROQ_TEMPERATURE
            self.provider = "groq"
        elif settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.OPENAI_MODEL or "gpt-4o-mini"
            self.fallback_model = "gpt-4o-mini"
            self.max_tokens = settings.OPENAI_MAX_TOKENS
            self.temperature = settings.OPENAI_TEMPERATURE
            self.provider = "openai"
        else:
            self.client = None
            self.model = "offline-pedagogy"
            self.fallback_model = "offline-pedagogy"
            self.max_tokens = 4096
            self.temperature = 0.7
            self.provider = "offline"

    def _get_active_client(self, custom_groq_key: Optional[str] = None, custom_openai_key: Optional[str] = None):
        """Returns client, model, provider using custom key if provided, or default."""
        if custom_groq_key and custom_groq_key.startswith("gsk_"):
            client = AsyncOpenAI(api_key=custom_groq_key, base_url="https://api.groq.com/openai/v1")
            return client, "llama-3.3-70b-versatile", "llama-3.1-8b-instant", "groq"
        if custom_openai_key and custom_openai_key.startswith("sk-"):
            client = AsyncOpenAI(api_key=custom_openai_key)
            return client, "gpt-4o-mini", "gpt-4o-mini", "openai"
        return self.client, self.model, getattr(self, "fallback_model", "llama-3.1-8b-instant"), self.provider

    async def _chat_completion(
        self,
        messages: list[dict],
        response_format: dict = None,
        temperature: float = None,
        custom_groq_key: Optional[str] = None,
        custom_openai_key: Optional[str] = None
    ) -> dict:
        """Internal method to handle chat completions with automatic fallback."""
        client, model, fallback_model, provider = self._get_active_client(custom_groq_key, custom_openai_key)
        if not client:
            return {"content": None, "tokens_used": 0, "model_used": "offline"}

        temp = temperature if temperature is not None else self.temperature

        # Attempt primary model
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": temp,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = await client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            return {"content": content, "tokens_used": tokens_used, "model_used": model}
        except Exception as e:
            print(f"Primary AI model '{model}' failed ({provider}): {e}. Trying fallback model '{fallback_model}'...")

        # Attempt fallback model (e.g. llama-3.1-8b-instant on Groq)
        if fallback_model and fallback_model != model:
            try:
                kwargs = {
                    "model": fallback_model,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": temp,
                }
                if response_format:
                    kwargs["response_format"] = response_format

                response = await client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                tokens_used = response.usage.total_tokens if response.usage else 0
                return {"content": content, "tokens_used": tokens_used, "model_used": fallback_model}
            except Exception as e2:
                print(f"Fallback AI model '{fallback_model}' failed ({provider}): {e2}")

        return {"content": None, "tokens_used": 0, "model_used": "offline"}

    async def generate_study_plan(
        self,
        profile: dict,
        progress: dict,
        weak_subjects: list[str],
        custom_groq_key: Optional[str] = None,
        custom_openai_key: Optional[str] = None
    ) -> dict:
        """Generate a personalized daily study plan."""
        subjects = profile.get("subjects", []) or ["Mathematics", "Physics", "Chemistry"]
        study_hours = profile.get("study_hours_per_day", 3)
        class_level = profile.get("class_level", "Class 12")
        stream = profile.get("stream", "Science")

        subjects_info = []
        for s in subjects:
            mastery = progress.get(s, {}).get("mastery_percentage", 30) if isinstance(progress.get(s), dict) else 30
            is_weak = s in weak_subjects
            subjects_info.append({"subject": s, "mastery": mastery, "is_weak": is_weak})

        prompt = f"""You are an elite academic tutor and study architect. Create a personalized, high-impact daily study plan.

Student Profile:
- Name: {profile.get('name', 'Student')}
- Class Level: {class_level}
- Academic Stream: {stream}
- Total Study Hours Today: {study_hours} hours ({study_hours * 60} minutes)
- Active Subjects: {', '.join(subjects)}
- Weak Priority Areas: {', '.join(weak_subjects) if weak_subjects else 'None marked'}

Subject Mastery Data:
{json.dumps(subjects_info, indent=2)}

Guidelines:
1. Total time must equal approximately {study_hours * 60} minutes.
2. Allocate at least 40% of time to weak subjects or lower-mastery subjects.
3. Every block must feature a SPECIFIC chapter topic and an actionable task description (e.g. "Work through 5 past-paper problems on projectile motion" rather than "Study physics").
4. Divide the study into 3 to 5 realistic, high-focus blocks (25-75 minutes each).

Return ONLY valid JSON matching this schema:
{{
  "blocks": [
    {{
      "subject": "Physics",
      "topic": "Newtonian Dynamics & Friction",
      "minutes": 45,
      "task_description": "Draw free-body diagrams for inclined planes and solve 4 numerical problems on static vs kinetic friction.",
      "is_weak_subject": true
    }}
  ]
}}"""

        result = await self._chat_completion(
            messages=[
                {"role": "system", "content": "You are a master academic planner. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            custom_groq_key=custom_groq_key,
            custom_openai_key=custom_openai_key
        )

        if result["content"]:
            try:
                plan_data = json.loads(result["content"])
                if "blocks" in plan_data and isinstance(plan_data["blocks"], list) and len(plan_data["blocks"]) > 0:
                    return {
                        "plan": plan_data,
                        "tokens_used": result["tokens_used"],
                        "model_used": result["model_used"]
                    }
            except json.JSONDecodeError:
                pass

        return self._fallback_plan(profile, progress, weak_subjects)

    async def generate_quiz(
        self,
        subject: str,
        topic: str,
        difficulty: str = "medium",
        num_questions: int = 5,
        context: Optional[dict] = None,
        custom_groq_key: Optional[str] = None,
        custom_openai_key: Optional[str] = None
    ) -> dict:
        """Generate a quiz for a specific topic."""
        difficulty_prompts = {
            "easy": "conceptual understanding and basic recall",
            "medium": "application, analysis, and problem-solving steps",
            "hard": "multi-concept integration and rigorous exam-level evaluation"
        }

        prompt = f"""Generate a {difficulty} difficulty multiple-choice quiz for the subject '{subject}', focused on the topic '{topic}'.
Target depth: {difficulty_prompts.get(difficulty, 'application and understanding')}
Number of questions: {num_questions}

Requirements:
1. Each question must have:
   - "question": A precise, challenging question.
   - "options": 4 distinct options ["A", "B", "C", "D"].
   - "answer": Index of correct option (0, 1, 2, or 3).
   - "explanation": Clear 1-2 sentence explanation of why this answer is correct and why other options fail.
2. Never repeat questions or use generic placeholder choices.

Return ONLY valid JSON matching this schema:
{{
  "questions": [
    {{
      "question": "What is the primary factor determining...",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": 0,
      "explanation": "Option A is correct because..."
    }}
  ]
}}"""

        result = await self._chat_completion(
            messages=[
                {"role": "system", "content": "You are a senior exam creator. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            custom_groq_key=custom_groq_key,
            custom_openai_key=custom_openai_key
        )

        if result["content"]:
            try:
                quiz_data = json.loads(result["content"])
                if "questions" in quiz_data and isinstance(quiz_data["questions"], list) and len(quiz_data["questions"]) > 0:
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
        level: str = "high_school",
        custom_groq_key: Optional[str] = None,
        custom_openai_key: Optional[str] = None
    ) -> dict:
        """Generate a pedagogical breakdown for a topic."""
        prompt = f"""Provide an in-depth, intuitive pedagogical explanation of '{topic}' in the subject '{subject}' for a {level} student.

Return ONLY valid JSON matching this schema:
{{
  "overview": "A clear, compelling 2-3 sentence overview explaining what the concept is and why it matters.",
  "key_concepts": [
    "First core principle with brief intuition",
    "Second core principle with real-world connection",
    "Third core principle with edge case consideration"
  ],
  "formulas_rules": [
    "Key equation or formal rule",
    "Secondary relationship or condition"
  ],
  "common_mistakes": [
    "Classic exam trap or misconception #1",
    "Classic exam trap or misconception #2"
  ],
  "practice_tip": "One actionable memory retention or problem-solving heuristic for this topic."
}}"""

        result = await self._chat_completion(
            messages=[
                {"role": "system", "content": "You are an award-winning STEM educator. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
            custom_groq_key=custom_groq_key,
            custom_openai_key=custom_openai_key
        )

        if result["content"]:
            try:
                data = json.loads(result["content"])
                if "overview" in data:
                    return {
                        "explanation": data,
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
        weak_areas: list[str],
        custom_groq_key: Optional[str] = None,
        custom_openai_key: Optional[str] = None
    ) -> dict:
        """Generate a focused practice sprint."""
        prompt = f"""Create an active practice sprint for '{subject}' - '{topic}'.
Student Mastery Level: {mastery}%
Flagged Weak Areas: {', '.join(weak_areas) if weak_areas else 'None'}

Return ONLY valid JSON:
{{
  "warmup": [
    "Quick recall question or conceptual check 1",
    "Quick recall question or conceptual check 2"
  ],
  "main_practice": [
    {{"type": "numerical/problem", "description": "Specific problem statement 1", "hint": "Useful conceptual hint without giving away the full answer"}},
    {{"type": "application", "description": "Specific problem statement 2", "hint": "Step-by-step guidance"}}
  ],
  "challenge": {{
    "description": "High-order thinking challenge problem",
    "hint": "Key insight to break down the complexity"
  }},
  "self_check": [
    "Did you double check units / boundary conditions?",
    "Can you explain the main rationale in 30 seconds?"
  ]
}}"""

        result = await self._chat_completion(
            messages=[
                {"role": "system", "content": "You are an expert tutor designing deliberate practice. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.6,
            custom_groq_key=custom_groq_key,
            custom_openai_key=custom_openai_key
        )

        if result["content"]:
            try:
                data = json.loads(result["content"])
                if "main_practice" in data:
                    return {
                        "practice": data,
                        "tokens_used": result["tokens_used"],
                        "model_used": result["model_used"]
                    }
            except json.JSONDecodeError:
                pass

        return self._fallback_practice(subject, topic)

    async def chat(
        self,
        messages: list[dict],
        context: Optional[dict] = None,
        custom_groq_key: Optional[str] = None,
        custom_openai_key: Optional[str] = None
    ) -> dict:
        """Non-streaming chat response."""
        system_prompt = """You are StudyMentor AI, an expert, empathetic study coach and tutor.
Your goals:
- Explain complex topics using vivid metaphors and structured breakdowns.
- Help students structure their study routines, overcome procrastination, and apply active recall.
- Format responses cleanly with bold headings, bullet points, and code/math blocks where helpful.
- Keep responses focused, encouraging, and actionable."""

        if context:
            system_prompt += f"\n\nStudent Profile Context: {json.dumps(context)}"

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        result = await self._chat_completion(
            messages=full_messages,
            custom_groq_key=custom_groq_key,
            custom_openai_key=custom_openai_key
        )

        if result["content"]:
            return result

        # Dynamic offline pedagogical reasoning response
        user_query = messages[-1].get("content", "") if messages else ""
        offline_reply = self._generate_offline_chat_response(user_query, context)
        return {"content": offline_reply, "tokens_used": 0, "model_used": "offline-pedagogy"}

    async def chat_stream(
        self,
        messages: list[dict],
        context: Optional[dict] = None,
        custom_groq_key: Optional[str] = None,
        custom_openai_key: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream chat response."""
        client, model, _, _ = self._get_active_client(custom_groq_key, custom_openai_key)
        if not client:
            user_query = messages[-1].get("content", "") if messages else ""
            reply = self._generate_offline_chat_response(user_query, context)
            for word in reply.split(" "):
                yield word + " "
            return

        system_prompt = "You are StudyMentor AI, an encouraging and expert study tutor. Provide structured, insightful answers."
        if context:
            system_prompt += f"\nStudent Context: {json.dumps(context)}"

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            stream = await client.chat.completions.create(
                model=model,
                messages=full_messages,
                max_tokens=self.max_tokens,
                temperature=0.7,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            fallback_reply = self._generate_offline_chat_response(messages[-1].get("content", ""), context)
            yield f"\n*(AI Network Notice: Switched to intelligent offline mode - {e})*\n\n{fallback_reply}"

    # -------------------------------------------------------------
    # Curated Academic Curriculum & Offline Engine
    # -------------------------------------------------------------
    def _generate_offline_chat_response(self, query: str, context: Optional[dict] = None) -> str:
        q = query.lower()
        if "plan" in q or "schedule" in q or "routine" in q:
            return (
                "### 📅 Recommended Study Strategy\n\n"
                "To maximize retention and minimize cognitive fatigue, follow the **Pomodoro Power Schedule**:\n\n"
                "1. **Deep Focus Block (50 min)**: Tackle your most difficult subject first thing (e.g. your weakest topic) while mental energy is peak.\n"
                "2. **Cognitive Reset (10 min)**: Step away from screens, stretch, and hydrate.\n"
                "3. **Practice & Problem Solving (40 min)**: Apply the Feynman Technique—write down solutions as if teaching a beginner.\n"
                "4. **Active Recall Quiz (20 min)**: Test yourself with 5-10 flashcard or quiz questions before concluding.\n\n"
                "💡 *Pro Tip*: Never study two similar topics back-to-back (e.g., separate Algebra from Calculus with English or Biology to prevent memory interference)."
            )
        elif "exam" in q or "test" in q or "stress" in q:
            return (
                "### 🎯 Exam Preparation & Mastery Protocol\n\n"
                "1. **Prioritize High-Yield Topics**: Focus 70% of remaining time on topics carrying the highest weight and past exam question patterns.\n"
                "2. **The 3-Pass Rule**: In exams, answer all confident questions first (Pass 1), calculation-heavy questions second (Pass 2), and leave unknown or hard questions for Pass 3.\n"
                "3. **Error Log**: Keep a notebook of every single quiz error. Re-solve missed problems 24 hours later to lock in the correction.\n\n"
                "You've got this! Consistency beats cramming every time."
            )
        elif "math" in q or "calculus" in q or "equation" in q:
            return (
                "### 📐 Mathematics Study Guide\n\n"
                "- **Understand, Don't Memorize**: Mathematical formulas are derived from fundamental geometric or algebraic truths. Always understand *why* a formula works before memorizing it.\n"
                "- **The Scaffold Method**: Start with 2 basic textbook examples, move to 3 medium-level application problems, and end with 1 multi-step past-exam question.\n"
                "- **Common Pitfall**: Watch out for sign errors when expanding parentheses or transposing terms across an inequality."
            )
        elif "physics" in q or "mechanics" in q:
            return (
                "### ⚡ Physics Mastery Guide\n\n"
                "- **Free Body Diagrams (FBDs)**: 80% of mechanics mistakes happen because an external force or component was omitted in the initial diagram.\n"
                "- **Dimensional Analysis**: Always verify the units on both sides of your final equation before moving on.\n"
                "- **Conservation Laws**: When kinematics seems too complex, check if Conservation of Energy or Momentum can simplify the problem."
            )
        return (
            f"### 💡 StudyMentor Guidance\n\n"
            f"Here are key insights regarding your question:\n\n"
            f"- **Active Recall**: Convert your notes into questions and answers rather than passively re-reading.\n"
            f"- **Spaced Repetition**: Review this topic again in 2 days, then in 5 days, to prevent the Ebbinghaus forgetting curve.\n"
            f"- **Self-Testing**: Use the **Take Quiz** tab on your dashboard to instantly assess your mastery and uncover blind spots.\n\n"
            f"*(Connect your Groq API key in AI Settings for live unbounded LLM chat on any topic!)*"
        )

    def _fallback_plan(self, profile: dict, progress: dict, weak_subjects: list[str]) -> dict:
        subjects = profile.get("subjects", []) or ["Math", "Physics", "Chemistry"]
        study_hours = profile.get("study_hours_per_day", 3)
        total_minutes = study_hours * 60
        blocks = []

        curriculum_map = {
            "Math": [("Quadratic Equations & Roots", "Derive roots using quadratic formula and solve 5 factorisation problems"),
                     ("Differential Calculus", "Practice chain rule and finding local maxima/minima on curve sketches")],
            "Mathematics": [("Calculus Fundamentals", "Practice chain rule and tangent line calculations"),
                            ("Vectors & Matrices", "Solve matrix determinant and inverse problems")],
            "Physics": [("Newton's Laws & Friction", "Draw free-body diagrams for inclined planes and compute normal forces"),
                        ("Work, Energy & Power", "Apply work-energy theorem to conservative and non-conservative systems")],
            "Chemistry": [("Chemical Bonding & Molecular Orbitals", "Draw Lewis structures and predict hybridization geometries"),
                          ("Thermodynamics & Enthalpy", "Calculate reaction enthalpy using Hess's law")],
            "Biology": [("Cellular Respiration & Glycolysis", "Trace glucose breakdown pathway through Krebs cycle and ATP yield"),
                        ("Mendelian Genetics", "Construct Punnett squares for dihybrid crosses and calculate phenotypic ratios")],
            "Computer Science": [("Data Structures & Complexity", "Implement stack operations and calculate Big-O time complexity"),
                                 ("Object-Oriented Programming", "Design classes with inheritance, encapsulation, and polymorphism")],
            "Economics": [("Demand & Supply Elasticity", "Graph consumer surplus shifts and calculate price elasticity coefficients"),
                          ("Fiscal & Monetary Policy", "Analyze Central Bank reserve ratio impacts on inflation and money supply")],
            "History": [("Modern World Revolutions", "Compare industrialization impacts on urban labor and constitutional reforms"),
                        ("Post-War Geopolitics", "Summarize key treaties, alliances, and economic reconstruction phases")],
            "Accountancy": [("Journal Entries & Ledger Posting", "Record debit/credit ledger transactions with dual-aspect balance"),
                            ("Balance Sheet Preparation", "Categorize current assets and long-term liabilities accurately")],
            "Business Studies": [("Principles of Management", "Evaluate Fayol's 14 principles applied to organizational hierarchies"),
                                 ("Marketing Mix (4 Ps)", "Formulate pricing and distribution strategies for consumer goods")]
        }

        allocations = []
        n = min(len(subjects), 4)
        selected_subjects = subjects[:n]
        remaining = total_minutes

        for i, s in enumerate(selected_subjects):
            is_weak = s in weak_subjects
            mins = 50 if is_weak else 35
            mins = min(mins, max(25, remaining // max(1, (n - i))))
            remaining -= mins
            allocations.append((s, mins, is_weak))

        if allocations and remaining > 0:
            allocations[0] = (allocations[0][0], allocations[0][1] + remaining, allocations[0][2])

        for s, mins, is_weak in allocations:
            topics = curriculum_map.get(s, [
                (f"{s} Core Mastery", f"Review foundational chapters of {s} and complete 4 end-of-unit problems")
            ])
            top_title, top_desc = topics[0] if is_weak else topics[-1]
            blocks.append({
                "subject": s,
                "topic": top_title,
                "minutes": mins,
                "task_description": top_desc,
                "is_weak_subject": is_weak
            })

        return {"plan": {"blocks": blocks}, "tokens_used": 0, "model_used": "offline-curriculum"}

    def _fallback_explanation(self, subject: str, topic: str) -> dict:
        curriculum_explanations = {
            "Math": {
                "overview": f"{topic} forms the foundation of mathematical problem-solving, governing relationships between variables and rates of change.",
                "key_concepts": [
                    "Formulating algebraic expressions from geometric or word problems.",
                    "Applying transformation rules while maintaining arithmetic equivalence.",
                    "Testing solutions against boundary conditions and constraints."
                ],
                "formulas_rules": [
                    "Quadratic formula: x = (-b ± √(b² - 4ac)) / (2a)",
                    "Discriminant rule: D > 0 (two real roots), D = 0 (repeated root), D < 0 (complex roots)"
                ],
                "common_mistakes": [
                    "Forgetting the ± symbol when taking square roots on both sides.",
                    "Dividing both sides of an inequality by a negative number without flipping the inequality sign."
                ],
                "practice_tip": "Always substitute your computed roots back into the original equation to verify that both sides balance."
            },
            "Physics": {
                "overview": f"{topic} explains how physical objects interact through fundamental forces, conservation laws, and energy transfer.",
                "key_concepts": [
                    "Every mechanical system responds according to net unbalanced force (F_net = ma).",
                    "Energy cannot be created or destroyed, only transformed between kinetic, potential, and thermal forms.",
                    "Forces always occur in matched interaction pairs acting on distinct bodies (Newton's 3rd Law)."
                ],
                "formulas_rules": [
                    "Newton's Second Law: ΣF = m · a",
                    "Kinetic Energy: KE = 1/2 · m · v² | Work-Energy: W_net = ΔKE"
                ],
                "common_mistakes": [
                    "Confusing action-reaction pairs as canceling forces on the same object.",
                    "Neglecting friction or air resistance direction (always opposite to relative motion)."
                ],
                "practice_tip": "Start every physics problem by drawing a clear Free Body Diagram (FBD) and establishing positive coordinate axes."
            },
            "Chemistry": {
                "overview": f"{topic} describes the electronic structure, valence electron sharing, and thermodynamics driving chemical reactivity.",
                "key_concepts": [
                    "Atoms bond to achieve stable electronic configurations with minimized potential energy.",
                    "Molecular geometry is dictated by electron pair repulsions in valence shells (VSEPR theory).",
                    "Le Chatelier's Principle: systems at equilibrium shift to counteract applied changes in pressure, volume, or temperature."
                ],
                "formulas_rules": [
                    "Gibbs Free Energy: ΔG = ΔH - TΔS (Spontaneous when ΔG < 0)",
                    "Ideal Gas Law: PV = nRT"
                ],
                "common_mistakes": [
                    "Confusing intermediate transition states with stable reaction intermediates.",
                    "Forgetting that catalyst additions alter activation energy without shifting equilibrium position."
                ],
                "practice_tip": "Track oxidation numbers and electron transfers explicitly when balancing complex redox and ionic reactions."
            }
        }

        subj_key = next((k for k in curriculum_explanations if k.lower() in subject.lower()), None)
        if subj_key:
            return {"explanation": curriculum_explanations[subj_key], "tokens_used": 0, "model_used": "offline-curriculum"}

        return {
            "explanation": {
                "overview": f"{topic} is a cornerstone concept in {subject}, linking core theoretical models with practical real-world applications.",
                "key_concepts": [
                    f"Understanding the fundamental definitions and axiomatic properties of {topic}.",
                    f"Analyzing how {topic} influences interconnected systems and processes.",
                    "Applying structured analytical techniques to solve multi-stage problems."
                ],
                "formulas_rules": [
                    "Standard Governing Equation: Input + Generation = Output + Accumulation",
                    "Conservation Principle: Total system measure is conserved under isolated conditions."
                ],
                "common_mistakes": [
                    "Conflating correlation with direct causation in system analysis.",
                    "Overlooking boundary constraints and edge condition assumptions."
                ],
                "practice_tip": "Use deliberate practice: break the topic into micro-skills and solve targeted exercises with increasing difficulty."
            },
            "tokens_used": 0,
            "model_used": "offline-curriculum"
        }

    def _fallback_practice(self, subject: str, topic: str) -> dict:
        return {
            "practice": {
                "warmup": [
                    f"State the core definition of {topic} in your own words without checking notes.",
                    f"Identify which key variables directly influence {topic}."
                ],
                "main_practice": [
                    {
                        "type": "Application Problem",
                        "description": f"Calculate the expected outcome when input parameters for {topic} are doubled under standard conditions.",
                        "hint": "Check the power or order of the governing variable in the primary formula."
                    },
                    {
                        "type": "Analytical Reasoning",
                        "description": f"A student claims that altering external constraints will invert the outcome of {topic}. Evaluate this claim.",
                        "hint": "Look for equilibrium thresholds and limiting factors."
                    }
                ],
                "challenge": {
                    "description": f"Derive the secondary relationship for {topic} starting from first principles.",
                    "hint": "Set up a balance equation between opposing forces or rates."
                },
                "self_check": [
                    "Did you include appropriate units and verify dimensional consistency?",
                    "Can you explain why the opposite hypothesis fails?"
                ]
            },
            "tokens_used": 0,
            "model_used": "offline-curriculum"
        }

    def _fallback_quiz(self, subject: str, topic: str, difficulty: str, num_questions: int) -> dict:
        curriculum_quizzes = {
            "Math": [
                {
                    "question": "What does the discriminant (b² - 4ac) of a quadratic equation ax² + bx + c = 0 signify if it is strictly greater than 0?",
                    "options": ["Two distinct real roots exist", "Two complex conjugate roots exist", "Exactly one repeated real root exists", "No roots exist"],
                    "answer": 0,
                    "explanation": "When b² - 4ac > 0, the square root yields a positive real number, giving two distinct real roots."
                },
                {
                    "question": "What is the derivative of f(x) = ln(x) with respect to x for x > 0?",
                    "options": ["1 / x", "e^x", "x", "1 / x²"],
                    "answer": 0,
                    "explanation": "By definition of logarithmic differentiation, d/dx[ln(x)] = 1/x."
                },
                {
                    "question": "If two lines are perpendicular in the Cartesian plane and the slope of the first line is m (m ≠ 0), what is the slope of the second line?",
                    "options": ["-1 / m", "m", "-m", "1 / m"],
                    "answer": 0,
                    "explanation": "Perpendicular lines satisfy m1 · m2 = -1, hence m2 = -1 / m1."
                },
                {
                    "question": "What is the value of ∫ (2x + 3) dx evaluated from x = 0 to x = 2?",
                    "options": ["10", "8", "12", "6"],
                    "answer": 0,
                    "explanation": "The antiderivative is [x² + 3x]. Evaluated from 0 to 2: (2² + 3(2)) - (0) = 4 + 6 = 10."
                },
                {
                    "question": "Which of the following matrices is invertible?",
                    "options": ["A matrix with determinant ≠ 0", "A matrix with all zero entries", "A matrix whose determinant is 0", "Any non-square matrix"],
                    "answer": 0,
                    "explanation": "A square matrix is invertible if and only if its determinant is non-zero."
                }
            ],
            "Physics": [
                {
                    "question": "According to Newton's First Law of Motion, what happens to an object moving at constant velocity if no net external force acts upon it?",
                    "options": ["It continues at constant velocity in a straight line", "It gradually slows down due to inertia", "It accelerates in the direction of its momentum", "It comes to an abrupt halt"],
                    "answer": 0,
                    "explanation": "An object in motion remains in uniform straight-line motion unless acted upon by a net external force."
                },
                {
                    "question": "If the kinetic energy of an object is quadrupled, by what factor did its velocity increase?",
                    "options": ["2", "4", "8", "16"],
                    "answer": 0,
                    "explanation": "Kinetic Energy = 1/2 m v². Since KE is proportional to v², quadrupling KE means v increased by √4 = 2."
                },
                {
                    "question": "Which thermodynamic law states that the entropy of an isolated system always increases over time in a spontaneous process?",
                    "options": ["Second Law of Thermodynamics", "First Law of Thermodynamics", "Zeroth Law of Thermodynamics", "Third Law of Thermodynamics"],
                    "answer": 0,
                    "explanation": "The Second Law dictates that total entropy of an isolated system never decreases in natural processes."
                },
                {
                    "question": "What is the SI unit of electric potential difference?",
                    "options": ["Volt", "Ampere", "Ohm", "Watt"],
                    "answer": 0,
                    "explanation": "The volt (V) is the SI unit of electric potential, equivalent to one joule per coulomb."
                },
                {
                    "question": "When light passes from a less dense optical medium into a denser optical medium at an angle, how does the ray bend?",
                    "options": ["Toward the normal", "Away from the normal", "Reflects back at 90 degrees", "Travels straight without deviation"],
                    "answer": 0,
                    "explanation": "Entering an optically denser medium reduces wave speed, bending the refracted ray toward the normal line."
                }
            ],
            "Chemistry": [
                {
                    "question": "Which type of chemical bond involves the electrostatic attraction between oppositely charged ions formed by electron transfer?",
                    "options": ["Ionic bond", "Covalent bond", "Hydrogen bond", "Metallic bond"],
                    "answer": 0,
                    "explanation": "Ionic bonding occurs between metals and non-metals via complete electron transfer."
                },
                {
                    "question": "What is the pH of a neutral aqueous solution at 25°C?",
                    "options": ["7", "0", "14", "1"],
                    "answer": 0,
                    "explanation": "At 25°C, pure water has [H+] = [OH-] = 10^-7 M, resulting in pH = -log(10^-7) = 7."
                },
                {
                    "question": "According to Le Chatelier's Principle, how will an exothermic reaction at equilibrium respond to an increase in temperature?",
                    "options": ["Shift toward reactants (left)", "Shift toward products (right)", "No shift occurs", "Equilibrium constant increases"],
                    "answer": 0,
                    "explanation": "For exothermic reactions, heat is a product. Adding heat shifts equilibrium toward reactants to absorb heat."
                },
                {
                    "question": "What hybridization is present in the central carbon of a methane (CH4) molecule?",
                    "options": ["sp³", "sp²", "sp", "sp³d"],
                    "answer": 0,
                    "explanation": "Methane has 4 single sigma bonds and no lone pairs, forming a tetrahedral geometry with sp³ hybridization."
                },
                {
                    "question": "What is the term for a substance that increases the rate of a chemical reaction without being consumed?",
                    "options": ["Catalyst", "Inhibitor", "Substrate", "Solvent"],
                    "answer": 0,
                    "explanation": "A catalyst provides an alternative reaction pathway with lower activation energy."
                }
            ]
        }

        subj_key = next((k for k in curriculum_quizzes if k.lower() in subject.lower()), None)
        questions = curriculum_quizzes.get(subj_key, [
            {
                "question": f"Which principle is central to mastering {topic} in {subject}?",
                "options": [
                    "Active recall and systematic application to practice problems",
                    "Passive memorization of formulas without understanding",
                    "Studying only the day before exams",
                    "Ignoring intermediate steps in calculations"
                ],
                "answer": 0,
                "explanation": f"Effective mastery of {subject} requires active problem-solving and foundational concept mapping."
            },
            {
                "question": f"When analyzing a complex problem in {topic}, what is the best first step?",
                "options": [
                    "Identify the given parameters and state the governing equation",
                    "Immediately guess the final numerical answer",
                    "Skip all assumptions and boundary conditions",
                    "Look up the solution without attempting"
                ],
                "answer": 0,
                "explanation": "Formalizing given variables and identifying boundary conditions prevents logical errors."
            },
            {
                "question": f"How do expert students retain concepts in {topic} long term?",
                "options": [
                    "Using spaced repetition and periodic diagnostic testing",
                    "Highlighting the entire textbook chapter in color",
                    "Re-reading notes 10 times consecutively",
                    "Avoiding self-testing"
                ],
                "answer": 0,
                "explanation": "Spaced repetition halts the forgetting curve and strengthens neural consolidation."
            }
        ])

        return {"quiz": {"questions": questions[:num_questions]}, "tokens_used": 0, "model_used": "offline-curriculum"}


ai_service = AIService()
