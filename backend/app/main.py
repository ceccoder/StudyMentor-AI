"""
StudyMentor AI - Main FastAPI Application Entry Point
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.db.session import engine, init_db
from app.api.routes import auth, study, quiz, websocket, ai
from app.models import models  # noqa: F401 - ensures models are registered


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="StudyMentor AI - Personalized AI Study Assistant API",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if settings.DEBUG:
        import traceback
        traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error" if not settings.DEBUG else str(exc)},
    )


# Health check
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(study.router, prefix="/api")
app.include_router(study.progress_router, prefix="/api")
app.include_router(study.plan_router, prefix="/api")
app.include_router(quiz.router, prefix="/api")
app.include_router(websocket.router, prefix="/api")
app.include_router(ai.router, prefix="/api")


# Custom OpenAPI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="StudyMentor AI - Personalized AI Study Assistant API",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
        "CookieAuth": {"type": "apiKey", "in": "cookie", "name": "access_token"},
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Serve static files for frontend
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if os.path.isfile(os.path.join(frontend_dir, "index.html")):
    from fastapi.responses import FileResponse

    @app.get("/", include_in_schema=False)
    async def serve_root():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/index.html", include_in_schema=False)
    async def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/planning.html", include_in_schema=False)
    async def serve_planning():
        return FileResponse(os.path.join(frontend_dir, "planning.html"))

    @app.get("/dashboard.html", include_in_schema=False)
    async def serve_dashboard():
        return FileResponse(os.path.join(frontend_dir, "dashboard.html"))

    @app.get("/style.css", include_in_schema=False)
    async def serve_css():
        return FileResponse(os.path.join(frontend_dir, "style.css"), media_type="text/css")

    @app.get("/script.js", include_in_schema=False)
    async def serve_js():
        return FileResponse(os.path.join(frontend_dir, "script.js"), media_type="application/javascript")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )