# StudyMentor AI - Production-Ready Study Assistant

A full-stack AI-powered study assistant with personalized planning, quizzes, progress tracking, and real-time chat.

## Architecture

```
StudyMentor AI/
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── api/routes/      # API endpoints
│   │   ├── core/            # Config, security, dependencies
│   │   ├── db/              # Database session & models
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # AI service (OpenAI)
│   │   └── main.py          # FastAPI app entry point
│   ├── alembic/             # Database migrations
│   ├── tests/               # Pytest test suite
│   ├── requirements.txt     # Python dependencies
│   ├── Dockerfile           # Container configuration
│   └── .env.example         # Environment template
├── frontend/                # Vanilla JS Frontend
│   ├── index.html           # Landing page
│   ├── planning.html        # Study profile setup
│   ├── dashboard.html       # Main dashboard
│   ├── style.css            # Styling
│   └── script.js            # Frontend logic
├── docker-compose.yml       # Multi-container orchestration
└── README.md
```

## Features

### Backend (FastAPI)
- **Authentication**: JWT-based auth with httpOnly cookies
- **Study Profiles**: Class (9-12), streams (Science, Commerce, Arts, General, **Engineering**), subjects, weak areas, study hours
- **AI-Generated Plans**: Personalized daily study plans via OpenAI GPT-4o-mini
- **Progress Tracking**: Per-subject mastery, completed topics, weak areas
- **Quiz System**: AI-generated quizzes with multiple difficulties (easy/medium/hard) and explanations
- **AI Content Generation**: Explanations, practice sprints, real-time chat via WebSocket
- **Streak Tracking**: Daily login streaks with longest streak record
- **Database**: PostgreSQL with async SQLAlchemy + Alembic migrations
- **Testing**: Comprehensive pytest suite with async support

### Frontend (Vanilla JS)
- **Landing Page**: Hero, features, navigation
- **Planning Page**: Dynamic stream-based subject selection (updates subjects when stream changes), multi-step onboarding with validation
- **Dashboard**: Three-tab layout (Plan, Study, Progress)
- **Interactive Study**: Topic cards, AI-generated explanations, AI-generated practice sprints, AI-generated quizzes with "Generate New Quiz" button
- **Progress Visualization**: Bars, stats, weak subject alerts
- **Dark Mode**: Persisted theme preference
- **Hybrid Mode**: Works with backend API when available, falls back to localStorage offline mode
- **Engineering Stream**: 22 engineering subjects including Mathematics 1/2, Engineering Physics/Chemistry, Programming (C/Python), Data Structures, Thermodynamics, Control Systems, Digital Electronics, etc.

## Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL 16+ (or use Docker)
- **API Key (Groq recommended - free tier available at https://console.groq.com/keys)**

### Option 1: Docker (Recommended)

```bash
# Clone and navigate
cd StudyMentor AI

# Copy environment template (already includes a working Groq API key)
cp backend/.env.example backend/.env

# The .env.example already includes a working Groq API key!
# You can optionally add your own OpenAI key for GPT models

# Start all services
docker-compose up -d

# Backend available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Option 2: Local Development

```bash
cd StudyMentor AI/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment (already includes working Groq API key)
cp .env.example .env
# Optionally add your own OPENAI_API_KEY for GPT models

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

Open `frontend/index.html` directly in browser, or serve with any static server:
```bash
cd StudyMentor AI/frontend
python -m http.server 5500
# Visit http://localhost:5500
```

## API Documentation

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login user |
| POST | `/api/auth/logout` | Logout user |
| GET | `/api/auth/me` | Get current user |
| POST | `/api/auth/refresh` | Refresh access token |

### Study Profile
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/profile` | Create study profile |
| GET | `/api/profile` | Get study profile |
| PUT | `/api/profile` | Update study profile |
| DELETE | `/api/profile` | Delete study profile |

### Progress
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/progress` | Get all subject progress |
| GET | `/api/progress/{subject}` | Get specific subject progress |
| PUT | `/api/progress/{subject}` | Update subject progress |

### Study Plans
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/plan/generate` | Generate AI study plan |
| GET | `/api/plan/today` | Get today's plan |
| GET | `/api/plan/{date}` | Get plan for date |
| PUT | `/api/plan/blocks/{id}/complete` | Complete plan block |

### Quizzes
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/quiz/generate` | Generate AI quiz |
| GET | `/api/quiz` | List quizzes |
| GET | `/api/quiz/{id}` | Get quiz details |
| POST | `/api/quiz/{id}/attempt` | Attempt quiz |
| GET | `/api/quiz/attempts/history` | Get attempt history |
| GET | `/api/quiz/subjects/available` | Get available subjects |

### WebSocket
```
WS /api/ws/chat?token=<access_token>
```

Message types:
- `chat` - Regular chat with streaming response
- `generate_plan` - Generate study plan
- `generate_quiz` - Generate quiz
- `generate_explanation` - Generate topic explanation
- `generate_practice` - Generate practice sprint

## Database Schema

Key tables:
- `users` - Authentication and profile info
- `study_profiles` - Study preferences and subjects
- `subject_progress` - Per-subject mastery tracking
- `study_plans` - Daily AI-generated plans
- `study_plan_blocks` - Individual study blocks
- `quizzes` - AI-generated quizzes
- `quiz_attempts` - User quiz attempts with scores
- `user_streaks` - Login streak tracking
- `ai_content_generations` - AI usage logging

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `SECRET_KEY` | JWT signing key (32+ chars) | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `DEBUG` | Enable debug mode | No (default: false) |
| `ENVIRONMENT` | `development` or `production` | No |
| `CORS_ORIGINS` | Allowed CORS origins | No |

## Testing

```bash
cd backend
pytest tests/ -v --cov=app --cov-report=term-missing
```

## Production Deployment

1. **Set production environment variables**:
   ```bash
   ENVIRONMENT=production
   DEBUG=false
   SECRET_KEY=<secure-random-32-char-string>
   DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
   ```

2. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

3. **Use production WSGI server**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

4. **Configure reverse proxy** (nginx) with SSL

5. **Set up monitoring** (Prometheus/Grafana, Sentry)

## Frontend-Backend Integration

The frontend (`script.js`) currently uses `localStorage` for demo mode. To connect to backend:

1. Update `script.js` to use `fetch` API calls to `/api/*` endpoints
2. Handle authentication flow (login/register → store token)
3. Replace localStorage operations with API calls
4. Add WebSocket connection for real-time features

See `frontend/script.js` for the current localStorage implementation that can be adapted.

## Contributing

1. Fork the repository
2. Create feature branch
3. Write tests for new features
4. Ensure all tests pass
5. Submit pull request

## License

MIT License - see LICENSE file for details.