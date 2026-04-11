"""
main.py – FastAPI application entry point for AI-DAN Managing Director.

Registers all route modules, serves the root UI, and configures the application.
"""

import logging
import pathlib
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.middleware import APIKeyMiddleware, RateLimitMiddleware
from app.routes import (
    analytics,
    analyze,
    approvals,
    chat,
    commands,
    control,
    dashboard,
    distribution,
    factory,
    feedback,
    ideas,
    intelligence,
    memory,
    ops,
    portfolio,
    projects,
    revenue,
)

_settings = get_settings()

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

_VERSION = "3.0.0"

_logger = logging.getLogger("aidan.startup")

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    _logger.info("AI-DAN Managing Director v%s starting", _VERSION)
    missing = _settings.validate_production_secrets()
    if missing:
        _logger.warning("Missing production secrets: %s", ", ".join(missing))
    else:
        _logger.info("All production secrets configured")
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI-DAN Managing Director",
    version=_VERSION,
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

# Middleware
app.add_middleware(APIKeyMiddleware, api_key=_settings.api_key)
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)

# Routers
app.include_router(analyze.router, prefix="/api/analyze")
app.include_router(chat.router, prefix="/chat")
app.include_router(ideas.router, prefix="/ideas")
app.include_router(projects.router, prefix="/projects")
app.include_router(portfolio.router, prefix="/portfolio")
app.include_router(feedback.router, prefix="/feedback")
app.include_router(analytics.router, prefix="/analytics")
app.include_router(approvals.router, prefix="/approvals")
app.include_router(commands.router, prefix="/commands")
app.include_router(factory.router, prefix="/factory")
app.include_router(memory.router, prefix="/memory")
app.include_router(intelligence.router, prefix="/intelligence")
app.include_router(revenue.router, prefix="/revenue")
app.include_router(control.router, prefix="/control")
app.include_router(distribution.router, prefix="/api/distribution")
app.include_router(dashboard.router, prefix="/api/dashboard")
app.include_router(ops.router, prefix="/ops")

# Static files
_STATIC_DIR = pathlib.Path(__file__).resolve().parent / "static"
if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Premium Dashboard
# ---------------------------------------------------------------------------

_DASHBOARD_HTML_PATH = _STATIC_DIR / "dashboard.html"


