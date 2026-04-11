# AI-DAN Managing Director

AI-DAN is the **strategic decision engine** for an AI venture system. It transforms founder input into structured decisions, machine-readable commands, and launch-ready business packages – all optimized for a **single non-technical operator**.

## ✨ What It Does

1. **Enter a business idea** → AI-DAN researches, scores, and structures it
2. **Get a full business verdict** → Feasibility, profitability, risk, pricing, distribution
3. **Monetization-ready output** → Every response includes target user, pricing, and go-to-market plan
4. **Marketing Hub** → Generate region-aware campaigns, social cards, and launch copy
5. **My Projects** → Track your venture portfolio and build history in one place

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
Idea → Research (Perplexity) → Validate → Score → Structure (AI) → Output
```

**This repo = BRAIN** (strategy, decisions, commands). Execution happens in downstream systems (GitHub Factory, Vercel, etc.).

### Core Modules

| Module | Purpose |
|--------|---------|
| `app/reasoning/` | Intent classification, idea generation, scoring (0–10), adversarial critique |
| `app/planning/` | Execution plans, command compilation, business packages, distribution plans |
| `app/integrations/` | AI providers, GitHub, Vercel, LemonSqueezy, Telegram, Registry clients |
| `app/factory/` | BuildBrief validation, factory orchestration, deployment coordination |
| `app/portfolio/` | SQLite-backed lifecycle state machine (idea → scaled/killed) |
| `app/feedback/` | Metrics ingestion, deterministic decisions (kill/scale/revise/monitor) |
| `app/memory/` | Learning signals, auto-learning system with weight adjustment |
| `app/governance/` | Policy-driven approvals, safety classification, human-in-the-loop gates |
| `app/agents/` | Guardian agent for feasibility, competition, and scope risk checks |
| `app/observability/` | Control plane, circuit breakers, operational snapshots |
| `app/command_center/` | Operator-facing summaries, build status, command tracking |

### AI Providers

| Provider | Purpose | Key |
|----------|---------|-----|
| **Groq** (LLaMA 3.3) | Fast inference, launch copy, daily scoring | `GROQ_API_KEY` |
| **Anthropic** (Claude) | Reasoning, scoring, adversarial critique | `ANTHROPIC_API_KEY` |
| **OpenAI** (GPT-4o) | Structured output, business verdicts | `OPENAI_API_KEY` |
| **Perplexity** | Market research, competitor analysis, demand validation | `PERPLEXITY_API_KEY` |
| **Deepseek** | Cost-efficient code generation | `DEEPSEEK_API_KEY` |
| **xAI Grok** | Real-time trend analysis | `GROK_API_KEY` |

All providers have **graceful fallback** to deterministic mode when API keys are not configured. Provider priority: Groq → OpenAI → Anthropic → Deepseek → fallback.

### Integration Clients

| Client | Purpose |
|--------|---------|
| `ai_provider.py` | Multi-provider routing (Groq → OpenAI → Anthropic → Deepseek → Grok) |
| `github_client.py` | Repo creation, issue bundles, workflow dispatch |
| `vercel_client.py` | Deployment triggering, project management via Vercel API |
| `lemonsqueezy_client.py` | Payment checkout URL generation, product/variant listing |
| `telegram_client.py` | Build notifications (started, success, failed, idea approved) |
| `registry_client.py` | Service registry for deployed product tracking |
| `marketing_engine.py` | Region-aware campaign generation, platform-specific copy |
| `perplexity_client.py` | Market research and competitor analysis |

### Pipeline Flow

1. **Input** → User submits business idea via API or chat UI
2. **Research** → Perplexity analyzes market, competitors, pricing (when configured)
3. **Validation Gate 0** → Deterministic field checks + market truth
4. **Scoring Engine** → 0–10 mandatory gate: `<6` reject, `6–8` hold, `≥8` approve
5. **AI Analysis** → Routes to best available provider for structured output
6. **Business Package** → Problem, customer, pricing, delivery, CTA
7. **Distribution Plan** → ONE channel, first-10-users plan, messaging (region-aware)
8. **Output** → Complete monetization-ready structured response

### Lifecycle State Machine

```
idea → review → approved → queued → building → launched → monitoring → scaled/killed
```

No stage can be skipped. Terminal states: `scaled`, `killed`.

---

## UI Tabs (v3.0)

The root UI is a single-page app with 8 tabs:

| Tab | Purpose |
|-----|---------|
| **Chat** | Conversational AI agent — ask anything, get structured decisions |
| **Dashboard** | Portfolio health, build status, revenue signals |
| **Analyze** | Submit a business idea for full AI-powered scoring |
| **Factory** | Trigger builds, monitor pipeline runs |
| **Launch** | Animated social card generator, launch copy preview |
| **Revenue** | Payment signals, fast kill/scale decisions |
| **Marketing Hub** | Region-aware campaign management, platform-specific copy |
| **My Projects** | Full portfolio tracker — all your ventures in one place |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

### AI Providers

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | Groq API key (free tier available — recommended first) |
| `ANTHROPIC_API_KEY` | — | Anthropic Claude key for reasoning and scoring |
| `OPENAI_API_KEY` | — | OpenAI GPT-4o key for structured output |
| `PERPLEXITY_API_KEY` | — | Perplexity for market research |
| `DEEPSEEK_API_KEY` | — | Deepseek for cost-efficient tasks |
| `GROK_API_KEY` | — | xAI Grok for real-time trend analysis |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model override |
| `ANTHROPIC_MODEL` | `claude-3-5-sonnet-20241022` | Anthropic model override |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model override |

At least one AI key is recommended. All features degrade gracefully to deterministic mode if none are set.

### Integrations

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_TOKEN` | — | GitHub PAT for factory dispatch and repo ops |
| `VERCEL_TOKEN` | — | Vercel API token for deployment management |
| `VERCEL_TEAM_ID` | — | Vercel team ID (if using a team project) |
| `LEMONSQUEEZY_API_KEY` | — | LemonSqueezy API key for payment checkouts |
| `LEMONSQUEEZY_STORE_ID` | — | LemonSqueezy store ID |
| `TELEGRAM_BOT_TOKEN` | — | Telegram bot token for build notifications |
| `TELEGRAM_CHAT_ID` | — | Telegram chat ID to send notifications to |

