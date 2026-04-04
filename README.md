# AI-DAN Managing Director

AI-DAN is the **strategic decision engine** for an AI venture system. It transforms founder input into structured decisions, machine-readable commands, and launch-ready business packages – all optimized for a **single non-technical operator**.

## ✨ What It Does

1. **Enter a business idea** → AI-DAN researches, scores, and structures it
2. **Get a full business verdict** → Feasibility, profitability, risk, pricing, distribution
3. **Monetization-ready output** → Every response includes target user, pricing, and go-to-market plan

## 🚀 Quick Start

### One-Click Local Startup

**Mac/Linux:**
```bash
./scripts/start_local.sh
```

**Windows:**
```bat
scripts\start_local.bat
```

### Manual Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # Edit with your API keys
uvicorn main:app --reload
```

Open **http://localhost:8000** in your browser → the UI loads at root.

---

## Architecture

```
Idea → Research (Perplexity) → Validate → Score → Structure (OpenAI) → Output
```

**This repo = BRAIN** (strategy, decisions, commands). Execution happens in downstream systems (GitHub Factory, Vercel, etc.).

### Core Modules

| Module | Purpose |
|--------|---------|
| `app/reasoning/` | Intent classification, idea generation, scoring (0–10), adversarial critique |
| `app/planning/` | Execution plans, command compilation, business packages, distribution plans |
| `app/integrations/` | OpenAI, Perplexity, GitHub, Vercel, Registry clients |
| `app/factory/` | BuildBrief validation, factory orchestration, deployment coordination |
| `app/portfolio/` | SQLite-backed lifecycle state machine (idea → scaled/killed) |
| `app/feedback/` | Metrics ingestion, deterministic decisions (kill/scale/revise/monitor) |
| `app/memory/` | Learning signals, auto-learning system with weight adjustment |
| `app/governance/` | Policy-driven approvals, safety classification, human-in-the-loop gates |
| `app/agents/` | Guardian agent for feasibility, competition, and scope risk checks |
| `app/observability/` | Control plane, circuit breakers, operational snapshots |
| `app/command_center/` | Operator-facing summaries, build status, command tracking |

### AI Integration

| Provider | Purpose | Required |
|----------|---------|----------|
| **OpenAI** | Reasoning, structured output, business verdicts | Yes (for AI mode) |
| **Perplexity** | Market research, competitor analysis, demand validation | Yes (for research) |

Both providers have **graceful fallback** to deterministic mode when API keys are not configured.

### Pipeline Flow

1. **Input** → User enters business idea via UI or API
2. **Research** → Perplexity analyzes market, competitors, pricing (when configured)
3. **Validation Gate 0** → Deterministic field checks + market truth
4. **Scoring Engine** → 0–10 mandatory gate: `<6` reject, `6–8` hold, `≥8` approve
5. **AI Analysis** → OpenAI structures output with monetization details (when configured)
6. **Business Package** → Problem, customer, pricing, delivery, CTA
7. **Distribution Plan** → ONE channel, first-10-users plan, messaging
8. **Output** → Complete monetization-ready structured response

### Lifecycle State Machine

```
idea → review → approved → queued → building → launched → monitoring → scaled/killed
```

No stage can be skipped. Terminal states: `scaled`, `killed`.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

### Required for AI Mode

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for reasoning and structured output |
| `PERPLEXITY_API_KEY` | Perplexity API key for market research |
| `PERPLEXITY_MODEL` | Perplexity model (default: `sonar`) |
| `RESEARCH_PROVIDER` | Research provider (default: `perplexity`) |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model for reasoning |
| `APP_ENV` | `development` | Environment mode |
| `APP_PORT` | `8000` | Listen port |
| `LLM_API_KEY` | — | Legacy: falls back from `OPENAI_API_KEY` |
| `GITHUB_TOKEN` | — | GitHub personal access token |
| `VERCEL_TOKEN` | — | Vercel deployment token |
| `PORTFOLIO_DB_PATH` | `data/portfolio.sqlite3` | SQLite path |
| `MEMORY_MAX_EVENTS` | `2000` | Memory event limit |

**Stub mode** works without API keys — all AI features degrade gracefully to deterministic output.

---

## URLs

| Service | URL |
|---------|-----|
| **Web UI** | `http://localhost:8000` |
| **API Docs (Swagger)** | `http://localhost:8000/docs` |
| **Health Check** | `http://localhost:8000/health` |
| **Streamlit UI** | `http://localhost:8501` (optional, separate process) |

