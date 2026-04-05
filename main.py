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


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Return a simple health-check response."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Root UI – embedded HTML command center dashboard
# ---------------------------------------------------------------------------
_ROOT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>AI-DAN Command Center</title>
<style>
:root{
  --bg:#0a0a0a;--surface:#1a1a2e;--surface2:#16213e;--border:#2a2a3e;
  --text:#e0e0e0;--muted:#888;--accent:#5b6ef7;--accent-h:#4a5ce6;
  --green:#16a34a;--amber:#d97706;--red:#dc2626;--blue:#2563eb;
  --radius:10px;--shadow:0 4px 24px rgba(0,0,0,.4);
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  background:var(--bg);color:var(--text);font-size:15px}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}

/* ---- Layout ---- */
.app{display:flex;flex-direction:column;min-height:100vh}
.app-header{display:flex;align-items:center;justify-content:space-between;
  padding:.75rem 1.5rem;background:var(--surface);border-bottom:1px solid var(--border);
  position:sticky;top:0;z-index:100}
.header-left{display:flex;align-items:center;gap:.75rem}
.header-left h1{font-size:1.15rem;color:#fff;white-space:nowrap}
.header-left .sub{font-size:.75rem;color:var(--muted);margin-top:1px}
.logo{font-size:1.5rem;line-height:1}
.header-right{display:flex;align-items:center;gap:.5rem}
.api-key-wrap{display:flex;align-items:center;gap:.4rem}
.api-key-wrap input{width:180px;padding:.35rem .6rem;border:1px solid var(--border);
  border-radius:6px;background:#111;color:var(--text);font-size:.8rem}
.api-key-wrap input:focus{outline:none;border-color:var(--accent)}
.health-dot{width:10px;height:10px;border-radius:50%;background:var(--muted);display:inline-block}
.health-dot.ok{background:var(--green)}
.health-dot.warn{background:var(--amber)}
.health-dot.err{background:var(--red)}

/* ---- Tab nav ---- */
.tab-nav{display:flex;gap:0;background:var(--surface2);border-bottom:1px solid var(--border);
  padding:0 1rem;overflow-x:auto;scrollbar-width:none}
.tab-nav::-webkit-scrollbar{display:none}
.tab-btn{padding:.65rem 1rem;border:none;background:transparent;color:var(--muted);
  font-size:.85rem;cursor:pointer;white-space:nowrap;border-bottom:2px solid transparent;
  transition:all .15s;font-weight:500}
.tab-btn:hover{color:var(--text)}
.tab-btn.active{color:var(--accent);border-bottom-color:var(--accent)}

/* ---- Content ---- */
.content{flex:1;padding:1.5rem;max-width:1200px;width:100%;margin:0 auto}
.tab-panel{display:none}
.tab-panel.active{display:block}

/* ---- Cards ---- */
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:1.25rem;margin-bottom:1.25rem}
.card-title{font-size:.95rem;font-weight:600;color:#fff;margin-bottom:1rem}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:.75rem;
  margin-bottom:1.25rem}
.stat-card{background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius);
  padding:1rem;text-align:center}