### App Config

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment mode |
| `APP_PORT` | `8000` | Listen port |
| `PORTFOLIO_DB_PATH` | `data/portfolio.sqlite3` | SQLite path (auto-set to `/tmp/` on Vercel) |
| `MEMORY_MAX_EVENTS` | `2000` | Memory event limit |
| `FACTORY_OWNER` | `ismaelloveexcel` | GitHub org for factory dispatch |
| `FACTORY_REPO` | `ai-dan-factory` | Factory repo name |
| `FACTORY_CALLBACK_SECRET` | — | Shared secret for factory callbacks |
| `API_KEY` | — | API key for securing endpoints |

---

## URLs

| Service | URL |
|---------|-----|
| **Web UI** | `http://localhost:8000` |
| **API Docs (Swagger)** | `http://localhost:8000/docs` |
| **Health Check** | `http://localhost:8000/health` |

---

## API Endpoints

### Primary (UI-connected)
- `GET /` — Web UI (single-page application, v3.0)
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

### Projects
- `GET /projects/` — List all projects
- `POST /projects/` — Create project entry
- `GET /projects/{id}` — Project detail

### Distribution & Marketing
- `POST /distribution/campaigns` — Generate region-aware marketing campaign
- `GET /distribution/campaigns/{id}` — Campaign detail and copy

### Feedback & Decisions
- `POST /feedback/metrics` — Ingest product metrics
- `GET /feedback/projects/{id}/decision` — Deterministic decision
- `GET /feedback/projects/{id}/fast-decision` — Fast kill/iterate/scale decision

### Revenue
- `POST /revenue/fast-decision` — Fast kill/scale/iterate based on payment signals
- `POST /revenue/projects/{id}/business-output` — Generate business output snapshot

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
- `GET /factory/runs` — List factory runs
- `GET /factory/runs/{id}` — Factory run status

### Health
- `GET /health` — Health check

---

## Deployment

### Vercel (Recommended)

1. Connect this repo to Vercel
2. Set environment variables in Vercel dashboard (see table above)
3. Deploy — the `vercel.json` config handles Python runtime setup
4. Root URL loads the UI, all API routes are accessible

### Render / Railway / Fly.io

1. Set environment variables from `.env.example`
2. Deploy with `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Health check: `GET /health` returns `{"status": "ok"}`

---

## Monetization Strategy

AI-DAN enforces revenue-readiness at every stage:

1. **Research** → Perplexity validates market demand and pricing benchmarks
2. **Validation Gate** → Rejects ideas without monetization proof
3. **Scoring Engine** → Monetization potential scored 0–2
4. **AI Analysis** → Best available provider generates pricing and distribution plans
5. **Business Package** → Mandatory pricing model, price range, CTA, and GTM strategy
6. **Distribution Plan** → Concrete first-10-users plan with single channel focus
7. **Fast Decision** → Revenue detected → SCALE; no traction → KILL (max 1 iteration)
8. **LemonSqueezy** → Checkout URL generated for every approved product

Target: first revenue within 14 days of launch.

---

## Run Tests

```bash
python -m pytest tests/ -v
```

---

## System Flow

```
POST /api/analyze/
        │
        ├── Perplexity: market research, competitors, pricing
        │
        ├── Pipeline: intent → idea → score → critique → plan
        │
        ├── AI Provider: Groq → OpenAI → Anthropic (best available)
        │
        ▼
Monetization-ready output:
  ├── Business idea (title, problem, target user, solution)
  ├── Scores (overall, feasibility, profitability, speed, competition)
  ├── Verdict (APPROVE / HOLD / REJECT)
  ├── Monetization (method, pricing, competitive edge, LemonSqueezy checkout URL)
  └── Distribution (channel, first 10 users plan, region-aware copy)
```
