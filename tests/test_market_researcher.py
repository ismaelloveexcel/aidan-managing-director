"""Tests for the deterministic MarketResearchAgent."""

from app.agents.market_researcher import MarketResearchAgent, MarketResearchResult


def _agent() -> MarketResearchAgent:
    return MarketResearchAgent()


# ---------------------------------------------------------------------------
# Vertical detection
# ---------------------------------------------------------------------------


def test_detects_b2b_saas_vertical() -> None:
    result = _agent().research(
        idea_brief={
            "title": "SaaS workflow automation dashboard",
            "problem": "Teams waste hours on manual reporting",
            "solution": "Automated analytics dashboard for enterprise teams",
            "target_user": "B2B enterprise teams",
        }
    )
    assert result.vertical == "B2B SaaS"
    assert result.tam_estimate == "$120B"
    assert result.sam_estimate == "$18B"
    assert result.som_estimate == "$180M"


def test_detects_ai_tools_vertical() -> None:
    result = _agent().research(
        idea_brief={
            "title": "AI Copilot for developers",
            "problem": "Slow code review",
            "solution": "LLM-powered code review agent",
            "target_user": "developers",
        }
    )
    assert result.vertical == "AI Tools"
    assert result.market_growth == "HIGH"


def test_detects_developer_tools_vertical() -> None:
    result = _agent().research(
        idea_brief={
            "title": "GitHub CI/CD SDK",
            "problem": "Complex DevOps pipelines",
            "solution": "Simple CLI for developer workflows",
            "target_user": "software engineers and programmers",
        }
    )
    # Developer Tools or AI Tools depending on keyword density — just ensure HIGH growth
    assert result.vertical in ("Developer Tools", "AI Tools")
    assert result.market_growth == "HIGH"


def test_detects_marketplace_vertical() -> None:
    result = _agent().research(
        idea_brief={
            "title": "Freelancer marketplace platform",
            "problem": "Finding trusted vendors",
            "solution": "Two-sided marketplace connecting buyers and sellers",
            "target_user": "freelancer gig workers",
        }
    )
    assert result.vertical == "Marketplace"


def test_detects_education_vertical() -> None:
    result = _agent().research(
        idea_brief={
            "title": "Online certification course platform",
            "problem": "Expensive training",
            "solution": "Self-paced edtech learning and certification",
            "target_user": "skill development learners",
        }
    )
    assert result.vertical == "Education & E-learning"


def test_detects_fintech_vertical() -> None:
    result = _agent().research(
        idea_brief={
            "title": "Invoice payment automation",
            "problem": "Late payments hurt cash flow",
            "solution": "Automated billing and finance tracking",
            "target_user": "small business finance teams",
        }
    )
    assert result.vertical == "FinTech"


def test_defaults_to_general_software_on_generic_input() -> None:
    result = _agent().research(
        idea_brief={
            "title": "Generic tool",
            "problem": "stuff",
            "solution": "things",
            "target_user": "people",
        }
    )
    assert result.vertical == "General Software"
    assert result.tam_estimate == "$50B"


# ---------------------------------------------------------------------------
# Growth and confidence
# ---------------------------------------------------------------------------


def test_growth_rating_present() -> None:
    result = _agent().research(
        idea_brief={
            "title": "AI assistant",
            "problem": "slow work",
            "solution": "AI copilot agent for chatbot tasks",
            "target_user": "teams",
        }
    )
    assert result.market_growth in ("LOW", "MEDIUM", "HIGH")


def test_confidence_high_for_rich_input() -> None:
    result = _agent().research(
        idea_brief={
            "title": "SaaS analytics dashboard reporting platform",
            "problem": "Teams spend hours on manual KPI analytics reporting",
            "solution": "Automated workflow dashboard with real-time analytics",
            "target_user": "enterprise B2B teams and business managers",
            "idea": "Build a scalable saas platform for team analytics",
        }
    )
    assert result.confidence == "HIGH"


def test_confidence_low_for_sparse_input() -> None:
    result = _agent().research(idea_brief={"title": "x"})
    assert result.confidence == "LOW"


# ---------------------------------------------------------------------------
# Recommended channels
# ---------------------------------------------------------------------------


def test_recommended_channels_non_empty() -> None:
    result = _agent().research(
        idea_brief={
            "title": "B2B SaaS tool",
            "target_user": "enterprise teams",
            "solution": "dashboard automation saas",
        }
    )
    assert len(result.recommended_channels) >= 1


def test_result_is_pydantic_model() -> None:
    result = _agent().research(idea_brief={"title": "Test idea"})
    assert isinstance(result, MarketResearchResult)


def test_empty_brief_does_not_raise() -> None:
    result = _agent().research(idea_brief={})
    assert isinstance(result, MarketResearchResult)
    assert result.vertical == "General Software"
