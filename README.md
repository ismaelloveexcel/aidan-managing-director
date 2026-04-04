# AI-DAN Managing Director

AI-DAN is the **strategic decision engine** for an AI venture system. It transforms founder input into structured decisions, machine-readable commands, and launch-ready business packages – all optimized for a **single non-technical operator**.

## Architecture

```
Idea → Validate → Score → Offer → Distribution → Approve → Queue → Build → Deploy → Verify → Track → Decide (Scale/Kill)
```

**This repo = BRAIN** (strategy, decisions, commands). Execution happens in downstream systems (GitHub Factory, Vercel, etc.).

### Core Modules

| Module | Purpose |
|--------|---------|
| `app/reasoning/` | Intent classification, idea generation, scoring (0–10), adversarial critique |
| `app/planning/` | Execution plans, command compilation, business packages, distribution plans |
| `app/factory/` | BuildBrief validation, factory orchestration, deployment coordination |
| `app/portfolio/` | SQLite-backed lifecycle state machine (idea → scaled/killed) |
| `app/feedback/` | Metrics ingestion, deterministic decisions (kill/scale/revise/monitor), fast-decision engine |
| `app/memory/` | Learning signals, auto-learning system with weight adjustment |
| `app/governance/` | Policy-driven approvals, safety classification, human-in-the-loop gates |
| `app/agents/` | Guardian agent for feasibility, competition, and scope risk checks |
| `app/observability/` | Control plane, circuit breakers, operational snapshots |
| `app/command_center/` | Operator-facing summaries, build status, command tracking |
| `app/integrations/` | GitHub, Vercel, LLM, and Registry clients (stub-ready for real API wiring) |

### Pipeline Flow

1. **Validation Gate 0** – Deterministic field checks + market truth (demand, monetization proof, saturation)
2. **Scoring Engine** – 0–10 mandatory gate: `<6` reject, `6–8` hold, `≥8` approve
3. **Offer Engine** – Problem, customer, pricing (mandatory), delivery, CTA
4. **Distribution Engine** – ONE channel, first-10-users plan, messaging, execution steps
5. **Guardian Review** – Scope, competition, differentiation checks
6. **Governance Gate** – Safety classification, approval workflow
7. **Factory Build** – Repo creation, file injection, Vercel deployment
8. **Feedback Loop** – Metrics → fast-decision (kill/iterate/scale) with strict 1-iteration limit
9. **Auto-Learning** – Track outcomes, adjust scoring weights over time

### Lifecycle State Machine

```
idea → review → approved → queued → building → launched → monitoring → scaled/killed
```

No stage can be skipped. Terminal states: `scaled`, `killed`.

### Control Layer

- `max_active_projects = 3`
- `max_builds_in_parallel = 2`
- `max_launches_per_week = 2`
- Priority queue: revenue score → validation strength → speed
- Guardian checks: no duplicates, still valid, highest priority

---

## Quick Start

### One-Click Local Startup

**Mac/Linux:**
```bash
./scripts/start_local.sh
```

**Windows:**
```bat
scripts\start_local.bat
```

This installs dependencies, starts the backend (Uvicorn) and frontend (Streamlit).

### Manual Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Run backend:**
```bash
uvicorn main:app --reload
```

**Run frontend (separate terminal):**
```bash
streamlit run frontend/command_center.py
```

### URLs

| Service | URL |
|---------|-----|
| Backend API | `http://localhost:8000` |
| API Docs (Swagger) | `http://localhost:8000/docs` |
| Frontend (Command Center) | `http://localhost:8501` |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

