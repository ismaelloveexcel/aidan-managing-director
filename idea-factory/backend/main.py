"""
Idea Factory — AI-powered idea validation tool.
Private single-user tool. No auth, no rate limiting.
Goals: decision quality and speed to revenue.
"""

import asyncio
import json
import os
from datetime import datetime
from html import escape  # Step 7: XSS protection
from typing import AsyncGenerator

import anthropic
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

# ── Env vars ──────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
GROK_API_KEY = os.getenv("GROK_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ideas.db")

# Step 5: Module-level Anthropic client — instantiated once, reused on every request
_claude_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

# ── Database ──────────────────────────────────────────────
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class IdeaDB(Base):
    __tablename__ = "ideas"

    id = Column(Integer, primary_key=True, index=True)
    idea_text = Column(Text, nullable=True)
    concept = Column(String, nullable=True)
    target_user = Column(String, nullable=True)
    core_pain = Column(String, nullable=True)
    value_promise = Column(String, nullable=True)
    price = Column(String, nullable=True)
    category = Column(String, nullable=True)
    g1r = Column(String, nullable=True)
    g2r = Column(String, nullable=True)
    g3r = Column(String, nullable=True)
    summary = Column(String, nullable=True)
    kill_reason = Column(String, nullable=True)
    final_decision = Column(String, nullable=True)
    score = Column(Integer, nullable=True)
    score_reasoning = Column(String, nullable=True)
    pain_score = Column(Integer, nullable=True)
    market_score = Column(Integer, nullable=True)
    execution_score = Column(Integer, nullable=True)
    why_it_fails = Column(String, nullable=True)
    what_must_be_true = Column(Text, nullable=True)
    directions = Column(Text, nullable=True)
    regional_scores = Column(Text, nullable=True)  # kept for backward compat; no longer written
    # Step 14: New columns
    fastest_revenue = Column(String, nullable=True)
    global_viability = Column(String, nullable=True)
    best_launch_market = Column(String, nullable=True)
    pricing_power = Column(String, nullable=True)
    global_scalability = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Step 14: Safe migration block — idempotent ALTER TABLE statements
_MIGRATE = [
    "ALTER TABLE ideas ADD COLUMN fastest_revenue TEXT",
    "ALTER TABLE ideas ADD COLUMN global_viability TEXT",
    "ALTER TABLE ideas ADD COLUMN best_launch_market TEXT",
    "ALTER TABLE ideas ADD COLUMN pricing_power TEXT",
    "ALTER TABLE ideas ADD COLUMN global_scalability TEXT",
]


def _run_migrations() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        for stmt in _MIGRATE:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass  # column already exists — safe to ignore


_run_migrations()

# ── App ───────────────────────────────────────────────────
app = FastAPI(title="Idea Factory")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ───────────────────────────────────────
class IdeaInput(BaseModel):
    idea: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatInput(BaseModel):
    messages: list[ChatMessage]
    state: dict = {}


# ── LLM helpers ───────────────────────────────────────────
async def _call_claude(
    prompt: str,
    max_tokens: int = 2000,
    system: str | None = None,
) -> str:
    """Call Claude using the module-level client (Step 5)."""
    kwargs: dict = {
        "model": "claude-opus-4-6",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    msg = await _claude_client.messages.create(**kwargs)
    return msg.content[0].text


async def _call_claude_messages(
    messages: list[dict],
    max_tokens: int = 2000,
    system: str | None = None,
) -> str:
    """Call Claude with a full message list (used by chat endpoint)."""
    kwargs: dict = {
        "model": "claude-opus-4-6",
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system
    msg = await _claude_client.messages.create(**kwargs)
    return msg.content[0].text


async def _call_perplexity(query: str) -> dict:
    if not PERPLEXITY_API_KEY:
        return {}
    async with httpx.AsyncClient(timeout=35) as client:
        resp = await client.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}"},
            json={
                "model": "llama-3.1-sonar-small-128k-online",
                "messages": [{"role": "user", "content": (
                    f"Market research for this startup idea: {query}\n"
                    "Give: market size estimate, 2-3 top competitors, "
                    "evidence of willingness to pay. Be concise."
                )}],
                "max_tokens": 600,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return {"perplexity_context": data["choices"][0]["message"]["content"]}


async def _call_grok(idea: str) -> dict:
    if not GROK_API_KEY:
        return {}
    async with httpx.AsyncClient(timeout=35) as client:
        resp = await client.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROK_API_KEY}"},
            json={
                "model": "grok-beta",
                "messages": [{"role": "user", "content": (
                    f"Contrarian take on this business idea in 2-3 sentences: {idea}"
                )}],
                "max_tokens": 300,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return {"grok_take": data["choices"][0]["message"]["content"]}


async def _call_gpt(idea: str) -> dict:
    if not OPENAI_API_KEY:
        return {}
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": (
                    f"Rate this startup idea 0-100 and give one sentence why.\n"
                    f"Idea: {idea}\n"
                    'Respond as JSON: {"gpt_score": 0, "gpt_reasoning": "..."}'
                )}],
                "max_tokens": 150,
                "response_format": {"type": "json_object"},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return json.loads(data["choices"][0]["message"]["content"])


