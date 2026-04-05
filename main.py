"""
main.py – FastAPI application entry point for AI-DAN Managing Director.

Registers all route modules and configures the application.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.routes import (
    analytics,
    analyze,
    approvals,
    chat,
    commands,
    control,
    factory,
    feedback,
    ideas,
    intelligence,
    memory,
    portfolio,
    projects,
)

_VERSION = "0.2.0"


@asynccontextmanager
async def _lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: clean up cached HTTP clients on shutdown."""
    yield
    # Shutdown: close cached AI provider clients to avoid leaking sockets.
    from app.core.dependencies import get_ai_provider

    try:
        get_ai_provider().close()
    except Exception:  # pragma: no cover – best-effort cleanup
        pass


app = FastAPI(
    title="AI-DAN Managing Director",
    description=(
        "Core managing director layer for strategy, idea generation, "
        "portfolio control, approvals, and command routing to the GitHub Factory."
    ),
    version=_VERSION,
    lifespan=_lifespan,
)

# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------
app.include_router(analyze.router, prefix="/api/analyze", tags=["Analyze"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(ideas.router, prefix="/ideas", tags=["Ideas"])
app.include_router(projects.router, prefix="/projects", tags=["Projects"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(approvals.router, prefix="/approvals", tags=["Approvals"])
app.include_router(commands.router, prefix="/commands", tags=["Commands"])
app.include_router(factory.router, prefix="/factory", tags=["Factory"])
app.include_router(memory.router, prefix="/memory", tags=["Memory"])
app.include_router(intelligence.router, prefix="/intelligence", tags=["Intelligence"])
app.include_router(control.router, prefix="/control", tags=["Control"])


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Return a simple health-check response."""
    return {"status": "ok"}