.stat-val{font-size:1.8rem;font-weight:700;color:#fff;line-height:1}
.stat-label{font-size:.75rem;color:var(--muted);margin-top:.3rem}

/* ---- Tables ---- */
.tbl-wrap{overflow-x:auto;border-radius:var(--radius);border:1px solid var(--border)}
table{width:100%;border-collapse:collapse;font-size:.85rem}
th{background:var(--surface2);padding:.6rem .8rem;text-align:left;color:var(--muted);
  font-weight:500;white-space:nowrap;border-bottom:1px solid var(--border)}
td{padding:.6rem .8rem;border-bottom:1px solid var(--border);vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover td{background:rgba(255,255,255,.02)}

/* ---- Badges ---- */
.badge{display:inline-block;padding:.2rem .5rem;border-radius:4px;font-size:.72rem;
  font-weight:600;text-transform:uppercase;white-space:nowrap}
.badge-idea,.badge-review{background:#222;color:#aaa;border:1px solid #444}
.badge-approved{background:#1e3a5f;color:#60a5fa}
.badge-queued{background:#1e3a5f;color:#93c5fd}
.badge-building{background:#451a03;color:#fbbf24}
.badge-launched,.badge-monitoring,.badge-scaled{background:#14532d;color:#4ade80}
.badge-killed{background:#450a0a;color:#f87171}
.badge-succeeded{background:#14532d;color:#4ade80}
.badge-running{background:#451a03;color:#fbbf24}
.badge-failed{background:#450a0a;color:#f87171}
.badge-pending,.badge-unknown{background:#222;color:#aaa;border:1px solid #444}
.badge-healthy{background:#14532d;color:#4ade80}
.badge-degraded{background:#451a03;color:#fbbf24}

/* ---- Forms ---- */
label{display:block;font-size:.8rem;color:var(--muted);margin-bottom:.25rem;margin-top:.75rem}
label:first-child{margin-top:0}
input,select,textarea{width:100%;padding:.55rem .75rem;border:1px solid var(--border);
  border-radius:7px;background:#111;color:var(--text);font-size:.9rem;font-family:inherit}
textarea{resize:vertical;min-height:80px}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--accent)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:.75rem}
.row3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:.75rem}
.form-check{display:flex;align-items:center;gap:.5rem;margin-top:.75rem}
.form-check input{width:auto}
.form-check label{margin:0}

/* ---- Buttons ---- */
.btn{display:inline-flex;align-items:center;gap:.4rem;padding:.55rem 1rem;border:none;
  border-radius:7px;font-size:.85rem;font-weight:600;cursor:pointer;transition:all .15s;
  white-space:nowrap}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btn-primary{background:var(--accent);color:#fff}
.btn-primary:hover:not(:disabled){background:var(--accent-h)}
.btn-success{background:var(--green);color:#fff}
.btn-success:hover:not(:disabled){background:#15803d}
.btn-danger{background:var(--red);color:#fff}
.btn-danger:hover:not(:disabled){background:#b91c1c}
.btn-ghost{background:transparent;color:var(--muted);border:1px solid var(--border)}
.btn-ghost:hover:not(:disabled){color:var(--text);border-color:#555}
.btn-sm{padding:.3rem .6rem;font-size:.75rem}
.btn-full{width:100%;justify-content:center;margin-top:1rem}

/* ---- Spinners ---- */
.spinner{display:inline-block;width:14px;height:14px;border:2px solid rgba(255,255,255,.25);
  border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite;flex-shrink:0}
.spinner-lg{width:28px;height:28px;border-width:3px;border-top-color:var(--accent)}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-row{display:flex;align-items:center;justify-content:center;gap:.5rem;
  padding:2rem;color:var(--muted)}

/* ---- Toast ---- */
#toastWrap{position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;
  display:flex;flex-direction:column;gap:.5rem;pointer-events:none}
.toast{padding:.65rem 1rem;border-radius:8px;font-size:.85rem;color:#fff;
  box-shadow:var(--shadow);animation:slideIn .2s ease;pointer-events:auto;max-width:320px}
.toast-ok{background:#166534}
.toast-err{background:#991b1b}
.toast-info{background:#1e3a5f}
@keyframes slideIn{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}

/* ---- Modal ---- */
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:500;
  display:flex;align-items:center;justify-content:center;padding:1rem}
.modal-overlay.hidden{display:none}
.modal-box{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:1.5rem;width:100%;max-width:500px;max-height:90vh;overflow-y:auto}
.modal-title{font-size:1rem;font-weight:600;color:#fff;margin-bottom:1rem}
.modal-actions{display:flex;gap:.5rem;justify-content:flex-end;margin-top:1.25rem}

/* ---- Misc ---- */
.empty-state{text-align:center;padding:3rem 1rem;color:var(--muted)}
.empty-state .emoji{font-size:2rem;margin-bottom:.5rem}
.section-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem}
.section-title{font-size:1rem;font-weight:600;color:#fff}
.text-muted{color:var(--muted);font-size:.8rem}
.text-green{color:#4ade80}
.text-red{color:#f87171}
.text-amber{color:#fbbf24}
.gap{gap:.5rem}
.flex{display:flex;align-items:center}
.result-block{background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius);
  padding:1rem;margin-top:1rem}
.platform-row{display:flex;align-items:flex-start;justify-content:space-between;
  gap:.75rem;padding:.6rem 0;border-bottom:1px solid var(--border)}
.platform-row:last-child{border-bottom:none}
.platform-label{font-size:.8rem;font-weight:600;color:var(--accent);min-width:90px}
.platform-msg{font-size:.82rem;color:var(--text);flex:1;white-space:pre-wrap;word-break:break-word}
.score-bar{height:6px;border-radius:3px;background:#333;margin:.25rem 0;overflow:hidden}
.score-fill{height:100%;border-radius:3px;transition:width .4s}
.score-high{background:var(--green)}.score-med{background:var(--amber)}.score-low{background:var(--red)}
.decision-badge{display:inline-block;padding:.3rem .8rem;border-radius:6px;
  font-weight:700;font-size:.85rem;margin:.25rem 0}
.decision-APPROVED{background:var(--green);color:#fff}
.decision-HOLD{background:var(--amber);color:#fff}
.decision-REJECTED{background:var(--red);color:#fff}
.detail-row{display:flex;justify-content:space-between;padding:.2rem 0;font-size:.82rem}
.detail-label{color:var(--muted)}.detail-value{color:var(--text);text-align:right;max-width:65%}
.blocking{color:#fca5a5;font-size:.82rem;margin:.15rem 0}
.reason-ok{color:#86efac;font-size:.82rem;margin:.15rem 0}
.section-sep{margin-top:.75rem;padding-top:.75rem;border-top:1px solid var(--border)}
.tag{display:inline-block;background:#222;border:1px solid #444;border-radius:4px;
  padding:.1rem .35rem;font-size:.72rem;margin:.1rem;color:#ccc}
.activity-item{display:flex;align-items:flex-start;gap:.75rem;padding:.5rem 0;
  border-bottom:1px solid var(--border);font-size:.82rem}
.activity-item:last-child{border-bottom:none}
.activity-dot{width:8px;height:8px;border-radius:50%;background:var(--accent);
  flex-shrink:0;margin-top:4px}
.activity-time{color:var(--muted);white-space:nowrap;font-size:.75rem}

/* ---- Responsive ---- */
@media(max-width:640px){
  .stats-grid{grid-template-columns:1fr 1fr}
  .row2,.row3{grid-template-columns:1fr}
  .app-header{flex-wrap:wrap;gap:.5rem}
  .api-key-wrap input{width:130px}
  .content{padding:1rem .75rem}
  .tab-btn{padding:.55rem .75rem;font-size:.8rem}
}
</style>
</head>
<body>
<div class="app">

<!-- ===== Header ===== -->
<header class="app-header">
  <div class="header-left">
    <span class="logo">&#x1F9E0;</span>
    <div>
      <h1>AI-DAN Managing Director</h1>
      <div class="sub">Command Center v{version}</div>
    </div>
  </div>
  <div class="header-right">
    <span id="healthDot" class="health-dot" title="System health"></span>
    <div class="api-key-wrap">
      <input type="password" id="apiKeyInput" placeholder="API Key (optional)" autocomplete="off"/>
      <button class="btn btn-ghost btn-sm" onclick="saveApiKey()">Save</button>
    </div>
  </div>
</header>

<!-- ===== Tab Navigation ===== -->
<nav class="tab-nav" id="tabNav">
  <button class="tab-btn active" data-tab="dashboard" onclick="switchTab('dashboard')">&#x1F4CA; Dashboard</button>
  <button class="tab-btn" data-tab="analyze" onclick="switchTab('analyze')">&#x1F4A1; Analyze Idea</button>
  <button class="tab-btn" data-tab="portfolio" onclick="switchTab('portfolio')">&#x1F4E6; Portfolio</button>
  <button class="tab-btn" data-tab="factory" onclick="switchTab('factory')">&#x1F3ED; Factory</button>
  <button class="tab-btn" data-tab="distribution" onclick="switchTab('distribution')">&#x1F4E3; Distribution</button>
  <button class="tab-btn" data-tab="revenue" onclick="switchTab('revenue')">&#x1F4B0; Revenue</button>
</nav>

<main class="content">

<!-- ===== TAB: Dashboard ===== -->
<div id="tab-dashboard" class="tab-panel active">
  <div id="statsGrid" class="stats-grid">
    <div class="stat-card"><div class="stat-val" id="st-total">—</div><div class="stat-label">Total Projects</div></div>
    <div class="stat-card"><div class="stat-val" id="st-approved">—</div><div class="stat-label">Approved</div></div>
    <div class="stat-card"><div class="stat-val" id="st-building">—</div><div class="stat-label">Building</div></div>
    <div class="stat-card"><div class="stat-val" id="st-launched">—</div><div class="stat-label">Launched</div></div>
    <div class="stat-card"><div class="stat-val" id="st-killed">—</div><div class="stat-label">Killed</div></div>
  </div>

  <div class="row2">
    <div class="card">
      <div class="card-title">&#x26A1; Quick Actions</div>
      <div style="display:flex;flex-direction:column;gap:.5rem">
        <button class="btn btn-primary" onclick="switchTab('analyze')">&#x1F4A1; New Idea</button>
        <button class="btn btn-ghost" onclick="switchTab('portfolio')">&#x1F4E6; View All Projects</button>
        <button class="btn btn-ghost" onclick="switchTab('factory')">&#x1F3ED; Factory Runs</button>
      </div>
    </div>
    <div class="card">
      <div class="card-title">&#x1F9E9; System Health
        <span id="healthLabel" style="margin-left:.5rem;font-size:.8rem;color:var(--muted)">Checking...</span>
      </div>
      <div id="healthBody" style="font-size:.85rem;color:var(--muted)">Loading...</div>
    </div>
  </div>

  <div class="card">
    <div class="section-header">
      <div class="section-title">&#x1F4DC; Recent Activity</div>
      <span class="text-muted" id="lastRefresh"></span>
    </div>
    <div id="activityFeed"><div class="loading-row"><div class="spinner spinner-lg"></div><span>Loading...</span></div></div>
  </div>
</div>

<!-- ===== TAB: Analyze Idea ===== -->
<div id="tab-analyze" class="tab-panel">
  <div class="card">
    <div class="card-title">&#x1F4A1; Analyze New Idea</div>

    <label for="idea">Your Idea *</label>
    <textarea id="idea" placeholder="Describe your idea in detail..."></textarea>

    <div class="row2">
      <div>
        <label for="problem">Problem</label>
        <input id="problem" placeholder="What problem does it solve?"/>
      </div>
      <div>
        <label for="target_user">Target User</label>
        <input id="target_user" placeholder="Who is this for?"/>
      </div>
    </div>

    <div class="row2">
      <div>
        <label for="monetization_model">Monetization Model</label>
        <select id="monetization_model">
          <option value="">Select...</option>
          <option value="subscription">Subscription/SaaS</option>
          <option value="freemium">Freemium</option>
          <option value="marketplace">Marketplace</option>
          <option value="one-time">One-time Purchase</option>
          <option value="api">API Usage-based</option>
          <option value="ads">Advertising</option>
          <option value="affiliate">Affiliate</option>
        </select>
      </div>
      <div>
        <label for="competition_level">Competition Level</label>
        <select id="competition_level">
          <option value="">Select...</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
      </div>
    </div>

    <div class="row2">
      <div>
        <label for="difficulty">Build Difficulty</label>
        <select id="difficulty">
          <option value="">Select...</option>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </select>
      </div>
      <div>
        <label for="time_to_revenue">Time to Revenue</label>
        <select id="time_to_revenue">
          <option value="">Select...</option>
          <option value="days">Days</option>
          <option value="weeks">Weeks</option>
          <option value="months">Months</option>
        </select>
      </div>
    </div>

    <label for="differentiation">Differentiation</label>
    <input id="differentiation" placeholder="What makes this unique?"/>

    <button class="btn btn-primary btn-full" id="analyzeBtn" onclick="runAnalyze()">&#x1F50D; Analyze Idea</button>
  </div>

  <div id="loading" style="display:none" class="loading-row"><div class="spinner spinner-lg"></div><span>Running full pipeline analysis...</span></div>
  <div id="errorBox" style="display:none;background:#2d1111;border:1px solid var(--red);border-radius:var(--radius);padding:1rem;color:#fca5a5;margin-bottom:1rem"></div>

  <div id="analyzeResult" style="display:none">
    <div class="card" id="analyzeResultBody"></div>
    <div style="display:flex;gap:.75rem;flex-wrap:wrap">
      <button class="btn btn-success" id="approveBuildBtn" onclick="approveAndBuild()" style="display:none">&#x2705; Approve &amp; Build</button>
      <button class="btn btn-ghost" id="saveDraftBtn" onclick="saveAsDraft()" style="display:none">&#x1F4BE; Save as Draft</button>
    </div>
  </div>
</div>

<!-- ===== TAB: Portfolio ===== -->
<div id="tab-portfolio" class="tab-panel">
  <div class="section-header">
    <div class="section-title">&#x1F4E6; Projects</div>
    <button class="btn btn-primary btn-sm" onclick="showAddProjectModal()">&#x2795; Add Project</button>
  </div>

  <div id="portfolioLoading" class="loading-row"><div class="spinner spinner-lg"></div><span>Loading projects...</span></div>
  <div id="portfolioEmpty" style="display:none" class="empty-state">
    <div class="emoji">&#x1F4E6;</div>
    <p>No projects yet. <a href="#" onclick="switchTab('analyze');return false">Start by analyzing an idea &rarr;</a></p>
  </div>
  <div id="portfolioTable" style="display:none" class="tbl-wrap">
    <table>
      <thead>
        <tr>
          <th>Name</th><th>Status</th><th>Deploy URL</th><th>Created</th><th>Actions</th>
        </tr>
      </thead>
      <tbody id="portfolioBody"></tbody>
    </table>
  </div>
</div>

<!-- ===== TAB: Factory ===== -->
<div id="tab-factory" class="tab-panel">
  <div class="row2" style="align-items:start">
    <div>
      <div class="section-header">
        <div class="section-title">&#x1F527; Trigger Build</div>
      </div>
      <div class="card">
        <label for="fProjectId">Project</label>
        <select id="fProjectId"><option value="">Select project...</option></select>
        <label for="fTemplate">Template</label>
        <select id="fTemplate">
          <option value="saas-template">SaaS App</option>
          <option value="landing-page">Landing Page</option>
        </select>
        <div class="form-check">
          <input type="checkbox" id="fDryRun" checked/>
          <label for="fDryRun">Dry Run (safe preview)</label>
        </div>
        <button class="btn btn-primary btn-full" id="triggerBuildBtn" onclick="triggerBuild()">&#x1F680; Launch Build</button>
      </div>
    </div>
    <div>
      <div class="section-header">
        <div class="section-title">&#x1F4CB; Factory Runs</div>
        <button class="btn btn-ghost btn-sm" onclick="loadFactoryRuns()">&#x21BB; Refresh</button>
      </div>
      <div id="factoryLoading" class="loading-row"><div class="spinner spinner-lg"></div><span>Loading runs...</span></div>
      <div id="factoryEmpty" style="display:none" class="empty-state">
        <div class="emoji">&#x1F3ED;</div><p>No factory runs yet.</p>
      </div>
      <div id="factoryTable" style="display:none" class="tbl-wrap">
        <table>
          <thead><tr><th>Project</th><th>Status</th><th>Repo</th><th>Deploy</th><th>Created</th><th>Error</th></tr></thead>
          <tbody id="factoryBody"></tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- ===== TAB: Distribution ===== -->
<div id="tab-distribution" class="tab-panel">
  <div class="row2" style="align-items:start">
    <div class="card">
      <div class="card-title">&#x1F4E3; Generate Share Messages</div>
      <label for="distTitle">Product Title *</label>
      <input id="distTitle" placeholder="e.g. QuickInvoice"/>
      <label for="distUrl">URL *</label>
      <input id="distUrl" placeholder="https://yourapp.vercel.app"/>
      <label for="distDesc">Description *</label>
      <textarea id="distDesc" style="min-height:60px" placeholder="One or two sentences about the product..."></textarea>
      <label for="distUser">Target User *</label>
      <input id="distUser" placeholder="e.g. freelance developers"/>
      <label for="distCta">CTA</label>
      <input id="distCta" placeholder="Try it free" value="Try it free"/>
      <button class="btn btn-primary btn-full" id="distBtn" onclick="generateDistribution()">&#x2728; Generate Messages</button>
    </div>
    <div>
      <div id="distLoading" style="display:none" class="loading-row"><div class="spinner spinner-lg"></div><span>Generating...</span></div>
      <div id="distResults" style="display:none" class="card">
        <div class="card-title">&#x1F4CB; Platform Messages</div>
        <div id="distPlatforms"></div>
      </div>
      <div id="distEmpty" style="display:none" class="empty-state">
        <div class="emoji">&#x1F4E3;</div><p>Fill the form and click Generate.</p>
      </div>
    </div>
  </div>
</div>

<!-- ===== TAB: Revenue ===== -->
<div id="tab-revenue" class="tab-panel">
  <div class="row2" style="align-items:start">
    <div class="card">
      <div class="card-title">&#x1F4CA; Revenue Report</div>
      <label for="revProjectId">Project</label>
      <select id="revProjectId"><option value="">Select project...</option></select>
      <button class="btn btn-primary btn-full" id="revReportBtn" onclick="getRevenueReport()">&#x1F4C8; Get Report</button>
      <div id="revReportLoading" style="display:none" class="loading-row"><div class="spinner"></div><span>Fetching...</span></div>
      <div id="revReportResult" style="display:none" class="result-block"></div>
    </div>
    <div class="card">
      <div class="card-title">&#x1F4B3; Business Output</div>
      <label for="bizProjectId">Project</label>
      <select id="bizProjectId"><option value="">Select project...</option></select>
      <label for="bizPaymentLink">Payment Link (optional)</label>
      <input id="bizPaymentLink" placeholder="https://stripe.com/..."/>
      <button class="btn btn-primary btn-full" id="bizOutputBtn" onclick="generateBusinessOutput()">&#x1F4C4; Generate Output</button>
      <div id="bizLoading" style="display:none" class="loading-row"><div class="spinner"></div><span>Generating...</span></div>
      <div id="bizResult" style="display:none" class="result-block"></div>
    </div>
  </div>
</div>

</main>
</div><!-- .app -->

<!-- ===== Toast Container ===== -->
<div id="toastWrap"></div>

<!-- ===== Modal ===== -->
<div id="modalOverlay" class="modal-overlay hidden" onclick="closeModalOnBg(event)">
  <div class="modal-box">
    <div class="modal-title" id="modalTitle"></div>
    <div id="modalBody"></div>
    <div class="modal-actions" id="modalActions"></div>
  </div>
</div>

<script>
// ============================================================
// Core utilities
// ============================================================
var _lastAnalysis = null;

function getApiKey(){return localStorage.getItem("aidan_api_key")||"";}
function saveApiKey(){
  var v=document.getElementById("apiKeyInput").value.trim();
  if(v){localStorage.setItem("aidan_api_key",v);showToast("API key saved","ok");}
  else{localStorage.removeItem("aidan_api_key");showToast("API key cleared","info");}
}

// Load saved key on startup
(function(){
  var k=getApiKey();
  if(k) document.getElementById("apiKeyInput").value=k;
})();

function apiCall(method,path,body){
  var opts={method:method,headers:{"Content-Type":"application/json"}};
  var k=getApiKey();
  if(k) opts.headers["X-API-Key"]=k;
  if(body!==undefined) opts.body=JSON.stringify(body);
  return fetch(path,opts).then(function(r){
    if(!r.ok) return r.json().then(function(e){throw new Error(e.detail||r.statusText);});
    return r.json();
  });
}

// ============================================================
// Toast
// ============================================================
function showToast(msg,type){
  type=type||"info";
  var wrap=document.getElementById("toastWrap");
  var t=document.createElement("div");
  t.className="toast toast-"+(type==="ok"?"ok":type==="err"?"err":"info");
  t.textContent=msg;
  wrap.appendChild(t);
  setTimeout(function(){if(t.parentNode)t.parentNode.removeChild(t);},3500);
}

// ============================================================
// Modal
// ============================================================
function showModal(title,bodyHtml,actions){
  document.getElementById("modalTitle").textContent=title;
  document.getElementById("modalBody").innerHTML=bodyHtml;
  var a=document.getElementById("modalActions");
  a.innerHTML="";
  if(actions){actions.forEach(function(ac){
    var b=document.createElement("button");
    b.className="btn "+(ac.cls||"btn-ghost");
    b.textContent=ac.label;
    b.onclick=function(){closeModal();if(ac.fn)ac.fn();};
    a.appendChild(b);
  });}
  var cancel=document.createElement("button");
  cancel.className="btn btn-ghost";
  cancel.textContent="Cancel";
  cancel.onclick=closeModal;
  a.appendChild(cancel);
  document.getElementById("modalOverlay").classList.remove("hidden");
}
function closeModal(){document.getElementById("modalOverlay").classList.add("hidden");}
function closeModalOnBg(e){if(e.target===document.getElementById("modalOverlay"))closeModal();}

// ============================================================
// Tab switching
// ============================================================
function switchTab(name){
  document.querySelectorAll(".tab-btn").forEach(function(b){
    b.classList.toggle("active",b.dataset.tab===name);
  });
  document.querySelectorAll(".tab-panel").forEach(function(p){
    p.classList.toggle("active",p.id==="tab-"+name);
  });
  if(name==="dashboard") loadDashboard();
  else if(name==="portfolio") loadPortfolio();
  else if(name==="factory"){loadFactoryRuns();populateProjectDropdowns();}
  else if(name==="revenue") populateProjectDropdowns();
}

// ============================================================
// Helpers
// ============================================================
function esc(s){if(!s)return"";var d=document.createElement("div");
  d.appendChild(document.createTextNode(String(s)));return d.innerHTML;}
var escapeHtml=esc;

function fmtDate(iso){if(!iso)return"—";
  try{return new Date(iso).toLocaleString(undefined,{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"});}
  catch(e){return iso;}}

function badge(st){st=(st||"unknown").toLowerCase();
  return'<span class="badge badge-'+st+'">'+esc(st)+'</span>';}

function linkOrDash(url,label){
  if(!url||url.startsWith("dry-run://"))return'<span class="text-muted">'+(url?esc(url):"—")+'</span>';
  return'<a href="'+esc(url)+'" target="_blank" rel="noopener">'+(label||esc(url))+'</a>';}

// ============================================================
// Dashboard Tab
// ============================================================
var _autoRefreshTimer=null;

function loadDashboard(){
  loadHealthStatus();
  loadPortfolioStats();
  cancelAutoRefresh();
  _autoRefreshTimer=setTimeout(function(){
    if(document.querySelector(".tab-btn.active").dataset.tab==="dashboard") loadDashboard();
  },30000);
}

function cancelAutoRefresh(){if(_autoRefreshTimer)clearTimeout(_autoRefreshTimer);}

function loadHealthStatus(){
  var dot=document.getElementById("healthDot");
  var lbl=document.getElementById("healthLabel");
  var body=document.getElementById("healthBody");
  apiCall("GET","/health").then(function(d){
    dot.className="health-dot ok";
    lbl.textContent="Healthy";
    body.innerHTML='<span class="text-green">&#x2705; All systems operational</span>';
  }).catch(function(){
    dot.className="health-dot err";
    lbl.textContent="Unavailable";
    body.innerHTML='<span class="text-red">&#x274C; Health check failed</span>';
  });
}

function loadPortfolioStats(){
  var feed=document.getElementById("activityFeed");
  var now=new Date().toLocaleTimeString();
  document.getElementById("lastRefresh").textContent="Updated "+now;
  apiCall("GET","/portfolio/projects").then(function(projects){
    var counts={total:projects.length,approved:0,building:0,launched:0,killed:0};
    var recent=[];
    projects.forEach(function(p){
      var s=p.status||"";
      if(s==="approved"||s==="queued") counts.approved++;
      if(s==="building") counts.building++;
      if(s==="launched"||s==="monitoring"||s==="scaled") counts.launched++;
      if(s==="killed") counts.killed++;
      recent.push({name:p.name,status:p.status,time:p.updated_at||p.created_at});
    });
    document.getElementById("st-total").textContent=counts.total;
    document.getElementById("st-approved").textContent=counts.approved;
    document.getElementById("st-building").textContent=counts.building;
    document.getElementById("st-launched").textContent=counts.launched;
    document.getElementById("st-killed").textContent=counts.killed;

    recent.sort(function(a,b){return(b.time||"").localeCompare(a.time||"");});
    recent=recent.slice(0,5);
    if(!recent.length){
      feed.innerHTML='<div class="empty-state"><div class="emoji">&#x1F4CB;</div><p>No activity yet. <a href="#" onclick="switchTab(\'analyze\');return false">Add your first idea &rarr;</a></p></div>';
      return;
    }
    feed.innerHTML=recent.map(function(r){
      return'<div class="activity-item"><div class="activity-dot"></div>'+
        '<div style="flex:1"><strong>'+esc(r.name)+'</strong> &mdash; '+badge(r.status)+'</div>'+
        '<div class="activity-time">'+fmtDate(r.time)+'</div></div>';
    }).join("");
  }).catch(function(e){
    feed.innerHTML='<div class="empty-state"><span class="text-red">Failed to load: '+esc(e.message)+'</span></div>';
  });
}

// ============================================================
// Portfolio Tab
// ============================================================
function loadPortfolio(){
  document.getElementById("portfolioLoading").style.display="flex";
  document.getElementById("portfolioTable").style.display="none";
  document.getElementById("portfolioEmpty").style.display="none";
  apiCall("GET","/portfolio/projects").then(function(projects){
    document.getElementById("portfolioLoading").style.display="none";
    if(!projects||!projects.length){
      document.getElementById("portfolioEmpty").style.display="block";return;
    }
    document.getElementById("portfolioTable").style.display="block";
    var tbody=document.getElementById("portfolioBody");
    tbody.innerHTML=projects.map(function(p){
      var meta=p.metadata||{};
      var deployUrl=meta.deploy_url||meta.deployment_url||"";
      var repoUrl=meta.repo_url||"";
      var actions=[];
      actions.push('<button class="btn btn-ghost btn-sm" title="Check Health" onclick="checkHealth('+JSON.stringify(p.project_id)+','+JSON.stringify(deployUrl)+')">&#x1F50D;</button>');
      var s=p.status||"";
      if(s==="idea"||s==="review"){
        actions.push('<button class="btn btn-success btn-sm" onclick="transitionProject('+JSON.stringify(p.project_id)+',' +JSON.stringify("approved")+')">&#x2705; Approve</button>');
        actions.push('<button class="btn btn-danger btn-sm" onclick="transitionProject('+JSON.stringify(p.project_id)+','+JSON.stringify("killed")+')">&#x274C; Reject</button>');
      }
      if(s==="approved"||s==="queued"){
        actions.push('<button class="btn btn-primary btn-sm" onclick="buildProject('+JSON.stringify(p.project_id)+')">&#x1F680; Build</button>');
      }
      actions.push('<button class="btn btn-ghost btn-sm" onclick="prefillDistribution('+JSON.stringify(p)+')">&#x1F4E3;</button>');
      if(repoUrl&&!repoUrl.startsWith("dry-run://"))
        actions.push('<a class="btn btn-ghost btn-sm" href="'+esc(repoUrl)+'" target="_blank" rel="noopener">&#x1F517; Repo</a>');
      if(deployUrl&&!deployUrl.startsWith("dry-run://"))
        actions.push('<a class="btn btn-ghost btn-sm" href="'+esc(deployUrl)+'" target="_blank" rel="noopener">&#x1F310; Deploy</a>');

      return'<tr>'+
        '<td><strong>'+esc(p.name)+'</strong><br/><span class="text-muted">'+esc(p.project_id)+'</span></td>'+
        '<td>'+badge(p.status)+'</td>'+
        '<td>'+linkOrDash(deployUrl,"&#x1F517; Open")+'</td>'+
        '<td class="text-muted">'+fmtDate(p.created_at)+'</td>'+
        '<td><div style="display:flex;gap:.3rem;flex-wrap:wrap">'+actions.join("")+'</div></td>'+
        '</tr>';
    }).join("");
  }).catch(function(e){
    document.getElementById("portfolioLoading").style.display="none";
    showToast("Failed to load projects: "+e.message,"err");
  });
}

function showAddProjectModal(){
  showModal("Add Project",
    '<label>Name *</label><input id="mpName" placeholder="My awesome project"/>' +
    '<label>Description *</label><textarea id="mpDesc" style="min-height:60px" placeholder="What does it do?"></textarea>',
    [{label:"Create",cls:"btn-primary",fn:function(){
      var name=document.getElementById("mpName").value.trim();
      var desc=document.getElementById("mpDesc").value.trim();
      if(!name||!desc){showToast("Name and description required","err");return;}
      apiCall("POST","/portfolio/projects",{name:name,description:desc}).then(function(p){
        showToast("Project '"+p.name+"' created","ok");
        loadPortfolio();
      }).catch(function(e){showToast("Error: "+e.message,"err");});
    }}]
  );
}

function transitionProject(projectId,newState){
  showModal("Confirm",
    "Transition project <strong>"+esc(projectId)+"</strong> to <strong>"+esc(newState)+"</strong>?",
    [{label:"Confirm",cls:newState==="killed"?"btn-danger":"btn-success",fn:function(){
      apiCall("POST","/portfolio/projects/"+encodeURIComponent(projectId)+"/transition",
        {new_state:newState}).then(function(){
          showToast("Project updated to "+newState,"ok");loadPortfolio();
        }).catch(function(e){showToast("Error: "+e.message,"err");});
    }}]
  );
}

function buildProject(projectId){
  showModal("Confirm Build",
    "<p>Trigger a factory build for project <strong>"+esc(projectId)+"</strong>?</p>" +
    '<div class="form-check" style="margin-top:.75rem"><input type="checkbox" id="bfDryRun" checked/><label for="bfDryRun">Dry Run</label></div>',
    [{label:"Launch Build",cls:"btn-primary",fn:function(){
      var dr=document.getElementById("bfDryRun")&&document.getElementById("bfDryRun").checked;
      _doTriggerBuild(projectId,dr);
    }}]
  );
}

function checkHealth(projectId,deployUrl){
  if(!deployUrl){showToast("No deploy URL for this project","err");return;}
  apiCall("POST","/factory/verify-deployment",{project_id:projectId,deploy_url:deployUrl}).then(function(r){
    showModal("Deployment Health: "+projectId,
      '<p>Status: '+badge(r.status)+'</p>'+
      '<p style="margin-top:.5rem;font-size:.85rem">Response time: '+(r.response_time_ms||0).toFixed(0)+'ms</p>'+
      (r.issues&&r.issues.length?'<p style="margin-top:.5rem" class="text-red">Issues:<br>'+r.issues.map(esc).join("<br>")+'</p>':
        '<p style="margin-top:.5rem" class="text-green">No issues detected</p>'),
      []
    );
  }).catch(function(e){showToast("Verification error: "+e.message,"err");});
}

function prefillDistribution(p){
  switchTab("distribution");
  document.getElementById("distTitle").value=p.name||"";
  var meta=p.metadata||{};
  document.getElementById("distUrl").value=(meta.deploy_url||meta.deployment_url)||"";
  document.getElementById("distDesc").value=p.description||"";
}

// ============================================================
// Factory Tab
// ============================================================
function loadFactoryRuns(){
  document.getElementById("factoryLoading").style.display="flex";
  document.getElementById("factoryTable").style.display="none";
  document.getElementById("factoryEmpty").style.display="none";
  apiCall("GET","/factory/runs").then(function(runs){
    document.getElementById("factoryLoading").style.display="none";
    if(!runs||!runs.length){document.getElementById("factoryEmpty").style.display="block";return;}
    document.getElementById("factoryTable").style.display="block";
    document.getElementById("factoryBody").innerHTML=runs.map(function(r){
      return'<tr>'+
        '<td>'+esc(r.project_id)+'</td>'+
        '<td>'+badge(r.status)+'</td>'+
        '<td>'+linkOrDash(r.repo_url,"Repo")+'</td>'+
        '<td>'+linkOrDash(r.deploy_url,"Deploy")+'</td>'+
        '<td class="text-muted">'+fmtDate(r.created_at)+'</td>'+
        '<td class="text-red" style="font-size:.78rem">'+esc(r.error||"")+'</td>'+
        '</tr>';
    }).join("");
  }).catch(function(e){
    document.getElementById("factoryLoading").style.display="none";
    showToast("Failed to load runs: "+e.message,"err");
  });
}

function populateProjectDropdowns(){
  apiCall("GET","/portfolio/projects").then(function(projects){
    var selectors=["fProjectId","revProjectId","bizProjectId"];
    selectors.forEach(function(id){
      var el=document.getElementById(id);
      if(!el) return;
      var current=el.value;
      el.innerHTML='<option value="">Select project...</option>';
      projects.forEach(function(p){
        var o=document.createElement("option");
        o.value=p.project_id;
        o.textContent=p.name+" ("+p.status+")";
        el.appendChild(o);
      });
      if(current) el.value=current;
    });
  }).catch(function(){});
}

function triggerBuild(){
  var projectId=document.getElementById("fProjectId").value;
  if(!projectId){showToast("Please select a project","err");return;}
  var dryRun=document.getElementById("fDryRun").checked;
  _doTriggerBuild(projectId,dryRun);
}

function _doTriggerBuild(projectId,dryRun){
  var btn=document.getElementById("triggerBuildBtn");
  if(btn){btn.disabled=true;btn.innerHTML='<div class="spinner"></div> Triggering...';}
  apiCall("POST","/factory/ideas/execute",{message:"Build project "+projectId,project_id:projectId,dry_run:dryRun}).then(function(r){
    showToast("Build "+(r.status||"triggered")+" for "+projectId+(dryRun?" (dry run)":""),"ok");
    loadFactoryRuns();
  }).catch(function(e){
    showToast("Build error: "+e.message,"err");
  }).finally(function(){
    if(btn){btn.disabled=false;btn.innerHTML='&#x1F680; Launch Build';}
  });
}

// ============================================================
// Analyze Tab
// ============================================================
function runAnalyze(){
  var btn=document.getElementById("analyzeBtn");
  var loading=document.getElementById("loading");
  var result=document.getElementById("analyzeResult");
  var errBox=document.getElementById("errorBox");
  var idea=document.getElementById("idea").value.trim();

  if(!idea){errBox.textContent="Please enter an idea.";errBox.style.display="block";return;}
  btn.disabled=true;btn.innerHTML='<div class="spinner"></div> Analyzing...';
  loading.style.display="flex";result.style.display="none";errBox.style.display="none";
  document.getElementById("approveBuildBtn").style.display="none";
  document.getElementById("saveDraftBtn").style.display="none";

  var body={
    idea:idea,
    problem:document.getElementById("problem").value.trim(),
    target_user:document.getElementById("target_user").value.trim(),
    monetization_model:document.getElementById("monetization_model").value,
    competition_level:document.getElementById("competition_level").value,
    difficulty:document.getElementById("difficulty").value,
    time_to_revenue:document.getElementById("time_to_revenue").value,
    differentiation:document.getElementById("differentiation").value.trim()
  };

  apiCall("POST","/api/analyze/",body).then(function(d){
    _lastAnalysis=d;
    renderAnalyzeResult(d);
    result.style.display="block";
    document.getElementById("approveBuildBtn").style.display="inline-flex";
    document.getElementById("saveDraftBtn").style.display="inline-flex";
  }).catch(function(e){
    errBox.textContent="Error: "+e.message;errBox.style.display="block";
  }).finally(function(){
    btn.disabled=false;btn.innerHTML='&#x1F50D; Analyze Idea';
    loading.style.display="none";
  });
}

function renderAnalyzeResult(d){
  var r=document.getElementById("analyzeResultBody");
  var sc=d.total_score||0;
  var pct=(sc/10*100).toFixed(0);
  var cls=sc>=8?"high":sc>=6?"med":"low";
  var dec=d.final_decision||"UNKNOWN";
  var h='<div style="display:flex;justify-content:space-between;align-items:center">';
  h+='<span class="decision-badge decision-'+dec+'">'+dec+'</span>';
  h+='<span style="font-size:1.4rem;font-weight:700">'+sc.toFixed(1)+'<span style="font-size:.85rem;color:var(--muted)">/10</span></span></div>';
  h+='<div class="score-bar"><div class="score-fill score-'+cls+'" style="width:'+pct+'%"></div></div>';
  h+='<p style="font-size:.82rem;color:var(--muted);margin-top:.25rem">'+esc(d.score_decision_reason||d.next_step||"")+'</p>';
  if(d.validation_blocking&&d.validation_blocking.length){
    h+='<div class="section-sep"><strong style="font-size:.85rem">&#x1F6D1; Blocking</strong>';
    d.validation_blocking.forEach(function(b){h+='<p class="blocking">&bull; '+esc(b)+'</p>';});
    h+='</div>';
  }
  if(d.validation_reasons&&d.validation_reasons.length){
    h+='<div class="section-sep"><strong style="font-size:.85rem">&#x2705; Validation</strong>';
    d.validation_reasons.forEach(function(v){h+='<p class="reason-ok">&bull; '+esc(v)+'</p>';});
    h+='</div>';
  }
  if(d.score_dimensions&&d.score_dimensions.length){
    h+='<div class="section-sep"><strong style="font-size:.85rem">&#x1F4CA; Score Breakdown</strong>';
    d.score_dimensions.forEach(function(dim){
      var dp=(dim.score/2*100).toFixed(0);
      var dc=dim.score>=1.5?"high":dim.score>=1?"med":"low";
      h+='<div class="detail-row"><span class="detail-label">'+esc(dim.name)+'</span><span class="detail-value">'+dim.score.toFixed(1)+'/2</span></div>';
      h+='<div class="score-bar"><div class="score-fill score-'+dc+'" style="width:'+dp+'%"></div></div>';
      if(dim.reason) h+='<p style="font-size:.78rem;color:#666;margin-bottom:.25rem">'+esc(dim.reason)+'</p>';
    });
    h+='</div>';
  }
  var o=d.offer||{};
  if(o.decision==="generated"){
    h+='<div class="section-sep"><strong style="font-size:.85rem">&#x1F4B0; Offer</strong>';
    h+=detailRow("Pricing",o.pricing)+detailRow("Model",o.pricing_model)+detailRow("Delivery",o.delivery_method)+detailRow("CTA",o.cta);
    h+='</div>';
  }
  var di=d.distribution||{};
  if(di.decision==="generated"){
    h+='<div class="section-sep"><strong style="font-size:.85rem">&#x1F680; Distribution</strong>';
    h+=detailRow("Channel",di.primary_channel)+detailRow("Acquisition",di.acquisition_method)+detailRow("First 10 users",di.first_10_users_plan);
    h+='</div>';
  }
  h+='<div class="section-sep"><strong style="font-size:.85rem">&#x27A1; Next Step</strong><p style="font-size:.85rem;margin-top:.3rem">'+esc(d.next_step||"Awaiting analysis.")+'</p></div>';
  r.innerHTML=h;
}

function detailRow(l,v){if(!v)return"";
  return'<div class="detail-row"><span class="detail-label">'+esc(l)+'</span><span class="detail-value">'+esc(v)+'</span></div>';}

function approveAndBuild(){
  if(!_lastAnalysis){showToast("Run analysis first","err");return;}
  var idea=document.getElementById("idea").value.trim();
  var name=idea.length>60?idea.substring(0,40)+"...":idea.substring(0,60);
  var btn=document.getElementById("approveBuildBtn");
  btn.disabled=true;btn.innerHTML='<div class="spinner"></div> Creating...';
  apiCall("POST","/portfolio/projects",{
    name:name,
    description:idea,
    metadata:{analysis:_lastAnalysis}
  }).then(function(p){
    showToast("Project '"+p.name+"' created! ID: "+p.project_id,"ok");
    return apiCall("POST","/portfolio/projects/"+encodeURIComponent(p.project_id)+"/transition",{new_state:"approved"});
  }).then(function(){
    showToast("Project approved and queued for build","ok");
  }).catch(function(e){
    showToast("Error: "+e.message,"err");
  }).finally(function(){
    btn.disabled=false;btn.innerHTML='&#x2705; Approve &amp; Build';
  });
}

function saveAsDraft(){
  if(!_lastAnalysis){showToast("Run analysis first","err");return;}
  var idea=document.getElementById("idea").value.trim();
  var name=idea.length>60?idea.substring(0,40)+"...":idea.substring(0,60);
  var btn=document.getElementById("saveDraftBtn");
  btn.disabled=true;
  apiCall("POST","/portfolio/projects",{
    name:name,
    description:idea,
    metadata:{analysis:_lastAnalysis,draft:true}
  }).then(function(p){
    showToast("Draft saved: "+p.project_id,"ok");
  }).catch(function(e){
    showToast("Error: "+e.message,"err");
  }).finally(function(){
    btn.disabled=false;
  });
}

// ============================================================
// Distribution Tab
// ============================================================
var PLATFORM_EMOJIS={twitter:"&#x1F426;",linkedin:"&#x1F4BC;",whatsapp:"&#x1F4AC;",email:"&#x2709;&#xFE0F;",sms:"&#x1F4F1;",reddit:"&#x1F916;",product_hunt:"&#x1F98A;"};

function generateDistribution(){
  var title=document.getElementById("distTitle").value.trim();
  var url=document.getElementById("distUrl").value.trim();
  var desc=document.getElementById("distDesc").value.trim();
  var user=document.getElementById("distUser").value.trim();
  var cta=document.getElementById("distCta").value.trim()||"Try it free";
  if(!title||!url||!desc||!user){showToast("Please fill all required fields","err");return;}

  var btn=document.getElementById("distBtn");
  btn.disabled=true;btn.innerHTML='<div class="spinner"></div> Generating...';
  document.getElementById("distLoading").style.display="flex";
  document.getElementById("distResults").style.display="none";
  document.getElementById("distEmpty").style.display="none";

  apiCall("POST","/api/distribution/share-messages",{title:title,url:url,description:desc,target_user:user,cta:cta}).then(function(d){
    document.getElementById("distLoading").style.display="none";
    document.getElementById("distResults").style.display="block";
    var platforms=document.getElementById("distPlatforms");
    var keys=Object.keys(d).filter(function(k){return typeof d[k]==="string"&&k!=="title"&&k!=="url";});
    platforms.innerHTML=keys.map(function(k){
      var em=PLATFORM_EMOJIS[k]||"&#x1F4E2;";
      return'<div class="platform-row">'+
        '<div><div class="platform-label">'+em+' '+esc(k)+'</div></div>'+
        '<div class="platform-msg" id="pmsg-'+esc(k)+'">'+esc(d[k])+'</div>'+
        '<button class="btn btn-ghost btn-sm" onclick="copyPlatform('+JSON.stringify(k)+','+JSON.stringify(d[k])+')">&#x1F4CB;</button>'+
        '</div>';
    }).join("");
  }).catch(function(e){
    document.getElementById("distLoading").style.display="none";
    document.getElementById("distEmpty").style.display="block";
    showToast("Error: "+e.message,"err");
  }).finally(function(){
    btn.disabled=false;btn.innerHTML='&#x2728; Generate Messages';
  });
}

function copyPlatform(platform,text){
  if(navigator.clipboard){navigator.clipboard.writeText(text).then(function(){showToast("Copied "+platform+" message","ok");});}
  else{var ta=document.createElement("textarea");ta.value=text;document.body.appendChild(ta);ta.select();document.execCommand("copy");document.body.removeChild(ta);showToast("Copied","ok");}
}

// ============================================================
// Revenue Tab
// ============================================================
function getRevenueReport(){
  var pid=document.getElementById("revProjectId").value;
  if(!pid){showToast("Please select a project","err");return;}
  var btn=document.getElementById("revReportBtn");
  btn.disabled=true;btn.innerHTML='<div class="spinner"></div> Fetching...';
  document.getElementById("revReportLoading").style.display="flex";
  document.getElementById("revReportResult").style.display="none";

  apiCall("GET","/revenue/projects/"+encodeURIComponent(pid)+"/learning-report").then(function(d){
    var el=document.getElementById("revReportResult");
    el.innerHTML='<div>'+
      detailRow("Decision",d.decision)+
      detailRow("Confidence",d.confidence)+
      (d.recommendations&&d.recommendations.length?'<p style="margin-top:.5rem;font-size:.82rem;color:var(--muted)">Recommendations:</p>'+
        d.recommendations.map(function(r){return'<p style="font-size:.82rem">&bull; '+esc(r)+'</p>';}).join(""):"")+'</div>';
    el.style.display="block";
  }).catch(function(e){
    showToast("Error: "+e.message,"err");
  }).finally(function(){
    btn.disabled=false;btn.innerHTML='&#x1F4C8; Get Report';
    document.getElementById("revReportLoading").style.display="none";
  });
}

function generateBusinessOutput(){
  var pid=document.getElementById("bizProjectId").value;
  if(!pid){showToast("Please select a project","err");return;}
  var paymentLink=document.getElementById("bizPaymentLink").value.trim();
  var btn=document.getElementById("bizOutputBtn");
  btn.disabled=true;btn.innerHTML='<div class="spinner"></div> Generating...';
  document.getElementById("bizLoading").style.display="flex";
  document.getElementById("bizResult").style.display="none";

  apiCall("POST","/revenue/projects/"+encodeURIComponent(pid)+"/business-output",{payment_link:paymentLink||null}).then(function(d){
    var el=document.getElementById("bizResult");
    el.innerHTML='<div>'+
      detailRow("Payment Readiness",d.payment_readiness)+
      detailRow("Conversion Status",d.conversion_status)+
      (d.next_steps&&d.next_steps.length?'<p style="margin-top:.5rem;font-size:.82rem;color:var(--muted)">Next Steps:</p>'+
        d.next_steps.map(function(s){return'<p style="font-size:.82rem">&bull; '+esc(s)+'</p>';}).join(""):"")+'</div>';
    el.style.display="block";
  }).catch(function(e){
    showToast("Error: "+e.message,"err");
  }).finally(function(){
    btn.disabled=false;btn.innerHTML='&#x1F4C4; Generate Output';
    document.getElementById("bizLoading").style.display="none";
  });
}

// ============================================================
// Init
// ============================================================
document.addEventListener("DOMContentLoaded",function(){
  loadDashboard();
});
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def root_ui() -> HTMLResponse:
    """Serve the root idea-analysis UI."""
    html = _ROOT_HTML.replace("{version}", _VERSION)
    return HTMLResponse(content=html)
