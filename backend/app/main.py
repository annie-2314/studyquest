"""FastAPI app: CORS, routers, and a consistent JSON error shape {detail, code}."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.api.routes import (health, auth, chat, study, courses, code, video,
                            game, plan, analytics, evaluation, materials, learning)
from app.observability import init_tracing

def _init_db() -> None:
    """Create any missing tables on boot so a fresh database (e.g. a brand-new
    cloud Postgres/SQLite on first deploy) is usable immediately. Importing
    `app.models` registers every table on the shared Base; create_all is a no-op
    for tables that already exist, so it's safe to run on every startup."""
    import app.models  # noqa: F401  (registers all ORM models on Base.metadata)
    from app.database import Base, engine

    # pgvector: ensure the extension exists before create_all builds vector columns.
    if settings.vector_backend == "pgvector":
        from sqlalchemy import text
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            pass  # extension may require superuser; surfaced at query time if missing

    Base.metadata.create_all(bind=engine)


app = FastAPI(title="StudyQuest AI", on_startup=[_init_db])

# Enable LangSmith tracing if configured (no-op otherwise).
init_tracing()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code,
                        content={"detail": exc.detail, "code": f"http_{exc.status_code}"})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422,
                        content={"detail": "Invalid request data", "code": "validation_error"})


app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(study.router, prefix="/api")
app.include_router(courses.router, prefix="/api")
app.include_router(code.router, prefix="/api")
app.include_router(video.router, prefix="/api")
app.include_router(game.router, prefix="/api")
app.include_router(plan.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(evaluation.router, prefix="/api")
app.include_router(materials.router, prefix="/api")
app.include_router(learning.router, prefix="/api")
