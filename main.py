"""
main.py – FastAPI application entry point for AI-DAN Managing Director.

Registers all route modules and configures the application.
"""

from fastapi import FastAPI

from app.routes import approvals, chat, commands, factory, feedback, ideas, portfolio, projects

app = FastAPI(
    title="AI-DAN Managing Director",
    description=(
        "Core managing director layer for strategy, idea generation, "
        "portfolio control, approvals, and command routing to the GitHub Factory."
    ),
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(ideas.router, prefix="/ideas", tags=["Ideas"])
app.include_router(projects.router, prefix="/projects", tags=["Projects"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
app.include_router(approvals.router, prefix="/approvals", tags=["Approvals"])
app.include_router(commands.router, prefix="/commands", tags=["Commands"])
app.include_router(factory.router, prefix="/factory", tags=["Factory"])


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Return a simple health-check response."""
    return {"status": "ok"}
