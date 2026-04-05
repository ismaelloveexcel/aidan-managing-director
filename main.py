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
# Root UI – embedded HTML for idea analysis
# ---------------------------------------------------------------------------
_ROOT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>AI-DAN Command Center</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
background:#0a0a0a;color:#e0e0e0;min-height:100vh}
/* -- Layout -- */
.app-header{background:#111;border-bottom:1px solid #222;padding:.8rem 1.5rem;
display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}
.app-header h1{font-size:1.2rem;color:#fff}
.app-header .version{font-size:.75rem;color:#555;margin-left:.5rem}
.health-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-left:.5rem;
background:#555;vertical-align:middle}
.health-dot.healthy{background:#16a34a}
.health-dot.degraded{background:#d97706}
.health-dot.failed{background:#dc2626}
/* -- Tabs -- */
.tab-bar{display:flex;gap:0;background:#111;border-bottom:1px solid #222;
overflow-x:auto;-webkit-overflow-scrolling:touch}
.tab-btn{flex-shrink:0;padding:.75rem 1.1rem;background:transparent;border:none;
color:#888;cursor:pointer;font-size:.85rem;font-weight:500;border-bottom:2px solid transparent;
transition:all .2s;white-space:nowrap}
.tab-btn:hover{color:#e0e0e0;background:#1a1a1a}
.tab-btn.active{color:#5b6ef7;border-bottom-color:#5b6ef7;background:#0f0f1a}
.tab-content{display:none;padding:1.5rem;max-width:1100px;margin:0 auto}
.tab-content.active{display:block}
/* -- Cards -- */
.card{background:#111828;border:1px solid #2a2a3a;border-radius:10px;padding:1.2rem;margin-bottom:1.2rem}
.card-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem}
.card-title{font-size:.95rem;font-weight:600;color:#ccc}
/* -- Stats -- */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:.8rem;margin-bottom:1.2rem}
.stat-card{background:#111828;border:1px solid #2a2a3a;border-radius:10px;padding:1rem;text-align:center}
.stat-value{font-size:2rem;font-weight:700;color:#5b6ef7;line-height:1}
.stat-label{font-size:.75rem;color:#888;margin-top:.3rem}
/* -- Forms -- */
label{display:block;font-size:.82rem;color:#999;margin-bottom:.25rem;margin-top:.8rem}
label:first-child{margin-top:0}
textarea,input,select{width:100%;padding:.55rem .75rem;border-radius:7px;border:1px solid #333;
background:#0d0d18;color:#e0e0e0;font-size:.88rem;font-family:inherit}
textarea{resize:vertical;min-height:75px}
textarea:focus,input:focus,select:focus{outline:none;border-color:#5b6ef7}
.row{display:grid;grid-template-columns:1fr 1fr;gap:.8rem}
@media(max-width:600px){.row{grid-template-columns:1fr}}
/* -- Buttons -- */
.btn{display:inline-block;padding:.6rem 1.1rem;border:none;border-radius:7px;
font-size:.88rem;font-weight:600;cursor:pointer;transition:all .2s;text-align:center}
.btn-full{width:100%;padding:.8rem}
.btn-primary{background:#5b6ef7;color:#fff}
.btn-primary:hover{background:#4a5ce6}
.btn-primary:disabled{background:#222;color:#555;cursor:not-allowed}
.btn-success{background:#16a34a;color:#fff}
.btn-success:hover{background:#138d3f}
.btn-danger{background:#dc2626;color:#fff}
.btn-danger:hover{background:#b91c1c}
.btn-secondary{background:#222;color:#ccc;border:1px solid #444}
.btn-secondary:hover{background:#2a2a2a}
.btn-warning{background:#d97706;color:#fff}
.btn-warning:hover{background:#b45309}
.btn-sm{padding:.35rem .7rem;font-size:.78rem}
.btn-row{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.8rem}
/* -- Table -- */
.table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{width:100%;border-collapse:collapse;font-size:.85rem}
th{background:#0d0d18;color:#888;font-weight:600;padding:.6rem .8rem;text-align:left;
border-bottom:1px solid #2a2a3a;white-space:nowrap}
td{padding:.6rem .8rem;border-bottom:1px solid #1e1e2e;vertical-align:middle}
tr:hover td{background:#131320}
/* -- Badges -- */
.badge{display:inline-block;padding:.2rem .6rem;border-radius:4px;font-size:.75rem;font-weight:600}
.badge-approved,.badge-launched{background:#14532d;color:#86efac}
.badge-building{background:#1e3a5f;color:#93c5fd;animation:pulse 1.5s infinite}
.badge-hold,.badge-queued{background:#451a03;color:#fdba74}
.badge-rejected,.badge-failed{background:#450a0a;color:#fca5a5}
.badge-draft,.badge-unknown{background:#1c1c1c;color:#888}
.badge-succeeded{background:#14532d;color:#86efac}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.6}}
/* -- Misc -- */
.decision-badge{display:inline-block;padding:.3rem .8rem;border-radius:6px;
font-weight:700;font-size:.9rem;margin:.5rem 0}
.decision-APPROVED{background:#16a34a;color:#fff}
.decision-HOLD{background:#d97706;color:#fff}
.decision-REJECTED{background:#dc2626;color:#fff}
.score-bar{height:8px;border-radius:4px;background:#1e1e2e;margin:.3rem 0;overflow:hidden}
.score-fill{height:100%;border-radius:4px;transition:width .5s}
.score-high{background:#16a34a}.score-med{background:#d97706}.score-low{background:#dc2626}
.section{margin-top:1rem;padding-top:1rem;border-top:1px solid #222}
.section h3{font-size:.9rem;color:#aaa;margin-bottom:.5rem}
.detail-row{display:flex;justify-content:space-between;padding:.2rem 0;font-size:.82rem}
.detail-label{color:#777}.detail-value{color:#ddd;text-align:right;max-width:60%}
.blocking{color:#fca5a5;font-size:.82rem;margin:.2rem 0}
.reason{color:#86efac;font-size:.82rem;margin:.2rem 0}
.tag{display:inline-block;background:#1a1a2e;border:1px solid #333;border-radius:4px;
padding:.12rem .35rem;font-size:.72rem;margin:.1rem;color:#ccc}
.loading-overlay{display:none;text-align:center;padding:1.5rem;color:#888}
.spinner{display:inline-block;width:22px;height:22px;border:3px solid #222;
border-top-color:#5b6ef7;border-radius:50%;animation:spin .8s linear infinite;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.error-box{background:#2d1111;border:1px solid #dc2626;border-radius:8px;padding:.8rem 1rem;
color:#fca5a5;margin:.8rem 0;display:none;font-size:.88rem}
.success-box{background:#0d2d1a;border:1px solid #16a34a;border-radius:8px;padding:.8rem 1rem;
color:#86efac;margin:.8rem 0;display:none;font-size:.88rem}
/* -- Toast -- */
#toast-container{position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;display:flex;
flex-direction:column;gap:.5rem;pointer-events:none}
.toast{padding:.7rem 1.2rem;border-radius:8px;font-size:.88rem;font-weight:500;
pointer-events:auto;animation:slideIn .3s ease;max-width:320px}
.toast-success{background:#14532d;color:#86efac;border:1px solid #16a34a}
.toast-error{background:#450a0a;color:#fca5a5;border:1px solid #dc2626}
.toast-info{background:#1e3a5f;color:#93c5fd;border:1px solid #2563eb}
@keyframes slideIn{from{transform:translateX(120%);opacity:0}to{transform:translateX(0);opacity:1}}
/* -- Messages -- */
.msg-card{background:#0d0d18;border:1px solid #2a2a3a;border-radius:8px;padding:.9rem;margin:.6rem 0}
.msg-platform{font-size:.78rem;color:#888;font-weight:600;margin-bottom:.4rem;text-transform:uppercase}
.msg-text{font-size:.88rem;color:#ddd;white-space:pre-wrap;word-break:break-word}
.copy-btn{float:right;font-size:.72rem;padding:.2rem .5rem;margin-left:.5rem}
/* -- Quick actions -- */
.quick-actions{display:flex;gap:.6rem;flex-wrap:wrap;margin-top:.8rem}
footer{padding:1.5rem;text-align:center;color:#444;font-size:.78rem;border-top:1px solid #1a1a1a;margin-top:2rem}
</style>
</head>
<body>

<header class="app-header">
  <div>
    <span style="font-size:1.3rem">&#x1F9E0;</span>
    <strong style="margin-left:.4rem;color:#fff">AI-DAN</strong>
    <span class="version">v{version}</span>
    <span id="globalHealthDot" class="health-dot" title="System health"></span>
  </div>
  <div style="font-size:.8rem;color:#555" id="lastRefresh"></div>
</header>

<nav class="tab-bar" role="tablist">
  <button class="tab-btn active" onclick="showTab('dash')" role="tab">&#x1F4CA; Dashboard</button>
  <button class="tab-btn" onclick="showTab('analyze')" role="tab">&#x1F4A1; Analyze</button>
  <button class="tab-btn" onclick="showTab('portfolio')" role="tab">&#x1F4E6; Portfolio</button>
  <button class="tab-btn" onclick="showTab('factory')" role="tab">&#x1F3ED; Factory</button>
  <button class="tab-btn" onclick="showTab('distribution')" role="tab">&#x1F4E3; Distribution</button>
  <button class="tab-btn" onclick="showTab('revenue')" role="tab">&#x1F4B0; Revenue</button>
</nav>

<!-- ═══════════════ DASHBOARD TAB ═══════════════ -->
<section id="tab-dash" class="tab-content active">
  <div class="stats-grid" id="portfolioStats">
    <div class="stat-card"><div class="stat-value" id="statTotal">—</div><div class="stat-label">Total Projects</div></div>
    <div class="stat-card"><div class="stat-value" id="statApproved" style="color:#16a34a">—</div><div class="stat-label">Approved</div></div>
    <div class="stat-card"><div class="stat-value" id="statBuilding" style="color:#3b82f6">—</div><div class="stat-label">Building</div></div>
    <div class="stat-card"><div class="stat-value" id="statLaunched" style="color:#a855f7">—</div><div class="stat-label">Launched</div></div>
    <div class="stat-card"><div class="stat-value" id="statRejected" style="color:#dc2626">—</div><div class="stat-label">Rejected</div></div>
  </div>

  <div class="card">
    <div class="card-header">
      <span class="card-title">&#x26A1; Quick Actions</span>
      <button class="btn btn-secondary btn-sm" onclick="refreshDashboard()">&#x1F504; Refresh</button>
    </div>
    <div class="quick-actions">
      <button class="btn btn-primary" onclick="showTab('analyze')">&#x1F4A1; New Idea</button>
      <button class="btn btn-secondary" onclick="showTab('portfolio')">&#x1F4E6; View Portfolio</button>
      <button class="btn btn-secondary" onclick="showTab('factory')">&#x1F3ED; Factory Runs</button>
      <button class="btn btn-secondary" onclick="showTab('distribution')">&#x1F4E3; Share Product</button>
      <button class="btn btn-secondary" onclick="showTab('revenue')">&#x1F4B0; Revenue Report</button>
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <span class="card-title">&#x1F4CB; Recent Projects</span>
    </div>
    <div id="dashRecentProjects"><div class="loading-overlay" style="display:block"><span class="spinner"></span> Loading…</div></div>
  </div>
</section>

<!-- ═══════════════ ANALYZE TAB ═══════════════ -->
<section id="tab-analyze" class="tab-content">
  <div class="card">
    <div class="card-title" style="margin-bottom:1rem">&#x1F4A1; Analyze Idea</div>
    <label for="idea">Your Idea *</label>
    <textarea id="idea" placeholder="Describe your idea in detail…"></textarea>
    <div class="row">
      <div><label for="problem">Problem</label><input id="problem" placeholder="What problem does it solve?"/></div>
      <div><label for="target_user">Target User</label><input id="target_user" placeholder="Who is this for?"/></div>
    </div>
    <div class="row">
      <div>
        <label for="monetization_model">Monetization Model</label>
        <select id="monetization_model">
          <option value="">Select…</option>
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
          <option value="">Select…</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
      </div>
    </div>
    <div class="row">
      <div>
        <label for="difficulty">Build Difficulty</label>
        <select id="difficulty">
          <option value="">Select…</option>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </select>
      </div>
      <div>
        <label for="time_to_revenue">Time to Revenue</label>
        <select id="time_to_revenue">
          <option value="">Select…</option>
          <option value="days">Days</option>
          <option value="weeks">Weeks</option>
          <option value="months">Months</option>
        </select>
      </div>
    </div>
    <label for="differentiation">Differentiation</label>
    <input id="differentiation" placeholder="What makes this unique?"/>
    <div class="btn-row">
      <button class="btn btn-primary btn-full" id="analyzeBtn" onclick="analyze()">&#x1F50D; Analyze Idea</button>
    </div>
  </div>

  <div class="loading-overlay" id="analyzeLoading"><span class="spinner"></span><p style="margin-top:.6rem">Running full pipeline analysis…</p></div>
  <div class="error-box" id="analyzeError"></div>
  <div id="analyzeResult"></div>
</section>

<!-- ═══════════════ PORTFOLIO TAB ═══════════════ -->
<section id="tab-portfolio" class="tab-content">
  <div class="card">
    <div class="card-title" style="margin-bottom:1rem">&#x2795; Add Project</div>
    <div class="row">
      <div><label for="newProjId">Project ID *</label><input id="newProjId" placeholder="prj-my-idea"/></div>
      <div><label for="newProjName">Name *</label><input id="newProjName" placeholder="My Idea"/></div>
    </div>
    <div class="row">
      <div><label for="newProjStatus">Initial Status</label>
        <select id="newProjStatus">
          <option value="draft">Draft</option>
          <option value="approved">Approved</option>
        </select>
      </div>
      <div><label for="newProjUrl">Deploy URL</label><input id="newProjUrl" placeholder="https://…"/></div>
    </div>
    <div class="btn-row">
      <button class="btn btn-success btn-full" onclick="addProject()">&#x2795; Create Project</button>
    </div>
    <div class="error-box" id="portfolioError"></div>
    <div class="success-box" id="portfolioSuccess"></div>
  </div>

  <div class="card">
    <div class="card-header">
      <span class="card-title">&#x1F4E6; All Projects</span>
      <button class="btn btn-secondary btn-sm" onclick="loadPortfolio()">&#x1F504; Refresh</button>
    </div>
    <div class="table-wrap">
      <table id="portfolioTable">
        <thead><tr>
          <th>Name</th><th>Status</th><th>Deploy URL</th><th>Actions</th>
        </tr></thead>
        <tbody id="portfolioBody"><tr><td colspan="4" style="color:#555;text-align:center">Loading…</td></tr></tbody>
      </table>
    </div>
  </div>
</section>

<!-- ═══════════════ FACTORY TAB ═══════════════ -->
<section id="tab-factory" class="tab-content">
  <div class="card">
    <div class="card-title" style="margin-bottom:1rem">&#x1F680; Trigger Build</div>
    <div class="row">
      <div>
        <label for="factoryProjectId">Project ID *</label>
        <input id="factoryProjectId" placeholder="prj-my-idea"/>
      </div>
      <div>
        <label for="factoryTemplate">Template</label>
        <select id="factoryTemplate">
          <option value="saas-template">SaaS Template</option>
          <option value="landing-page">Landing Page</option>
        </select>
      </div>
    </div>
    <label style="display:flex;align-items:center;gap:.5rem;cursor:pointer;margin-top:.8rem">
      <input type="checkbox" id="factoryDryRun" checked style="width:auto"/>
      <span style="color:#ccc;font-size:.88rem">Dry Run (safe — no real deployment)</span>
    </label>
    <div class="btn-row">
      <button class="btn btn-primary btn-full" onclick="triggerBuild()">&#x1F3ED; Trigger Build</button>
    </div>
    <div class="error-box" id="factoryError"></div>
    <div class="success-box" id="factorySuccess"></div>
  </div>

  <div class="card">
    <div class="card-header">
      <span class="card-title">&#x1F4CB; Build Runs</span>
      <button class="btn btn-secondary btn-sm" onclick="loadRuns()">&#x1F504; Refresh</button>
    </div>
    <div class="table-wrap">
      <table id="runsTable">
        <thead><tr>
          <th>Run ID</th><th>Project</th><th>Status</th><th>Deploy URL</th><th>Actions</th>
        </tr></thead>
        <tbody id="runsBody"><tr><td colspan="5" style="color:#555;text-align:center">Loading…</td></tr></tbody>
      </table>
    </div>
  </div>
</section>

<!-- ═══════════════ DISTRIBUTION TAB ═══════════════ -->
<section id="tab-distribution" class="tab-content">
  <div class="card">
    <div class="card-title" style="margin-bottom:1rem">&#x1F4E3; Generate Share Messages</div>
    <div class="row">
      <div><label for="distProduct">Product Name *</label><input id="distProduct" placeholder="My SaaS"/></div>
      <div><label for="distHook">Hook / Tagline</label><input id="distHook" placeholder="One-line pitch"/></div>
    </div>
    <div class="row">
      <div><label for="distUrl">Launch URL</label><input id="distUrl" placeholder="https://myapp.com"/></div>
      <div><label for="distAudience">Target Audience</label><input id="distAudience" placeholder="Indie founders"/></div>
    </div>
    <label for="distProblem">Problem Solved</label>
    <textarea id="distProblem" style="min-height:55px" placeholder="Describe the problem this solves…"></textarea>
    <div class="btn-row">
      <button class="btn btn-primary btn-full" onclick="generateMessages()">&#x2728; Generate Messages</button>
    </div>
    <div class="error-box" id="distError"></div>
    <div class="loading-overlay" id="distLoading"><span class="spinner"></span><p style="margin-top:.6rem">Generating messages…</p></div>
  </div>
  <div id="distMessages"></div>
</section>

<!-- ═══════════════ REVENUE TAB ═══════════════ -->
<section id="tab-revenue" class="tab-content">
  <div class="card">
    <div class="card-title" style="margin-bottom:1rem">&#x1F4B0; Revenue Intelligence</div>
    <div class="row">
      <div>
        <label for="revProjectId">Project ID *</label>
        <input id="revProjectId" placeholder="prj-my-idea"/>
      </div>
      <div style="display:flex;flex-direction:column;justify-content:flex-end">
        <div class="btn-row" style="margin-top:1.55rem">
          <button class="btn btn-primary" onclick="loadLearningReport()">&#x1F4C8; Learning Report</button>
          <button class="btn btn-secondary" onclick="generateBusinessOutput()">&#x1F4CA; Business Output</button>
        </div>
      </div>
    </div>
    <div class="error-box" id="revError"></div>
    <div class="loading-overlay" id="revLoading"><span class="spinner"></span><p style="margin-top:.6rem">Loading…</p></div>
  </div>
  <div id="revResult"></div>
</section>

<footer>AI-DAN Managing Director v{version} &mdash; Monetization-first decision engine</footer>
<div id="toast-container"></div>

<script>
// -------------------------------------------
// Utilities
// -------------------------------------------
function escapeHtml(s){
  if(s==null||s===undefined)return'';
  var d=document.createElement("div");
  d.appendChild(document.createTextNode(String(s)));
  return d.innerHTML;
}
function jsEscape(s){
  if(s==null||s===undefined)return'';
  return String(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'").replace(/"/g,'\\"')
    .replace(/</g,'\\x3c').replace(/>/g,'\\x3e').replace(/&/g,'\\x26')
    .replace(/\n/g,'\\n').replace(/\r/g,'\\r')
    .replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029');
}
function toast(msg,type){
  type=type||'info';
  var tc=document.getElementById('toast-container');
  var t=document.createElement('div');
  t.className='toast toast-'+type;
  t.textContent=msg;
  tc.appendChild(t);
  setTimeout(function(){t.style.transition='opacity .4s';t.style.opacity='0';
    setTimeout(function(){tc.removeChild(t)},400);},3500);
}
function showLoading(id){document.getElementById(id).style.display='block'}
function hideLoading(id){document.getElementById(id).style.display='none'}
function showError(id,msg){var el=document.getElementById(id);el.textContent=msg;el.style.display='block'}
function hideError(id){document.getElementById(id).style.display='none'}
function showSuccess(id,msg){var el=document.getElementById(id);el.textContent=msg;el.style.display='block'}
function hideSuccess(id){document.getElementById(id).style.display='none'}
function statusBadge(s){
  var cls={approved:'badge-approved',launched:'badge-launched',building:'badge-building',
    queued:'badge-queued',hold:'badge-hold',rejected:'badge-rejected',failed:'badge-failed',
    succeeded:'badge-succeeded',draft:'badge-draft'}[s]||'badge-unknown';
  return'<span class="badge '+cls+'">'+escapeHtml(s)+'</span>';
}
function shortId(id){return id?id.substring(0,12)+(id.length>12?'…':''):'-'}

// -------------------------------------------
// Tab navigation
// -------------------------------------------
function showTab(name){
  document.querySelectorAll('.tab-content').forEach(function(el){el.classList.remove('active')});
  document.querySelectorAll('.tab-btn').forEach(function(el){el.classList.remove('active')});
  document.getElementById('tab-'+name).classList.add('active');
  var btns=document.querySelectorAll('.tab-btn');
  var map={dash:0,analyze:1,portfolio:2,factory:3,distribution:4,revenue:5};
  if(map[name]!==undefined)btns[map[name]].classList.add('active');
  if(name==='portfolio')loadPortfolio();
  if(name==='factory')loadRuns();
  if(name==='dash')refreshDashboard();
}

// -------------------------------------------
// Dashboard
// -------------------------------------------
function refreshDashboard(){
  document.getElementById('lastRefresh').textContent='Refreshing…';
  fetch('/portfolio/projects').then(function(r){return r.json()}).then(function(data){
    var projects=Array.isArray(data)?data:(data.projects||[]);
    var counts={total:projects.length,approved:0,building:0,launched:0,rejected:0};
    projects.forEach(function(p){
      var s=(p.status||'').toLowerCase();
      if(s==='approved')counts.approved++;
      else if(s==='building')counts.building++;
      else if(s==='launched')counts.launched++;
      else if(s==='rejected')counts.rejected++;
    });
    document.getElementById('statTotal').textContent=counts.total;
    document.getElementById('statApproved').textContent=counts.approved;
    document.getElementById('statBuilding').textContent=counts.building;
    document.getElementById('statLaunched').textContent=counts.launched;
    document.getElementById('statRejected').textContent=counts.rejected;
    // Health dot
    var dot=document.getElementById('globalHealthDot');
    if(counts.building>0){dot.className='health-dot degraded';dot.title='Build in progress'}
    else if(counts.launched>0){dot.className='health-dot healthy';dot.title='Projects live'}
    else{dot.className='health-dot';dot.title='No launched projects'}
    // Recent projects table (top 5)
    var recent=projects.slice(0,5);
    var html='';
    if(recent.length===0){html='<p style="color:#555;font-size:.85rem">No projects yet. <a href="#" style="color:#5b6ef7" onclick="showTab(\'analyze\');return false">Analyze your first idea →</a></p>';}
    else{
      html='<div class="table-wrap"><table><thead><tr><th>Name</th><th>Status</th><th>URL</th></tr></thead><tbody>';
      recent.forEach(function(p){
        var url=p.deploy_url||p.deployUrl||'';
        html+='<tr><td>'+escapeHtml(p.name||p.project_id)+'</td><td>'+statusBadge((p.status||'draft').toLowerCase())+'</td>';
        html+='<td>'+(url?'<a href="'+escapeHtml(url)+'" target="_blank" style="color:#5b6ef7;font-size:.8rem">'+escapeHtml(url.replace(/https?:[/][/]/,''))+'</a>':'-')+'</td></tr>';
      });
      html+='</tbody></table></div>';
    }
    document.getElementById('dashRecentProjects').innerHTML=html;
    document.getElementById('lastRefresh').textContent='Updated '+new Date().toLocaleTimeString();
  }).catch(function(){
    document.getElementById('globalHealthDot').className='health-dot failed';
    document.getElementById('lastRefresh').textContent='Refresh failed';
  });
}
// Auto-refresh every 30s
setInterval(refreshDashboard,30000);

// -------------------------------------------
// Analyze
// -------------------------------------------
function analyze(){
  var btn=document.getElementById('analyzeBtn');
  var idea=document.getElementById('idea').value.trim();
  if(!idea){showError('analyzeError','Please enter an idea.');return}
  hideError('analyzeError');
  btn.disabled=true;showLoading('analyzeLoading');
  document.getElementById('analyzeResult').innerHTML='';
  var body={idea:idea,
    problem:document.getElementById('problem').value.trim(),
    target_user:document.getElementById('target_user').value.trim(),
    monetization_model:document.getElementById('monetization_model').value,
    competition_level:document.getElementById('competition_level').value,
    difficulty:document.getElementById('difficulty').value,
    time_to_revenue:document.getElementById('time_to_revenue').value,
    differentiation:document.getElementById('differentiation').value.trim()};
  fetch('/api/analyze/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
    .then(function(r){if(!r.ok)return r.json().then(function(e){throw new Error(e.detail||r.statusText)});return r.json()})
    .then(function(d){renderAnalysis(d);toast('Analysis complete','success')})
    .catch(function(err){showError('analyzeError','Error: '+err.message);toast(err.message,'error')})
    .finally(function(){btn.disabled=false;hideLoading('analyzeLoading')});
}
function renderAnalysis(d){
  var r=document.getElementById('analyzeResult');
  var sc=d.total_score||0;
  var pct=(sc/10*100).toFixed(0);
  var cls=sc>=8?'high':sc>=6?'med':'low';
  var dec=d.final_decision||'UNKNOWN';
  var h='<div class="card">';
  h+='<div style="display:flex;justify-content:space-between;align-items:center">';
  h+='<div><span class="decision-badge decision-'+dec+'">'+dec+'</span></div>';
  h+='<div style="text-align:right;font-size:1.5rem;font-weight:700">'+sc.toFixed(1)+'<span style="font-size:.9rem;color:#888">/10</span></div></div>';
  h+='<div class="score-bar"><div class="score-fill score-'+cls+'" style="width:'+pct+'%"></div></div>';
  h+='<p style="font-size:.82rem;color:#aaa;margin-top:.3rem">'+escapeHtml(d.score_decision_reason||d.next_step||'')+'</p>';
  if(d.validation_blocking&&d.validation_blocking.length){
    h+='<div class="section"><h3>&#x1F6D1; Blocking Issues</h3>';
    d.validation_blocking.forEach(function(b){h+='<p class="blocking">• '+escapeHtml(b)+'</p>'});
    h+='</div>';
  }
  if(d.validation_reasons&&d.validation_reasons.length){
    h+='<div class="section"><h3>&#x2705; Validation</h3>';
    d.validation_reasons.forEach(function(v){h+='<p class="reason">• '+escapeHtml(v)+'</p>'});
    h+='</div>';
  }
  if(d.score_dimensions&&d.score_dimensions.length){
    h+='<div class="section"><h3>&#x1F4CA; Score Breakdown</h3>';
    d.score_dimensions.forEach(function(dim){
      var dp=(dim.score/2*100).toFixed(0);
      var dc=dim.score>=1.5?'high':dim.score>=1?'med':'low';
      h+='<div class="detail-row"><span class="detail-label">'+escapeHtml(dim.name)+'</span><span class="detail-value">'+dim.score.toFixed(1)+'/2</span></div>';
      h+='<div class="score-bar"><div class="score-fill score-'+dc+'" style="width:'+dp+'%"></div></div>';
      h+='<p style="font-size:.78rem;color:#666;margin-bottom:.3rem">'+escapeHtml(dim.reason)+'</p>';
    });
    h+='</div>';
  }
  var o=d.offer||{};
  if(o.decision==='generated'){
    h+='<div class="section"><h3>&#x1F4B0; Offer</h3>';
    h+=detailRow('Pricing',o.pricing);h+=detailRow('Model',o.pricing_model);
    h+=detailRow('Delivery',o.delivery_method);h+=detailRow('Value',o.value_proposition);
    h+=detailRow('CTA',o.cta);h+='</div>';
  }
  var di=d.distribution||{};
  if(di.decision==='generated'){
    h+='<div class="section"><h3>&#x1F680; Distribution</h3>';
    h+=detailRow('Channel',di.primary_channel);h+=detailRow('Acquisition',di.acquisition_method);
    h+=detailRow('First 10 Users',di.first_10_users_plan);h+=detailRow('Messaging',di.messaging);
    h+='</div>';
  }
  h+='<div class="section"><h3>&#x27A1;&#xFE0F; Next Step</h3>';
  h+='<p style="font-size:.88rem">'+escapeHtml(d.next_step||'Awaiting analysis.')+'</p></div>';
  // Create project button if APPROVED or HOLD
  if(dec==='APPROVED'||dec==='HOLD'){
    h+='<div class="section">';
    h+='<button class="btn btn-success btn-full" data-idea="'+escapeHtml(d.idea||'')+'" onclick="createProjectFromAnalysis(this.dataset.idea)">&#x2795; Create Project from This Idea</button>';
    h+='</div>';
  }
  h+='</div>';
  r.innerHTML=h;
}
function detailRow(l,v){
  if(!v)return'';
  return'<div class="detail-row"><span class="detail-label">'+escapeHtml(l)+'</span><span class="detail-value">'+escapeHtml(v)+'</span></div>';
}
function createProjectFromAnalysis(ideaText){
  showTab('portfolio');
  document.getElementById('newProjName').value=ideaText?ideaText.substring(0,40):'New Project';
  document.getElementById('newProjId').value='prj-'+Date.now().toString(36);
  toast('Prefilled project form — review and click Create','info');
}

// -------------------------------------------
// Portfolio
// -------------------------------------------
function loadPortfolio(){
  var tbody=document.getElementById('portfolioBody');
  tbody.innerHTML='<tr><td colspan="4" style="color:#555;text-align:center"><span class="spinner" style="width:16px;height:16px;border-width:2px"></span> Loading…</td></tr>';
  fetch('/portfolio/projects').then(function(r){return r.json()}).then(function(data){
    var projects=Array.isArray(data)?data:(data.projects||[]);
    if(projects.length===0){tbody.innerHTML='<tr><td colspan="4" style="color:#555;text-align:center">No projects yet.</td></tr>';return}
    var rows='';
    projects.forEach(function(p){
      var pid=p.project_id||p.id||'';
      var url=p.deploy_url||p.deployUrl||'';
      var status=(p.status||'draft').toLowerCase();
      rows+='<tr>';
      rows+='<td>'+escapeHtml(p.name||pid)+'</td>';
      rows+='<td>'+statusBadge(status)+'</td>';
      rows+='<td>'+(url?'<a href="'+escapeHtml(url)+'" target="_blank" style="color:#5b6ef7;font-size:.8rem">View ↗</a>':'-')+'</td>';
      rows+='<td><div style="display:flex;gap:.3rem;flex-wrap:wrap">';
      if(status!=='approved'&&status!=='building'&&status!=='launched'){
        rows+='<button class="btn btn-success btn-sm" onclick="approveProject(\''+jsEscape(pid)+'\')">✅ Approve</button>';
      }
      rows+='<button class="btn btn-primary btn-sm" onclick="buildProject(\''+jsEscape(pid)+'\')">🚀 Build</button>';
      rows+='<button class="btn btn-secondary btn-sm" onclick="shareProject(\''+jsEscape(p.name||pid)+'\',\''+jsEscape(url)+'\')">📣 Share</button>';
      if(url){rows+='<button class="btn btn-secondary btn-sm" onclick="checkHealth(\''+jsEscape(pid)+'\',\''+jsEscape(url)+'\')">🩺 Health</button>';}
      rows+='</div></td></tr>';
    });
    tbody.innerHTML=rows;
  }).catch(function(){tbody.innerHTML='<tr><td colspan="4" style="color:#fca5a5;text-align:center">Failed to load projects.</td></tr>'});
}
function addProject(){
  var pid=document.getElementById('newProjId').value.trim();
  var name=document.getElementById('newProjName').value.trim();
  var status=document.getElementById('newProjStatus').value;
  var url=document.getElementById('newProjUrl').value.trim();
  hideError('portfolioError');hideSuccess('portfolioSuccess');
  if(!pid||!name){showError('portfolioError','Project ID and Name are required.');return}
  fetch('/portfolio/projects',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({project_id:pid,name:name,status:status,deploy_url:url})})
    .then(function(r){if(!r.ok)return r.json().then(function(e){throw new Error(e.detail||r.statusText)});return r.json()})
    .then(function(){
      showSuccess('portfolioSuccess','Project created!');
      toast('Project created','success');
      document.getElementById('newProjId').value='';
      document.getElementById('newProjName').value='';
      document.getElementById('newProjUrl').value='';
      loadPortfolio();
    })
    .catch(function(err){showError('portfolioError',err.message);toast(err.message,'error')});
}
function approveProject(pid){
  fetch('/portfolio/projects/'+pid+'/transition',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({new_state:'approved'})})
    .then(function(r){if(!r.ok)return r.json().then(function(e){throw new Error(e.detail||r.statusText)});return r.json()})
    .then(function(){toast('Project approved','success');loadPortfolio()})
    .catch(function(err){toast('Approve failed: '+err.message,'error')});
}
function buildProject(pid){
  showTab('factory');
  document.getElementById('factoryProjectId').value=pid;
  toast('Project ID prefilled — click Trigger Build','info');
}
function shareProject(name,url){
  showTab('distribution');
  if(name)document.getElementById('distProduct').value=name;
  if(url)document.getElementById('distUrl').value=url;
  toast('Product prefilled — click Generate Messages','info');
}
function checkHealth(pid,url){
  toast('Checking deployment health…','info');
  fetch('/factory/verify-deployment',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({project_id:pid,deploy_url:url})})
    .then(function(r){return r.json()})
    .then(function(d){
      var emoji={'healthy':'🟢','degraded':'🟡','failed':'🔴','unknown':'⚪'}[d.status]||'⚪';
      toast(emoji+' '+pid+': '+d.status+(d.issues&&d.issues.length?' — '+d.issues[0]:''),'info');
    })
    .catch(function(){toast('Health check failed','error')});
}

// -------------------------------------------
// Factory
// -------------------------------------------
function loadRuns(){
  var tbody=document.getElementById('runsBody');
  tbody.innerHTML='<tr><td colspan="5" style="color:#555;text-align:center"><span class="spinner" style="width:16px;height:16px;border-width:2px"></span> Loading…</td></tr>';
  fetch('/factory/runs').then(function(r){return r.json()}).then(function(runs){
    if(!Array.isArray(runs)||runs.length===0){
      tbody.innerHTML='<tr><td colspan="5" style="color:#555;text-align:center">No runs yet.</td></tr>';return;
    }
    var rows='';
    runs.forEach(function(run){
      var status=(run.status||'unknown').toLowerCase();
      var url=run.deploy_url||run.deployUrl||'';
      rows+='<tr>';
      rows+='<td><span style="font-family:monospace;font-size:.78rem">'+escapeHtml(shortId(run.run_id))+'</span></td>';
      rows+='<td>'+escapeHtml(run.project_id||'-')+'</td>';
      rows+='<td>'+statusBadge(status)+'</td>';
      rows+='<td>'+(url?'<a href="'+escapeHtml(url)+'" target="_blank" style="color:#5b6ef7;font-size:.8rem">View ↗</a>':'-')+'</td>';
      rows+='<td>';
      if(url){rows+='<button class="btn btn-secondary btn-sm" onclick="checkHealth(\''+jsEscape(run.project_id)+'\',\''+jsEscape(url)+'\')">🩺 Health</button>';}
      rows+='</td></tr>';
    });
    tbody.innerHTML=rows;
  }).catch(function(){tbody.innerHTML='<tr><td colspan="5" style="color:#fca5a5;text-align:center">Failed to load runs.</td></tr>'});
}
function triggerBuild(){
  var pid=document.getElementById('factoryProjectId').value.trim();
  var template=document.getElementById('factoryTemplate').value;
  var dryRun=document.getElementById('factoryDryRun').checked;
  hideError('factoryError');hideSuccess('factorySuccess');
  if(!pid){showError('factoryError','Project ID is required.');return}
  var brief={project_id:pid,idea_id:'idea-'+pid,hypothesis:'Build '+pid,
    target_user:'users',problem:'needs solution',solution:'our product',
    mvp_scope:['core feature'],acceptance_criteria:['deploys successfully'],
    landing_page_requirements:['clear CTA'],cta:'Get Started',pricing_hint:'freemium',
    deployment_target:'vercel',command_bundle:{template:template},
    feature_flags:{dry_run:dryRun,live_factory:!dryRun}};
  fetch('/factory/runs',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({build_brief:brief,dry_run:dryRun})})
    .then(function(r){if(!r.ok)return r.json().then(function(e){throw new Error(e.detail||r.statusText)});return r.json()})
    .then(function(d){
      showSuccess('factorySuccess','Build triggered! Run ID: '+d.run_id+' — Status: '+d.status);
      toast('Build triggered: '+d.status,'success');
      loadRuns();
    })
    .catch(function(err){showError('factoryError',err.message);toast(err.message,'error')});
}

// -------------------------------------------
// Distribution
// -------------------------------------------
function generateMessages(){
  var product=document.getElementById('distProduct').value.trim();
  hideError('distError');
  if(!product){showError('distError','Product name is required.');return}
  showLoading('distLoading');
  document.getElementById('distMessages').innerHTML='';
  var body={product_name:product,
    hook:document.getElementById('distHook').value.trim(),
    url:document.getElementById('distUrl').value.trim(),
    target_audience:document.getElementById('distAudience').value.trim(),
    problem:document.getElementById('distProblem').value.trim()};
  fetch('/api/distribution/share-messages',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
    .then(function(r){if(!r.ok)return r.json().then(function(e){throw new Error(e.detail||r.statusText)});return r.json()})
    .then(function(d){renderMessages(d);toast('Messages generated','success')})
    .catch(function(err){showError('distError',err.message);toast(err.message,'error')})
    .finally(function(){hideLoading('distLoading')});
}
function renderMessages(d){
  var container=document.getElementById('distMessages');
  var platforms=['twitter','linkedin','whatsapp','email','sms','reddit','product_hunt'];
  var icons={twitter:'🐦',linkedin:'💼',whatsapp:'💬',email:'📧',sms:'📱',reddit:'🤖',product_hunt:'🚀'};
  var html='<div class="card"><div class="card-title" style="margin-bottom:.8rem">📋 Generated Messages</div>';
  var found=false;
  var msgCounter=0;
  platforms.forEach(function(p){
    var msg=d[p]||d[p.replace('_',' ')]||'';
    if(!msg)return;
    found=true;
    var msgId='msg-'+msgCounter++;
    html+='<div class="msg-card">';
    html+='<div class="msg-platform">'+(icons[p]||'')+'&nbsp;'+p.replace('_',' ')+'</div>';
    html+='<button class="btn btn-secondary btn-sm copy-btn" onclick="copyMsg(\''+msgId+'\')">Copy</button>';
    html+='<div class="msg-text" id="'+escapeHtml(msgId)+'">'+escapeHtml(msg)+'</div>';
    html+='</div>';
  });
  if(!found){
    // Try rendering all keys
    Object.keys(d).forEach(function(k){
      if(typeof d[k]==='string'&&d[k].length>5){
        found=true;
        var msgId='msg-'+msgCounter++;
        html+='<div class="msg-card">';
        html+='<div class="msg-platform">'+escapeHtml(k.replace('_',' '))+'</div>';
        html+='<button class="btn btn-secondary btn-sm copy-btn" onclick="copyMsg(\''+msgId+'\')">Copy</button>';
        html+='<div class="msg-text" id="'+escapeHtml(msgId)+'">'+escapeHtml(d[k])+'</div>';
        html+='</div>';
      }
    });
  }
  if(!found){html+='<p style="color:#555;font-size:.85rem">No messages returned. Check the API response.</p>';}
  html+='</div>';
  container.innerHTML=html;
}
function copyMsg(id){
  var el=document.getElementById(id);
  if(!el)return;
  var text=el.textContent||el.innerText;
  navigator.clipboard.writeText(text).then(function(){toast('Copied!','success')})
    .catch(function(){
      var ta=document.createElement('textarea');ta.value=text;
      document.body.appendChild(ta);ta.select();document.execCommand('copy');
      document.body.removeChild(ta);toast('Copied!','success');
    });
}

// -------------------------------------------
// Revenue
// -------------------------------------------
function loadLearningReport(){
  var pid=document.getElementById('revProjectId').value.trim();
  hideError('revError');
  if(!pid){showError('revError','Project ID is required.');return}
  showLoading('revLoading');
  document.getElementById('revResult').innerHTML='';
  fetch('/revenue/projects/'+pid+'/learning-report')
    .then(function(r){if(!r.ok)return r.json().then(function(e){throw new Error(e.detail||r.statusText)});return r.json()})
    .then(function(d){renderRevResult(d,'Learning Report');toast('Report loaded','success')})
    .catch(function(err){showError('revError',err.message);toast(err.message,'error')})
    .finally(function(){hideLoading('revLoading')});
}
function generateBusinessOutput(){
  var pid=document.getElementById('revProjectId').value.trim();
  hideError('revError');
  if(!pid){showError('revError','Project ID is required.');return}
  showLoading('revLoading');
  document.getElementById('revResult').innerHTML='';
  fetch('/revenue/projects/'+pid+'/business-output',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})
    .then(function(r){if(!r.ok)return r.json().then(function(e){throw new Error(e.detail||r.statusText)});return r.json()})
    .then(function(d){renderRevResult(d,'Business Output');toast('Output generated','success')})
    .catch(function(err){showError('revError',err.message);toast(err.message,'error')})
    .finally(function(){hideLoading('revLoading')});
}
function renderRevResult(d,title){
  var el=document.getElementById('revResult');
  var html='<div class="card"><div class="card-title" style="margin-bottom:.8rem">'+escapeHtml(title)+'</div>';
  html+=renderObj(d);
  html+='</div>';
  el.innerHTML=html;
}
function renderObj(obj,depth){
  depth=depth||0;
  if(obj===null||obj===undefined)return'<span style="color:#555">—</span>';
  if(typeof obj==='string'||typeof obj==='number'||typeof obj==='boolean'){
    return'<span style="color:#ddd">'+escapeHtml(String(obj))+'</span>';
  }
  if(Array.isArray(obj)){
    if(obj.length===0)return'<span style="color:#555">[]</span>';
    var html='<ul style="margin-left:1rem;list-style:disc">';
    obj.forEach(function(item){html+='<li style="font-size:.85rem;color:#ccc;margin:.15rem 0">'+renderObj(item,depth+1)+'</li>'});
    html+='</ul>';return html;
  }
  if(typeof obj==='object'){
    var html='<div style="'+(depth>0?'margin-left:.8rem':'')+'">';
    Object.keys(obj).forEach(function(k){
      html+='<div class="detail-row"><span class="detail-label">'+escapeHtml(k.replace(/_/g,' '))+'</span>';
      html+='<span class="detail-value">'+renderObj(obj[k],depth+1)+'</span></div>';
    });
    html+='</div>';return html;
  }
  return escapeHtml(String(obj));
}

// -------------------------------------------
// Init
// -------------------------------------------
refreshDashboard();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def root_ui() -> HTMLResponse:
    """Serve the root idea-analysis UI."""
    html = _ROOT_HTML.replace("{version}", _VERSION)
    return HTMLResponse(content=html)