---

## API Endpoints

### Primary (UI-connected)
- `GET /` — Web UI (single-page application)
- `POST /api/analyze/` — Full AI-powered idea analysis with monetization output

### Core Decision Flow
- `POST /chat/` — Full founder flow: intent → idea → score → critique → plan → commands
- `POST /factory/ideas/execute` — End-to-end: validate → score → offer → build → deploy

### Ideas & Evaluation
- `POST /ideas/generate` — Generate idea from prompt
- `POST /ideas/brainstorm` — Generate up to 5 ideas
- `POST /ideas/evaluate` — Score idea (0–10 mandatory gate)
- `POST /ideas/critique` — Adversarial critique

### Portfolio & Lifecycle
- `POST /portfolio/projects` — Create project
- `POST /portfolio/projects/{id}/transition` — Enforce state transition
- `GET /portfolio/projects/{id}/events` — Audit trail

### Feedback & Decisions
- `POST /feedback/metrics` — Ingest product metrics
- `GET /feedback/projects/{id}/decision` — Deterministic decision
- `GET /feedback/projects/{id}/fast-decision` — Fast kill/iterate/scale decision

### Analytics
- `POST /analytics/events` — Record analytics event
- `GET /analytics/projects/{id}/summary` — Aggregated analytics

### Memory & Learning
- `POST /memory/events` — Record memory event
- `POST /memory/signals` — Record learning signal
- `POST /memory/outcomes` — Record outcome for auto-learning
- `GET /memory/learning/insight` — Auto-learning weights and insight

### Intelligence & Control
- `GET /intelligence/ranked-projects` — Projects ranked by health
- `GET /intelligence/operator/daily-digest` — Top 3 actions for operator
- `GET /control/state` — Command center snapshot

### Factory & Deployment
- `POST /factory/briefs/validate` — Validate BuildBrief
- `POST /factory/runs` — Create factory run
- `GET /factory/runs/{id}` — Factory run status

### Health
- `GET /health` — Health check

---

## Deployment

### Vercel (Recommended)

1. Connect this repo to Vercel
2. Set environment variables in Vercel dashboard:
   - `OPENAI_API_KEY`
   - `PERPLEXITY_API_KEY`
   - `PERPLEXITY_MODEL=sonar`
   - `RESEARCH_PROVIDER=perplexity`
3. Deploy — the `vercel.json` config handles Python runtime setup
4. Root URL loads the UI, all API routes are accessible

### Render / Railway / Fly.io

1. Set environment variables from `.env.example`
2. Deploy with `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Health check: `GET /health` returns `{"status": "ok"}`

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Monetization Strategy

AI-DAN enforces revenue-readiness at every stage:

1. **Research** → Perplexity validates market demand and pricing benchmarks
2. **Validation Gate** → Rejects ideas without monetization proof
3. **Scoring Engine** → Monetization potential scored 0–2
4. **AI Analysis** → OpenAI generates specific pricing and distribution plans
5. **Business Package** → Mandatory pricing model, price range, CTA, and GTM strategy
6. **Distribution Plan** → Concrete first-10-users plan with single channel focus
7. **Fast Decision** → Revenue detected → SCALE; no traction → KILL (max 1 iteration)

Target: first revenue within 14 days of launch.

---

## Run Tests

```bash
python -m pytest tests/ -v
```

---

## System Flow

```
User enters idea in UI (/)
        │
        ▼
POST /api/analyze/
        │
        ├── Perplexity: market research, competitors, pricing
        │
        ├── Pipeline: intent → idea → score → critique → plan
        │
        ├── OpenAI: structured reasoning, business verdict
        │
        ▼
Monetization-ready output:
  ├── Business idea (title, problem, target user, solution)
  ├── Scores (overall, feasibility, profitability, speed, competition)
  ├── Verdict (APPROVE / HOLD / REJECT)
  ├── Monetization (method, pricing, competitive edge)
  └── Distribution (channel, first 10 users plan)
```