# ── Claude analysis ───────────────────────────────────────
_ANALYZE_SYSTEM = (
    "You are a brutally honest startup idea evaluator. "
    "Surface the single biggest risk, quantify it, give a clear GO/SKIP/KILL verdict. "
    "Respond ONLY with valid JSON. No markdown, no text outside the JSON."
)


def _strip_json_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip().rstrip("`").strip()


async def analyze_with_claude(idea_text: str, context: str = "") -> dict:
    """Run the main Claude analysis. Returns structured dict."""
    ctx_block = f"\nAdditional context:\n{context}" if context else ""
    # Steps 11, 12, 13: fastest_revenue, kill_reason enforcement, global fields
    prompt = f"""Evaluate this startup idea:{ctx_block}

IDEA: {idea_text}

Return ONLY this JSON (no other text):
{{
  "concept": "One line: what it is",
  "target_user": "Specific person with this problem right now",
  "core_pain": "The specific pain being solved",
  "value_promise": "Why they pay — exact benefit",
  "price": "Suggested price point with brief rationale",
  "category": "B2B SaaS / Consumer / Marketplace / etc.",
  "pain_score": 0,
  "market_score": 0,
  "execution_score": 0,
  "gate1": {{"pass": true, "confidence": 0, "reasoning": "one sentence"}},
  "gate2": {{"pass": true, "confidence": 0, "reasoning": "one sentence"}},
  "gate3": {{"pass": true, "confidence": 0, "reasoning": "one sentence"}},
  "score": 0,
  "score_reasoning": "Two sentences max",
  "why_it_fails": "The single most likely failure mode",
  "what_must_be_true": ["assumption 1", "assumption 2", "assumption 3"],
  "directions": {{
    "safe": "Low-risk version of this idea",
    "fast": "Fastest path to first dollar",
    "high_upside": "Highest-ceiling version"
  }},
  "fastest_revenue": "One sentence: the exact first transaction possible this week. Who pays, what they pay for, which channel, in which market.",
  "final_decision": "GO or SKIP or KILL",
  "kill_reason": "REQUIRED if final_decision is SKIP or KILL. Must start with 'This fails because' and name the single specific reason. Never empty when skipping.",
  "summary": "Three sentences: problem, solution, verdict",
  "global_viability": "HIGH or MEDIUM or LOW — can this work as a digital-first global product?",
  "best_launch_market": "Single market where first dollar is most likely. Format: Market — one sentence why",
  "pricing_power": "LOW or MEDIUM or HIGH — willingness to pay in best launch market, one sentence why",
  "global_scalability": "One sentence: what must be true to expand beyond the launch market"
}}"""

    raw = await _call_claude(prompt, max_tokens=2000, system=_ANALYZE_SYSTEM)
    raw = _strip_json_fences(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start:end])
            except Exception:
                pass
    return {"error": "parse_failed", "raw": raw}