@app.get("/dashboard", response_class=HTMLResponse)
async def premium_dashboard() -> HTMLResponse:
    """Serve the premium founder dashboard."""
    if _DASHBOARD_HTML_PATH.exists():
        return HTMLResponse(content=_DASHBOARD_HTML_PATH.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    checks: dict[str, str] = {}
    overall = "ok"

    # Database connectivity check
    try:
        from app.core.dependencies import get_portfolio_repository
        repo = get_portfolio_repository()
        repo.list_projects()
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        overall = "degraded"

    # Config readiness check
    missing = _settings.validate_production_secrets()
    if missing:
        checks["config"] = "missing_secrets"
        if _settings.is_production_mode():
            overall = "degraded"
    else:
        checks["config"] = "ok"

    return {"status": overall, "checks": checks, "version": _VERSION}


# ---------------------------------------------------------------------------
# Root UI
# ---------------------------------------------------------------------------

_ROOT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>AI-DAN &#128039; Managing Director</title>
<style>
:root {
  --bg1:#0a0a10;--bg2:#12121c;--bg3:#1a1a2e;--bg4:#22224a;
  --text1:#f0f0ff;--text2:#b8b8d0;--text3:#7878a8;--text4:#4a4a6a;
  --accent:#5b6ef7;--accent2:#7c3aed;--accent3:#06b6d4;
  --success:#10b981;--warn:#f59e0b;--error:#ef4444;
  --border1:#2a2a4a;--border2:#3a3a5a;
  --card-bg:#14142a;--card-border:#252545;
  --radius:12px;--radius-sm:8px;
  --shadow:0 4px 24px rgba(0,0,0,.4);
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',system-ui,sans-serif;background:var(--bg1);color:var(--text1);min-height:100vh;font-size:14px}
a{color:var(--accent3);text-decoration:none}
a:hover{text-decoration:underline}

/* ─── Layout ─────────────────────────────────────── */
.shell{display:flex;flex-direction:column;height:100vh;overflow:hidden}
.topbar{display:flex;align-items:center;gap:.75rem;padding:.75rem 1.2rem;background:var(--bg2);border-bottom:1px solid var(--border1);flex-shrink:0}
.topbar-logo{font-size:1.3rem;font-weight:800;background:linear-gradient(135deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-.03em}
.topbar-sub{font-size:.72rem;color:var(--text3);margin-top:.1rem}
.topbar-right{margin-left:auto;display:flex;align-items:center;gap:.5rem}
.version-badge{background:var(--bg3);border:1px solid var(--border1);border-radius:99px;padding:.2rem .6rem;font-size:.65rem;color:var(--text3)}

.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:56px;background:var(--bg2);border-right:1px solid var(--border1);display:flex;flex-direction:column;align-items:center;padding:.5rem 0;gap:.2rem;flex-shrink:0}
.nav-btn{width:40px;height:40px;border-radius:var(--radius-sm);border:none;background:transparent;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:1.15rem;color:var(--text3);transition:.15s;position:relative}
.nav-btn:hover{background:var(--bg3);color:var(--text1)}
.nav-btn.active{background:var(--accent);color:#fff}
.nav-btn[title]:hover::after{content:attr(title);position:absolute;left:52px;top:50%;transform:translateY(-50%);background:var(--bg3);border:1px solid var(--border2);color:var(--text1);padding:.25rem .6rem;border-radius:6px;font-size:.72rem;white-space:nowrap;pointer-events:none;z-index:100}

.content{flex:1;overflow-y:auto;padding:1.2rem}

/* ─── Cards ─────────────────────────────────────── */
.card{background:var(--card-bg);border:1px solid var(--card-border);border-radius:var(--radius);padding:1.1rem 1.25rem;margin-bottom:1rem}
.card-title{font-size:.82rem;font-weight:700;color:var(--text2);text-transform:uppercase;letter-spacing:.06em;margin-bottom:.9rem}
.section-sep{height:1px;background:var(--border1);margin:.9rem 0}

/* ─── Tabs ───────────────────────────────────────── */
.tab-panel{display:none}.tab-panel.active{display:block}

/* ─── Forms ─────────────────────────────────────── */
label{display:block;font-size:.75rem;font-weight:600;color:var(--text3);margin:.75rem 0 .25rem;text-transform:uppercase;letter-spacing:.04em}
input[type=text],input[type=url],input[type=email],input[type=number],input[type=color],
textarea,select{
  width:100%;padding:.55rem .8rem;background:var(--bg3);border:1px solid var(--border2);
  border-radius:var(--radius-sm);color:var(--text1);font-size:.85rem;font-family:inherit;
  transition:.15s;outline:none
}
input:focus,textarea:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 2px rgba(91,110,247,.2)}
textarea{resize:vertical;min-height:80px}
select option{background:var(--bg3)}

/* ─── Buttons ───────────────────────────────────── */
.btn{display:inline-flex;align-items:center;gap:.4rem;padding:.5rem 1rem;border-radius:var(--radius-sm);font-size:.82rem;font-weight:600;cursor:pointer;border:1px solid transparent;transition:.15s;font-family:inherit}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btn-primary{background:var(--accent);color:#fff;border-color:var(--accent)}
.btn-primary:hover:not(:disabled){background:#4a5de6}
.btn-secondary{background:var(--bg3);color:var(--text2);border-color:var(--border2)}
.btn-secondary:hover:not(:disabled){background:var(--bg4)}
.btn-success{background:var(--success);color:#fff;border-color:var(--success)}
.btn-success:hover:not(:disabled){background:#0da872}
.btn-danger{background:var(--error);color:#fff;border-color:var(--error)}
.btn-full{width:100%;justify-content:center}

/* ─── Alerts ────────────────────────────────────── */
.alert{border-radius:var(--radius-sm);padding:.65rem .9rem;font-size:.8rem;line-height:1.5}
.alert-info{background:rgba(6,182,212,.1);border:1px solid rgba(6,182,212,.3);color:#67e8f9}
.alert-success{background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.3);color:#6ee7b7}
.alert-warn{background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);color:#fcd34d}
.alert-error{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:#fca5a5}

/* ─── Spinner ───────────────────────────────────── */
.spinner{display:inline-block;width:14px;height:14px;border:2px solid currentColor;border-top-color:transparent;border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* ─── Chat ──────────────────────────────────────── */
.chat-wrap{display:flex;flex-direction:column;height:calc(100vh - 130px);max-height:700px}
.chat-history{flex:1;overflow-y:auto;padding:.5rem 0;display:flex;flex-direction:column;gap:.75rem}
.msg{display:flex;gap:.6rem;align-items:flex-start}
.msg.user{flex-direction:row-reverse}
.msg-bubble{max-width:72%;padding:.65rem .9rem;border-radius:14px;font-size:.85rem;line-height:1.6;white-space:pre-wrap}
.msg.bot .msg-bubble{background:var(--bg3);color:var(--text1);border-bottom-left-radius:4px}
.msg.user .msg-bubble{background:var(--accent);color:#fff;border-bottom-right-radius:4px}
.msg-avatar{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.8rem;flex-shrink:0;margin-top:2px}
.msg.bot .msg-avatar{background:var(--accent2)}
.msg.user .msg-avatar{background:var(--bg4)}
.chat-input-row{display:flex;gap:.5rem;margin-top:.75rem;padding-top:.75rem;border-top:1px solid var(--border1)}
.chat-input{flex:1;padding:.65rem 1rem;background:var(--bg3);border:1px solid var(--border2);border-radius:99px;color:var(--text1);font-size:.85rem;outline:none;font-family:inherit}
.chat-input:focus{border-color:var(--accent)}
.chat-send{width:38px;height:38px;border-radius:50%;background:var(--accent);border:none;color:#fff;cursor:pointer;font-size:1rem;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.chat-send:hover{background:#4a5de6}
.typing-dots span{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--text3);margin:0 2px;animation:bounce 1.2s infinite}
.typing-dots span:nth-child(2){animation-delay:.2s}
.typing-dots span:nth-child(3){animation-delay:.4s}
@keyframes bounce{0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-6px)}}
.starter-prompts{display:flex;flex-wrap:wrap;gap:.4rem;margin-bottom:.75rem}
.starter-btn{padding:.3rem .75rem;border-radius:99px;border:1px solid var(--border2);background:var(--bg3);color:var(--text2);font-size:.75rem;cursor:pointer;transition:.15s}
.starter-btn:hover{border-color:var(--accent);color:var(--accent)}

/* ─── Dashboard ─────────────────────────────────── */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.75rem;margin-bottom:1rem}
.stat-card{background:var(--bg3);border:1px solid var(--border1);border-radius:var(--radius-sm);padding:.9rem 1rem;text-align:center}
.stat-val{font-size:1.8rem;font-weight:800;color:var(--accent);line-height:1}
.stat-label{font-size:.68rem;color:var(--text3);margin-top:.3rem;text-transform:uppercase;letter-spacing:.05em}
.health-dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:.3rem}
.health-dot.green{background:var(--success)}
.health-dot.red{background:var(--error)}
.health-dot.amber{background:var(--warn)}
.loading-row{color:var(--text3);font-size:.8rem;text-align:center;padding:.75rem 0;display:flex;align-items:center;justify-content:center;gap:.5rem}

/* ─── Builds table ───────────────────────────────── */
.builds-table{width:100%;border-collapse:collapse;font-size:.8rem}
.builds-table th{text-align:left;padding:.4rem .6rem;color:var(--text3);font-weight:600;border-bottom:1px solid var(--border1);font-size:.72rem;text-transform:uppercase}
.builds-table td{padding:.5rem .6rem;border-bottom:1px solid var(--border1);vertical-align:middle}
.builds-table tr:last-child td{border-bottom:none}
.badge{display:inline-flex;align-items:center;gap:.25rem;padding:.15rem .55rem;border-radius:99px;font-size:.7rem;font-weight:600}
.badge-success{background:rgba(16,185,129,.15);color:#6ee7b7}
.badge-error{background:rgba(239,68,68,.15);color:#fca5a5}
.badge-warn{background:rgba(245,158,11,.15);color:#fcd34d}
.badge-info{background:rgba(91,110,247,.15);color:#a5b4fc}
.badge-muted{background:rgba(120,120,168,.12);color:var(--text3)}

/* ─── Score bars ─────────────────────────────────── */
.score-row{margin-bottom:.6rem}
.score-label-row{display:flex;justify-content:space-between;font-size:.75rem;color:var(--text2);margin-bottom:.2rem}
.score-bar{height:6px;background:var(--bg3);border-radius:3px;overflow:hidden}
.score-fill{height:100%;border-radius:3px;transition:.4s}
.score-high{background:var(--success)}
.score-med{background:var(--warn)}
.score-low{background:var(--error)}
.result-card{border-left:3px solid var(--accent);padding-left:1rem}
.decision-badge{display:inline-block;padding:.4rem 1.1rem;border-radius:99px;font-size:.85rem;font-weight:800;letter-spacing:.06em;margin-bottom:.8rem}
.decision-approved{background:rgba(16,185,129,.18);color:#6ee7b7;border:1px solid rgba(16,185,129,.4)}
.decision-hold{background:rgba(245,158,11,.18);color:#fcd34d;border:1px solid rgba(245,158,11,.4)}
.decision-rejected{background:rgba(239,68,68,.18);color:#fca5a5;border:1px solid rgba(239,68,68,.4)}

/* ─── Launch kit ─────────────────────────────────── */
.platforms-grid{display:flex;flex-wrap:wrap;gap:.4rem;margin:.5rem 0 1rem}
.plat-check{display:flex;align-items:center;gap:.35rem;padding:.3rem .7rem;border-radius:99px;border:1px solid var(--border2);background:var(--bg3);cursor:pointer;font-size:.78rem;transition:.15s;user-select:none}
.plat-check:hover{border-color:var(--accent3)}
.plat-check input{display:none}
.plat-check.selected{border-color:var(--accent3);background:rgba(6,182,212,.12);color:var(--accent3)}
.platform-cards{display:flex;flex-direction:column;gap:.9rem}
.platform-card{background:var(--bg3);border:1px solid var(--border1);border-radius:var(--radius-sm);overflow:hidden}
.platform-header{display:flex;align-items:center;gap:.5rem;padding:.6rem .85rem;background:rgba(255,255,255,.03);border-bottom:1px solid var(--border1)}
.platform-body{padding:.8rem .85rem;font-size:.82rem;color:var(--text2);line-height:1.65}
.platform-field{margin-bottom:.65rem}
.platform-field-label{font-size:.7rem;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:.05em;margin-bottom:.2rem}
.copy-btn{padding:.18rem .5rem;font-size:.7rem;border-radius:5px;border:1px solid var(--border2);background:transparent;color:var(--text3);cursor:pointer;transition:.15s}
.copy-btn:hover{border-color:var(--accent);color:var(--accent)}
.checklist{list-style:none;padding:0}
.checklist li{display:flex;align-items:flex-start;gap:.5rem;padding:.35rem 0;font-size:.82rem;color:var(--text2);border-bottom:1px solid var(--border1)}
.checklist li:last-child{border-bottom:none}
.checklist li::before{content:"☐";color:var(--text3);flex-shrink:0;margin-top:.05rem}
.export-btn{display:flex;align-items:center;gap:.35rem;padding:.3rem .75rem;border-radius:var(--radius-sm);border:1px solid var(--border2);background:var(--bg3);color:var(--text2);font-size:.75rem;cursor:pointer;transition:.15s}
.export-btn:hover{border-color:var(--accent);color:var(--accent)}

/* ─── Revenue ───────────────────────────────────── */
.rev-table{width:100%;border-collapse:collapse;font-size:.82rem}
.rev-table th{text-align:left;padding:.4rem .5rem;color:var(--text3);font-weight:600;border-bottom:1px solid var(--border1);font-size:.72rem;text-transform:uppercase}
.rev-table td{padding:.45rem .5rem;border-bottom:1px solid var(--border1)}
.rev-table tr:last-child td{border-bottom:none}
.pipeline-bar{height:8px;background:var(--bg3);border-radius:4px;overflow:hidden;margin-top:.3rem}
.pipeline-fill{height:100%;background:linear-gradient(90deg,var(--accent),var(--accent2));border-radius:4px;transition:.6s}

/* ─── Marketing Hub ─────────────────────────────── */
.campaign-platform-card{background:var(--bg3);border:1px solid var(--border1);border-radius:var(--radius-sm);overflow:hidden;margin-bottom:.75rem}
.campaign-platform-header{display:flex;align-items:center;gap:.5rem;padding:.6rem .85rem;background:rgba(255,255,255,.03);border-bottom:1px solid var(--border1);font-size:.82rem;font-weight:700}
.campaign-platform-body{padding:.8rem .85rem}
.campaign-field{margin-bottom:.6rem}
.campaign-field-lbl{font-size:.7rem;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:.05em;margin-bottom:.2rem;display:flex;align-items:center;justify-content:space-between}
.campaign-field-val{font-size:.82rem;color:var(--text1);white-space:pre-wrap;word-break:break-word;line-height:1.55}
.project-pipeline-row{display:flex;align-items:center;gap:.75rem;padding:.5rem 0;border-bottom:1px solid var(--border1);font-size:.82rem}
.project-pipeline-row:last-child{border-bottom:none}

/* ─── Toast ─────────────────────────────────────── */
.toast-container{position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;display:flex;flex-direction:column;gap:.4rem}
.toast{padding:.6rem 1rem;border-radius:var(--radius-sm);font-size:.8rem;font-weight:600;min-width:200px;max-width:340px;box-shadow:var(--shadow);animation:slideIn .2s ease;pointer-events:none}
.toast.success{background:rgba(16,185,129,.9);color:#fff}
.toast.error{background:rgba(239,68,68,.9);color:#fff}
.toast.warn{background:rgba(245,158,11,.9);color:#000}
.toast.info{background:rgba(91,110,247,.9);color:#fff}
@keyframes slideIn{from{transform:translateX(60px);opacity:0}to{transform:none;opacity:1}}
</style>
</head>
<body>
<div class="shell">

<!-- TOPBAR -->
<div class="topbar">
  <div>
    <div class="topbar-logo">&#128039; AI-DAN</div>
    <div class="topbar-sub">Managing Director</div>
  </div>
  <div class="topbar-right">
    <span class="version-badge">v{version}</span>
    <span id="topbar-health" class="version-badge">&#9679; Loading...</span>
  </div>
</div>

<div class="main">
<!-- SIDEBAR -->
<div class="sidebar">
  <button class="nav-btn active" data-tab="chat" title="AI Chat" onclick="showTab('chat')">&#129302;</button>
  <button class="nav-btn" data-tab="dashboard" title="Dashboard" onclick="showTab('dashboard')">&#128200;</button>
  <button class="nav-btn" data-tab="analyze" title="Analyze Idea" onclick="showTab('analyze')">&#9889;</button>
  <button class="nav-btn" data-tab="factory" title="Factory" onclick="showTab('factory')">&#127981;</button>
  <button class="nav-btn" data-tab="launch" title="Launch Kit" onclick="showTab('launch')">&#128640;</button>
  <button class="nav-btn" data-tab="revenue" title="Revenue Loop" onclick="showTab('revenue')">&#128176;</button>
  <button class="nav-btn" data-tab="marketing" title="Marketing Hub" onclick="showTab('marketing')">&#127881;</button>
  <button class="nav-btn" data-tab="projects" title="My Projects" onclick="showTab('projects')">&#128218;</button>
</div>

<!-- CONTENT -->
<div class="content">

<!-- TAB 1: CHAT -->
<div class="tab-panel active" id="tab-chat">
  <div class="card" style="max-width:760px;margin:0 auto">
    <div class="card-title">&#129302; AI-DAN — Your Conversational Co-Founder</div>
    <div class="starter-prompts">
      <button class="starter-btn" onclick="usePrompt('I have a new business idea, let me tell you about it')">&#128161; Share an idea</button>
      <button class="starter-btn" onclick="usePrompt('What should I build next based on global trends?')">&#127758; Global trends</button>
      <button class="starter-btn" onclick="usePrompt('How do I get my first 100 paying customers fast?')">&#128176; Get customers</button>
      <button class="starter-btn" onclick="usePrompt('Roast my business idea honestly')">&#128293; Roast my idea</button>
      <button class="starter-btn" onclick="usePrompt('What is the fastest path to $10k MRR for a solo founder?')">&#128640; Fast revenue path</button>
      <button class="starter-btn" onclick="usePrompt('Give me an unconventional startup idea nobody is thinking about')">&#129323; Wild idea</button>
    </div>
    <div class="chat-wrap">
      <div class="chat-history" id="chat-history">
        <div class="msg bot">
          <div class="msg-avatar">&#128039;</div>
          <div class="msg-bubble">Hey! I'm AI-DAN, your co-founder. I've seen thousands of ideas — the brilliant ones, the terrible ones, and everything in between.<br><br>Got a concept cooking? Tell me about it and I'll give you the unfiltered truth. Or ask me anything about building, launching, or monetising a digital product. What's on your mind?</div>
        </div>
      </div>
      <div id="typing-indicator" style="display:none" class="msg bot">
        <div class="msg-avatar">&#128039;</div>
        <div class="msg-bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>
      </div>
      <div class="chat-input-row">
        <input class="chat-input" id="chat-input" placeholder="Ask AI-DAN anything…" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendChatMessage()}" autocomplete="off"/>
        <button class="chat-send" onclick="sendChatMessage()" title="Send">&#10148;</button>
      </div>
    </div>
  </div>
</div>

<!-- TAB 2: DASHBOARD -->
<div class="tab-panel" id="tab-dashboard">
  <div style="max-width:900px">
    <div class="stats-grid" id="dash-stats">
      <div class="stat-card"><div class="stat-val" style="font-size:1.2rem">&#8203;</div><div class="stat-label">Loading…</div></div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">
      <div class="card">
        <div class="card-title">&#127981; Active Builds</div>
        <div id="dash-builds"><div class="loading-row"><span class="spinner"></span></div></div>
      </div>
      <div class="card">
        <div class="card-title">&#128268; System Health</div>
        <div id="dash-health"><div class="loading-row"><span class="spinner"></span></div></div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">&#128336; Activity Feed</div>
      <div id="dash-activity"><div class="loading-row"><span class="spinner"></span></div></div>
    </div>
  </div>
</div>

<!-- TAB 3: ANALYZE IDEA -->
<div class="tab-panel" id="tab-analyze">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.2rem;max-width:1000px">
    <div class="card">
      <div class="card-title">&#9889; Score This Idea</div>

      <label for="idea-desc">Idea description *</label>
      <textarea id="idea-desc" placeholder="Describe your idea in 1-3 sentences. What does it do? Who is it for?" rows="3"></textarea>

      <label for="idea-problem">Problem being solved</label>
      <input type="text" id="idea-problem" placeholder="e.g. People struggle to find reliable freelancers"/>

      <label for="idea-user">Target user</label>
      <input type="text" id="idea-user" placeholder="e.g. Early-stage SaaS founders"/>

      <label for="idea-mono">Monetisation model</label>
      <select id="idea-mono">
        <option value="">Select model…</option>
        <option value="subscription">Subscription (SaaS)</option>
        <option value="marketplace">Marketplace (commission)</option>
        <option value="one_time">One-time purchase</option>
        <option value="freemium">Freemium</option>
        <option value="advertising">Advertising</option>
        <option value="enterprise">Enterprise / B2B</option>
        <option value="other">Other</option>
      </select>

      <label for="idea-comp">Competition level</label>
      <select id="idea-comp">
        <option value="">Select…</option>
        <option value="none">No direct competition</option>
        <option value="low">Low — small niche players</option>
        <option value="medium">Medium — some established players</option>
        <option value="high">High — dominated market</option>
      </select>

      <label for="idea-ttr">Time to first revenue</label>
      <select id="idea-ttr">
        <option value="">Select…</option>
        <option value="immediate">Immediate (days)</option>
        <option value="1_month">Within 1 month</option>
        <option value="3_months">1–3 months</option>
        <option value="6_months">3–6 months</option>
        <option value="1_year">6–12 months</option>
      </select>

      <label for="idea-diff">Key differentiator</label>
      <input type="text" id="idea-diff" placeholder="e.g. AI personalisation, 10x cheaper, unique distribution"/>

      <div id="analyze-error" class="alert alert-error" style="display:none;margin-top:.75rem"></div>

      <div style="display:flex;gap:.5rem;margin-top:1rem">
        <button class="btn btn-primary" style="flex:1" id="analyze-btn" onclick="submitAnalysis()">&#9889; Score This Idea</button>
        <button class="btn btn-secondary" onclick="clearAnalyzeForm()">Clear</button>
      </div>
    </div>

    <div id="analyze-results-col">
      <div class="card" style="text-align:center;color:var(--text4);padding:3rem 1rem">
        <div style="font-size:2rem;margin-bottom:.75rem">&#128202;</div>
        <div>Submit an idea to see your score</div>
      </div>
    </div>
  </div>
</div>

<!-- TAB 4: FACTORY -->
<div class="tab-panel" id="tab-factory">
  <div style="max-width:900px">
    <div class="card">
      <div class="card-title">&#127981; System Checks</div>
      <div id="factory-checks"><div class="loading-row"><span class="spinner"></span></div></div>
    </div>
    <div class="card">
      <div class="card-title" style="display:flex;justify-content:space-between;align-items:center">
        <span>&#9881; Build Runs</span>
        <button class="btn btn-secondary" style="font-size:.72rem;padding:.25rem .6rem" onclick="loadBuilds()">&#8635; Refresh</button>
      </div>
      <div id="factory-runs"><div class="loading-row"><span class="spinner"></span></div></div>
    </div>
  </div>
</div>

<!-- TAB 5: LAUNCH KIT -->
<div class="tab-panel" id="tab-launch">
  <div style="max-width:960px">
    <div style="display:grid;grid-template-columns:300px 1fr;gap:1.2rem;align-items:start">

      <!-- Left: config -->
      <div class="card">
        <div class="card-title">&#128640; Launch Config</div>

        <label for="launch-project">Link to project</label>
        <select id="launch-project">
          <option value="">— No project —</option>
        </select>

        <label for="launch-title">Product / Startup name *</label>
        <input type="text" id="launch-title" placeholder="e.g. GameForge"/>

        <label for="launch-url">Product URL</label>
        <input type="url" id="launch-url" placeholder="https://..."/>

        <label for="launch-desc">One-liner description *</label>
        <textarea id="launch-desc" rows="2" placeholder="e.g. Send personalised mini-games as digital gifts for any occasion"></textarea>

        <label for="launch-user">Target user</label>
        <input type="text" id="launch-user" placeholder="e.g. Gift-givers aged 25-40"/>

        <label for="launch-cta">Call to action</label>
        <input type="text" id="launch-cta" placeholder="e.g. Get early access free"/>

        <label for="launch-region">&#127758; Target Region</label>
        <select id="launch-region" onchange="onRegionChange()">
          <option value="global">&#127758; Global (All regions)</option>
          <option value="mena">MENA (Middle East &amp; North Africa)</option>
          <option value="africa">Sub-Saharan Africa</option>
          <option value="south_asia">South Asia (India, Pakistan, BD)</option>
          <option value="southeast_asia">Southeast Asia</option>
          <option value="latam">Latin America</option>
          <option value="europe">Western Europe</option>
          <option value="north_america">North America</option>
        </select>
        <div id="region-insight" class="alert alert-info" style="display:none;font-size:.78rem;margin:.5rem 0"></div>

        <div style="margin-top:1rem">
          <button class="btn btn-primary btn-full" id="launch-btn" onclick="generateLaunch()">
            &#9889; Generate All Content
          </button>
        </div>
        <div id="launch-error" class="alert alert-error" style="display:none"></div>

        <div class="section-sep"></div>

        <div class="card-title">&#127942; Platforms</div>
        <div class="platforms-grid" id="platforms-grid"></div>

        <div class="section-sep"></div>
        <div class="card-title">&#9200; 48h Checklist</div>
        <ul class="checklist" id="launch-checklist"></ul>
      </div>

      <!-- Right: generated content -->
      <div>
        <div id="launch-output">
          <div class="card" style="text-align:center;color:var(--text4);padding:3rem 1rem">
            <div style="font-size:2rem;margin-bottom:.75rem">&#128640;</div>
            <div>Fill in config and hit Generate</div>
          </div>
        </div>

        <!-- SOCIAL CARD GENERATOR -->
        <div class="card" style="margin-top:1.2rem">
          <div class="card-title">&#127912; Animated Social Card Generator</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.2rem;align-items:start">
            <div>
              <label for="card-size">Card Size</label>
              <select id="card-size" onchange="updateCardPreview()">
                <option value="square">Instagram Square (1080x1080)</option>
                <option value="landscape">Twitter/LinkedIn (1200x630)</option>
                <option value="story">Story / TikTok (1080x1920)</option>
              </select>
              <label for="card-style">Background Style</label>
              <select id="card-style" onchange="updateCardPreview()">
                <option value="purple">Gradient Purple</option>
                <option value="dark">Gradient Dark</option>
                <option value="sunset">Gradient Sunset</option>
                <option value="ocean">Gradient Ocean</option>
                <option value="black">Solid Black</option>
              </select>
              <label for="card-name">Product Name</label>
              <input type="text" id="card-name" placeholder="e.g. GameForge" oninput="updateCardPreview()"/>
              <label for="card-tagline">Tagline (max 60 chars)</label>
              <input type="text" id="card-tagline" maxlength="60" placeholder="e.g. Send games, not just gifts" oninput="updateCardPreview()"/>
              <label for="card-url">URL (short)</label>
              <input type="text" id="card-url" placeholder="e.g. gameforge.app" oninput="updateCardPreview()"/>
              <label for="card-accent">Accent Colour</label>
              <input type="color" id="card-accent" value="#5b6ef7" oninput="updateCardPreview()" style="width:60px;height:32px;padding:2px;cursor:pointer"/>
              <div style="margin-top:.8rem;display:flex;gap:.5rem">
                <button class="btn btn-secondary" style="flex:1" onclick="updateCardPreview()">&#128065; Preview</button>
                <button class="btn btn-success" style="flex:1" onclick="downloadSocialCard()">&#11123; Download PNG</button>
              </div>
            </div>
            <div style="text-align:center">
              <canvas id="social-card-canvas" width="300" height="300"
                style="border-radius:12px;width:100%;max-width:300px;border:1px solid var(--border2);cursor:pointer"
                onclick="downloadSocialCard()" title="Click to download full-size PNG"></canvas>
              <div style="font-size:.72rem;color:var(--text4);margin-top:.4rem">Click to download full-size PNG</div>
              <div style="margin-top:.5rem;font-size:.72rem;color:var(--text3)">&#128039; AI-DAN Dodo mascot included</div>
            </div>
          </div>
        </div>

        <!-- PROMO VIDEO GENERATOR -->
        <div class="card" style="margin-top:1.2rem">
          <div class="card-title">&#127916; AI Promo Video Generator <span style="font-size:.7rem;color:var(--text3);font-weight:400;margin-left:.5rem">Free &bull; GitHub Actions &bull; ~3 min</span></div>
          <div class="alert alert-info" style="font-size:.78rem;margin-bottom:.8rem">
            &#128161; AI writes a creative video script (Grok/OpenAI), then renders a free MP4 via GitHub Actions.
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:.8rem">
            <div>
              <label for="vid-product">Product Name</label>
              <input type="text" id="vid-product" placeholder="e.g. GameForge"/>
              <label for="vid-tagline">Tagline</label>
              <input type="text" id="vid-tagline" placeholder="e.g. Send games, not just gifts"/>
              <label for="vid-url">Product URL</label>
              <input type="url" id="vid-url" placeholder="https://..."/>
            </div>
            <div>
              <label for="vid-region">Target Region</label>
              <select id="vid-region">
                <option value="global">&#127758; Global</option>
                <option value="mena">MENA</option>
                <option value="africa">Africa</option>
                <option value="south_asia">South Asia</option>
                <option value="southeast_asia">Southeast Asia</option>
                <option value="latam">Latin America</option>
                <option value="europe">Europe</option>
                <option value="north_america">North America</option>
              </select>
              <div style="margin-top:.6rem">
                <label style="display:flex;align-items:center;gap:.5rem;cursor:pointer;font-weight:normal;font-size:.85rem;text-transform:none;letter-spacing:normal">
                  <input type="checkbox" id="vid-ai-concept" checked style="width:auto;margin:0"/>
                  &#10024; Use AI to write video script
                </label>
              </div>
              <div style="margin-top:.8rem">
                <button class="btn btn-primary btn-full" id="vid-btn" onclick="triggerVideoGeneration()">
                  &#127916; Generate Free Promo Video
                </button>
              </div>
              <div id="vid-result" style="margin-top:.6rem;font-size:.78rem"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
</div>

</div>
<!-- TAB 6: REVENUE LOOP -->
<div class="tab-panel" id="tab-revenue">
  <div style="max-width:900px">
    <div style="display:grid;grid-template-columns:340px 1fr;gap:1.2rem;align-items:start">
      <div class="card">
        <div class="card-title">&#128176; Log Revenue</div>
        <div class="alert alert-warn" style="font-size:.75rem;margin-bottom:.8rem">&#9888; Stored locally in this browser. Data will be lost if you clear browser storage.</div>

        <label for="rev-project">Project</label>
        <input type="text" id="rev-project" placeholder="e.g. GameForge"/>

        <label for="rev-amount">Amount (USD)</label>
        <input type="number" id="rev-amount" placeholder="0.00" min="0" step="0.01"/>

        <label for="rev-source">Source</label>
        <select id="rev-source">
          <option value="stripe">Stripe</option>
          <option value="lemonsqueezy">LemonSqueezy</option>
          <option value="paypal">PayPal</option>
          <option value="manual">Manual / Cash</option>
          <option value="other">Other</option>
        </select>

        <label for="rev-note">Note</label>
        <input type="text" id="rev-note" placeholder="Optional note…"/>

        <button class="btn btn-primary btn-full" style="margin-top:1rem" onclick="addRevenue()">&#10010; Log Revenue</button>

        <div class="section-sep"></div>
        <div class="card-title">&#128279; Payment Link</div>
        <input type="url" id="payment-url" placeholder="https://lemonsqueezy.com/..."/>
        <button class="btn btn-secondary btn-full" style="margin-top:.5rem" onclick="savePaymentLink()">Save Link</button>
        <div id="payment-link-display" style="margin-top:.5rem;font-size:.78rem;color:var(--text3)"></div>
      </div>

      <div>
        <div class="card">
          <div class="card-title" style="display:flex;justify-content:space-between">
            <span>&#128200; Revenue by Project</span>
            <button class="export-btn" onclick="exportRevenue()">&#11015; Export CSV</button>
          </div>
          <div id="rev-table-wrap"><div style="color:var(--text4);font-size:.82rem;text-align:center;padding:1.5rem">No revenue logged yet</div></div>
        </div>
        <div class="card">
          <div class="card-title">&#128293; Pipeline Score</div>
          <div id="pipeline-score-wrap">
            <div style="color:var(--text3);font-size:.82rem">Score will appear after logging revenue</div>
          </div>
        </div>
        <div class="card">
          <div class="card-title">&#128221; Learning Log</div>
          <textarea id="learning-log" rows="4" placeholder="What worked? What flopped? Record learnings here…"></textarea>
          <button class="btn btn-secondary" style="margin-top:.5rem;font-size:.75rem" onclick="saveLearningLog()">&#128190; Save</button>
        </div>
      </div>
    </div>
  </div>
</div>


<!-- TAB 7: MARKETING HUB -->
<div class="tab-panel" id="tab-marketing">
  <div style="max-width:960px">
    <div style="display:grid;grid-template-columns:300px 1fr;gap:1.2rem;align-items:start">

      <!-- Left: Config -->
      <div>
        <div class="card">
          <div class="card-title">&#127881; Campaign Generator</div>

          <label for="mkt-product">Product Name *</label>
          <input type="text" id="mkt-product" placeholder="e.g. GameForge"/>

          <label for="mkt-hook">Core Hook (what makes it special)</label>
          <input type="text" id="mkt-hook" placeholder="e.g. Send personalised mini-games as gifts"/>

          <label for="mkt-audience">Target Audience</label>
          <input type="text" id="mkt-audience" placeholder="e.g. Gift-givers aged 25-40"/>

          <label for="mkt-region">Primary Region</label>
          <select id="mkt-region" onchange="updateMktPlatforms()">
            <option value="global">&#127758; Global</option>
            <option value="mena">MENA (Middle East &amp; North Africa)</option>
            <option value="africa">Sub-Saharan Africa</option>
            <option value="south_asia">South Asia</option>
            <option value="southeast_asia">Southeast Asia</option>
            <option value="latam">Latin America</option>
            <option value="europe">Western Europe</option>
            <option value="north_america">North America</option>
          </select>
          <div id="mkt-region-insight" class="alert alert-info" style="margin:.5rem 0;font-size:.75rem;display:none"></div>

          <label for="mkt-goal">Campaign Goal</label>
          <select id="mkt-goal">
            <option value="awareness">Brand Awareness</option>
            <option value="signups">Email / Signups</option>
            <option value="sales">Direct Sales</option>
            <option value="viral">Viral / Shares</option>
          </select>

          <label for="mkt-budget">Budget Level</label>
          <select id="mkt-budget">
            <option value="zero">Zero Budget (organic only)</option>
            <option value="micro">Micro ($1–50/day)</option>
            <option value="small">Small ($50–200/day)</option>
          </select>

          <div style="margin-top:1rem;display:flex;gap:.5rem">
            <button class="btn btn-primary" style="flex:1" id="mkt-gen-btn" onclick="generateCampaign()">
              &#10024; Generate Campaign
            </button>
            <button class="btn btn-secondary" onclick="clearMktForm()">Clear</button>
          </div>
          <div id="mkt-error" class="alert alert-error" style="display:none;margin-top:.5rem"></div>
        </div>

        <div class="card">
          <div class="card-title">&#127758; Platform Playbook by Region</div>
          <div id="mkt-platform-guide" style="font-size:.8rem;line-height:1.7;color:var(--text2)">
            Select a region above to see the best platforms to use.
          </div>
        </div>
      </div>

      <!-- Right: Generated output -->
      <div>
        <div id="mkt-output">
          <div class="card" style="text-align:center;color:var(--text4);padding:3rem 1rem">
            <div style="font-size:2.5rem;margin-bottom:.75rem">&#127756;</div>
            <div style="font-size:.9rem">Fill in your product details and hit Generate Campaign</div>
            <div style="font-size:.78rem;margin-top:.5rem;color:var(--text4)">AI-DAN will write region-specific content for each platform</div>
          </div>
        </div>

        <!-- Out-of-the-box concepts panel -->
        <div class="card" style="margin-top:1.2rem">
          <div class="card-title">&#129513; Out-of-the-Box Campaign Concepts</div>
          <div class="alert alert-info" style="font-size:.78rem;margin-bottom:.9rem">
            &#128161; These unconventional ideas have worked for zero-budget founders globally.
          </div>
          <div id="mkt-concepts-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem">
            <div class="card" style="padding:.8rem;margin:0">
              <div style="font-weight:700;font-size:.82rem;margin-bottom:.3rem;color:var(--accent3)">&#127926; Meme-first launch</div>
              <div style="font-size:.78rem;color:var(--text2)">Create 5 relatable memes about your audience's pain. Post them before showing your product. No pitch. Just laughs. Then drop the link in comment.</div>
            </div>
            <div class="card" style="padding:.8rem;margin:0">
              <div style="font-weight:700;font-size:.82rem;margin-bottom:.3rem;color:var(--accent3)">&#128247; Behind-the-scenes build</div>
              <div style="font-size:.78rem;color:var(--text2)">Document building your app in real time on TikTok/Instagram Reels. "Day 1 of building X" series. Founders get 10x more engagement than polished ads.</div>
            </div>
            <div class="card" style="padding:.8rem;margin:0">
              <div style="font-weight:700;font-size:.82rem;margin-bottom:.3rem;color:var(--accent3)">&#127942; Challenge campaign</div>
              <div style="font-size:.78rem;color:var(--text2)">Create a 7-day challenge relevant to your niche. Free, no signup. On day 7 offer your product as the "next level". Works brilliantly on WhatsApp groups.</div>
            </div>
            <div class="card" style="padding:.8rem;margin:0">
              <div style="font-weight:700;font-size:.82rem;margin-bottom:.3rem;color:var(--accent3)">&#128587; Controversy post</div>
              <div style="font-size:.78rem;color:var(--text2)">Post a hot take about your industry. Don't be rude — be insightful but polarising. Comments go wild. Algorithm loves this. Drop product link in bio.</div>
            </div>
            <div class="card" style="padding:.8rem;margin:0">
              <div style="font-weight:700;font-size:.82rem;margin-bottom:.3rem;color:var(--accent3)">&#128276; DM cold outreach wave</div>
              <div style="font-size:.78rem;color:var(--text2)">Send 50 personalised DMs per day to your ICP on Instagram/Twitter. Not a pitch — a genuine question about their problem. 2-3% will convert. That's 1-2 customers/day.</div>
            </div>
            <div class="card" style="padding:.8rem;margin:0">
              <div style="font-weight:700;font-size:.82rem;margin-bottom:.3rem;color:var(--accent3)">&#128101; Community infiltration</div>
              <div style="font-size:.78rem;color:var(--text2)">Find 10 Facebook Groups / Reddit communities where your ICP hangs out. Spend 2 weeks providing value. Then soft-mention your product when asked for solutions.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- TAB 8: MY PROJECTS -->
<div class="tab-panel" id="tab-projects">
  <div style="max-width:960px">
    <div class="card">
      <div class="card-title" style="display:flex;justify-content:space-between;align-items:center">
        <span>&#128218; My Projects Pipeline</span>
        <button class="btn btn-primary" style="font-size:.75rem;padding:.3rem .75rem" onclick="showTab('analyze')">&#43; Score New Idea</button>
      </div>
      <div id="projects-pipeline">
        <div class="loading-row"><span class="spinner"></span> Loading...</div>
      </div>
    </div>

    <!-- Pre-built project cards for the three known ideas -->
    <div style="margin-top:1rem">
      <div class="card-title" style="margin-bottom:.75rem;color:var(--text3);font-size:.75rem;text-transform:uppercase;letter-spacing:.06em">&#127959; In Development</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem">
        <div class="card" style="border-left:3px solid var(--accent3);margin:0">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.6rem">
            <div style="font-weight:700;font-size:.95rem">&#127918; Digital Gifts</div>
            <span class="badge badge-warn">Building</span>
          </div>
          <div style="font-size:.8rem;color:var(--text2);margin-bottom:.75rem;line-height:1.55">
            Personalised mini-games and animated digital invitation cards sold as gifts. AI customisation for any occasion.
          </div>
          <div style="font-size:.75rem;color:var(--text3);margin-bottom:.75rem">
            &#128279; <a href="https://github.com/ismaelloveexcel/gameforge-mobile" target="_blank">gameforge-mobile</a>
          </div>
          <div style="display:flex;gap:.4rem;flex-wrap:wrap">
            <button class="btn btn-secondary" style="font-size:.72rem;padding:.25rem .6rem" onclick="usePrompt('How do I get my first 10 paying customers for a digital gift card app that sells personalised mini-games?');showTab('chat')">&#128039; Ask AI-DAN</button>
            <button class="btn btn-secondary" style="font-size:.72rem;padding:.25rem .6rem" onclick="prefillLaunch('Digital Gifts','Send personalised mini-games as gifts','Gift-givers 25-40')">&#128640; Launch Kit</button>
            <button class="btn btn-secondary" style="font-size:.72rem;padding:.25rem .6rem" onclick="prefillMarketing('Digital Gifts','Personalised mini-games as digital gifts')">&#127881; Market It</button>
          </div>
        </div>

        <div class="card" style="border-left:3px solid var(--accent2);margin:0">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.6rem">
            <div style="font-weight:700;font-size:.95rem">&#127891; EduGate</div>
            <span class="badge badge-info">Ideation</span>
          </div>
          <div style="font-size:.8rem;color:var(--text2);margin-bottom:.75rem;line-height:1.55">
            Education platform — gateway to quality learning. Connecting students with curated courses and learning pathways.
          </div>
          <div style="font-size:.75rem;color:var(--text3);margin-bottom:.75rem">
            &#128279; <a href="https://github.com/ismaelloveexcel/EduGate" target="_blank">EduGate</a>
          </div>
          <div style="display:flex;gap:.4rem;flex-wrap:wrap">
            <button class="btn btn-secondary" style="font-size:.72rem;padding:.25rem .6rem" onclick="usePrompt('What is the fastest way to monetise an education platform targeting students in MENA and Africa?');showTab('chat')">&#128039; Ask AI-DAN</button>
            <button class="btn btn-secondary" style="font-size:.72rem;padding:.25rem .6rem" onclick="prefillAnalyze('EduGate — a platform connecting students with quality curated learning pathways and courses, starting in MENA and Africa','Education access is poor and expensive in emerging markets','Students 16-30 in MENA and Africa')">&#9889; Score It</button>
            <button class="btn btn-secondary" style="font-size:.72rem;padding:.25rem .6rem" onclick="prefillMarketing('EduGate','Quality education accessible to all students')">&#127881; Market It</button>
          </div>
        </div>

        <div class="card" style="border-left:3px solid #ec4899;margin:0">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.6rem">
            <div style="font-weight:700;font-size:.95rem">&#10084; Sparks</div>
            <span class="badge badge-info">Concept</span>
          </div>
          <div style="font-size:.8rem;color:var(--text2);margin-bottom:.75rem;line-height:1.55">
            Gaming platform for couples who match on dating apps. Replaces boring chat with fun mini-games to help people get to know each other naturally.
          </div>
          <div style="font-size:.75rem;color:var(--text3);margin-bottom:.75rem">
            &#128161; Concept stage — needs scoring
          </div>
          <div style="display:flex;gap:.4rem;flex-wrap:wrap">
            <button class="btn btn-secondary" style="font-size:.72rem;padding:.25rem .6rem" onclick="usePrompt('Score this business idea honestly: Sparks is a gaming platform where people who match on dating apps can play mini-games together to get to know each other. What are the biggest risks and the fastest path to monetisation?');showTab('chat')">&#128039; Ask AI-DAN</button>
            <button class="btn btn-secondary" style="font-size:.72rem;padding:.25rem .6rem" onclick="prefillAnalyze('Sparks — a gaming platform where people who match on dating apps can play fun mini-games together to get to know each other. Replaces awkward text conversations with interactive games.','People match on dating apps but lose momentum because chat is boring','Single people 18-35 who use dating apps')">&#9889; Score It</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

</div><!-- /content -->
</div><!-- /main -->
</div><!-- /shell -->

<div class="toast-container" id="toast-container"></div>

<script>
// ─── Utilities ────────────────────────────────────────────────────────────
function esc(s){var d=document.createElement('div');d.textContent=String(s||'');return d.innerHTML;}

function toast(msg, type, dur) {
  type = type || 'info'; dur = dur || 3200;
  var el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  var c = document.getElementById('toast-container');
  c.appendChild(el);
  setTimeout(function(){ el.style.opacity='0'; el.style.transition='opacity .3s'; setTimeout(function(){ el.remove(); }, 300); }, dur);
}

function copyText(text, label) {
  navigator.clipboard.writeText(text).then(function(){
    toast('Copied ' + (label||''), 'success', 1600);
  }).catch(function(){
    toast('Copy failed', 'error');
  });
}

function apiFetch(path, opts) {
  opts = opts || {};
  var mergedOpts = Object.assign({ headers: {'Content-Type':'application/json'} }, opts);
  if (opts.headers) mergedOpts.headers = Object.assign({'Content-Type':'application/json'}, opts.headers);
  return fetch(path, mergedOpts).then(function(r) {
    if (r.status === 401) throw new Error('Authentication required — check API key');
    if (r.status === 429) throw new Error('Rate limit hit — wait a moment');
    if (r.status >= 500) throw new Error('Server error ('+r.status+') — check Vercel logs');
    if (!r.ok) return r.text().then(function(t){
      var msg = t;
      try { var d = JSON.parse(t); msg = d.detail || d.message || t; } catch(e){}
      throw new Error(msg);
    });
    return r.text().then(function(t){
      if (!t) return {};
      try { return JSON.parse(t); } catch(e) { throw new Error('Invalid JSON response'); }
    });
  }).catch(function(e) {
    if (e.message && e.message.indexOf('fetch') !== -1) throw new Error("Can't reach server — check your network");
    throw e;
  });
}

// ─── Tab switching ────────────────────────────────────────────────────────
function showTab(name) {
  document.querySelectorAll('.nav-btn').forEach(function(b){ b.classList.remove('active'); });
  document.querySelectorAll('.tab-panel').forEach(function(p){ p.classList.remove('active'); });
  document.querySelector('[data-tab="'+name+'"]').classList.add('active');
  document.getElementById('tab-'+name).classList.add('active');
  if (name === 'dashboard') loadDashboard();
  if (name === 'factory') loadFactory();
  if (name === 'launch') loadLaunchProjects();
  if (name === 'revenue') renderRevTable();
  if (name === 'marketing') updateMktPlatforms();
  if (name === 'projects') loadProjectsPipeline();
}

// ─── Chat ─────────────────────────────────────────────────────────────────
var chatHistory = [];

function usePrompt(text) {
  document.getElementById('chat-input').value = text;
  sendChatMessage();
}

function formatBotMsg(text) {
  // Render basic markdown: **bold**, numbered lists, and preserve newlines
  return text
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/\\*\\*(.+?)\\*\\*/g,'<strong>$1</strong>')
    .replace(/^(\\d+\\. .+)$/gm,'<div style="margin:.15rem 0">$1</div>')
    .replace(/^(#{1,3} .+)$/gm,'<div style="font-weight:700;margin:.4rem 0;color:#fff">$1</div>')
    .replace(/\\n\\n/g,'<br><br>')
    .replace(/\\n/g,'<br>');
}

function appendMsg(role, text) {
  var hist = document.getElementById('chat-history');
  var div = document.createElement('div');
  div.className = 'msg ' + (role === 'user' ? 'user' : 'bot');
  var avatar = role === 'user' ? '&#128100;' : '&#128039;';
  var formatted = role === 'bot' ? formatBotMsg(text) : esc(text);
  div.innerHTML = '<div class="msg-avatar">'+avatar+'</div><div class="msg-bubble">'+formatted+'</div>';
  hist.appendChild(div);
  hist.scrollTop = hist.scrollHeight;
  return div;
}

function sendChatMessage() {
  var input = document.getElementById('chat-input');
  var msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  appendMsg('user', msg);
  chatHistory.push({role:'user', content:msg});
  document.getElementById('typing-indicator').style.display = 'flex';
  document.getElementById('chat-history').scrollTop = 99999;

  apiFetch('/chat/talk', {method:'POST', body:JSON.stringify({message:msg, history:chatHistory.slice(-20)})})
    .then(function(data) {
      document.getElementById('typing-indicator').style.display = 'none';
      var reply = data.reply || data.message || JSON.stringify(data);
      appendMsg('bot', reply);
      chatHistory.push({role:'assistant', content:reply});
      if (data.model) document.getElementById('topbar-health').textContent = '&#9679; ' + data.model;
    })
    .catch(function(err) {
      document.getElementById('typing-indicator').style.display = 'none';
      appendMsg('bot', '&#9888; Error: ' + err.message);
      toast(err.message, 'error');
    });
}

// ─── Dashboard ────────────────────────────────────────────────────────────
function loadDashboard() {
  Promise.all([
    apiFetch('/portfolio/projects').catch(function(){return [];}),
    apiFetch('/api/dashboard/health').catch(function(){return {};}),
    apiFetch('/factory/runs').catch(function(){return {runs:[]};})
  ]).then(function(results) {
    renderDashStats(results[0], results[1]);
    renderDashHealth(results[1]);
    renderDashBuilds(results[2]);
    renderDashActivity(results[0]);
  });
}

function renderDashStats(projects, health) {
  var total = Array.isArray(projects) ? projects.length : 0;
  var approved = Array.isArray(projects) ? projects.filter(function(p){return p.state==='approved';}).length : 0;
  var rev = health.revenue_total || 0;
  var hStatus = health.health_status || 'RED';
  document.getElementById('dash-stats').innerHTML =
    '<div class="stat-card"><div class="stat-val">'+total+'</div><div class="stat-label">Projects</div></div>' +
    '<div class="stat-card"><div class="stat-val">'+approved+'</div><div class="stat-label">Approved</div></div>' +
    '<div class="stat-card"><div class="stat-val">$'+rev.toLocaleString()+'</div><div class="stat-label">Revenue</div></div>' +
    '<div class="stat-card"><div class="stat-val" style="font-size:1rem">'+(hStatus==='GREEN'?'&#128994;':hStatus==='AMBER'?'&#128993;':'&#128308;')+'</div><div class="stat-label">Health</div></div>';
  var hEl = document.getElementById('topbar-health');
  hEl.textContent = '&#9679; ' + (health.summary || hStatus);
  hEl.style.color = hStatus === 'GREEN' ? 'var(--success)' : hStatus === 'AMBER' ? 'var(--warn)' : 'var(--error)';
}

function renderDashBuilds(data) {
  var runs = (data && data.runs) ? data.runs : (Array.isArray(data) ? data : []);
  if (!runs.length) { document.getElementById('dash-builds').innerHTML = '<div class="loading-row">No build runs yet</div>'; return; }
  var html = '<table class="builds-table"><thead><tr><th>Project</th><th>Status</th><th>Time</th></tr></thead><tbody>';
  runs.slice(0,5).forEach(function(r) {
    var cls = r.status==='success'?'badge-success':r.status==='failed'?'badge-error':'badge-info';
    html += '<tr><td>'+esc(r.project_name||r.name||'—')+'</td><td><span class="badge '+cls+'">'+esc(r.status||'—')+'</span></td><td style="color:var(--text3)">'+esc(r.created_at||r.timestamp||'')+'</td></tr>';
  });
  html += '</tbody></table>';
  document.getElementById('dash-builds').innerHTML = html;
}

function renderDashHealth(h) {
  if (!h || !Object.keys(h).length) { document.getElementById('dash-health').innerHTML = '<div class="loading-row">No data</div>'; return; }
  var items = [
    ['Portfolio', h.health_status === 'GREEN' ? 'green' : h.health_status === 'AMBER' ? 'amber' : 'red', h.summary || h.health_status],
    ['Total Projects', 'green', (h.total_projects||0) + ' tracked'],
    ['Approved', 'green', (h.approved_count||0) + ' ready to build'],
    ['Revenue', h.revenue_total > 0 ? 'green' : 'amber', '$' + (h.revenue_total||0).toLocaleString() + ' total'],
  ];
  document.getElementById('dash-health').innerHTML = items.map(function(i){
    return '<div style="display:flex;align-items:center;gap:.5rem;padding:.35rem 0;border-bottom:1px solid var(--border1);font-size:.8rem"><span class="health-dot '+i[1]+'"></span><span style="color:var(--text2);flex:1">'+esc(i[0])+'</span><span style="color:var(--text3)">'+esc(i[2])+'</span></div>';
  }).join('');
}

function renderDashActivity(projects) {
  if (!Array.isArray(projects) || !projects.length) {
    document.getElementById('dash-activity').innerHTML = '<div class="loading-row">No activity yet — add your first project idea</div>';
    return;
  }
  var html = '';
  projects.slice(0,8).forEach(function(p) {
    var state = p.state || 'idea';
    var icon = {idea:'&#128161;',approved:'&#9989;',building:'&#127981;',deployed:'&#127640;',scaling:'&#128640;'}[state] || '&#128462;';
    html += '<div style="display:flex;align-items:center;gap:.6rem;padding:.4rem 0;border-bottom:1px solid var(--border1);font-size:.8rem">' +
      '<span>'+icon+'</span>' +
      '<span style="flex:1;color:var(--text1)">'+esc(p.name||p.title||'Untitled')+'</span>' +
      '<span class="badge badge-muted">'+esc(state)+'</span>' +
    '</div>';
  });
  document.getElementById('dash-activity').innerHTML = html;
}

// ─── Analyze ──────────────────────────────────────────────────────────────
function submitAnalysis() {
  const desc = document.getElementById('idea-desc').value.trim();
  if (!desc) { toast('Please enter your idea description', 'warn'); return; }

  const btn = document.getElementById('analyze-btn');
  const errEl = document.getElementById('analyze-error');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Scoring...';
  errEl.style.display = 'none';

  const payload = {
    idea: desc,
    problem: document.getElementById('idea-problem').value.trim(),
    target_user: document.getElementById('idea-user').value.trim(),
    monetization_model: document.getElementById('idea-mono').value,
    competition_level: document.getElementById('idea-comp').value,
    time_to_revenue: document.getElementById('idea-ttr').value,
    differentiation: document.getElementById('idea-diff').value.trim(),
  };

  apiFetch('/api/analyze/', {method:'POST', body: JSON.stringify(payload)})
    .then(function(data) { renderAnalysisResult(data); })
    .catch(function(err) {
      errEl.textContent = err.message;
      errEl.style.display = 'block';
      toast('Analysis failed: ' + err.message, 'error');
    })
    .finally(function() {
      btn.disabled = false;
      btn.innerHTML = '&#9889; Score This Idea';
    });
}

function clearAnalyzeForm() {
  ['idea-desc','idea-problem','idea-user','idea-diff'].forEach(function(id){ document.getElementById(id).value=''; });
  ['idea-mono','idea-comp','idea-ttr'].forEach(function(id){ document.getElementById(id).selectedIndex=0; });
  document.getElementById('analyze-error').style.display = 'none';
  document.getElementById('analyze-results-col').innerHTML =
    '<div class="card" style="text-align:center;color:var(--text4);padding:3rem 1rem"><div style="font-size:2rem;margin-bottom:.75rem">&#128202;</div><div>Submit an idea to see your score</div></div>';
}

function scoreColor(s) {
  if (s >= 7) return 'score-high';
  if (s >= 4) return 'score-med';
  return 'score-low';
}

function renderAnalysisResult(d) {
  const decision = (d.final_decision || d.score_decision || d.decision || d.verdict || 'HOLD').toUpperCase();
  const scores = d.score_breakdown || d.scores || {};
  const overall = d.total_score || scores.overall || d.overall_score || 0;

  const scoreFields = [
    ['Overall','overall', overall],
    ['Feasibility','feasibility', scores.feasibility || d.feasibility_score || 0],
    ['Profitability','profitability', scores.profitability || d.profitability_score || 0],
    ['Speed to Revenue','speed_to_revenue', scores.speed_to_revenue || scores.speed || d.speed_score || 0],
    ['Competition','competition', scores.competition || d.competition_score || 0],
  ];

  const lowScores = scoreFields.filter(function(s){ return parseFloat(s[2]) < 5; });

  let barsHtml = '';
  scoreFields.forEach(function(sf) {
    const val = parseFloat(sf[2]) || 0;
    const pct = (val / 10) * 100;
    const cls = scoreColor(val);
    barsHtml += '<div class="score-row">' +
      '<div class="score-label-row"><span>' + esc(sf[0]) + '</span><span>' + val.toFixed(1) + '/10</span></div>' +
      '<div class="score-bar"><div class="score-fill ' + cls + '" style="width:' + pct + '%"></div></div>' +
    '</div>';
  });

  let validHtml = '';
  const blockers = d.validation_blocking || [];
  if (blockers.length) {
    validHtml = '<div class="alert alert-error" style="margin-bottom:.5rem"><strong>&#9888; Blockers:</strong><ul style="margin:.3rem 0 0 1rem;padding:0">' +
      blockers.map(function(b){return '<li>'+esc(b)+'</li>';}).join('') + '</ul></div>';
  }

  let warnHtml = '';
  if (lowScores.length > 0) {
    warnHtml = '<div class="alert alert-warn">&#9888; Low scores: ' +
      lowScores.map(function(s){ return esc(s[0]) + ' (' + parseFloat(s[2]).toFixed(1) + ')'; }).join(', ') +
    '. Consider these risks carefully.</div>';
  }

  const brief = d.offer || d.business_brief || d.brief || {};
  let briefHtml = '';
  if (brief.title || d.title) {
    briefHtml = '<div class="section-sep"></div><div style="font-size:.85rem">' +
      '<div style="font-weight:700;color:#fff;margin-bottom:.4rem">' + esc(brief.title || d.title || '') + '</div>' +
      (brief.target_user ? '<div style="color:var(--text3);margin-bottom:.2rem">&#127989; ' + esc(brief.target_user) + '</div>' : '') +
      (brief.problem ? '<div style="color:var(--text2);margin-bottom:.2rem">Problem: ' + esc(brief.problem) + '</div>' : '') +
      (brief.solution ? '<div style="color:var(--text2)">Solution: ' + esc(brief.solution) + '</div>' : '') +
    '</div>';
  }

  const nextMoves = {
    APPROVED: (d.next_step || d.next_move || 'Start building the MVP immediately.'),
    HOLD: (d.next_step || d.next_move || 'Validate the idea with 5 real users before building.'),
    REJECTED: (d.next_step || d.next_move || 'Move on. Your time is too valuable for this one.'),
  };

  let actionHtml = '';
  if (decision === 'APPROVED') {
    const projName = (d.title || brief.title || 'New Project').replace(/[^a-z0-9-]/gi,'_').toLowerCase();
    actionHtml = '<button class="btn btn-success btn-full" style="margin-top:.75rem" onclick="triggerBuild(\''+esc(projName)+'\')">&#127981; Trigger Build in Factory</button>';
  }

  const decisionClass = decision === 'APPROVED' ? 'decision-approved' : decision === 'REJECTED' ? 'decision-rejected' : 'decision-hold';

  document.getElementById('analyze-results-col').innerHTML =
    '<div class="card result-card">' +
      '<span class="decision-badge ' + decisionClass + '">' + decision + '</span>' +
      validHtml +
      warnHtml +
      barsHtml +
      briefHtml +
      '<div class="section-sep"></div>' +
      '<div style="font-size:.82rem;color:var(--text2);line-height:1.6">' + esc(nextMoves[decision] || nextMoves.HOLD) + '</div>' +
      actionHtml +
    '</div>';
}

// ─── Factory ──────────────────────────────────────────────────────────────
function loadFactory() {
  loadSystemChecks();
  loadBuilds();
  if (window._factoryRefreshTimer) clearInterval(window._factoryRefreshTimer);
  window._factoryRefreshTimer = setInterval(function(){
    var t = document.querySelector('.nav-btn[data-tab="factory"]');
    if (t && t.classList.contains('active')) { loadBuilds(); }
  }, 30000);
}

function loadSystemChecks() {
  document.getElementById('factory-checks').innerHTML = '<div class="loading-row"><span class="spinner"></span></div>';
  apiFetch('/api/dashboard/health')
    .then(function(h) {
      const checks = [
        {label:'AI Provider', ok: !!h.health_status, info: h.health_status || 'unknown'},
        {label:'Portfolio DB', ok: (h.total_projects !== undefined), info: (h.total_projects||0)+' projects'},
        {label:'System', ok: h.health_status !== 'RED', info: h.summary || h.health_status || '—'},
      ];
      document.getElementById('factory-checks').innerHTML = checks.map(function(c){
        return '<div style="display:flex;align-items:center;gap:.5rem;padding:.35rem 0;border-bottom:1px solid var(--border1);font-size:.8rem">' +
          '<span class="health-dot '+(c.ok?'green':'red')+'"></span>' +
          '<span style="flex:1;color:var(--text2)">'+esc(c.label)+'</span>' +
          '<span style="color:var(--text3)">'+esc(c.info)+'</span>' +
        '</div>';
      }).join('');
    })
    .catch(function(){ document.getElementById('factory-checks').innerHTML = '<div class="alert alert-error">Failed to load checks</div>'; });
}

function loadBuilds() {
  document.getElementById('factory-runs').innerHTML = '<div class="loading-row"><span class="spinner"></span></div>';
  apiFetch('/factory/runs')
    .then(function(data) {
      var runs = data.runs || (Array.isArray(data) ? data : []);
      if (!runs.length) {
        document.getElementById('factory-runs').innerHTML =
          '<div style="color:var(--text4);text-align:center;padding:1.2rem;font-size:.82rem">No build runs yet.<br><span style="font-size:.75rem">Score an idea and hit Trigger Build to start.</span></div>';
        return;
      }
      var html = '<table class="builds-table"><thead><tr><th>Project</th><th>Status</th><th>Deployment</th><th>Created</th><th></th></tr></thead><tbody>';
      runs.slice(0,20).forEach(function(r) {
        var cls = r.status==='success'?'badge-success':r.status==='failed'?'badge-error':r.status==='running'?'badge-info':'badge-muted';
        var depLink = r.deployment_url ? '<a href="'+esc(r.deployment_url)+'" target="_blank" class="badge badge-success">&#127640; Live</a>' : '<span class="badge badge-muted">—</span>';
        html += '<tr>' +
          '<td>'+esc(r.project_name||r.name||'—')+'</td>' +
          '<td><span class="badge '+cls+'">'+esc(r.status||'—')+'</span></td>' +
          '<td>'+depLink+'</td>' +
          '<td style="color:var(--text3);font-size:.72rem">'+esc(r.created_at||r.timestamp||'')+'</td>' +
          '<td><button class="copy-btn" onclick="copyText(\''+esc(JSON.stringify(r))+'\',\'run data\')">&#128203;</button></td>' +
        '</tr>';
      });
      html += '</tbody></table>';
      document.getElementById('factory-runs').innerHTML = html;
    })
    .catch(function(e){ document.getElementById('factory-runs').innerHTML = '<div class="alert alert-error">&#9888; '+esc(e.message)+'</div>'; });
}

function triggerBuild(name) {
  name = name || prompt('Project name to build:');
  if (!name) return;
  apiFetch('/factory/trigger', {method:'POST', body: JSON.stringify({project_name: name, dry_run: false})})
    .then(function(){ toast('Build triggered for: ' + name, 'success'); loadBuilds(); })
    .catch(function(e){ toast('Trigger failed: ' + e.message, 'error'); });
}

// ─── Launch Kit ───────────────────────────────────────────────────────────
var _launchPlatforms = ['instagram','tiktok','whatsapp','twitter','linkedin','reddit','youtube','email','snapchat','facebook','producthunt'];
var _platIcons = {instagram:'&#128247;',tiktok:'&#127925;',whatsapp:'&#128172;',twitter:'&#120143;',linkedin:'&#128188;',reddit:'&#128172;',youtube:'&#128249;',email:'&#128140;',snapchat:'&#128163;',facebook:'&#128100;',producthunt:'&#128018;'};
var _platLabels = {instagram:'Instagram',tiktok:'TikTok',whatsapp:'WhatsApp',twitter:'Twitter/X',linkedin:'LinkedIn',reddit:'Reddit',youtube:'YouTube',email:'Email',snapchat:'Snapchat',facebook:'Facebook',producthunt:'Product Hunt'};

function loadLaunchProjects() {
  apiFetch('/portfolio/projects')
    .then(function(projects) {
      var sel = document.getElementById('launch-project');
      var prev = sel.value;
      sel.innerHTML = '<option value="">— No project —</option>';
      (Array.isArray(projects) ? projects : []).forEach(function(p){
        var o = document.createElement('option');
        o.value = p.id || p.project_id || '';
        o.textContent = p.name || p.title || p.id || '—';
        sel.appendChild(o);
      });
      if (prev) sel.value = prev;
    })
    .catch(function(){});
  renderPlatformCheckboxes();
  renderChecklist();
}

function renderPlatformCheckboxes() {
  var html = '';
  _launchPlatforms.forEach(function(p){
    html += '<label class="plat-check" id="plat-'+p+'" onclick="togglePlatform(this)">' +
      '<input type="checkbox" value="'+p+'" checked/>' +
      (_platIcons[p]||'') + ' ' + (_platLabels[p]||p) +
    '</label>';
  });
  var el = document.getElementById('platforms-grid');
  if (el) {
    el.innerHTML = html;
    el.querySelectorAll('.plat-check').forEach(function(l){ l.classList.add('selected'); });
  }
}

function togglePlatform(lbl) {
  var cb = lbl.querySelector('input');
  cb.checked = !cb.checked;
  lbl.classList.toggle('selected', cb.checked);
}

function getSelectedPlatforms() {
  var result = [];
  document.querySelectorAll('#platforms-grid input:checked').forEach(function(cb){ result.push(cb.value); });
  return result;
}

function renderChecklist() {
  var items = [
    'Create accounts on selected platforms','Set up payment link (LemonSqueezy / Stripe)',
    'Write first post manually to test response','Set up basic analytics (Plausible or similar)',
    'Share in 3 relevant communities/groups','Record a 60-second demo video',
    'Set up email capture (Mailchimp free tier)','Monitor comments for first 48 hours',
    'Follow up with anyone who engages','Log revenue and learnings in Revenue Loop',
  ];
  var el = document.getElementById('launch-checklist');
  if (el) el.innerHTML = items.map(function(i){ return '<li>'+esc(i)+'</li>'; }).join('');
}

function generateLaunch() {
  const title = document.getElementById('launch-title').value.trim();
  const url = document.getElementById('launch-url').value.trim();
  const desc = document.getElementById('launch-desc').value.trim();
  if (!title || !desc) { toast('Product title and description are required', 'warn'); return; }

  const selectedPlatforms = getSelectedPlatforms ? getSelectedPlatforms() : [];
  if (!selectedPlatforms.length) { toast('Select at least one platform \u2193', 'warn'); return; }

  const btn = document.getElementById('launch-btn');
  const errEl = document.getElementById('launch-error');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Generating...';
  errEl.style.display = 'none';

  const projId = document.getElementById('launch-project').value;
  const payload = {
    project_id: projId || null,
    title: title,
    url: url,
    description: desc,
    target_user: document.getElementById('launch-user').value.trim(),
    cta: document.getElementById('launch-cta').value.trim(),
    target_region: (document.getElementById('launch-region') || {}).value || 'global',
  };

  apiFetch('/api/distribution/generate', {method:'POST', body: JSON.stringify(payload)})
    .then(function(data) { renderLaunchContent(data, title, url); })
    .catch(function(err) {
      errEl.textContent = err.message;
      errEl.style.display = 'block';
      toast('Generation failed: ' + err.message, 'error');
    })
    .finally(function() {
      btn.disabled = false;
      btn.innerHTML = '&#9889; Generate All Content';
    });
}

function renderLaunchContent(data, title, url) {
  var platforms = data.platforms || {};
  var selectedPlatforms = getSelectedPlatforms();
  var cards = '';

  selectedPlatforms.forEach(function(p) {
    var pdata = platforms[p] || {};
    if (!pdata || Object.keys(pdata).length === 0) return;
    cards += _renderPlatformCard(p, pdata);
  });

  if (!cards) {
    cards = '<div class="alert alert-warn">No content generated. Make sure platforms are selected and try again.</div>';
  }

  var exportAll = '<div style="display:flex;justify-content:flex-end;margin-bottom:.75rem">' +
    '<button class="export-btn" onclick="exportLaunchContent('+esc(JSON.stringify(data))+')">&#11015; Export All Content</button>' +
  '</div>';

  document.getElementById('launch-output').innerHTML = exportAll + '<div class="platform-cards">' + cards + '</div>';
  toast('Launch content generated!', 'success');
}

function _renderPlatformCard(p, pdata) {
  var icon = _platIcons[p] || '&#128462;';
  var label = _platLabels[p] || p;
  var fields = '';

  function addField(lbl, val) {
    if (!val) return;
    var text = (typeof val === 'object') ? JSON.stringify(val, null, 2) : String(val);
    fields += '<div class="platform-field">' +
      '<div class="platform-field-label">' + esc(lbl) + ' <button class="copy-btn" onclick="copyText('+JSON.stringify(text)+',\''+esc(lbl)+'\')">&#128203; copy</button></div>' +
      '<div style="white-space:pre-wrap;word-break:break-word">' + esc(text) + '</div>' +
    '</div>';
  }

  if (typeof pdata === 'string') {
    addField('Content', pdata);
  } else if (Array.isArray(pdata)) {
    pdata.forEach(function(item, i){ addField('Item '+(i+1), item); });
  } else {
    Object.keys(pdata).forEach(function(k){ addField(k.replace(/_/g,' '), pdata[k]); });
  }

  return '<div class="platform-card">' +
    '<div class="platform-header"><span>'+icon+'</span><span style="font-weight:700;font-size:.85rem;color:var(--text1)">'+esc(label)+'</span></div>' +
    '<div class="platform-body">' + (fields || '<span style="color:var(--text4)">No content</span>') + '</div>' +
  '</div>';
}

function exportLaunchContent(data) {
  var blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'launch-content-' + Date.now() + '.json';
  a.click();
  URL.revokeObjectURL(a.href);
  toast('Exported!', 'success');
}

// ─── Region / Social card / Video ─────────────────────────────────────────
const REGION_NOTES={global:null,mena:'&#128161; MENA: Instagram+Snapchat lead. WhatsApp forwards = #1 viral. Arabic content outperforms English.',africa:'&#128161; Africa: WhatsApp group forwards are massive. Facebook groups drive trust. Short videos win.',south_asia:'&#128161; South Asia: WhatsApp groups = viral channel #1. High price sensitivity \u2014 offer free/cheap tier.',southeast_asia:'&#128161; SE Asia: Facebook dominant in PH/MY/ID. TikTok exploding in TH/VN. Playful tone wins.',latam:'&#128161; LatAm: Instagram Stories & Reels dominate. Emotional storytelling beats feature lists.',europe:'&#128161; Europe: Privacy-conscious \u2014 mention data safety. LinkedIn for B2B. TikTok growing in UK/DE.',north_america:'&#128161; North America: Reddit & X for community. TikTok for consumer. LinkedIn for B2B.'};

function onRegionChange(){
  var r=(document.getElementById('launch-region')||{}).value||'global';
  var el=document.getElementById('region-insight');
  var n=REGION_NOTES[r];
  if(el){if(n){el.innerHTML=n;el.style.display='block';}else el.style.display='none';}
  var vr=document.getElementById('vid-region');
  if(vr)vr.value=r;
}

const CARD_GRADIENTS={purple:['#1a0533','#3d1470','#5b1ea8','#7c3aed'],dark:['#0a0a0a','#1a1a2e','#16213e','#0f3460'],sunset:['#1a0520','#6b1a1a','#c0392b','#e67e22'],ocean:['#0a1628','#1a3a5c','#0e7490','#22d3ee'],black:['#000','#111','#111','#000']};

function drawDodoOnCanvas(ctx,x,y,sz){
  var s=sz/100;ctx.save();ctx.translate(x,y);ctx.scale(s,s);
  ctx.beginPath();ctx.ellipse(50,62,28,26,0,0,Math.PI*2);ctx.fillStyle='#6B4DFF';ctx.fill();
  ctx.beginPath();ctx.ellipse(50,67,16,18,0,0,Math.PI*2);ctx.fillStyle='#e8e8ff';ctx.fill();
  ctx.beginPath();ctx.arc(50,36,18,0,Math.PI*2);ctx.fillStyle='#6B4DFF';ctx.fill();
  ctx.beginPath();ctx.arc(43,32,7,0,Math.PI*2);ctx.fillStyle='white';ctx.fill();
  ctx.beginPath();ctx.arc(57,32,7,0,Math.PI*2);ctx.fillStyle='white';ctx.fill();
  ctx.beginPath();ctx.arc(44,33,3.5,0,Math.PI*2);ctx.fillStyle='#1a1a2e';ctx.fill();
  ctx.beginPath();ctx.arc(58,33,3.5,0,Math.PI*2);ctx.fillStyle='#1a1a2e';ctx.fill();
  ctx.beginPath();ctx.moveTo(47,40);ctx.lineTo(53,40);ctx.lineTo(50,46);ctx.closePath();ctx.fillStyle='#f59e0b';ctx.fill();
  ctx.restore();
}

var _cHue=0,_cAF=null;
function updateCardPreview(){
  var cv=document.getElementById('social-card-canvas');if(!cv)return;
  var ctx=cv.getContext('2d');
  var st=(document.getElementById('card-style')||{value:'purple'}).value||'purple';
  var sk=(document.getElementById('card-size')||{value:'square'}).value||'square';
  var pn=(document.getElementById('card-name')||{value:''}).value||'Your Product';
  var tg=(document.getElementById('card-tagline')||{value:''}).value||'Your tagline here';
  var ut=(document.getElementById('card-url')||{value:''}).value||'yourproduct.com';
  var ac=(document.getElementById('card-accent')||{value:'#5b6ef7'}).value||'#5b6ef7';
  var wh={square:[300,300],landscape:[300,158],story:[169,300]}[sk]||[300,300];
  var w=wh[0],h=wh[1];cv.width=w;cv.height=h;
  if(_cAF){cancelAnimationFrame(_cAF);_cAF=null;}
  function df(){
    _cHue=(_cHue+0.6)%360;
    ctx.save();ctx.filter='hue-rotate('+_cHue+'deg)';
    var g=CARD_GRADIENTS[st]||CARD_GRADIENTS.purple;
    var grd=ctx.createLinearGradient(0,0,w,h);
    grd.addColorStop(0,g[0]);grd.addColorStop(0.35,g[1]);grd.addColorStop(0.7,g[2]);grd.addColorStop(1,g[3]);
    ctx.fillStyle=grd;ctx.fillRect(0,0,w,h);ctx.filter='none';ctx.restore();
    drawDodoOnCanvas(ctx,w-42,h-52,40);
    ctx.textAlign='center';ctx.shadowColor='rgba(0,0,0,0.5)';ctx.fillStyle='#fff';
    ctx.font='bold '+Math.round(w*0.09)+'px system-ui,sans-serif';ctx.shadowBlur=8;ctx.fillText(pn,w/2,h*0.38);
    ctx.font=Math.round(w*0.052)+'px system-ui,sans-serif';ctx.fillStyle='rgba(255,255,255,0.85)';ctx.shadowBlur=4;
    var wd=tg.split(' '),ln='',lns=[],mW=w*0.82;
    wd.forEach(function(d){var t=ln+(ln?' ':'')+d;if(ctx.measureText(t).width>mW&&ln){lns.push(ln);ln=d;}else ln=t;});
    if(ln)lns.push(ln);
    var lh=Math.round(w*0.065),sy=h*0.52;
    lns.forEach(function(l,i){ctx.fillText(l,w/2,sy+i*lh);});
    ctx.font=Math.round(w*0.042)+'px system-ui,sans-serif';ctx.fillStyle=ac;ctx.shadowBlur=0;ctx.fillText(ut,w/2,h*0.85);
    var gl=Math.abs(Math.sin(_cHue*Math.PI/180))*5+2;ctx.strokeStyle=ac;ctx.lineWidth=gl;ctx.strokeRect(1,1,w-2,h-2);
    _cAF=requestAnimationFrame(df);
  }
  df();
}

function downloadSocialCard(){
  var sk=(document.getElementById('card-size')||{value:'square'}).value||'square';
  var fd={square:[1080,1080],landscape:[1200,630],story:[1080,1920]}[sk]||[1080,1080];
  var fw=fd[0],fh=fd[1];
  var off=document.createElement('canvas');off.width=fw;off.height=fh;
  var ctx=off.getContext('2d');
  var st=(document.getElementById('card-style')||{value:'purple'}).value||'purple';
  var pn=(document.getElementById('card-name')||{value:''}).value||'Your Product';
  var tg=(document.getElementById('card-tagline')||{value:''}).value||'tagline';
  var ut=(document.getElementById('card-url')||{value:''}).value||'yourproduct.com';
  var ac=(document.getElementById('card-accent')||{value:'#5b6ef7'}).value||'#5b6ef7';
  var g=CARD_GRADIENTS[st]||CARD_GRADIENTS.purple;
  var grd=ctx.createLinearGradient(0,0,fw,fh);
  grd.addColorStop(0,g[0]);grd.addColorStop(0.35,g[1]);grd.addColorStop(0.7,g[2]);grd.addColorStop(1,g[3]);
  ctx.fillStyle=grd;ctx.fillRect(0,0,fw,fh);
  drawDodoOnCanvas(ctx,fw-110,fh-140,100);
  ctx.textAlign='center';ctx.shadowColor='rgba(0,0,0,0.5)';ctx.fillStyle='#fff';
  ctx.font='bold '+Math.round(fw*0.09)+'px system-ui,sans-serif';ctx.shadowBlur=15;ctx.fillText(pn,fw/2,fh*0.38);
  ctx.font=Math.round(fw*0.052)+'px system-ui,sans-serif';ctx.fillStyle='rgba(255,255,255,0.85)';ctx.shadowBlur=8;
  var wd=tg.split(' '),ln='',lns=[],mW=fw*0.82;
  wd.forEach(function(d){var t=ln+(ln?' ':'')+d;if(ctx.measureText(t).width>mW&&ln){lns.push(ln);ln=d;}else ln=t;});
  if(ln)lns.push(ln);
  var lh=Math.round(fw*0.065),sy=fh*0.52;
  lns.forEach(function(l,i){ctx.fillText(l,fw/2,sy+i*lh);});
  ctx.font=Math.round(fw*0.042)+'px system-ui,sans-serif';ctx.fillStyle=ac;ctx.shadowBlur=0;ctx.fillText(ut,fw/2,fh*0.85);
  ctx.strokeStyle=ac;ctx.lineWidth=6;ctx.strokeRect(3,3,fw-6,fh-6);
  off.toBlob(function(b){
    var a=document.createElement('a');a.href=URL.createObjectURL(b);
    a.download=(pn.replace(/\\s+/g,'-').toLowerCase()||'card')+'-'+sk+'.png';
    a.click();URL.revokeObjectURL(a.href);toast('Social card downloaded!','success');
  },'image/png');
}

function triggerVideoGeneration(){
  var p=(document.getElementById('vid-product')||{}).value||'';
  var tg=(document.getElementById('vid-tagline')||{}).value||'';
  var u=(document.getElementById('vid-url')||{}).value||'';
  var r=(document.getElementById('vid-region')||{}).value||'global';
  var ai=(document.getElementById('vid-ai-concept')||{}).checked||false;
  if(!p.trim()){toast('Enter a product name first','warn');return;}
  var btn=document.getElementById('vid-btn'),res=document.getElementById('vid-result');
  btn.disabled=true;btn.innerHTML='<span class="spinner"></span> Triggering...';res.innerHTML='';
  apiFetch('/api/distribution/generate-video',{method:'POST',body:JSON.stringify({
    title:p.trim(),description:tg||p.trim(),url:u||'https://example.com',target_region:r,use_ai_concept:ai
  })}).then(function(d){
    var h='<div class="alert alert-success">&#10003; Video job started!</div>';
    if(d.workflow_url)h+='<div style="margin-top:.4rem">&#128279; <a href="'+esc(d.workflow_url)+'" target="_blank">Track on GitHub Actions</a></div>';
    if(d.note)h+='<div style="color:var(--text3);font-size:.76rem;margin-top:.3rem">&#9432; '+esc(d.note)+'</div>';
    res.innerHTML=h;toast('Video triggered!','success');
  }).catch(function(e){
    res.innerHTML='<div class="alert alert-error">'+esc(e.message)+'</div>';
    toast('Video failed: '+e.message,'error');
  }).finally(function(){btn.disabled=false;btn.innerHTML='&#127916; Generate Free Promo Video';});
}

// ─── Revenue ──────────────────────────────────────────────────────────────
function addRevenue() {
  // Stored locally — will be lost if browser storage is cleared
  var proj = document.getElementById('rev-project').value.trim();
  var amount = parseFloat(document.getElementById('rev-amount').value) || 0;
  var source = document.getElementById('rev-source').value;
  var note = document.getElementById('rev-note').value.trim();
  if (!proj) { toast('Enter a project name', 'warn'); return; }
  if (!amount || amount <= 0) { toast('Enter a valid amount > 0', 'warn'); return; }

  var entries = JSON.parse(localStorage.getItem('revenue_entries') || '[]');
  entries.push({project:proj, amount:amount, source:source, note:note, date:new Date().toISOString().split('T')[0]});
  localStorage.setItem('revenue_entries', JSON.stringify(entries));
  document.getElementById('rev-project').value = '';
  document.getElementById('rev-amount').value = '';
  document.getElementById('rev-note').value = '';
  renderRevTable();
  toast('Revenue logged: $' + amount.toFixed(2), 'success');
}

function renderRevTable() {
  var entries = JSON.parse(localStorage.getItem('revenue_entries') || '[]');
  if (!entries.length) {
    document.getElementById('rev-table-wrap').innerHTML = '<div style="color:var(--text4);font-size:.82rem;text-align:center;padding:1.5rem">No revenue logged yet</div>';
    document.getElementById('pipeline-score-wrap').innerHTML = '<div style="color:var(--text3);font-size:.82rem">Score will appear after logging revenue</div>';
    return;
  }
  var totals = {};
  entries.forEach(function(e){ totals[e.project] = (totals[e.project]||0) + e.amount; });
  var maxRev = Math.max.apply(null, Object.values(totals));
  var html = '<table class="rev-table"><thead><tr><th>Project</th><th>Revenue</th><th>Score</th></tr></thead><tbody>';
  Object.entries(totals).sort(function(a,b){return b[1]-a[1];}).forEach(function(kv){
    var pct = maxRev > 0 ? (kv[1]/maxRev)*100 : 0;
    html += '<tr><td>'+esc(kv[0])+'</td><td>$'+kv[1].toFixed(2)+'</td>' +
      '<td><div class="pipeline-bar"><div class="pipeline-fill" style="width:'+pct+'%"></div></div></td></tr>';
  });
  html += '</tbody></table>';
  document.getElementById('rev-table-wrap').innerHTML = html;
  var total = entries.reduce(function(s,e){return s+e.amount;},0);
  var score = Math.min(100, Math.round((total / 1000) * 100));
  document.getElementById('pipeline-score-wrap').innerHTML =
    '<div style="font-size:1.6rem;font-weight:800;color:var(--accent);margin-bottom:.3rem">$'+total.toFixed(2)+'</div>' +
    '<div style="font-size:.75rem;color:var(--text3);margin-bottom:.5rem">Total revenue logged</div>' +
    '<div class="pipeline-bar"><div class="pipeline-fill" style="width:'+score+'%"></div></div>' +
    '<div style="font-size:.72rem;color:var(--text3);margin-top:.3rem">'+score+'% to $1,000 milestone</div>';
  var pl = localStorage.getItem('payment_link');
  if (pl) document.getElementById('payment-link-display').innerHTML = '&#128279; <a href="'+esc(pl)+'" target="_blank">'+esc(pl)+'</a>';
}

function exportRevenue() {
  var entries = JSON.parse(localStorage.getItem('revenue_entries') || '[]');
  if (!entries.length) { toast('No revenue data to export', 'warn'); return; }
  var csv = 'Date,Project,Amount,Source,Note\\n' + entries.map(function(e){
    return [e.date,e.project,e.amount,e.source,e.note].map(function(v){return '"'+String(v||'').replace(/"/g,'""')+'"';}).join(',');
  }).join('\\n');
  var blob = new Blob([csv], {type:'text/csv'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'revenue-' + new Date().toISOString().split('T')[0] + '.csv';
  a.click();
  URL.revokeObjectURL(a.href);
  toast('Revenue exported!', 'success');
}

function savePaymentLink() {
  var url = document.getElementById('payment-url').value.trim();
  if (!url) return;
  if (!url.startsWith('http')) { toast('Enter a valid URL starting with http', 'warn'); return; }
  localStorage.setItem('payment_link', url);
  document.getElementById('payment-link-display').innerHTML = '&#128279; <a href="'+esc(url)+'" target="_blank">'+esc(url)+'</a>';
  toast('Payment link saved!', 'success');
}

function saveLearningLog() {
  var val = document.getElementById('learning-log').value;
  localStorage.setItem('learning_log', val);
  toast('Learning saved!', 'success');
}

// ─── Init ─────────────────────────────────────────────────────────────────
// ─── Marketing Hub ─────────────────────────────────────────────────────────
var _mktRegionData = {
  global:       {top:['instagram','tiktok','youtube','twitter','reddit'], note:'All platforms relevant. Prioritise Instagram + TikTok for visual products, Reddit for tech.'},
  mena:         {top:['instagram','whatsapp','tiktok','snapchat','youtube'], note:'WhatsApp groups are extremely powerful for viral spread in MENA. Snapchat dominant in Saudi/UAE for under-30s.'},
  africa:       {top:['whatsapp','facebook','tiktok','instagram','youtube'], note:'WhatsApp is the #1 channel in Sub-Saharan Africa. Facebook groups still massive for community reach.'},
  south_asia:   {top:['whatsapp','instagram','youtube','facebook','snapchat'], note:'WhatsApp dominates India, Pakistan, Bangladesh. YouTube is the #1 video platform. Instagram growing fast.'},
  southeast_asia:{top:['tiktok','facebook','instagram','youtube','twitter'], note:'TikTok is dominant in SEA. Facebook still very strong in Philippines, Indonesia, Vietnam.'},
  latam:        {top:['instagram','tiktok','whatsapp','facebook','youtube'], note:'Instagram + WhatsApp are the power combo in Brazil, Mexico, Colombia. TikTok growing very fast.'},
  europe:       {top:['instagram','linkedin','twitter','reddit','tiktok'], note:'LinkedIn matters more for B2B. Instagram strong for consumer. TikTok growing rapidly with under-35s.'},
  north_america:{top:['tiktok','instagram','twitter','reddit','linkedin'], note:'TikTok dominates for viral reach. Reddit strong for tech/niche. Twitter/X for building in public.'},
};

function updateMktPlatforms() {
  var region = (document.getElementById('mkt-region') || {}).value || 'global';
  var data = _mktRegionData[region] || _mktRegionData.global;
  var insight = document.getElementById('mkt-region-insight');
  if (insight) {
    insight.style.display = 'block';
    insight.innerHTML = '<strong>Best platforms for this region:</strong> ' +
      data.top.map(function(p){ return (_platLabels[p]||p); }).join(', ') +
      '<br><span style="color:var(--text2)">' + data.note + '</span>';
  }
  var guide = document.getElementById('mkt-platform-guide');
  if (guide) {
    guide.innerHTML = '<div style="margin-bottom:.5rem"><strong style="color:var(--text1)">Top 5 platforms:</strong></div>' +
      data.top.map(function(p, i){
        return '<div style="display:flex;align-items:center;gap:.5rem;padding:.3rem 0;border-bottom:1px solid var(--border1)">' +
          '<span style="color:var(--text3);font-size:.72rem;width:16px">' + (i+1) + '.</span>' +
          '<span>' + (_platIcons[p]||'') + '</span>' +
          '<span style="flex:1">' + (_platLabels[p]||p) + '</span>' +
        '</div>';
      }).join('') +
      '<div style="font-size:.78rem;color:var(--text3);margin-top:.5rem;line-height:1.55">' + data.note + '</div>';
  }
}

function clearMktForm() {
  ['mkt-product','mkt-hook','mkt-audience'].forEach(function(id){
    var el = document.getElementById(id);
    if (el) el.value = '';
  });
  document.getElementById('mkt-output').innerHTML =
    '<div class="card" style="text-align:center;color:var(--text4);padding:3rem 1rem"><div style="font-size:2.5rem;margin-bottom:.75rem">&#127756;</div><div>Fill in your product details and hit Generate Campaign</div></div>';
  document.getElementById('mkt-error').style.display = 'none';
}

function generateCampaign() {
  var product = (document.getElementById('mkt-product') || {}).value || '';
  var hook = (document.getElementById('mkt-hook') || {}).value || '';
  var audience = (document.getElementById('mkt-audience') || {}).value || '';
  var region = (document.getElementById('mkt-region') || {}).value || 'global';
  var goal = (document.getElementById('mkt-goal') || {}).value || 'awareness';
  var budget = (document.getElementById('mkt-budget') || {}).value || 'zero';
  
  if (!product.trim()) { toast('Enter your product name', 'warn'); return; }
  if (!hook.trim()) { toast('Enter your product hook/value proposition', 'warn'); return; }

  var btn = document.getElementById('mkt-gen-btn');
  var errEl = document.getElementById('mkt-error');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Writing campaigns...';
  errEl.style.display = 'none';

  var regionData = _mktRegionData[region] || _mktRegionData.global;
  var platforms = regionData.top.slice(0,4).map(function(p){ return _platLabels[p]||p; }).join(', ');

  var prompt = 'You are a viral marketing expert. Write a complete marketing campaign for: ' +
    product + '. Hook: ' + hook + '. Target audience: ' + audience + '. ' +
    'Region: ' + region + ' (best platforms: ' + platforms + '). ' +
    'Campaign goal: ' + goal + '. Budget: ' + budget + '. ' +
    'For each of the top 4 platforms ('+platforms+'), write: ' +
    '1) A specific post/caption (ready to copy-paste), ' +
    '2) Best time to post, ' +
    '3) One unconventional growth hack for that platform. ' +
    'Be creative, specific, and conversion-focused. No generic advice.';

  apiFetch('/chat/talk', {method:'POST', body: JSON.stringify({message: prompt, history: []})})
    .then(function(data) {
      var reply = data.reply || data.message || '';
      renderCampaignOutput(reply, product, regionData.top.slice(0,4));
    })
    .catch(function(err) {
      errEl.textContent = err.message;
      errEl.style.display = 'block';
      toast('Campaign generation failed: ' + err.message, 'error');
    })
    .finally(function() {
      btn.disabled = false;
      btn.innerHTML = '&#10024; Generate Campaign';
    });
}

function renderCampaignOutput(text, product, platforms) {
  var html = '<div class="card">' +
    '<div class="card-title" style="display:flex;justify-content:space-between;align-items:center">' +
      '<span>&#127881; ' + esc(product) + ' — Campaign</span>' +
      '<button class="export-btn" onclick="copyText('+JSON.stringify(text)+', 'campaign content')">&#128203; Copy All</button>' +
    '</div>' +
    '<div style="white-space:pre-wrap;font-size:.83rem;color:var(--text1);line-height:1.7">' + esc(text) + '</div>' +
    '<div class="section-sep"></div>' +
    '<div style="display:flex;gap:.5rem;flex-wrap:wrap">' +
      '<button class="btn btn-secondary" style="font-size:.72rem" onclick="copyText('+JSON.stringify(text)+','campaign content')">&#128203; Copy All</button>' +
      '<button class="btn btn-secondary" style="font-size:.72rem" onclick="generateCampaign()">&#8635; Regenerate</button>' +
      '<button class="btn btn-primary" style="font-size:.72rem" onclick="showTab('launch')">&#128640; Build Launch Kit</button>' +
    '</div>' +
  '</div>';
  document.getElementById('mkt-output').innerHTML = html;
  toast('Campaign generated! Copy and post.', 'success');
}

// ─── Projects Pipeline ─────────────────────────────────────────────────────
function loadProjectsPipeline() {
  apiFetch('/portfolio/projects')
    .then(function(projects) {
      var list = Array.isArray(projects) ? projects : [];
      if (!list.length) {
        document.getElementById('projects-pipeline').innerHTML =
          '<div style="color:var(--text4);text-align:center;padding:1.2rem;font-size:.82rem">No projects in pipeline yet. Score an idea to add one.</div>';
        return;
      }
      var html = '';
      list.forEach(function(p) {
        var state = p.state || 'idea';
        var icon = {idea:'&#128161;',approved:'&#9989;',building:'&#127981;',deployed:'&#127640;',scaling:'&#128640;'}[state] || '&#128462;';
        var badgeCls = {idea:'badge-muted',approved:'badge-success',building:'badge-info',deployed:'badge-success',scaling:'badge-warn'}[state] || 'badge-muted';
        html += '<div class="project-pipeline-row">' +
          '<span style="font-size:1.1rem">' + icon + '</span>' +
          '<span style="flex:1;font-weight:600">' + esc(p.name||p.title||'Untitled') + '</span>' +
          '<span class="badge ' + badgeCls + '">' + esc(state) + '</span>' +
          (p.score ? '<span style="color:var(--text3);font-size:.75rem">' + p.score + '/10</span>' : '') +
          '<button class="btn btn-secondary" style="font-size:.7rem;padding:.2rem .5rem" onclick="prefillLaunch('+JSON.stringify(p.name||p.title||'')+','+JSON.stringify(p.description||'')+',\'\')">&#128640;</button>' +
        '</div>';
      });
      document.getElementById('projects-pipeline').innerHTML = html;
    })
    .catch(function() {
      document.getElementById('projects-pipeline').innerHTML =
        '<div class="alert alert-error">Failed to load projects pipeline</div>';
    });
}

// ─── Cross-tab helpers ─────────────────────────────────────────────────────
function prefillLaunch(title, desc, user) {
  showTab('launch');
  setTimeout(function() {
    var el = document.getElementById('launch-title');
    if (el && title) el.value = title;
    el = document.getElementById('launch-desc');
    if (el && desc) el.value = desc;
    el = document.getElementById('launch-user');
    if (el && user) el.value = user;
  }, 100);
}

function prefillMarketing(product, hook) {
  showTab('marketing');
  setTimeout(function() {
    var el = document.getElementById('mkt-product');
    if (el && product) el.value = product;
    el = document.getElementById('mkt-hook');
    if (el && hook) el.value = hook;
    updateMktPlatforms();
  }, 100);
}

function prefillAnalyze(idea, problem, user) {
  showTab('analyze');
  setTimeout(function() {
    var el = document.getElementById('idea-desc');
    if (el && idea) el.value = idea;
    el = document.getElementById('idea-problem');
    if (el && problem) el.value = problem;
    el = document.getElementById('idea-user');
    if (el && user) el.value = user;
  }, 100);
}

(function init(){
  // Load learning log
  var ll = localStorage.getItem('learning_log');
  if (ll) document.getElementById('learning-log').value = ll;
  var pl = localStorage.getItem('payment_link');
  if (pl) document.getElementById('payment-url').value = pl;

  // Init platform checkboxes
  renderPlatformCheckboxes();
  renderChecklist();

  // Auto-init card preview after slight delay
  setTimeout(function(){ if(document.getElementById('social-card-canvas')) updateCardPreview(); }, 600);

  // Check health on load
  apiFetch('/api/dashboard/health').then(function(h){
    var el = document.getElementById('topbar-health');
    el.textContent = '&#9679; ' + (h.health_status||'OK');
    el.style.color = h.health_status === 'GREEN' ? 'var(--success)' : h.health_status === 'AMBER' ? 'var(--warn)' : 'var(--error)';
  }).catch(function(){
    document.getElementById('topbar-health').textContent = '&#9679; offline';
  });
})();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    html = _ROOT_HTML.replace("{version}", _VERSION)
    return HTMLResponse(content=html)
