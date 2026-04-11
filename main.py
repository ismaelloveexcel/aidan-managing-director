"""
main.py – FastAPI application entry point for AI-DAN Managing Director.

Registers all route modules, serves the root UI, and configures the application.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

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
    portfolio,
    projects,
    revenue,
)

_VERSION = "0.3.0"


@asynccontextmanager
async def _lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: clean up cached HTTP clients on shutdown."""
    yield
    # Shutdown: close cached AI provider clients to avoid leaking sockets.
    from app.core.dependencies import get_ai_provider

    try:
        get_ai_provider().close()
        get_ai_provider.cache_clear()
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
# Middleware registration (outermost = last to run on request / first on response)
# ---------------------------------------------------------------------------
_settings = get_settings()
app.add_middleware(APIKeyMiddleware, api_key=_settings.api_key)
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)

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
app.include_router(revenue.router, prefix="/revenue", tags=["Revenue Intelligence"])
app.include_router(control.router, prefix="/control", tags=["Control"])
app.include_router(distribution.router, prefix="/api/distribution", tags=["Distribution"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Return a simple health-check response."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Root UI – 6-tab command center dashboard for solo non-technical operator
# ---------------------------------------------------------------------------
_ROOT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>AI-DAN | Venture Command Center</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0a0a0a;--card:#111;--border:#222;--border2:#1e1e1e;
  --accent:#5b6ef7;--accent-dark:#4a5ce6;
  --green:#16a34a;--green-t:#4ade80;
  --amber:#d97706;--amber-t:#fbbf24;
  --red:#dc2626;--red-t:#fca5a5;
  --blue-t:#60a5fa;--purple-t:#c4b5fd;
  --text:#e0e0e0;--text2:#aaa;--text3:#888;--text4:#555;
  --ai-bubble:#1a1a2e;--user-bubble:#1e1e2e;
}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  background:var(--bg);color:var(--text);min-height:100vh;display:flex;flex-direction:column}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}

/* ── HEADER ── */
header{background:var(--card);border-bottom:1px solid var(--border);
  padding:.75rem 1.5rem;display:flex;align-items:center;justify-content:space-between;
  position:sticky;top:0;z-index:200;gap:1rem;flex-wrap:wrap}