# ── Scoring ───────────────────────────────────────────────
def calculate_score(analysis: dict) -> int:
    """Composite score from gates + Claude score + sub-scores."""
    a = analysis
    s = 0

    # Gates: each contributes up to ~20 pts
    for gate_key in ("gate1", "gate2", "gate3"):
        gate = a.get(gate_key) or {}
        raw_val = gate.get("confidence", 50)
        # Step 9: Confidence capping
        try:
            conf = max(0, min(100, int(raw_val)))
        except Exception:
            conf = 50
        if gate.get("pass"):
            s += int(20 * conf / 100)
        else:
            s += int(20 * (100 - conf) / 100 * 0.15)

    # Claude's own score (40% weight)
    try:
        claude_score = max(0, min(100, int(a.get("score") or 0)))
    except Exception:
        claude_score = 0
    s = int(s * 0.6 + claude_score * 0.4)

    # Step 10: Feed sub-scores into the final number (8% weight)
    try:
        pain = max(0, min(100, int(a.get("pain_score") or 50)))
    except Exception:
        pain = 50
    try:
        market = max(0, min(100, int(a.get("market_score") or 50)))
    except Exception:
        market = 50
    try:
        execution = max(0, min(100, int(a.get("execution_score") or 50)))
    except Exception:
        execution = 50

    subscore = int((pain + market + execution) / 3 * 0.08)
    return min(s + subscore, 100)


# ── Result combining ──────────────────────────────────────
def combine_results(
    analysis: dict,
    perplexity: dict,
    grok: dict,
    gpt: dict,
) -> dict:
    """Merge all LLM outputs. Step 15: includes all new fields, no regional_scores."""
    return {
        "concept": analysis.get("concept", ""),
        "target_user": analysis.get("target_user", ""),
        "core_pain": analysis.get("core_pain", ""),
        "value_promise": analysis.get("value_promise", ""),
        "price": analysis.get("price", ""),
        "category": analysis.get("category", ""),
        "pain_score": analysis.get("pain_score", 50),
        "market_score": analysis.get("market_score", 50),
        "execution_score": analysis.get("execution_score", 50),
        "gate1": analysis.get("gate1", {}),
        "gate2": analysis.get("gate2", {}),
        "gate3": analysis.get("gate3", {}),
        "g1r": json.dumps(analysis.get("gate1", {})),
        "g2r": json.dumps(analysis.get("gate2", {})),
        "g3r": json.dumps(analysis.get("gate3", {})),
        "score": calculate_score(analysis),
        "score_reasoning": analysis.get("score_reasoning", ""),
        "why_it_fails": analysis.get("why_it_fails", ""),
        "what_must_be_true": analysis.get("what_must_be_true", []),
        "directions": analysis.get("directions", {}),
        "summary": analysis.get("summary", ""),
        "kill_reason": analysis.get("kill_reason", ""),
        "final_decision": analysis.get("final_decision", "SKIP"),
        # Step 15: New fields
        "fastest_revenue": analysis.get("fastest_revenue", ""),
        "global_viability": analysis.get("global_viability", ""),
        "best_launch_market": analysis.get("best_launch_market", ""),
        "pricing_power": analysis.get("pricing_power", ""),
        "global_scalability": analysis.get("global_scalability", ""),
        # Cross-LLM context
        "perplexity_context": perplexity.get("perplexity_context", ""),
        "grok_take": grok.get("grok_take", ""),
        "gpt_score": gpt.get("gpt_score"),
        "gpt_reasoning": gpt.get("gpt_reasoning", ""),
    }