| Variable | Required | Description |
|----------|----------|-------------|
| `APP_ENV` | No | `development` or `production` (default: `development`) |
| `APP_HOST` | No | Listen host (default: `0.0.0.0`) |
| `APP_PORT` | No | Listen port (default: `8000`) |
| `APP_LOG_LEVEL` | No | Log level (default: `info`) |
| `LLM_API_KEY` | Yes* | API key for LLM provider |
| `LLM_MODEL` | No | Model name (default: `gpt-4o`) |
| `LLM_BASE_URL` | No | Custom LLM endpoint |
| `GITHUB_TOKEN` | Yes* | GitHub personal access token |
| `GITHUB_API_BASE_URL` | No | GitHub API URL (default: `https://api.github.com`) |
| `GITHUB_FACTORY_OWNER` | No | GitHub org for factory repos (default: `ai-dan`) |
| `GITHUB_FACTORY_TEMPLATE_REPO` | No | Template repo name (default: `saas-template`) |
| `FACTORY_OWNER` | No | Factory workflow owner (default: `ai-dan`) |
| `FACTORY_REPO` | No | Factory workflow repo (default: `ai-dan-factory`) |
| `FACTORY_WORKFLOW_ID` | No | Workflow filename (default: `factory-build.yml`) |
| `FACTORY_BASE_URL` | No | Base URL of the AI-DAN API for factory-related endpoints (e.g. this service's `/factory/runs` route) |
| `VERCEL_TOKEN` | Yes* | Vercel deployment token |
| `VERCEL_TEAM_ID` | No | Vercel team ID |
| `REGISTRY_URL` | No | Service registry URL |
| `REGISTRY_API_KEY` | No | Service registry API key |
| `PORTFOLIO_DB_PATH` | No | SQLite path (default: `data/portfolio.sqlite3`) |
| `MEMORY_MAX_EVENTS` | No | Memory event limit (default: `2000`) |

*Required for live mode; stub mode works without them.

---

## API Endpoints

### Core Decision Flow
- `POST /chat/` – Full founder flow: intent → idea → score → critique → plan → commands
- `POST /factory/ideas/execute` – End-to-end: validate → score → offer → build → deploy

### Ideas & Evaluation
- `POST /ideas/generate` – Generate idea from prompt
- `POST /ideas/brainstorm` – Generate up to 5 ideas
- `POST /ideas/evaluate` – Score idea (0–10 mandatory gate)
- `POST /ideas/critique` – Adversarial critique

### Portfolio & Lifecycle
- `POST /portfolio/projects` – Create project
- `POST /portfolio/projects/{id}/transition` – Enforce state transition
- `GET /portfolio/projects/{id}/events` – Audit trail

### Feedback & Decisions
- `POST /feedback/metrics` – Ingest product metrics
- `GET /feedback/projects/{id}/decision` – Deterministic decision
- `GET /feedback/projects/{id}/fast-decision` – Fast kill/iterate/scale decision

### Analytics
- `POST /analytics/events` – Record analytics event (page_view, click, signup, purchase)
- `GET /analytics/projects/{id}/summary` – Aggregated analytics

### Memory & Learning
- `POST /memory/events` – Record memory event
- `POST /memory/signals` – Record learning signal
- `POST /memory/outcomes` – Record outcome for auto-learning
- `GET /memory/learning/insight` – Auto-learning weights and insight

### Intelligence & Control
- `GET /intelligence/ranked-projects` – Projects ranked by health
- `GET /intelligence/operator/daily-digest` – Top 3 actions for operator
- `GET /intelligence/operator/limits` – Capacity limits
- `GET /control/state` – Command center snapshot
- `POST /control/circuit` – Toggle circuit breaker

### Factory & Deployment
- `POST /factory/briefs/validate` – Validate BuildBrief
- `POST /factory/runs` – Create factory run
- `GET /factory/runs/{id}` – Factory run status

### Health
- `GET /health` – Health check

---

## CI/CD & Automation

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push/PR to `main` | Runs full test suite |
| `factory-build.yml` | `workflow_dispatch` | Triggers factory build for a project |
| `scheduled-pipeline.yml` | Every 6 hours / manual | Checks project health, generates digest |

---

## Monetization Strategy

AI-DAN enforces revenue-readiness at every stage:

1. **Validation Gate** – Rejects ideas without monetization proof
2. **Scoring Engine** – Monetization potential scored 0–2 (subscription/SaaS = 2.0, unproven = 0.0)
3. **Business Package** – Mandatory pricing model, price range, CTA, and GTM strategy
4. **Distribution Plan** – Concrete first-10-users plan with single channel focus
5. **Fast Decision** – Revenue detected → SCALE; no traction → KILL (max 1 iteration)
6. **Auto-Learning** – Tracks pricing performance, adjusts weights based on outcomes

Target: first revenue within 14 days of launch.

---

## Run Tests

```bash
python -m pytest tests/ -v
```

---

## Deployment

### Production (Render / Railway / Fly.io)

1. Set environment variables from `.env.example`
2. Deploy with `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Health check: `GET /health` returns `{"status": "ok"}`

### Docker (optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```