.header-left{display:flex;align-items:center;gap:.75rem}
.header-logo{font-size:1.15rem;font-weight:800;color:#fff;letter-spacing:-.02em}
.header-logo span{color:var(--accent)}
.header-ver{font-size:.72rem;color:var(--text4);background:#1a1a1a;
  padding:.15rem .4rem;border-radius:4px;border:1px solid var(--border)}
.header-right{display:flex;align-items:center;gap:.6rem}
.api-key-wrap{display:flex;align-items:center;gap:.4rem}
.api-key-wrap label{font-size:.75rem;color:var(--text3);white-space:nowrap}
.api-key-wrap input{width:180px;padding:.3rem .5rem;border-radius:5px;
  border:1px solid var(--border);background:#0d0d0d;color:var(--text);font-size:.75rem}

/* ── AI BANNER ── */
#ai-banner{display:none;background:#1c1700;border-bottom:1px solid var(--amber);
  padding:.5rem 1.5rem;font-size:.82rem;color:var(--amber-t);text-align:center}

/* ── TABS NAV ── */
.nav{display:flex;gap:.15rem;background:var(--card);padding:.4rem 1.5rem;
  border-bottom:1px solid var(--border2);overflow-x:auto;flex-shrink:0;scrollbar-width:none}
.nav::-webkit-scrollbar{display:none}
.nav button{background:none;border:none;color:var(--text3);padding:.45rem .85rem;
  border-radius:6px;cursor:pointer;font-size:.83rem;font-weight:500;
  white-space:nowrap;transition:all .15s;border-bottom:2px solid transparent}
.nav button:hover{color:var(--text);background:#1a1a1a}
.nav button.active{color:#fff;background:#1a1a2e;border-bottom-color:var(--accent)}

/* ── TAB PANELS ── */
.tab{display:none;flex:1;padding:1.5rem;max-width:1100px;margin:0 auto;width:100%}
.tab.active{display:flex;flex-direction:column}
@media(max-width:700px){.tab{padding:1rem}}

/* ── CARDS ── */
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;
  padding:1.2rem;margin-bottom:1.2rem}
.card-title{font-size:.95rem;font-weight:700;color:#fff;margin-bottom:1rem;
  display:flex;align-items:center;gap:.4rem}
.card-title small{font-size:.75rem;font-weight:400;color:var(--text3);margin-left:auto}

/* ── FORMS ── */
label{display:block;font-size:.8rem;color:var(--text2);margin-bottom:.3rem;margin-top:.85rem}
label:first-child{margin-top:0}
textarea,input[type=text],input[type=number],input[type=date],input[type=url],select{
  width:100%;padding:.55rem .75rem;border-radius:7px;border:1px solid #333;
  background:#0d0d0d;color:var(--text);font-size:.875rem;font-family:inherit;
  transition:border-color .15s}
textarea{resize:vertical;min-height:90px}
textarea:focus,input:focus,select:focus{outline:none;border-color:var(--accent)}
select option{background:#111}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:.8rem}
.row3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:.8rem}
@media(max-width:600px){.row2,.row3{grid-template-columns:1fr}}

/* ── BUTTONS ── */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:.4rem;
  padding:.65rem 1.1rem;border:none;border-radius:7px;font-size:.875rem;
  font-weight:600;cursor:pointer;transition:all .18s;white-space:nowrap}
.btn:disabled{opacity:.45;cursor:not-allowed}
.btn-sm{padding:.3rem .65rem;font-size:.78rem;font-weight:500;border-radius:5px}
.btn-xs{padding:.2rem .45rem;font-size:.72rem;font-weight:500;border-radius:4px}
.btn-full{width:100%}
.btn-primary{background:var(--accent);color:#fff}
.btn-primary:hover:not(:disabled){background:var(--accent-dark)}
.btn-success{background:var(--green);color:#fff}
.btn-success:hover:not(:disabled){background:#15803d}
.btn-danger{background:var(--red);color:#fff}
.btn-danger:hover:not(:disabled){background:#b91c1c}
.btn-secondary{background:#1e1e1e;color:var(--text2);border:1px solid #333}
.btn-secondary:hover:not(:disabled){background:#2a2a2a;color:var(--text)}
.btn-amber{background:var(--amber);color:#fff}
.btn-amber:hover:not(:disabled){background:#b45309}
.btn-ghost{background:none;border:1px solid var(--border);color:var(--text3)}
.btn-ghost:hover:not(:disabled){background:#1a1a1a;color:var(--text)}

/* ── BADGES ── */
.badge{display:inline-block;padding:.15rem .45rem;border-radius:4px;
  font-size:.7rem;font-weight:700;letter-spacing:.02em}
.badge-idea{background:#292524;color:#d6d3d1}
.badge-approved{background:#14532d;color:var(--green-t)}
.badge-building{background:#1e3a5f;color:var(--blue-t)}
.badge-launched{background:#4a1d96;color:var(--purple-t)}
.badge-hold{background:#451a03;color:var(--amber-t)}
.badge-rejected,.badge-killed{background:#450a0a;color:var(--red-t)}
.badge-succeeded,.badge-success{background:#14532d;color:var(--green-t)}
.badge-failed,.badge-error{background:#450a0a;color:var(--red-t)}
.badge-pending{background:#292524;color:#d6d3d1}
.badge-running{background:#1e3a5f;color:var(--blue-t);animation:pulse 1.5s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.6}}

/* ── STATS ── */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:.75rem;margin-bottom:1.2rem}
.stat-box{background:var(--card);border:1px solid var(--border);border-radius:8px;
  padding:1rem;text-align:center;cursor:pointer;transition:border-color .15s}
.stat-box:hover{border-color:var(--accent)}
.stat-num{font-size:1.8rem;font-weight:800;color:var(--accent)}
.stat-num.green{color:var(--green-t)}
.stat-num.amber{color:var(--amber-t)}
.stat-label{font-size:.72rem;color:var(--text3);margin-top:.2rem;text-transform:uppercase;letter-spacing:.05em}

/* ── VENTURE LOOP ── */
.loop-flow{display:flex;align-items:center;gap:.4rem;overflow-x:auto;
  padding:1rem;background:#0d0d0d;border-radius:8px;margin-bottom:1rem;scrollbar-width:none}
.loop-flow::-webkit-scrollbar{display:none}
.loop-step{display:flex;flex-direction:column;align-items:center;gap:.3rem;
  min-width:80px;cursor:pointer;padding:.4rem;border-radius:6px;transition:background .15s}
.loop-step:hover{background:#1a1a1a}
.loop-step-icon{font-size:1.3rem}
.loop-step-label{font-size:.68rem;color:var(--text3);font-weight:600;text-align:center;text-transform:uppercase;letter-spacing:.04em}
.loop-step-count{font-size:1.1rem;font-weight:800;color:var(--text)}
.loop-arrow{color:var(--text4);font-size:1.1rem;flex-shrink:0}

/* ── TABLES ── */
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:.82rem}
th{text-align:left;padding:.5rem .7rem;border-bottom:1px solid var(--border);
  color:var(--text3);font-weight:600;font-size:.73rem;text-transform:uppercase;letter-spacing:.05em}
td{padding:.55rem .7rem;border-bottom:1px solid var(--border2);vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover td{background:#0f0f0f}

/* ── ALERTS ── */
.alert{border-radius:8px;padding:.85rem 1rem;margin:.5rem 0;font-size:.85rem}
.alert-error{background:#2d1111;border:1px solid var(--red);color:var(--red-t)}
.alert-warn{background:#1c1700;border:1px solid var(--amber);color:var(--amber-t)}
.alert-success{background:#0d2217;border:1px solid var(--green);color:var(--green-t)}
.alert-info{background:#0d1a3a;border:1px solid #1e3a5f;color:var(--blue-t)}

/* ── LOADING ── */
.spinner{display:inline-block;width:18px;height:18px;border:2.5px solid #333;
  border-top-color:var(--accent);border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-row{text-align:center;padding:2rem;color:var(--text3);font-size:.85rem}
.empty-state{text-align:center;padding:3rem 1rem;color:var(--text4);font-size:.88rem}
.empty-state .empty-icon{font-size:2.5rem;margin-bottom:.75rem}

/* ── SCORE BARS ── */
.score-row{margin:.4rem 0}
.score-label-row{display:flex;justify-content:space-between;font-size:.78rem;color:var(--text2);margin-bottom:.2rem}
.score-bar{height:8px;border-radius:4px;background:#1e1e1e;overflow:hidden}
.score-fill{height:100%;border-radius:4px;transition:width .6s cubic-bezier(.4,0,.2,1)}
.score-high{background:var(--green)}
.score-med{background:var(--amber)}
.score-low{background:var(--red)}

/* ── DECISION BADGE ── */
.decision-badge{display:inline-flex;align-items:center;gap:.4rem;padding:.4rem 1rem;
  border-radius:8px;font-weight:800;font-size:1rem;margin:.5rem 0}
.decision-APPROVED{background:var(--green);color:#fff}
.decision-HOLD{background:var(--amber);color:#fff}
.decision-REJECTED{background:var(--red);color:#fff}

/* ── CHAT ── */
#tab-chat{padding:0;display:none;flex-direction:column;height:calc(100vh - 100px)}
#tab-chat.active{display:flex}
.chat-layout{display:flex;flex:1;overflow:hidden;gap:0}
.chat-main{display:flex;flex-direction:column;flex:1;min-width:0}
.chat-history{flex:1;overflow-y:auto;padding:1.2rem;display:flex;flex-direction:column;gap:.75rem;scrollbar-width:thin;scrollbar-color:#333 transparent}
.chat-history::-webkit-scrollbar{width:5px}
.chat-history::-webkit-scrollbar-track{background:transparent}
.chat-history::-webkit-scrollbar-thumb{background:#333;border-radius:3px}
.chat-msg{display:flex;gap:.6rem;max-width:85%;animation:fadeUp .25s ease}
@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.chat-msg.user{align-self:flex-end;flex-direction:row-reverse}
.chat-msg.ai{align-self:flex-start}
.chat-avatar{width:30px;height:30px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-size:.9rem;flex-shrink:0;margin-top:.1rem}
.chat-avatar.ai-av{background:#1a1a2e;border:1px solid #2a2a4e}
.chat-avatar.user-av{background:#1e1e2e;border:1px solid #2a2a3e}
.chat-bubble{padding:.65rem .9rem;border-radius:12px;font-size:.875rem;line-height:1.55;max-width:100%}
.chat-msg.ai .chat-bubble{background:var(--ai-bubble);border:1px solid #2a2a4e;
  border-radius:12px 12px 12px 4px;white-space:pre-wrap;word-break:break-word}
.chat-msg.user .chat-bubble{background:var(--user-bubble);border:1px solid #2a2a3e;
  border-radius:12px 12px 4px 12px;color:var(--text)}
.chat-meta{font-size:.68rem;color:var(--text4);margin-top:.25rem;padding:0 .2rem}
.chat-msg.user .chat-meta{text-align:right}
.typing-dots{display:inline-flex;gap:3px;align-items:center;padding:.5rem 0}
.typing-dots span{width:6px;height:6px;border-radius:50%;background:var(--text3);
  animation:dotBounce 1.2s ease-in-out infinite}
.typing-dots span:nth-child(2){animation-delay:.2s}
.typing-dots span:nth-child(3){animation-delay:.4s}
@keyframes dotBounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-5px)}}
.chat-starters{display:flex;flex-wrap:wrap;gap:.5rem;padding:.75rem 1.2rem;
  border-top:1px solid var(--border2);background:var(--card)}
.starter-chip{background:none;border:1px solid #333;color:var(--text2);padding:.35rem .75rem;
  border-radius:20px;font-size:.78rem;cursor:pointer;transition:all .15s;white-space:nowrap}
.starter-chip:hover{border-color:var(--accent);color:var(--text);background:#1a1a2e}
.chat-input-area{padding:.85rem 1.2rem;border-top:1px solid var(--border);
  background:var(--card);display:flex;gap:.5rem;align-items:flex-end}
.chat-input-area textarea{flex:1;min-height:42px;max-height:150px;resize:none;
  border-radius:8px;padding:.55rem .8rem;font-size:.875rem;line-height:1.4}
.chat-send{flex-shrink:0;height:42px;padding:0 1rem;align-self:flex-end}
.chat-sidebar{width:200px;border-left:1px solid var(--border);background:var(--card);
  padding:1rem;display:flex;flex-direction:column;gap:.5rem;flex-shrink:0}
.chat-sidebar h3{font-size:.78rem;color:var(--text3);text-transform:uppercase;
  letter-spacing:.06em;margin-bottom:.25rem}
.chat-sidebar .btn{font-size:.78rem;padding:.45rem .7rem;justify-content:flex-start}
@media(max-width:700px){.chat-sidebar{display:none}#tab-chat{height:calc(100vh - 120px)}}

/* ── LAUNCH KIT CONTENT ── */
.content-block{background:#0d0d0d;border:1px solid #2a2a2a;border-radius:8px;padding:.85rem 1rem;margin:.6rem 0}
.content-platform{font-size:.72rem;font-weight:700;color:var(--text3);margin-bottom:.4rem;
  text-transform:uppercase;letter-spacing:.06em;display:flex;justify-content:space-between;align-items:center}
.content-text{font-size:.82rem;color:var(--text2);white-space:pre-wrap;word-break:break-word;line-height:1.5}

/* ── CHECKLIST ── */
.checklist{list-style:none;padding:0}
.checklist li{display:flex;align-items:flex-start;gap:.5rem;padding:.35rem 0;
  border-bottom:1px solid var(--border2);font-size:.83rem}
.checklist li:last-child{border-bottom:none}
.checklist input[type=checkbox]{width:auto;margin-top:2px;accent-color:var(--accent)}

/* ── TOASTS ── */
#toasts{position:fixed;top:1rem;right:1rem;z-index:9999;display:flex;
  flex-direction:column;gap:.5rem;pointer-events:none}
.toast{background:#1a1a1a;border:1px solid var(--border);border-radius:8px;
  padding:.7rem 1rem;font-size:.83rem;color:var(--text);min-width:220px;max-width:320px;
  animation:toastIn .25s ease;pointer-events:all;display:flex;align-items:center;gap:.5rem}
.toast.success{border-color:var(--green);color:var(--green-t)}
.toast.error{border-color:var(--red);color:var(--red-t)}
.toast.warn{border-color:var(--amber);color:var(--amber-t)}
@keyframes toastIn{from{opacity:0;transform:translateX(20px)}to{opacity:1;transform:translateX(0)}}

/* ── MISC ── */
.section-sep{border:none;border-top:1px solid var(--border);margin:1rem 0}
.detail-grid{display:grid;grid-template-columns:auto 1fr;gap:.25rem .75rem;font-size:.83rem}
.detail-key{color:var(--text3)}
.detail-val{color:var(--text)}
.copy-btn-icon{cursor:pointer;opacity:.6;transition:opacity .15s;font-size:.85rem}
.copy-btn-icon:hover{opacity:1}
.health-row{display:flex;align-items:center;gap:.5rem;padding:.35rem 0;font-size:.83rem;border-bottom:1px solid var(--border2)}
.health-row:last-child{border-bottom:none}
.health-dot{width:9px;height:9px;border-radius:50%;flex-shrink:0}
.dot-green{background:var(--green)}
.dot-amber{background:var(--amber)}
.dot-red{background:var(--red)}
.dot-grey{background:#555}
.quick-actions{display:flex;gap:.6rem;flex-wrap:wrap;margin-bottom:1.2rem}
.quick-actions .btn{flex:1;min-width:120px}
.revenue-total{font-size:3rem;font-weight:900;color:var(--green-t);
  text-align:center;padding:1.5rem 0;letter-spacing:-.03em}
.revenue-total small{font-size:1rem;color:var(--text3);font-weight:400}
.loop-insight{background:#0d1a0d;border:1px solid #1a3a1a;border-radius:8px;
  padding:1rem;font-size:.85rem;color:var(--green-t);line-height:1.6}

/* ── ACTIVITY FEED ── */
.activity-item{display:flex;gap:.6rem;align-items:flex-start;padding:.5rem 0;
  border-bottom:1px solid var(--border2);font-size:.82rem}
.activity-item:last-child{border-bottom:none}
.activity-dot{width:7px;height:7px;border-radius:50%;background:var(--accent);margin-top:.35rem;flex-shrink:0}
.activity-text{color:var(--text2);flex:1}
.activity-time{color:var(--text4);font-size:.72rem;white-space:nowrap}

/* ── SYSTEM CHECKS ── */
.checks-grid{display:grid;grid-template-columns:1fr 1fr;gap:.5rem}
@media(max-width:600px){.checks-grid{grid-template-columns:1fr}}
.check-item{background:#0d0d0d;border:1px solid var(--border);border-radius:6px;
  padding:.6rem .8rem;display:flex;align-items:center;gap:.5rem;font-size:.82rem}
</style>
</head>
<body>

<!-- ── HEADER ── -->
<header>
  <div class="header-left">
    <div class="header-logo">AI-<span>DAN</span></div>
    <span class="header-ver">v{version}</span>
  </div>
  <div class="header-right">
    <div class="api-key-wrap">
      <label for="api-key-input">API Key</label>
      <input type="text" id="api-key-input" placeholder="sk-..." autocomplete="off"/>
    </div>
  </div>
</header>

<!-- ── AI NOT CONFIGURED BANNER ── -->
<div id="ai-banner">
  &#9888; AI not configured. Add <strong>ANTHROPIC_API_KEY</strong>, <strong>OPENAI_API_KEY</strong>, or <strong>GROQ_API_KEY</strong> to your Vercel environment variables to activate AI-DAN.
</div>

<!-- ── NAV TABS ── -->
<nav class="nav" role="tablist">
  <button class="active" onclick="showTab('chat')" id="nav-chat">&#129504; AI-DAN</button>
  <button onclick="showTab('dashboard')" id="nav-dashboard">&#128202; Dashboard</button>
  <button onclick="showTab('analyze')" id="nav-analyze">&#128161; Analyze Idea</button>
  <button onclick="showTab('factory')" id="nav-factory">&#127981; Factory</button>
  <button onclick="showTab('launch')" id="nav-launch">&#128227; Launch Kit</button>
  <button onclick="showTab('revenue')" id="nav-revenue">&#128176; Revenue Loop</button>
</nav>

<!-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     TAB 1 — AI-DAN CHAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ -->
<div class="tab active" id="tab-chat" role="tabpanel">
  <div class="chat-layout">
    <div class="chat-main">
      <div class="chat-history" id="chat-history"></div>
      <div class="chat-starters" id="chat-starters">
        <button class="starter-chip" onclick="sendStarter('Score my latest idea')">Score my latest idea</button>
        <button class="starter-chip" onclick="sendStarter('What should I build next?')">What should I build next?</button>
        <button class="starter-chip" onclick="sendStarter('Generate launch content')">Generate launch content</button>
        <button class="starter-chip" onclick="sendStarter('Show my project status')">Show my project status</button>
      </div>
      <div class="chat-input-area">
        <textarea id="chat-input" placeholder="Ask AI-DAN anything... (Ctrl+Enter to send)" rows="1"></textarea>
        <button class="btn btn-primary chat-send" id="chat-send-btn" onclick="sendChatMessage()">Send &#10148;</button>
      </div>
    </div>
    <div class="chat-sidebar">
      <h3>Quick Actions</h3>
      <button class="btn btn-ghost" onclick="showTab('analyze')">&#128161; Analyze Idea</button>
      <button class="btn btn-ghost" onclick="showTab('dashboard')">&#128202; Dashboard</button>
      <button class="btn btn-ghost" onclick="showTab('factory')">&#127981; Factory</button>
      <button class="btn btn-ghost" onclick="showTab('launch')">&#128227; Launch Kit</button>
      <hr class="section-sep"/>
      <button class="btn btn-ghost btn-sm" onclick="clearChat()">&#128465; Clear chat</button>
    </div>
  </div>
</div>

<!-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     TAB 2 — DASHBOARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ -->
<div class="tab" id="tab-dashboard" role="tabpanel">

  <!-- Quick Actions -->
  <div class="quick-actions">
    <button class="btn btn-primary" onclick="showTab('analyze')">&#10133; New Idea</button>
    <button class="btn btn-secondary" onclick="showTab('factory')">&#127981; Check Factory</button>
    <button class="btn btn-secondary" onclick="showTab('launch')">&#128227; Launch Content</button>
    <button class="btn btn-ghost btn-sm" onclick="loadDashboard()" style="margin-left:auto">&#8635; Refresh</button>
  </div>

  <!-- Venture Loop Flow -->
  <div class="card">
    <div class="card-title">&#9889; Venture Loop <small id="dash-last-refresh"></small></div>
    <div class="loop-flow" id="loop-flow">
      <div class="loop-step" onclick="showTab('analyze')" title="Total ideas analyzed">
        <div class="loop-step-icon">&#128161;</div>
        <div class="loop-step-count" id="loop-ideas">–</div>
        <div class="loop-step-label">Ideas</div>
      </div>
      <div class="loop-arrow">&#8594;</div>
      <div class="loop-step" title="Ideas scored &amp; reviewed">
        <div class="loop-step-icon">&#128203;</div>
        <div class="loop-step-count" id="loop-scored">–</div>
        <div class="loop-step-label">Scored</div>
      </div>
      <div class="loop-arrow">&#8594;</div>
      <div class="loop-step" onclick="showTab('factory')" title="Approved to build">
        <div class="loop-step-icon">&#9989;</div>
        <div class="loop-step-count" id="loop-approved">–</div>
        <div class="loop-step-label">Approved</div>
      </div>
      <div class="loop-arrow">&#8594;</div>
      <div class="loop-step" onclick="showTab('factory')" title="Currently building">
        <div class="loop-step-icon">&#9881;</div>
        <div class="loop-step-count" id="loop-building">–</div>
        <div class="loop-step-label">Building</div>
      </div>
      <div class="loop-arrow">&#8594;</div>
      <div class="loop-step" onclick="showTab('launch')" title="Launched products">
        <div class="loop-step-icon">&#128640;</div>
        <div class="loop-step-count" id="loop-launched">–</div>
        <div class="loop-step-label">Launched</div>
      </div>
      <div class="loop-arrow">&#8594;</div>
      <div class="loop-step" onclick="showTab('revenue')" title="Generating revenue">
        <div class="loop-step-icon">&#128176;</div>
        <div class="loop-step-count" id="loop-revenue-count">–</div>
        <div class="loop-step-label">Revenue</div>
      </div>
    </div>
  </div>

  <!-- Stats Row -->
  <div class="stats-grid">
    <div class="stat-box" onclick="showTab('analyze')"><div class="stat-num" id="stat-ideas">0</div><div class="stat-label">Total Ideas</div></div>
    <div class="stat-box" onclick="showTab('factory')"><div class="stat-num" id="stat-approved">0</div><div class="stat-label">Approved</div></div>
    <div class="stat-box" onclick="showTab('factory')"><div class="stat-num amber" id="stat-building">0</div><div class="stat-label">Building</div></div>
    <div class="stat-box" onclick="showTab('launch')"><div class="stat-num green" id="stat-live">0</div><div class="stat-label">Live</div></div>
    <div class="stat-box" onclick="showTab('revenue')"><div class="stat-num green" id="stat-revenue">$0</div><div class="stat-label">Revenue</div></div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">
    <!-- Active Builds -->
    <div class="card">
      <div class="card-title">&#9881; Active Builds</div>
      <div id="dash-builds"><div class="loading-row"><span class="spinner"></span></div></div>
    </div>
    <!-- Recent Activity -->
    <div class="card">
      <div class="card-title">&#9889; Recent Activity</div>
      <div id="dash-activity"><div class="loading-row"><span class="spinner"></span></div></div>
    </div>
  </div>

  <!-- System Health -->
  <div class="card">
    <div class="card-title">&#128308; System Health</div>
    <div id="dash-health"><div class="loading-row"><span class="spinner"></span></div></div>
  </div>

</div>

<!-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     TAB 3 — ANALYZE IDEA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ -->
<div class="tab" id="tab-analyze" role="tabpanel">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.2rem;align-items:start">

    <!-- Form -->
    <div class="card">
      <div class="card-title">&#128161; Score Your Idea</div>
      <div id="analyze-form-area">
        <label for="idea-desc">Idea Description <span style="color:var(--red)">*</span></label>
        <textarea id="idea-desc" rows="4" placeholder="Describe your idea in 1-3 sentences..."></textarea>

        <label for="idea-problem">Problem it solves</label>
        <textarea id="idea-problem" rows="2" placeholder="What painful problem does this fix?"></textarea>

        <label for="idea-user">Target user</label>
        <input type="text" id="idea-user" placeholder="e.g. solo founders, freelance designers"/>

        <div class="row2">
          <div>
            <label for="idea-mono">Monetization model</label>
            <select id="idea-mono">
              <option value="">Select...</option>
              <option>SaaS subscription</option>
              <option>One-time purchase</option>
              <option>Marketplace / commission</option>
              <option>Freemium + upsell</option>
              <option>Service / done-for-you</option>
              <option>Affiliate / referral</option>
              <option>Usage-based / pay-per-use</option>
              <option>Other</option>
            </select>
          </div>
          <div>
            <label for="idea-comp">Competition level</label>
            <select id="idea-comp">
              <option value="">Select...</option>
              <option>Crowded (many players)</option>
              <option>Moderate</option>
              <option>Low (few direct competitors)</option>
              <option>Blue ocean (none)</option>
            </select>
          </div>
        </div>

        <label for="idea-ttr">Time to first revenue</label>
        <select id="idea-ttr">
          <option value="">Select...</option>
          <option>Under 1 week</option>
          <option>1-2 weeks</option>
          <option>2-4 weeks</option>
          <option>1-3 months</option>
          <option>3-6 months</option>
          <option>6+ months</option>
        </select>

        <label for="idea-diff">Differentiation (optional)</label>
        <textarea id="idea-diff" rows="2" placeholder="What makes this different or better?"></textarea>

        <div style="margin-top:1rem;display:flex;gap:.6rem">
          <button class="btn btn-primary" style="flex:1" id="analyze-btn" onclick="submitAnalysis()">
            &#9889; Score This Idea
          </button>
          <button class="btn btn-ghost" onclick="clearAnalyzeForm()">Clear</button>
        </div>
        <div id="analyze-error" class="alert alert-error" style="display:none"></div>
      </div>
    </div>

    <!-- Results -->
    <div id="analyze-results-col">
      <div class="card" style="text-align:center;color:var(--text4);padding:3rem 1rem">
        <div style="font-size:2rem;margin-bottom:.75rem">&#128202;</div>
        <div>Submit an idea to see your score</div>
      </div>
    </div>
  </div>
</div>

<!-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     TAB 4 — FACTORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ -->
<div class="tab" id="tab-factory" role="tabpanel">

  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
    <h2 style="font-size:1rem;font-weight:700;color:#fff">&#127981; Build Factory</h2>
    <button class="btn btn-ghost btn-sm" onclick="loadFactory()">&#8635; Refresh</button>
  </div>

  <!-- System Checks -->
  <div class="card">
    <div class="card-title">&#9989; System Checks</div>
    <div id="factory-checks">
      <div class="loading-row"><span class="spinner"></span></div>
    </div>
  </div>

  <!-- Build Runs -->
  <div class="card">
    <div class="card-title">&#9654; Build Runs</div>
    <div id="factory-runs">
      <div class="loading-row"><span class="spinner"></span></div>
    </div>
  </div>

</div>

<!-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     TAB 5 — LAUNCH KIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ -->
<div class="tab" id="tab-launch" role="tabpanel">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.2rem;align-items:start">

    <!-- Form -->
    <div>
      <div class="card">
        <div class="card-title">&#128227; Generate Launch Content</div>

        <label for="launch-project">Project</label>
        <select id="launch-project">
          <option value="">&#8212; Select project or enter below &#8212;</option>
        </select>

        <label for="launch-title">Product title</label>
        <input type="text" id="launch-title" placeholder="e.g. Waitlist Wizard"/>

        <label for="launch-url">Product URL</label>
        <input type="url" id="launch-url" placeholder="https://yourproduct.com"/>

        <label for="launch-desc">One-sentence description</label>
        <textarea id="launch-desc" rows="2" placeholder="The fastest way for solo founders to..."></textarea>

        <label for="launch-user">Target user</label>
        <input type="text" id="launch-user" placeholder="e.g. solo SaaS founders"/>

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
      </div>

      <!-- Payment Link Generator -->
      <div class="card">
        <div class="card-title">&#128179; Payment Link</div>
        <div class="alert alert-info" style="margin-bottom:.8rem;font-size:.8rem">
          &#128161; <strong>Recommended:</strong> Set up <a href="https://lemonsqueezy.com" target="_blank">LemonSqueezy</a> — free, global, no business registration needed.
        </div>
        <label for="payment-url">Your LemonSqueezy checkout URL</label>
        <div style="display:flex;gap:.5rem">
          <input type="url" id="payment-url" placeholder="https://yourstore.lemonsqueezy.com/checkout/..."/>
          <button class="btn btn-secondary" onclick="savePaymentLink()">Save</button>
        </div>
        <div id="saved-payment-link" style="margin-top:.6rem;font-size:.8rem;color:var(--text3)"></div>
      </div>
    </div>

    <!-- Output -->
    <div id="launch-output">
      <div class="card" style="text-align:center;color:var(--text4);padding:3rem 1rem">
        <div style="font-size:2rem;margin-bottom:.75rem">&#128227;</div>
        <div>Fill in your product details and hit Generate</div>
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
          <label style="display:flex;align-items:center;gap:.5rem;cursor:pointer;font-weight:normal;font-size:.85rem">
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
  </div></div>
</div>

<!-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     TAB 6 — REVENUE LOOP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ -->
<div class="tab" id="tab-revenue" role="tabpanel">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.2rem;align-items:start">

    <!-- Left: Total + Add Revenue -->
    <div>
      <div class="card" style="text-align:center">
        <div class="card-title" style="justify-content:center">&#128176; Total Revenue</div>
        <div class="revenue-total" id="rev-total">$0<small>.00</small></div>
        <div style="font-size:.78rem;color:var(--text3)" id="rev-sub">across all projects</div>
      </div>

      <div class="card">
        <div class="card-title">&#10133; Log Revenue</div>
        <label for="rev-project">Project name</label>
        <input type="text" id="rev-project" placeholder="e.g. Waitlist Wizard"/>
        <label for="rev-amount">Amount (USD)</label>
        <input type="number" id="rev-amount" placeholder="0.00" step="0.01" min="0"/>
        <label for="rev-date">Date</label>
        <input type="date" id="rev-date"/>
        <label for="rev-source">Source</label>
        <input type="text" id="rev-source" placeholder="e.g. Product Hunt, cold email"/>
        <div style="margin-top:.8rem">
          <button class="btn btn-success btn-full" onclick="addRevenue()">Log Revenue</button>
        </div>
      </div>

      <!-- Pipeline Score -->
      <div class="card">
        <div class="card-title">&#127919; Pipeline Score</div>
        <div class="loop-insight" id="pipeline-insight">Loading your venture loop stats...</div>
      </div>
    </div>

    <!-- Right: Tables + Learning Log -->
    <div>
      <div class="card">
        <div class="card-title">&#128200; Revenue by Project</div>
        <div id="rev-table"><div class="empty-state"><div class="empty-icon">&#128200;</div>No revenue logged yet. Time to change that.</div></div>
      </div>

      <div class="card">
        <div class="card-title">&#128214; Learning Log</div>
        <label for="learn-project">Project</label>
        <input type="text" id="learn-project" placeholder="Project name"/>
        <label for="learn-worked">What worked</label>
        <textarea id="learn-worked" rows="2" placeholder="What channels, messages, or tactics got results?"></textarea>
        <label for="learn-didnt">What didn't work</label>
        <textarea id="learn-didnt" rows="2" placeholder="What flopped? Be honest."></textarea>
        <div style="margin-top:.8rem;display:flex;gap:.5rem">
          <button class="btn btn-secondary" style="flex:1" onclick="saveLearning()">Save Note</button>
          <button class="btn btn-ghost btn-sm" onclick="loadLearnings()">View All</button>
        </div>
        <div id="learnings-list" style="margin-top:.8rem"></div>
      </div>
    </div>
  </div>
</div>

<!-- ── TOASTS ── -->
<div id="toasts"></div>

<!-- ── FOOTER ── -->
<footer style="text-align:center;padding:.6rem;font-size:.72rem;color:var(--text4);
  border-top:1px solid var(--border2);background:var(--card);margin-top:auto">
  AI-DAN Managing Director &nbsp;&#183;&nbsp; v{version}
</footer>

<script>
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// UTILITIES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function esc(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;')
    .replace(/'/g,'&#39;');
}

function jsStr(s) {
  if (s == null) return '';
  return String(s)
    .replace(/\\\\/g,'\\\\\\\\')
    .replace(/"/g,'\\\\"')
    .replace(/\\n/g,'\\\\n');
}

function apiFetch(path, opts) {
  const key = (document.getElementById('api-key-input') || {}).value || localStorage.getItem('api_key') || '';
  const defaultOpts = {
    headers: {'Content-Type':'application/json','X-API-Key':key},
  };
  const mergedOpts = Object.assign({}, defaultOpts, opts || {});
  if (opts && opts.headers) {
    mergedOpts.headers = Object.assign({}, defaultOpts.headers, opts.headers);
  }
  return fetch(path, mergedOpts).then(function(r) {
    if (r.status === 401) throw new Error('Authentication required. Set your API key above.');
    if (r.status === 429) throw new Error('Rate limit hit. Wait a moment and try again.');
    if (r.status >= 500) throw new Error('Server error. Check the Factory tab for details.');
    if (!r.ok) return r.json().then(function(d){ throw new Error(d.detail || d.message || 'Request failed ('+r.status+')'); });
    return r.json();
  }).catch(function(e) {
    if (e.message === 'Failed to fetch') throw new Error("Can't reach the server. Check your internet connection.");
    throw e;
  });
}

let _toastId = 0;
function toast(msg, type) {
  const id = ++_toastId;
  const icons = {success:'&#10003;', error:'&#10007;', warn:'&#9888;', info:'&#8505;'};
  const wrap = document.getElementById('toasts');
  const el = document.createElement('div');
  el.className = 'toast ' + (type||'info');
  el.innerHTML = '<span>' + (icons[type]||icons.info) + '</span><span>' + esc(msg) + '</span>';
  wrap.appendChild(el);
  setTimeout(function(){ if(el.parentNode) el.parentNode.removeChild(el); }, 4000);
}

function showTab(name) {
  document.querySelectorAll('.tab').forEach(function(t){ t.classList.remove('active'); });
  document.querySelectorAll('.nav button').forEach(function(b){ b.classList.remove('active'); });
  const panel = document.getElementById('tab-'+name);
  const btn = document.getElementById('nav-'+name);
  if (panel) panel.classList.add('active');
  if (btn) btn.classList.add('active');
  if (name === 'dashboard') loadDashboard();
  if (name === 'factory') loadFactory();
  if (name === 'launch') loadLaunchProjects();
  if (name === 'revenue') loadRevenue();
}

function relTime(ts) {
  if (!ts) return '–';
  const d = new Date(ts);
  if (isNaN(d)) return ts;
  const diff = Math.floor((Date.now() - d) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return Math.floor(diff/60) + 'm ago';
  if (diff < 86400) return Math.floor(diff/3600) + 'h ago';
  return Math.floor(diff/86400) + 'd ago';
}

function copyText(text, btn) {
  navigator.clipboard.writeText(text).then(function(){
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(function(){ btn.textContent = orig; }, 1500);
    toast('Copied to clipboard', 'success');
  }).catch(function(){ toast('Copy failed', 'error'); });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// API KEY PERSISTENCE
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
(function initApiKey() {
  const inp = document.getElementById('api-key-input');
  const saved = localStorage.getItem('api_key') || '';
  if (saved) inp.value = saved;
  inp.addEventListener('change', function(){ localStorage.setItem('api_key', inp.value.trim()); });
  inp.addEventListener('blur', function(){ localStorage.setItem('api_key', inp.value.trim()); });
})();

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CHAT MODULE
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
let chatHistory = [];
let chatBusy = false;

function initChat() {
  appendAIMessage(
    "Hey. I'm AI-DAN — your venture-loop advisor. No fluff, no flattery. Tell me an idea, ask what to build next, or ask me anything about your projects. Let's make some money.",
    null
  );

  const inp = document.getElementById('chat-input');
  inp.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      sendChatMessage();
    }
    // Auto-resize
    setTimeout(function(){
      inp.style.height = 'auto';
      inp.style.height = Math.min(inp.scrollHeight, 150) + 'px';
    }, 0);
  });
}

function appendAIMessage(text, model) {
  const hist = document.getElementById('chat-history');
  const starters = document.getElementById('chat-starters');
  if (starters && chatHistory.length > 0) starters.style.display = 'none';

  const wrap = document.createElement('div');
  wrap.className = 'chat-msg ai';
  wrap.innerHTML = '<div class="chat-avatar ai-av">&#129504;</div>' +
    '<div>' +
    '<div class="chat-bubble">' + esc(text) + '</div>' +
    (model ? '<div class="chat-meta">' + esc(model) + '</div>' : '') +
    '</div>';
  hist.appendChild(wrap);
  hist.scrollTop = hist.scrollHeight;
  return wrap;
}

function appendUserMessage(text) {
  const hist = document.getElementById('chat-history');
  const starters = document.getElementById('chat-starters');
  if (starters) starters.style.display = 'none';

  const wrap = document.createElement('div');
  wrap.className = 'chat-msg user';
  wrap.innerHTML = '<div class="chat-avatar user-av">&#128100;</div>' +
    '<div><div class="chat-bubble">' + esc(text) + '</div></div>';
  hist.appendChild(wrap);
  hist.scrollTop = hist.scrollHeight;
}

function showTypingIndicator() {
  const hist = document.getElementById('chat-history');
  const wrap = document.createElement('div');
  wrap.className = 'chat-msg ai';
  wrap.id = 'typing-indicator';
  wrap.innerHTML = '<div class="chat-avatar ai-av">&#129504;</div>' +
    '<div><div class="chat-bubble"><div class="typing-dots"><span></span><span></span><span></span></div>' +
    '<div style="font-size:.72rem;color:var(--text4);margin-top:.2rem">AI-DAN is thinking...</div></div></div>';
  hist.appendChild(wrap);
  hist.scrollTop = hist.scrollHeight;
}

function removeTypingIndicator() {
  const el = document.getElementById('typing-indicator');
  if (el) el.parentNode.removeChild(el);
}

function sendStarter(text) {
  document.getElementById('chat-input').value = text;
  sendChatMessage();
}

function sendChatMessage() {
  if (chatBusy) return;
  const inp = document.getElementById('chat-input');
  const msg = inp.value.trim();
  if (!msg) return;

  inp.value = '';
  inp.style.height = 'auto';
  chatBusy = true;
  document.getElementById('chat-send-btn').disabled = true;

  appendUserMessage(msg);
  chatHistory.push({role:'user', content:msg});

  showTypingIndicator();

  apiFetch('/chat/talk', {
    method: 'POST',
    body: JSON.stringify({message: msg, history: chatHistory.slice(-20)})
  }).then(function(data) {
    removeTypingIndicator();
    const reply = data.reply || data.message || data.response || JSON.stringify(data);
    const model = data.model || null;
    appendAIMessage(reply, model);
    chatHistory.push({role:'assistant', content:reply});
  }).catch(function(err) {
    removeTypingIndicator();
    appendAIMessage('Error: ' + err.message, null);
  }).finally(function() {
    chatBusy = false;
    document.getElementById('chat-send-btn').disabled = false;
    inp.focus();
  });
}

function clearChat() {
  chatHistory = [];
  const hist = document.getElementById('chat-history');
  hist.innerHTML = '';
  const starters = document.getElementById('chat-starters');
  if (starters) starters.style.display = 'flex';
  initChat();
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// DASHBOARD MODULE
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
let _dashProjects = [];

function loadDashboard() {
  const refreshEl = document.getElementById('dash-last-refresh');
  if (refreshEl) refreshEl.textContent = 'Loading...';

  Promise.all([
    apiFetch('/portfolio/projects').catch(function(){ return []; }),
    apiFetch('/api/dashboard/health').catch(function(){ return {}; }),
    apiFetch('/api/dashboard/tokens').catch(function(){ return {}; })
  ]).then(function(results) {
    const projects = Array.isArray(results[0]) ? results[0] : (results[0].projects || []);
    const health = results[1] || {};
    const tokens = results[2] || {};
    _dashProjects = projects;

    renderDashStats(projects);
    renderDashBuilds(projects);
    renderDashActivity(projects);
    renderDashHealth(health, tokens);
    loadLaunchProjects();

    if (refreshEl) refreshEl.textContent = 'Updated ' + new Date().toLocaleTimeString();
  }).catch(function(err) {
    toast('Dashboard error: ' + err.message, 'error');
  });
}

function renderDashStats(projects) {
  const total = projects.length;
  const approved = projects.filter(function(p){ return p.status === 'approved'; }).length;
  const building = projects.filter(function(p){ return p.status === 'building' || p.status === 'in_progress'; }).length;
  const live = projects.filter(function(p){ return p.status === 'launched' || p.status === 'live'; }).length;

  document.getElementById('stat-ideas').textContent = total;
  document.getElementById('stat-approved').textContent = approved;
  document.getElementById('stat-building').textContent = building;
  document.getElementById('stat-live').textContent = live;

  document.getElementById('loop-ideas').textContent = total;
  document.getElementById('loop-scored').textContent = projects.filter(function(p){ return p.status && p.status !== 'idea'; }).length;
  document.getElementById('loop-approved').textContent = approved + building + live;
  document.getElementById('loop-building').textContent = building;
  document.getElementById('loop-launched').textContent = live;
  document.getElementById('loop-revenue-count').textContent = live > 0 ? live : '0';

  const revEntries = JSON.parse(localStorage.getItem('revenue_entries') || '[]');
  const totalRev = revEntries.reduce(function(s,e){ return s + (parseFloat(e.amount)||0); }, 0);
  document.getElementById('stat-revenue').textContent = '$' + totalRev.toLocaleString('en-US', {minimumFractionDigits:0, maximumFractionDigits:0});
}

function renderDashBuilds(projects) {
  const el = document.getElementById('dash-builds');
  const active = projects.filter(function(p){ return p.status === 'building' || p.status === 'in_progress' || p.status === 'approved'; });
  if (!active.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">&#9881;</div>No active builds. <a href="#" onclick="showTab(\'analyze\');return false">Analyze an idea</a> to get started.</div>';
    return;
  }
  let html = '';
  active.forEach(function(p) {
    const statusCls = 'badge-' + (p.status||'idea').toLowerCase();
    html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:.4rem 0;border-bottom:1px solid var(--border2)">' +
      '<div>' +
        '<div style="font-size:.85rem;font-weight:600;color:var(--text)">' + esc(p.name||'Unnamed') + '</div>' +
        '<div style="font-size:.72rem;color:var(--text3)">' + relTime(p.created_at) + '</div>' +
      '</div>' +
      '<span class="badge ' + esc(statusCls) + '">' + esc((p.status||'').toUpperCase()) + '</span>' +
    '</div>';
  });
  el.innerHTML = html;
}

function renderDashActivity(projects) {
  const el = document.getElementById('dash-activity');
  const sorted = projects.slice().sort(function(a,b){
    return new Date(b.updated_at||b.created_at||0) - new Date(a.updated_at||a.created_at||0);
  }).slice(0, 5);
  if (!sorted.length) {
    el.innerHTML = '<div class="empty-state">No activity yet.</div>';
    return;
  }
  let html = '';
  sorted.forEach(function(p) {
    const statusVerbs = {idea:'created idea',approved:'approved',building:'started building',launched:'launched',killed:'killed'};
    const verb = statusVerbs[p.status] || p.status || 'updated';
    html += '<div class="activity-item">' +
      '<div class="activity-dot"></div>' +
      '<div class="activity-text"><strong>' + esc(p.name||'Unnamed') + '</strong> — ' + esc(verb) + '</div>' +
      '<div class="activity-time">' + relTime(p.updated_at||p.created_at) + '</div>' +
    '</div>';
  });
  el.innerHTML = html;
}

function renderDashHealth(health, tokens) {
  const el = document.getElementById('dash-health');
  const model = health.ai_model || health.model || tokens.model || 'Unknown';
  const ghOk = health.github_token !== false;
  const aiOk = health.ai_configured !== false && model !== 'Unknown';
  const factOk = health.factory_connected !== false;
  const lastDeploy = health.last_deploy || null;

  const checks = [
    [ghOk, 'GitHub Token', ghOk ? 'Connected' : 'Not configured — check GITHUB_TOKEN'],
    [factOk, 'Factory Repo', factOk ? 'Connected' : 'Not connected — check factory settings'],
    [aiOk, 'AI Model', aiOk ? model : 'Not configured — add API key to env vars'],
    [true, 'Last Deploy', lastDeploy ? relTime(lastDeploy) : 'No deploys yet'],
  ];

  let html = '<div class="checks-grid">';
  checks.forEach(function(c) {
    const dotCls = c[0] ? 'dot-green' : 'dot-red';
    html += '<div class="check-item"><div class="health-dot ' + dotCls + '"></div><div><strong>' + esc(c[1]) + '</strong><br><span style="color:var(--text3);font-size:.75rem">' + esc(c[2]) + '</span></div></div>';
  });
  html += '</div>';

  if (!aiOk) {
    document.getElementById('ai-banner').style.display = 'block';
  }

  if (tokens.used !== undefined) {
    html += '<div style="margin-top:.8rem;font-size:.78rem;color:var(--text3)">Token usage: <strong style="color:var(--text)">' + (tokens.used||0).toLocaleString() + '</strong> / ' + (tokens.limit ? tokens.limit.toLocaleString() : '&#8734;') + '</div>';
  }
  el.innerHTML = html;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ANALYZE MODULE
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function submitAnalysis() {
  const desc = document.getElementById('idea-desc').value.trim();
  if (!desc) { toast('Please enter your idea description', 'warn'); return; }

  const btn = document.getElementById('analyze-btn');
  const errEl = document.getElementById('analyze-error');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Scoring...';
  errEl.style.display = 'none';

  const payload = {
    description: desc,
    problem: document.getElementById('idea-problem').value.trim(),
    target_user: document.getElementById('idea-user').value.trim(),
    monetization: document.getElementById('idea-mono').value,
    competition: document.getElementById('idea-comp').value,
    time_to_revenue: document.getElementById('idea-ttr').value,
    differentiation: document.getElementById('idea-diff').value.trim(),
  };

  apiFetch('/api/analyze', {method:'POST', body: JSON.stringify(payload)})
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
  const decision = (d.decision || d.verdict || 'HOLD').toUpperCase();
  const scores = d.scores || {};
  const overall = scores.overall || d.overall_score || 0;

  const scoreFields = [
    ['Overall','overall', overall],
    ['Feasibility','feasibility', scores.feasibility || d.feasibility_score || 0],
    ['Profitability','profitability', scores.profitability || d.profitability_score || 0],
    ['Speed to Revenue','speed', scores.speed || d.speed_score || 0],
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

  let warnHtml = '';
  if (lowScores.length > 0) {
    warnHtml = '<div class="alert alert-warn">&#9888; Low scores: ' +
      lowScores.map(function(s){ return esc(s[0]) + ' (' + parseFloat(s[2]).toFixed(1) + ')'; }).join(', ') +
    '. Consider these risks carefully.</div>';
  }

  const brief = d.business_brief || d.brief || {};
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
    APPROVED: (d.next_move || 'Start building the MVP immediately.'),
    HOLD: (d.next_move || 'Validate the idea with 5 real users before building.'),
    REJECTED: (d.next_move || 'Move on. Your time is too valuable for this one.'),
  };

  let actionHtml = '';
  if (decision === 'APPROVED') {
    const projName = (d.title || brief.title || 'New Project').replace(/[^a-zA-Z0-9 -]/g,'').substring(0,40);
    actionHtml = '<button class="btn btn-success btn-full" onclick="triggerBuild(' + "'" + esc(projName) + "'" + ')">&#128640; BUILD THIS</button>';
  } else if (decision === 'HOLD') {
    actionHtml = '<button class="btn btn-amber btn-full" onclick="toast(\'Saved to your idea pipeline\',\'success\')">&#128203; Save for Later</button>';
  }

  let detailHtml = '';
  const details = [
    ['Pricing suggestion', d.pricing || d.price_suggestion],
    ['Distribution plan', d.distribution],
    ['First 10 customers', d.first_customers || d.acquisition],
    ['Main risk', d.main_risk || d.risk],
    ['Next move', nextMoves[decision] || d.next_move],
  ];
  details.forEach(function(det) {
    if (det[1]) {
      detailHtml += '<div style="margin:.5rem 0;font-size:.83rem"><span style="color:var(--text3)">' + esc(det[0]) + ': </span><span style="color:var(--text)">' + esc(det[1]) + '</span></div>';
    }
  });

  const col = document.getElementById('analyze-results-col');
  col.innerHTML = '<div class="card">' +
    '<div class="card-title">&#128202; Analysis Result</div>' +
    '<div class="decision-badge decision-' + esc(decision) + '">' +
      (decision === 'APPROVED' ? '&#9989; APPROVED' : decision === 'HOLD' ? '&#9203; HOLD' : '&#10060; REJECTED') +
    '</div>' +
    warnHtml +
    barsHtml +
    briefHtml +
    (detailHtml ? '<div class="section-sep"></div>' + detailHtml : '') +
    (actionHtml ? '<div style="margin-top:1rem">' + actionHtml + '</div>' : '') +
  '</div>';
}

function triggerBuild(projName) {
  const name = prompt('Project name (used for your repo):', projName);
  if (!name) return;
  apiFetch('/factory/trigger', {method:'POST', body: JSON.stringify({project_name: name})})
    .then(function(){ toast('Build triggered for: ' + name, 'success'); showTab('factory'); })
    .catch(function(err){ toast('Could not trigger build: ' + err.message, 'error'); });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FACTORY MODULE
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function loadFactory() {
  document.getElementById('factory-checks').innerHTML = '<div class="loading-row"><span class="spinner"></span></div>';
  document.getElementById('factory-runs').innerHTML = '<div class="loading-row"><span class="spinner"></span></div>';

  Promise.all([
    apiFetch('/portfolio/projects').catch(function(){ return []; }),
    apiFetch('/factory/runs').catch(function(){ return []; }),
    apiFetch('/api/dashboard/health').catch(function(){ return {}; }),
  ]).then(function(res) {
    const projects = Array.isArray(res[0]) ? res[0] : (res[0].projects || []);
    const runs = Array.isArray(res[1]) ? res[1] : (res[1].runs || []);
    const health = res[2] || {};
    renderFactoryChecks(health);
    renderFactoryRuns(projects, runs);
  }).catch(function(err) { toast('Factory load error: ' + err.message, 'error'); });
}

function renderFactoryChecks(health) {
  const el = document.getElementById('factory-checks');
  const ghOk = health.github_token !== false;
  const aiOk = health.ai_configured !== false;
  const factOk = health.factory_connected !== false;
  const model = health.ai_model || health.model || 'Not configured';
  const lastDeploy = health.last_deploy;

  const checks = [
    [ghOk, 'GitHub Token', ghOk ? 'Valid and connected' : 'Missing or expired. Check GITHUB_TOKEN in Vercel.'],
    [factOk, 'Factory Repo', factOk ? 'Connected' : 'Not found. Check factory repo settings.'],
    [aiOk, 'AI Model', aiOk ? model : 'No AI key found. Add ANTHROPIC_API_KEY / OPENAI_API_KEY / GROQ_API_KEY.'],
    [!!lastDeploy, 'Last Deploy', lastDeploy ? relTime(lastDeploy) : 'No successful deploys yet'],
  ];

  let html = '<div class="checks-grid">';
  checks.forEach(function(c) {
    const icon = c[0] ? '&#9989;' : '&#10060;';
    const dotCls = c[0] ? 'dot-green' : 'dot-red';
    html += '<div class="check-item"><div class="health-dot ' + dotCls + '"></div><div><strong>' + icon + ' ' + esc(c[1]) + '</strong><br><span style="font-size:.75rem;color:var(--text3)">' + esc(c[2]) + '</span></div></div>';
  });
  html += '</div>';
  el.innerHTML = html;
}

function renderFactoryRuns(projects, runs) {
  const el = document.getElementById('factory-runs');
  const buildable = projects.filter(function(p){
    return p.status === 'building' || p.status === 'in_progress' || p.status === 'launched' || p.status === 'approved';
  });
  const allItems = runs.length ? runs : buildable;

  if (!allItems.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">&#127981;</div>No builds yet. <a href="#" onclick="showTab(\'analyze\');return false">Score an idea</a> to get started.</div>';
    return;
  }

  let html = '';
  allItems.forEach(function(item) {
    const status = (item.status || item.conclusion || 'pending').toLowerCase();
    const name = item.name || item.project_name || item.repository || 'Build';
    const started = item.started_at || item.created_at || item.run_started_at;
    const url = item.deployed_url || item.html_url || item.url || null;
    const error = item.error || item.failure_reason || null;

    let statusBadge = 'badge-pending';
    if (status === 'success' || status === 'succeeded' || status === 'launched') statusBadge = 'badge-succeeded';
    else if (status === 'failure' || status === 'failed' || status === 'error') statusBadge = 'badge-failed';
    else if (status === 'in_progress' || status === 'running' || status === 'building') statusBadge = 'badge-running';
    else if (status === 'approved') statusBadge = 'badge-approved';

    let errorHtml = '';
    if ((status === 'failure' || status === 'failed' || status === 'error') && error) {
      let msg = error;
      if (error.toLowerCase().includes('github') || error.toLowerCase().includes('token')) {
        msg = 'Build failed: The GitHub token may be expired. Check your GITHUB_TOKEN secret in Vercel.';
      } else if (error.toLowerCase().includes('workflow') || error.toLowerCase().includes('action')) {
        msg = 'Build failed: Could not find the factory workflow. Make sure GitHub Actions is enabled.';
      } else if (error.toLowerCase().includes('permission') || error.toLowerCase().includes('403')) {
        msg = 'Build failed: Permission denied. Check your GitHub token has the right scopes.';
      } else {
        msg = 'Build failed: ' + error.substring(0, 200);
      }
      errorHtml = '<div class="alert alert-error" style="margin-top:.5rem;font-size:.8rem">&#10060; ' + esc(msg) + '</div>';
    }

    let deployLink = '';
    if (url && (status === 'success' || status === 'succeeded' || status === 'launched')) {
      deployLink = '<div style="margin-top:.4rem;display:flex;gap:.5rem;align-items:center">' +
        '<a href="' + esc(url) + '" target="_blank" class="btn btn-sm btn-success">&#128640; View Live</a>' +
        '<button class="btn btn-sm btn-ghost" onclick="prefillLaunch(\'' + jsStr(name) + '\',\'' + jsStr(url) + '\')">&#128227; Launch Content</button>' +
      '</div>';
    }

    let progress = '';
    if (status === 'in_progress' || status === 'running' || status === 'building') {
      progress = '<div style="height:3px;border-radius:2px;background:#1e1e1e;overflow:hidden;margin-top:.4rem">' +
        '<div style="height:100%;width:60%;background:var(--accent);border-radius:2px;animation:progressPulse 2s ease-in-out infinite"></div></div>';
    }

    html += '<div style="padding:.75rem 0;border-bottom:1px solid var(--border2)">' +
      '<div style="display:flex;align-items:center;justify-content:space-between">' +
        '<div><div style="font-weight:600;font-size:.9rem;color:#fff">' + esc(name) + '</div>' +
          '<div style="font-size:.72rem;color:var(--text3);margin-top:.15rem">Started ' + relTime(started) + '</div></div>' +
        '<span class="badge ' + esc(statusBadge) + '">' + esc(status.toUpperCase()) + '</span>' +
      '</div>' +
      progress + errorHtml + deployLink +
    '</div>';
  });
  el.innerHTML = html;
}

function prefillLaunch(name, url) {
  document.getElementById('launch-title').value = name;
  document.getElementById('launch-url').value = url;
  showTab('launch');
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// LAUNCH KIT MODULE
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function loadLaunchProjects() {
  apiFetch('/portfolio/projects').then(function(data) {
    const projects = Array.isArray(data) ? data : (data.projects || []);
    const sel = document.getElementById('launch-project');
    const current = sel.value;
    sel.innerHTML = '<option value="">&#8212; Select project or enter below &#8212;</option>';
    projects.forEach(function(p) {
      const opt = document.createElement('option');
      opt.value = p.id || p.name;
      opt.textContent = (p.name || p.id) + (p.status ? ' (' + p.status + ')' : '');
      sel.appendChild(opt);
    });
    if (current) sel.value = current;
  }).catch(function(){});

  const saved = localStorage.getItem('payment_link');
  if (saved) {
    document.getElementById('payment-url').value = saved;
    document.getElementById('saved-payment-link').innerHTML = '&#128279; Saved: <a href="' + esc(saved) + '" target="_blank">' + esc(saved) + '</a>';
  }
}


const REGION_NOTES={global:null,mena:'&#128161; MENA: Instagram+Snapchat lead. WhatsApp forwards = #1 viral. Arabic content outperforms English.',africa:'&#128161; Africa: WhatsApp group forwards are massive. Facebook groups drive trust. Short videos win.',south_asia:'&#128161; South Asia: WhatsApp groups = viral channel #1. High price sensitivity \u2014 offer free/cheap tier.',southeast_asia:'&#128161; SE Asia: Facebook dominant in PH/MY/ID. TikTok exploding in TH/VN. Playful tone wins.',latam:'&#128161; LatAm: Instagram Stories & Reels dominate. Emotional storytelling beats feature lists.',europe:'&#128161; Europe: Privacy-conscious \u2014 mention data safety. LinkedIn for B2B. TikTok growing in UK/DE.',north_america:'&#128161; North America: Reddit & X for community. TikTok for consumer. LinkedIn for B2B.'};
function onRegionChange(){var r=(document.getElementById('launch-region')||{}).value||'global';var el=document.getElementById('region-insight');var n=REGION_NOTES[r];if(el){if(n){el.innerHTML=n;el.style.display='block';}else el.style.display='none';}var vr=document.getElementById('vid-region');if(vr)vr.value=r;}
const CARD_GRADIENTS={purple:['#1a0533','#3d1470','#5b1ea8','#7c3aed'],dark:['#0a0a0a','#1a1a2e','#16213e','#0f3460'],sunset:['#1a0520','#6b1a1a','#c0392b','#e67e22'],ocean:['#0a1628','#1a3a5c','#0e7490','#22d3ee'],black:['#000','#111','#111','#000']};
function drawDodoOnCanvas(ctx,x,y,sz){var s=sz/100;ctx.save();ctx.translate(x,y);ctx.scale(s,s);ctx.beginPath();ctx.ellipse(50,62,28,26,0,0,Math.PI*2);ctx.fillStyle='#6B4DFF';ctx.fill();ctx.beginPath();ctx.ellipse(50,67,16,18,0,0,Math.PI*2);ctx.fillStyle='#e8e8ff';ctx.fill();ctx.beginPath();ctx.arc(50,36,18,0,Math.PI*2);ctx.fillStyle='#6B4DFF';ctx.fill();ctx.beginPath();ctx.arc(43,32,7,0,Math.PI*2);ctx.fillStyle='white';ctx.fill();ctx.beginPath();ctx.arc(57,32,7,0,Math.PI*2);ctx.fillStyle='white';ctx.fill();ctx.beginPath();ctx.arc(44,33,3.5,0,Math.PI*2);ctx.fillStyle='#1a1a2e';ctx.fill();ctx.beginPath();ctx.arc(58,33,3.5,0,Math.PI*2);ctx.fillStyle='#1a1a2e';ctx.fill();ctx.beginPath();ctx.moveTo(47,40);ctx.lineTo(53,40);ctx.lineTo(50,46);ctx.closePath();ctx.fillStyle='#f59e0b';ctx.fill();ctx.restore();}
var _cHue=0,_cAF=null;
function updateCardPreview(){var cv=document.getElementById('social-card-canvas');if(!cv)return;var ctx=cv.getContext('2d');var st=(document.getElementById('card-style')||{value:'purple'}).value||'purple';var sk=(document.getElementById('card-size')||{value:'square'}).value||'square';var pn=(document.getElementById('card-name')||{value:''}).value||'Your Product';var tg=(document.getElementById('card-tagline')||{value:''}).value||'Your tagline here';var ut=(document.getElementById('card-url')||{value:''}).value||'yourproduct.com';var ac=(document.getElementById('card-accent')||{value:'#5b6ef7'}).value||'#5b6ef7';var wh={square:[300,300],landscape:[300,158],story:[169,300]}[sk]||[300,300];var w=wh[0],h=wh[1];cv.width=w;cv.height=h;if(_cAF){cancelAnimationFrame(_cAF);_cAF=null;}function df(){_cHue=(_cHue+0.6)%360;ctx.save();ctx.filter='hue-rotate('+_cHue+'deg)';var g=CARD_GRADIENTS[st]||CARD_GRADIENTS.purple;var grd=ctx.createLinearGradient(0,0,w,h);grd.addColorStop(0,g[0]);grd.addColorStop(0.35,g[1]);grd.addColorStop(0.7,g[2]);grd.addColorStop(1,g[3]);ctx.fillStyle=grd;ctx.fillRect(0,0,w,h);ctx.filter='none';ctx.restore();drawDodoOnCanvas(ctx,w-42,h-52,40);ctx.textAlign='center';ctx.shadowColor='rgba(0,0,0,0.5)';ctx.fillStyle='#fff';ctx.font='bold '+Math.round(w*0.09)+'px system-ui,sans-serif';ctx.shadowBlur=8;ctx.fillText(pn,w/2,h*0.38);ctx.font=Math.round(w*0.052)+'px system-ui,sans-serif';ctx.fillStyle='rgba(255,255,255,0.85)';ctx.shadowBlur=4;var wd=tg.split(' '),ln='',lns=[],mW=w*0.82;wd.forEach(function(d){var t=ln+(ln?' ':'')+d;if(ctx.measureText(t).width>mW&&ln){lns.push(ln);ln=d;}else ln=t;});if(ln)lns.push(ln);var lh=Math.round(w*0.065),sy=h*0.52;lns.forEach(function(l,i){ctx.fillText(l,w/2,sy+i*lh);});ctx.font=Math.round(w*0.042)+'px system-ui,sans-serif';ctx.fillStyle=ac;ctx.shadowBlur=0;ctx.fillText(ut,w/2,h*0.85);var gl=Math.abs(Math.sin(_cHue*Math.PI/180))*5+2;ctx.strokeStyle=ac;ctx.lineWidth=gl;ctx.strokeRect(1,1,w-2,h-2);_cAF=requestAnimationFrame(df);}df();}
function downloadSocialCard(){var sk=(document.getElementById('card-size')||{value:'square'}).value||'square';var fd={square:[1080,1080],landscape:[1200,630],story:[1080,1920]}[sk]||[1080,1080];var fw=fd[0],fh=fd[1];var off=document.createElement('canvas');off.width=fw;off.height=fh;var ctx=off.getContext('2d');var st=(document.getElementById('card-style')||{value:'purple'}).value||'purple';var pn=(document.getElementById('card-name')||{value:''}).value||'Your Product';var tg=(document.getElementById('card-tagline')||{value:''}).value||'tagline';var ut=(document.getElementById('card-url')||{value:''}).value||'yourproduct.com';var ac=(document.getElementById('card-accent')||{value:'#5b6ef7'}).value||'#5b6ef7';var g=CARD_GRADIENTS[st]||CARD_GRADIENTS.purple;var grd=ctx.createLinearGradient(0,0,fw,fh);grd.addColorStop(0,g[0]);grd.addColorStop(0.35,g[1]);grd.addColorStop(0.7,g[2]);grd.addColorStop(1,g[3]);ctx.fillStyle=grd;ctx.fillRect(0,0,fw,fh);drawDodoOnCanvas(ctx,fw-110,fh-140,100);ctx.textAlign='center';ctx.shadowColor='rgba(0,0,0,0.5)';ctx.fillStyle='#fff';ctx.font='bold '+Math.round(fw*0.09)+'px system-ui,sans-serif';ctx.shadowBlur=15;ctx.fillText(pn,fw/2,fh*0.38);ctx.font=Math.round(fw*0.052)+'px system-ui,sans-serif';ctx.fillStyle='rgba(255,255,255,0.85)';ctx.shadowBlur=8;var wd=tg.split(' '),ln='',lns=[],mW=fw*0.82;wd.forEach(function(d){var t=ln+(ln?' ':'')+d;if(ctx.measureText(t).width>mW&&ln){lns.push(ln);ln=d;}else ln=t;});if(ln)lns.push(ln);var lh=Math.round(fw*0.065),sy=fh*0.52;lns.forEach(function(l,i){ctx.fillText(l,fw/2,sy+i*lh);});ctx.font=Math.round(fw*0.042)+'px system-ui,sans-serif';ctx.fillStyle=ac;ctx.shadowBlur=0;ctx.fillText(ut,fw/2,fh*0.85);ctx.strokeStyle=ac;ctx.lineWidth=6;ctx.strokeRect(3,3,fw-6,fh-6);off.toBlob(function(b){var a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=(pn.replace(/\s+/g,'-').toLowerCase()||'card')+'-'+sk+'.png';a.click();URL.revokeObjectURL(a.href);toast('Social card downloaded!','success');},'image/png');}
function triggerVideoGeneration(){var p=(document.getElementById('vid-product')||{}).value||'';var tg=(document.getElementById('vid-tagline')||{}).value||'';var u=(document.getElementById('vid-url')||{}).value||'';var r=(document.getElementById('vid-region')||{}).value||'global';var ai=(document.getElementById('vid-ai-concept')||{}).checked||false;if(!p.trim()){toast('Enter a product name first','warn');return;}var btn=document.getElementById('vid-btn'),res=document.getElementById('vid-result');btn.disabled=true;btn.innerHTML='<span class="spinner"></span> Triggering...';res.innerHTML='';apiFetch('/api/distribution/generate-video',{method:'POST',body:JSON.stringify({title:p.trim(),description:tg||p.trim(),url:u||'https://example.com',target_region:r,use_ai_concept:ai})}).then(function(d){var h='<div class="alert alert-success">&#10003; Video job started!</div>';if(d.workflow_url)h+='<div style="margin-top:.4rem">&#128279; <a href="'+esc(d.workflow_url)+'" target="_blank">Track on GitHub Actions</a></div>';if(d.note)h+='<div style="color:var(--text3);font-size:.76rem;margin-top:.3rem">&#9432; '+esc(d.note)+'</div>';res.innerHTML=h;toast('Video triggered!','success');}).catch(function(e){res.innerHTML='<div class="alert alert-error">'+esc(e.message)+'</div>';toast('Video failed: '+e.message,'error');}).finally(function(){btn.disabled=false;btn.innerHTML='&#127916; Generate Free Promo Video';});}
function savePaymentLink() {
  const url = document.getElementById('payment-url').value.trim();
  if (!url) return;
  localStorage.setItem('payment_link', url);
  document.getElementById('saved-payment-link').innerHTML = '&#10003; Saved: <a href="' + esc(url) + '" target="_blank">' + esc(url) + '</a>';
  toast('Payment link saved!', 'success');
}

function generateLaunch() {
  const title = document.getElementById('launch-title').value.trim();
  const url = document.getElementById('launch-url').value.trim();
  const desc = document.getElementById('launch-desc').value.trim();
  if (!title || !desc) { toast('Product title and description are required', 'warn'); return; }

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
  const paymentLink = localStorage.getItem('payment_link') || '';
  const content = data.content || data;

  const platforms = [
    {key:'twitter', label:'&#120143; X / Twitter', text: content.twitter || content.tweet || content.x || ''},
    {key:'linkedin', label:'&#128188; LinkedIn', text: content.linkedin || ''},
    {key:'email', label:'&#128140; Cold Outreach Email', text: content.email || content.cold_email || ''},
    {key:'producthunt', label:'&#128049; Product Hunt Tagline', text: content.product_hunt || content.ph_tagline || content.tagline || ''},
    {key:'reddit', label:'&#128257; Reddit Post', text: content.reddit || ''},
  ];

  let blocksHtml = '';
  platforms.forEach(function(p) {
    if (!p.text) return;
    const btnId = 'copy-' + p.key;
    blocksHtml += '<div class="content-block">' +
      '<div class="content-platform">' + p.label +
        '<button class="btn btn-xs btn-ghost" id="' + btnId + '" onclick="copyText(this.getAttribute(\'data-text\'),this)" data-text="' + esc(p.text) + '">Copy</button>' +
      '</div>' +
      '<div class="content-text">' + esc(p.text) + '</div>' +
    '</div>';
  });

  const checklist = data.checklist || [
    'Publish to Product Hunt',
    'Post on X/Twitter',
    'Post in relevant subreddits',
    'Send cold outreach emails',
    'Post in LinkedIn feed',
    'Share in Slack/Discord communities',
    'DM top 10 potential users personally',
    'Set up payment link (' + (paymentLink ? paymentLink : 'add LemonSqueezy link above') + ')',
    'Reply to every comment within 1 hour',
    'Measure signups at 24h mark',
    'Write a "lessons learned" note',
    'Decide: iterate, pivot, or kill',
  ];

  let checkHtml = '<ul class="checklist">';
  checklist.forEach(function(item) {
    const label = typeof item === 'string' ? item : (item.text || item.label || item);
    checkHtml += '<li><input type="checkbox"/><span>' + esc(String(label)) + '</span></li>';
  });
  checkHtml += '</ul>';

  document.getElementById('launch-output').innerHTML =
    '<div class="card"><div class="card-title">&#128227; Launch Content — ' + esc(title) + '</div>' +
    (url ? '<div style="font-size:.78rem;color:var(--text3);margin-bottom:.8rem">&#127758; ' + esc(url) + '</div>' : '') +
    blocksHtml + '</div>' +
    '<div class="card"><div class="card-title">&#9989; 48-Hour Launch Checklist</div>' + checkHtml + '</div>';
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// REVENUE MODULE
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function loadRevenue() {
  const entries = JSON.parse(localStorage.getItem('revenue_entries') || '[]');
  renderRevenueTable(entries);
  updateRevTotal(entries);
  updatePipelineInsight();
  loadLearnings();

  // Default date to today
  const dateInp = document.getElementById('rev-date');
  if (!dateInp.value) dateInp.value = new Date().toISOString().substring(0,10);
}

function addRevenue() {
  const project = document.getElementById('rev-project').value.trim();
  const amount = parseFloat(document.getElementById('rev-amount').value);
  const date = document.getElementById('rev-date').value;
  const source = document.getElementById('rev-source').value.trim();

  if (!project || isNaN(amount) || amount <= 0) {
    toast('Enter project name and valid amount', 'warn');
    return;
  }
  const entries = JSON.parse(localStorage.getItem('revenue_entries') || '[]');
  entries.push({id: Date.now(), project, amount, date: date||new Date().toISOString().substring(0,10), source});
  localStorage.setItem('revenue_entries', JSON.stringify(entries));

  document.getElementById('rev-project').value = '';
  document.getElementById('rev-amount').value = '';
  document.getElementById('rev-source').value = '';

  renderRevenueTable(entries);
  updateRevTotal(entries);
  updatePipelineInsight();
  toast('Revenue logged: $' + amount.toFixed(2), 'success');
}

function renderRevenueTable(entries) {
  const el = document.getElementById('rev-table');
  if (!entries.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128200;</div>No revenue logged yet. Time to change that.</div>';
    return;
  }

  const byProject = {};
  entries.forEach(function(e) {
    if (!byProject[e.project]) byProject[e.project] = {total:0, count:0, last:e.date};
    byProject[e.project].total += parseFloat(e.amount)||0;
    byProject[e.project].count += 1;
    if (e.date > byProject[e.project].last) byProject[e.project].last = e.date;
  });

  let html = '<div class="table-wrap"><table><thead><tr><th>Project</th><th>Revenue</th><th>Payments</th><th>Last</th></tr></thead><tbody>';
  Object.keys(byProject).sort(function(a,b){ return byProject[b].total - byProject[a].total; }).forEach(function(proj) {
    const p = byProject[proj];
    html += '<tr><td><strong>' + esc(proj) + '</strong></td><td style="color:var(--green-t);font-weight:700">$' +
      p.total.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}) + '</td><td>' + p.count + '</td><td>' + esc(p.last) + '</td></tr>';
  });
  html += '</tbody></table></div>';
  el.innerHTML = html;
}

function updateRevTotal(entries) {
  const total = entries.reduce(function(s,e){ return s + (parseFloat(e.amount)||0); }, 0);
  const whole = Math.floor(total);
  const cents = (total - whole).toFixed(2).substring(1);
  document.getElementById('rev-total').innerHTML = '$' + whole.toLocaleString() + '<small>' + cents + '</small>';
  const count = new Set(entries.map(function(e){ return e.project; })).size;
  document.getElementById('rev-sub').textContent = 'across ' + count + (count === 1 ? ' project' : ' projects');
}

function updatePipelineInsight() {
  const projects = _dashProjects;
  const entries = JSON.parse(localStorage.getItem('revenue_entries') || '[]');
  const total = entries.reduce(function(s,e){ return s + (parseFloat(e.amount)||0); }, 0);
  const ideas = projects.length;
  const building = projects.filter(function(p){ return p.status === 'building' || p.status === 'in_progress'; }).length;
  const live = projects.filter(function(p){ return p.status === 'launched' || p.status === 'live'; }).length;

  let insight = "You've analyzed " + ideas + " idea" + (ideas!==1?'s':'') + ", built " + building + ", and launched " + live + ".";
  if (total > 0) {
    insight += " You've made $" + total.toFixed(2) + " — real money. Keep shipping.";
  } else if (live > 0) {
    insight += " You have live products. Focus on distribution: find 10 paying customers before building anything new.";
  } else if (building > 0) {
    insight += " You're building. Ship in the next 7 days, then sell before you improve.";
  } else if (ideas > 0) {
    insight += " You've scored ideas but haven't built yet. Pick the best one and start today.";
  } else {
    insight += " Start by analyzing your first idea. The loop doesn't move until you do.";
  }

  const el = document.getElementById('pipeline-insight');
  if (el) el.textContent = insight;
}

function saveLearning() {
  const project = document.getElementById('learn-project').value.trim();
  const worked = document.getElementById('learn-worked').value.trim();
  const didnt = document.getElementById('learn-didnt').value.trim();
  if (!project) { toast('Enter a project name', 'warn'); return; }

  const logs = JSON.parse(localStorage.getItem('learning_logs') || '[]');
  logs.unshift({id:Date.now(), project, worked, didnt, date: new Date().toLocaleDateString()});
  localStorage.setItem('learning_logs', JSON.stringify(logs.slice(0, 50)));

  document.getElementById('learn-project').value = '';
  document.getElementById('learn-worked').value = '';
  document.getElementById('learn-didnt').value = '';
  toast('Learning saved!', 'success');
  loadLearnings();
}

function loadLearnings() {
  const logs = JSON.parse(localStorage.getItem('learning_logs') || '[]');
  const el = document.getElementById('learnings-list');
  if (!logs.length) { el.innerHTML = ''; return; }
  let html = '';
  logs.slice(0,5).forEach(function(l) {
    html += '<div style="border-top:1px solid var(--border);padding:.6rem 0;font-size:.8rem">' +
      '<div style="font-weight:700;color:var(--text)">' + esc(l.project) + ' <span style="color:var(--text4);font-weight:400">' + esc(l.date) + '</span></div>' +
      (l.worked ? '<div style="color:var(--green-t);margin-top:.2rem">&#10003; ' + esc(l.worked) + '</div>' : '') +
      (l.didnt ? '<div style="color:var(--red-t);margin-top:.2rem">&#10007; ' + esc(l.didnt) + '</div>' : '') +
    '</div>';
  });
  el.innerHTML = html;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// INIT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
(function init() {
  initChat();
  apiFetch('/api/dashboard/health').then(function(h) {
    if (h.ai_configured === false || h.ai_model === null) {
      document.getElementById('ai-banner').style.display = 'block';
    }
  }).catch(function(){});
  setInterval(function(){ loadDashboard(); }, 30000);
})();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def root_ui() -> HTMLResponse:
    """Serve the root idea-analysis UI."""
    html = _ROOT_HTML.replace("{version}", _VERSION)
    return HTMLResponse(content=html)