# ── SSE streaming ─────────────────────────────────────────
def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def stream(idea_text: str) -> AsyncGenerator[str, None]:
    yield _sse("status", {"message": "Starting analysis…"})

    # Step 6: Gather 1 — Perplexity + Grok with 40s timeout each
    perplexity_result, grok_result = await asyncio.gather(
        asyncio.wait_for(_call_perplexity(idea_text), timeout=40),
        asyncio.wait_for(_call_grok(idea_text), timeout=40),
        return_exceptions=True,
    )
    if isinstance(perplexity_result, Exception):
        perplexity_result = {}
    if isinstance(grok_result, Exception):
        grok_result = {}

    yield _sse("status", {"message": "Market research done. Running deep analysis…"})

    context = (perplexity_result or {}).get("perplexity_context", "")

    # Step 6: Gather 2 — Claude + GPT with 55s timeout each
    # Claude runs first because GPT is independent; both can overlap on the network
    claude_result, gpt_result = await asyncio.gather(
        asyncio.wait_for(analyze_with_claude(idea_text, context), timeout=55),
        asyncio.wait_for(_call_gpt(idea_text), timeout=55),
        return_exceptions=True,
    )
    # Claude failure is fatal
    if isinstance(claude_result, Exception):
        raise claude_result
    if isinstance(gpt_result, Exception):
        gpt_result = {}

    if claude_result.get("error"):
        yield _sse("error", {"message": "Analysis failed — Claude returned unparseable output."})
        return

    yield _sse("status", {"message": "Analysis complete. Saving…"})

    result = combine_results(
        claude_result,
        perplexity_result or {},
        grok_result or {},
        gpt_result or {},
    )

    # Step 16: Save to DB with all new fields; Step 17: regional_scores=None
    db: Session = SessionLocal()
    try:
        row = IdeaDB(
            idea_text=idea_text,
            concept=result.get("concept"),
            target_user=result.get("target_user"),
            core_pain=result.get("core_pain"),
            value_promise=result.get("value_promise"),
            price=result.get("price"),
            category=result.get("category"),
            g1r=result.get("g1r"),
            g2r=result.get("g2r"),
            g3r=result.get("g3r"),
            summary=result.get("summary"),
            kill_reason=result.get("kill_reason"),
            final_decision=result.get("final_decision"),
            score=result.get("score"),
            score_reasoning=result.get("score_reasoning"),
            pain_score=result.get("pain_score"),
            market_score=result.get("market_score"),
            execution_score=result.get("execution_score"),
            why_it_fails=result.get("why_it_fails"),
            what_must_be_true=json.dumps(result.get("what_must_be_true", [])),
            directions=json.dumps(result.get("directions", {})),
            regional_scores=None,  # Step 17: no longer written
            fastest_revenue=result.get("fastest_revenue"),
            global_viability=result.get("global_viability"),
            best_launch_market=result.get("best_launch_market"),
            pricing_power=result.get("pricing_power"),
            global_scalability=result.get("global_scalability"),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        result["id"] = row.id
    finally:
        db.close()

    yield _sse("result", result)
    yield _sse("done", {"message": "Analysis complete"})


# ── Routes ────────────────────────────────────────────────
@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze_idea(body: IdeaInput) -> StreamingResponse:
    idea_text = body.idea.strip()
    if not idea_text:
        raise HTTPException(400, "Idea cannot be empty")
    # Step 8: Minimum idea length
    if len(idea_text) < 40:
        raise HTTPException(400, "Add more detail — describe the idea and who it's for")
    return StreamingResponse(stream(idea_text), media_type="text/event-stream")


# ── Step 18: Stateless brainstorm chat endpoint ───────────
_CHAT_SYSTEM = """\
You are a startup idea coach helping a founder clarify their idea through conversation.
Ask only 1-2 focused questions per turn. Infer what you can from context.
Prioritize learning: exact problem + who has it, evidence of willingness to pay,
fastest path to first dollar, top failure risk.
Respond ONLY with valid JSON: {"reply": "...", "state_update": {...}, "ready": false}
Set ready: true only when you have enough to write a full analysis (usually turn 5-8).\
"""

_FINAL_ANALYSIS_PROMPT = """\
Based on this founder conversation, produce a complete idea analysis.

CONVERSATION:
{conversation}

ACCUMULATED STATE:
{state}

Return ONLY this JSON:
{{
  "concept": "One line: what it is",
  "target_user": "Specific person with this problem",
  "core_pain": "The specific pain being solved",
  "value_promise": "Why they pay",
  "fastest_revenue": "One sentence: exact first transaction this week. Who pays, what for, which channel, which market.",
  "final_decision": "GO or SKIP or KILL",
  "kill_reason": "REQUIRED if SKIP or KILL. Must start with 'This fails because'.",
  "score": 0,
  "score_reasoning": "Two sentences",
  "why_it_fails": "Top failure mode",
  "what_must_be_true": ["assumption 1", "assumption 2", "assumption 3"],
  "directions": {{
    "safe": "Low-risk version",
    "fast": "Fastest path to first dollar",
    "high_upside": "Highest-ceiling version"
  }},
  "global_viability": "HIGH or MEDIUM or LOW",
  "best_launch_market": "Market — one sentence why",
  "pricing_power": "LOW or MEDIUM or HIGH — one sentence why",
  "global_scalability": "One sentence: what must be true to expand"
}}\
"""


@app.post("/api/chat")
async def chat(body: ChatInput) -> JSONResponse:
    messages = body.messages
    state = dict(body.state)
    turns = int(state.get("turns", 0))
    is_complete = turns >= 8 or state.get("ready") is True

    chat_msgs = [{"role": m.role, "content": m.content} for m in messages]

    if not is_complete:
        # ── Conversation turn ──────────────────────────────
        system_with_state = (
            f"{_CHAT_SYSTEM}\n\nCurrent state (what you know so far):\n"
            f"{json.dumps(state, indent=2)}"
        )
        try:
            raw = await asyncio.wait_for(
                _call_claude_messages(chat_msgs, max_tokens=800, system=system_with_state),
                timeout=40,
            )
        except Exception as exc:
            return JSONResponse({
                "reply": "Something went wrong, try again.",
                "state": state,
                "is_complete": False,
                "error": str(exc),
            })

        raw = _strip_json_fences(raw)
        try:
            parsed = json.loads(raw)
            reply = parsed.get("reply", raw)
            state.update(parsed.get("state_update", {}))
            ready = bool(parsed.get("ready", False))
            if ready:
                state["ready"] = True
        except Exception:
            reply = raw
            ready = False

        state["turns"] = turns + 1
        is_complete = state["turns"] >= 8 or ready

        return JSONResponse({
            "reply": reply,
            "state": state,
            "is_complete": is_complete,
        })

    else:
        # ── Final structured output turn ───────────────────
        conversation_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in chat_msgs
        )
        final_prompt = _FINAL_ANALYSIS_PROMPT.format(
            conversation=conversation_text,
            state=json.dumps(state, indent=2),
        )
        try:
            raw = await asyncio.wait_for(
                _call_claude(final_prompt, max_tokens=2500),
                timeout=55,
            )
        except Exception as exc:
            return JSONResponse({
                "reply": "Analysis timed out, try again.",
                "state": state,
                "is_complete": True,
                "final_result": None,
                "error": str(exc),
            })

        raw = _strip_json_fences(raw)
        try:
            result = json.loads(raw)
        except Exception:
            start, end = raw.find("{"), raw.rfind("}") + 1
            try:
                result = json.loads(raw[start:end]) if start >= 0 and end > start else None
            except Exception:
                result = None

        if result is None:
            return JSONResponse({
                "reply": raw,
                "state": state,
                "is_complete": True,
                "final_result": None,
            })

        # Save to DB
        db: Session = SessionLocal()
        try:
            row = IdeaDB(
                idea_text=" / ".join(
                    m["content"] for m in chat_msgs if m["role"] == "user"
                ),
                concept=result.get("concept"),
                target_user=result.get("target_user"),
                core_pain=result.get("core_pain"),
                value_promise=result.get("value_promise"),
                kill_reason=result.get("kill_reason"),
                final_decision=result.get("final_decision"),
                score=result.get("score"),
                score_reasoning=result.get("score_reasoning"),
                why_it_fails=result.get("why_it_fails"),
                what_must_be_true=json.dumps(result.get("what_must_be_true", [])),
                directions=json.dumps(result.get("directions", {})),
                regional_scores=None,
                fastest_revenue=result.get("fastest_revenue"),
                global_viability=result.get("global_viability"),
                best_launch_market=result.get("best_launch_market"),
                pricing_power=result.get("pricing_power"),
                global_scalability=result.get("global_scalability"),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            result["id"] = row.id
        finally:
            db.close()

        return JSONResponse({
            "reply": "Analysis complete.",
            "state": state,
            "is_complete": True,
            "final_result": result,
        })


# ── Public HTML pages (Step 7: all DB values escaped) ─────
@app.get("/graveyard", response_class=HTMLResponse)
async def graveyard() -> HTMLResponse:
    db = SessionLocal()
    try:
        ideas = (
            db.query(IdeaDB)
            .filter(IdeaDB.final_decision.in_(["SKIP", "KILL"]))
            .order_by(IdeaDB.created_at.desc())
            .limit(50)
            .all()
        )
    finally:
        db.close()

    rows = "".join(
        f"<tr>"
        f"<td>{escape(i.concept or '')}</td>"
        f"<td>{escape(i.target_user or '')}</td>"
        f"<td>{escape(i.kill_reason or '')}</td>"
        f"<td>{escape(i.final_decision or '')}</td>"
        f"<td>{escape(str(i.score or ''))}</td>"
        f"</tr>"
        for i in ideas
    )
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Graveyard</title>
<style>body{{font-family:sans-serif;padding:2rem}}table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ddd;padding:.5rem;text-align:left}}th{{background:#f5f5f5}}</style>
</head><body>
<h1>Idea Graveyard</h1>
<table><tr><th>Concept</th><th>Target</th><th>Kill Reason</th><th>Decision</th><th>Score</th></tr>
{rows}
</table></body></html>""")


@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard() -> HTMLResponse:
    db = SessionLocal()
    try:
        ideas = (
            db.query(IdeaDB)
            .filter(IdeaDB.final_decision == "GO")
            .order_by(IdeaDB.score.desc())
            .limit(20)
            .all()
        )
    finally:
        db.close()

    rows = "".join(
        f"<tr>"
        f"<td><a href='/idea/{escape(str(i.id))}'>{escape(i.concept or '')}</a></td>"
        f"<td>{escape(str(i.score or ''))}</td>"
        f"<td>{escape(i.best_launch_market or '')}</td>"
        f"<td>{escape(i.pricing_power or '')}</td>"
        f"<td>{escape(i.global_viability or '')}</td>"
        f"</tr>"
        for i in ideas
    )
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Leaderboard</title>
<style>body{{font-family:sans-serif;padding:2rem}}table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ddd;padding:.5rem;text-align:left}}th{{background:#f5f5f5}}</style>
</head><body>
<h1>Top Ideas</h1>
<table><tr><th>Concept</th><th>Score</th><th>Best Market</th><th>Pricing Power</th><th>Global Viability</th></tr>
{rows}
</table></body></html>""")


@app.get("/idea/{idea_id}", response_class=HTMLResponse)
async def public_idea(idea_id: int) -> HTMLResponse:
    db = SessionLocal()
    try:
        i = db.query(IdeaDB).filter(IdeaDB.id == idea_id).first()
    finally:
        db.close()

    if not i:
        raise HTTPException(404, "Idea not found")

    def r(val: object) -> str:
        return escape(str(val or ""))

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{r(i.concept)}</title>
<style>body{{font-family:sans-serif;padding:2rem;max-width:800px}}
dl{{display:grid;grid-template-columns:auto 1fr;gap:.5rem 1rem}}
dt{{font-weight:bold}}dd{{margin:0}}</style>
</head><body>
<h1>{r(i.concept)}</h1>
<dl>
  <dt>Target User</dt><dd>{r(i.target_user)}</dd>
  <dt>Core Pain</dt><dd>{r(i.core_pain)}</dd>
  <dt>Value Promise</dt><dd>{r(i.value_promise)}</dd>
  <dt>Price</dt><dd>{r(i.price)}</dd>
  <dt>Category</dt><dd>{r(i.category)}</dd>
  <dt>Score</dt><dd>{r(i.score)}</dd>
  <dt>Decision</dt><dd>{r(i.final_decision)}</dd>
  <dt>Kill Reason</dt><dd>{r(i.kill_reason)}</dd>
  <dt>Summary</dt><dd>{r(i.summary)}</dd>
  <dt>Fastest Revenue</dt><dd>{r(i.fastest_revenue)}</dd>
  <dt>Global Viability</dt><dd>{r(i.global_viability)}</dd>
  <dt>Best Launch Market</dt><dd>{r(i.best_launch_market)}</dd>
  <dt>Pricing Power</dt><dd>{r(i.pricing_power)}</dd>
  <dt>Global Scalability</dt><dd>{r(i.global_scalability)}</dd>
</dl>
</body></html>""")
