"""
WalchandGPT Backend — FastAPI Application Entry Point
"""
import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import auth, chat, conversations, documents, admin, feedback
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import engine, init_db
from app.models import Base  # noqa: F401 — import all models so Alembic sees them

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    setup_logging()
    log.info("WalchandGPT starting up", environment=settings.APP_ENV)

    # Initialize database tables (idempotent; use Alembic for migrations)
    try:
        await init_db()
    except Exception as e:
        log.warning("Database initialization deferred: PostgreSQL not reachable yet", error=str(e))

    # Initialize MCP connection pool
    from app.agents.mcp_client import mcp_client
    await mcp_client.connect()

    log.info("WalchandGPT ready")
    yield

    log.info("WalchandGPT shutting down")
    await mcp_client.disconnect()
    await engine.dispose()


# ── Rate limiter ────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── FastAPI application ─────────────────────────────────────────
app = FastAPI(
    title="WalchandGPT API",
    description="AI-Powered College Assistant for Walchand College of Engineering",
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ──────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["Conversations"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


@app.get("/api/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION, "env": settings.APP_ENV}
