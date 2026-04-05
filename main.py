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
# Root UI – embedded HTML command center dashboard for solo operator
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
background:#0a0a0a;color:#e0e0e0;min-height:100vh;display:flex;flex-direction:column}
/* ---------- Tab bar ---------- */
.tabbar{position:sticky;top:0;z-index:100;background:#0f0f1a;
border-bottom:1px solid #333;display:flex;overflow-x:auto;padding:0 1rem}
.tabbar button{flex-shrink:0;background:none;border:none;color:#888;
padding:.85rem 1.1rem;cursor:pointer;font-size:.88rem;font-weight:500;
border-bottom:3px solid transparent;transition:all .2s;white-space:nowrap}
.tabbar button.active{color:#fff;border-bottom-color:#5b6ef7}
.tabbar button:hover:not(.active){color:#ccc}
/* ---------- Content ---------- */
.tab-content{display:none;flex:1;padding:1.5rem 1rem;max-width:1100px;
width:100%;margin:0 auto}
.tab-content.active{display:block}
/* ---------- Cards ---------- */
.card{background:#1a1a2e;border:1px solid #333;border-radius:12px;
padding:1.5rem;margin-bottom:1.5rem}
.card-title{font-size:1rem;font-weight:600;color:#fff;margin-bottom:1rem}
/* ---------- Stat cards ---------- */
.stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1rem;
margin-bottom:1.5rem}
.stat-card{background:#1a1a2e;border:1px solid #333;border-radius:10px;
padding:1rem;text-align:center}
.stat-num{font-size:2rem;font-weight:700;color:#5b6ef7}
.stat-label{font-size:.78rem;color:#888;margin-top:.2rem}
/* ---------- Health indicator ---------- */
.health{display:inline-flex;align-items:center;gap:.4rem;font-size:.85rem;
padding:.3rem .8rem;border-radius:20px;border:1px solid #333}
.health.green{background:#0d2a1a;border-color:#16a34a;color:#86efac}
.health.yellow{background:#2a1f0d;border-color:#d97706;color:#fde68a}
.health.red{background:#2d1111;border-color:#dc2626;color:#fca5a5}
/* ---------- Status badges ---------- */
.badge{display:inline-block;padding:.2rem .55rem;border-radius:5px;
font-size:.75rem;font-weight:600}
.badge-idea{background:#1e1b4b;color:#a5b4fc}
.badge-validated{background:#0d2a1a;color:#86efac}
.badge-approved{background:#14532d;color:#86efac}
.badge-building{background:#1c1f0a;color:#d9f99d}
.badge-launched{background:#0c2a2a;color:#67e8f9}
.badge-failed{background:#2d1111;color:#fca5a5}
.badge-hold{background:#2a1f0d;color:#fde68a}
/* ---------- Forms ---------- */
label{display:block;font-size:.82rem;color:#aaa;margin-bottom:.3rem;margin-top:.8rem}
label:first-child{margin-top:0}
textarea,input,select{width:100%;padding:.6rem .8rem;border-radius:8px;
border:1px solid #444;background:#111;color:#e0e0e0;font-size:.88rem;
font-family:inherit}
textarea{resize:vertical;min-height:80px}
textarea:focus,input:focus,select:focus{outline:none;border-color:#5b6ef7}
.row{display:grid;grid-template-columns:1fr 1fr;gap:.8rem}
@media(max-width:500px){.row{grid-template-columns:1fr}}
/* ---------- Buttons ---------- */
.btn{padding:.55rem 1rem;border:none;border-radius:8px;font-size:.85rem;
font-weight:600;cursor:pointer;transition:all .2s;display:inline-flex;
align-items:center;gap:.35rem}
.btn-primary{background:#5b6ef7;color:#fff}
.btn-primary:hover{background:#4a5ce6}
.btn-success{background:#16a34a;color:#fff}
.btn-success:hover{background:#15803d}
.btn-warning{background:#d97706;color:#fff}
.btn-warning:hover{background:#b45309}
.btn-danger{background:#dc2626;color:#fff}
.btn-danger:hover{background:#b91c1c}
.btn-ghost{background:#222;color:#ccc;border:1px solid #444}
.btn-ghost:hover{background:#2a2a2a}
.btn:disabled{opacity:.45;cursor:not-allowed}
.btn-full{width:100%;justify-content:center;padding:.75rem}
.btn-row{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:1rem}
/* ---------- Table ---------- */
.tbl-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:.85rem}
th{text-align:left;color:#888;font-weight:500;padding:.6rem .75rem;
border-bottom:1px solid #333}
td{padding:.6rem .75rem;border-bottom:1px solid #222;vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover td{background:rgba(255,255,255,.02)}
/* ---------- Analysis result ---------- */
.decision-badge{display:inline-block;padding:.3rem .8rem;border-radius:6px;
font-weight:700;font-size:.88rem}
.decision-APPROVED{background:#16a34a;color:#fff}
.decision-HOLD{background:#d97706;color:#fff}
.decision-REJECTED{background:#dc2626;color:#fff}
.score-bar{height:7px;border-radius:4px;background:#333;margin:.3rem 0;overflow:hidden}
.score-fill{height:100%;border-radius:4px;transition:width .5s}
.score-high{background:#16a34a}
.score-med{background:#d97706}
.score-low{background:#dc2626}
.section{margin-top:1rem;padding-top:1rem;border-top:1px solid #333}
.section h3{font-size:.88rem;color:#aaa;margin-bottom:.5rem}
.detail-row{display:flex;justify-content:space-between;padding:.2rem 0;font-size:.82rem}
.detail-label{color:#888}
.detail-value{color:#e0e0e0;text-align:right;max-width:60%}
/* ---------- Misc ---------- */
.error-box{background:#2d1111;border:1px solid #dc2626;border-radius:8px;
padding:.8rem 1rem;color:#fca5a5;margin-top:.8rem;display:none}
.info-box{background:#0d1f3a;border:1px solid #1e3a5f;border-radius:8px;
padding:.8rem 1rem;color:#93c5fd;margin-top:.8rem;display:none}
.spinner{display:inline-block;width:16px;height:16px;border:2px solid #555;
border-top-color:#5b6ef7;border-radius:50%;animation:spin .7s linear infinite;
vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.blocking{color:#fca5a5;font-size:.82rem;margin:.2rem 0}
.reason-line{color:#86efac;font-size:.82rem;margin:.2rem 0}
.empty-state{text-align:center;padding:2.5rem;color:#555}
.copy-btn{background:#222;border:1px solid #444;color:#aaa;border-radius:5px;
padding:.2rem .5rem;font-size:.75rem;cursor:pointer}
.copy-btn:hover{background:#333}
.platform-block{background:#111;border:1px solid #2a2a2a;border-radius:8px;
padding:.8rem 1rem;margin-bottom:.8rem}
.platform-name{font-size:.8rem;color:#888;margin-bottom:.4rem;font-weight:600;
text-transform:uppercase;letter-spacing:.05em}
.platform-msg{font-size:.85rem;color:#ccc;white-space:pre-wrap;word-break:break-word}
/* ---------- Toast ---------- */
#toast-container{position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;
display:flex;flex-direction:column;gap:.5rem;pointer-events:none}
.toast{background:#1a1a2e;border:1px solid #333;border-radius:8px;
padding:.65rem 1rem;font-size:.85rem;color:#e0e0e0;
animation:slideIn .25s ease;pointer-events:all;min-width:200px}
.toast.success{border-color:#16a34a;color:#86efac}
.toast.error{border-color:#dc2626;color:#fca5a5}
@keyframes slideIn{from{transform:translateY(12px);opacity:0}to{transform:translateY(0);opacity:1}}
footer{padding:.8rem 1rem;text-align:center;color:#444;font-size:.75rem;
border-top:1px solid #1a1a1a;margin-top:auto}
</style>
</head>
<body>

<!-- ============================================================ TAB BAR -->
<nav class="tabbar" role="tablist">
  <button class="active" onclick="switchTab('dashboard')" id="tab-dashboard">&#x1F4CA; Dashboard Home</button>
  <button onclick="switchTab('analyze')" id="tab-analyze">&#x1F4A1; Analyze Idea</button>
  <button onclick="switchTab('portfolio')" id="tab-portfolio">&#x1F4E6; Portfolio</button>
  <button onclick="switchTab('factory')" id="tab-factory">&#x1F3ED; Factory</button>
  <button onclick="switchTab('distribution')" id="tab-distribution">&#x1F4E3; Distribution</button>
  <button onclick="switchTab('revenue')" id="tab-revenue">&#x1F4B0; Revenue</button>
</nav>

<div id="toast-container"></div>

<!-- ============================================================ TAB: DASHBOARD HOME -->
<div class="tab-content active" id="pane-dashboard">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.2rem;flex-wrap:wrap;gap:.5rem">
    <div>
      <h2 style="font-size:1.3rem;color:#fff">Command Center</h2>
      <p style="color:#666;font-size:.82rem">AI-DAN Managing Director v{version}</p>
    </div>
    <div style="display:flex;align-items:center;gap:.8rem;flex-wrap:wrap">
      <span class="health green" id="health-indicator">&#x25CF; Healthy</span>
      <button class="btn btn-ghost" onclick="loadDashboard()">&#x21BB; Refresh</button>
    </div>
  </div>

  <div class="stat-grid" id="stat-grid">
    <div class="stat-card"><div class="stat-num" id="stat-total">—</div><div class="stat-label">Total Projects</div></div>
    <div class="stat-card"><div class="stat-num" style="color:#a5b4fc" id="stat-idea">—</div><div class="stat-label">Ideas</div></div>
    <div class="stat-card"><div class="stat-num" style="color:#86efac" id="stat-approved">—</div><div class="stat-label">Approved</div></div>
    <div class="stat-card"><div class="stat-num" style="color:#d9f99d" id="stat-building">—</div><div class="stat-label">Building</div></div>
    <div class="stat-card"><div class="stat-num" style="color:#67e8f9" id="stat-launched">—</div><div class="stat-label">Launched</div></div>
    <div class="stat-card"><div class="stat-num" style="color:#fca5a5" id="stat-failed">—</div><div class="stat-label">Failed</div></div>
  </div>

  <div class="card">
    <div class="card-title">&#x26A1; Quick Actions</div>
    <div class="btn-row">
      <button class="btn btn-primary" onclick="switchTab('analyze')">&#x2B; New Idea</button>
      <button class="btn btn-ghost" onclick="switchTab('portfolio')">&#x1F4CB; View Portfolio</button>
      <button class="btn btn-ghost" onclick="switchTab('factory')">&#x1F3ED; Factory Runs</button>
      <button class="btn btn-ghost" onclick="switchTab('distribution')">&#x1F4E3; Share</button>
      <button class="btn btn-ghost" onclick="switchTab('revenue')">&#x1F4B0; Revenue</button>
    </div>
  </div>

  <div class="card">
    <div class="card-title">&#x1F4CB; Recent Projects</div>
    <div id="dash-projects-wrap">
      <div class="empty-state">Loading...</div>
    </div>
  </div>
</div>

<!-- ============================================================ TAB: ANALYZE IDEA -->
<div class="tab-content" id="pane-analyze">
  <h2 style="font-size:1.3rem;color:#fff;margin-bottom:1.2rem">&#x1F4A1; Analyze Idea</h2>

  <div class="card">
    <label for="idea">Your Idea *</label>
    <textarea id="idea" placeholder="Describe your idea in detail..."></textarea>

    <div class="row">
      <div>
        <label for="problem">Problem</label>
        <input id="problem" placeholder="What problem does it solve?"/>
      </div>
      <div>
        <label for="target_user">Target User</label>
        <input id="target_user" placeholder="Who is this for?"/>
      </div>
    </div>

    <div class="row">
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

    <div class="row">
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

    <div class="btn-row">
      <button class="btn btn-primary btn-full" id="analyzeBtn" onclick="analyze()">&#x1F50D; Analyze Idea</button>
    </div>
  </div>

  <div id="loading" style="display:none;text-align:center;padding:1.5rem;color:#888">
    <span class="spinner"></span>
    <span style="margin-left:.6rem">Running full pipeline analysis...</span>
  </div>
  <div class="error-box" id="errorBox"></div>
  <div id="analyze-result" style="display:none"></div>

  <div id="analyze-actions" style="display:none" class="card">
    <div class="card-title">&#x27A1;&#xFE0F; Next Actions</div>
    <div class="btn-row">
      <button class="btn btn-success" id="createProjectBtn" onclick="createProjectFromAnalysis()">&#x2B; Create Project</button>
      <button class="btn btn-ghost" id="saveDraftBtn" onclick="saveDraftFromAnalysis()">&#x1F4BE; Save Draft</button>
    </div>
    <div class="error-box" id="actionError"></div>
    <div class="info-box" id="actionInfo"></div>
  </div>
</div>

<!-- ============================================================ TAB: PORTFOLIO -->
<div class="tab-content" id="pane-portfolio">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.2rem;flex-wrap:wrap;gap:.5rem">
    <h2 style="font-size:1.3rem;color:#fff">&#x1F4E6; Portfolio</h2>
    <button class="btn btn-ghost" onclick="loadPortfolio()">&#x21BB; Refresh</button>
  </div>

  <div class="card">
    <div class="card-title">Projects</div>
    <div id="portfolio-wrap">
      <div class="empty-state">Loading...</div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">&#x2B; Add Project</div>
    <label>Project Name *</label>
    <input id="new-proj-name" placeholder="My Awesome SaaS"/>
    <label>Description</label>
    <textarea id="new-proj-desc" placeholder="What does it do?" style="min-height:60px"></textarea>
    <div class="btn-row">
      <button class="btn btn-primary" id="addProjBtn" onclick="addProject()">&#x2B; Add Project</button>
    </div>
    <div class="error-box" id="addProjError"></div>
  </div>
</div>

<!-- ============================================================ TAB: FACTORY -->
<div class="tab-content" id="pane-factory">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.2rem;flex-wrap:wrap;gap:.5rem">
    <h2 style="font-size:1.3rem;color:#fff">&#x1F3ED; Factory</h2>
    <button class="btn btn-ghost" onclick="loadFactory()">&#x21BB; Refresh</button>
  </div>

  <div class="card">
    <div class="card-title">&#x1F680; Trigger Build</div>
    <label>Project ID *</label>
    <input id="factory-project-id" placeholder="prj-xxxxxxxx"/>
    <label>Template</label>
    <select id="factory-template">
      <option value="saas-template">SaaS Template</option>
      <option value="landing-page">Landing Page</option>
    </select>
    <label style="display:flex;align-items:center;gap:.5rem;margin-top:.8rem;cursor:pointer">
      <input type="checkbox" id="factory-dry-run" checked style="width:auto"/>
      Dry Run (no real deployment)
    </label>
    <div class="btn-row">
      <button class="btn btn-primary" id="triggerBuildBtn" onclick="triggerBuild()">&#x1F680; Trigger Build</button>
    </div>
    <div class="error-box" id="factoryError"></div>
    <div class="info-box" id="factoryInfo"></div>
  </div>

  <div class="card">
    <div class="card-title">Build Runs</div>
    <div id="factory-runs-wrap">
      <div class="empty-state">Loading...</div>
    </div>
  </div>
</div>

<!-- ============================================================ TAB: DISTRIBUTION -->
<div class="tab-content" id="pane-distribution">
  <h2 style="font-size:1.3rem;color:#fff;margin-bottom:1.2rem">&#x1F4E3; Distribution</h2>

  <div class="card">
    <div class="card-title">Generate Share Messages</div>
    <label>Project Name *</label>
    <input id="dist-project-name" placeholder="My Product"/>
    <label>Value Proposition *</label>
    <textarea id="dist-value-prop" placeholder="What does it do for the user?" style="min-height:60px"></textarea>
    <label>Target Audience</label>
    <input id="dist-audience" placeholder="Indie founders, SaaS builders..."/>
    <label>CTA URL</label>
    <input id="dist-cta-url" placeholder="https://myproduct.com"/>
    <div class="btn-row">
      <button class="btn btn-primary btn-full" id="genShareBtn" onclick="generateShareMessages()">&#x1F4E3; Generate Share Messages</button>
    </div>
    <div class="error-box" id="distError"></div>
  </div>

  <div id="dist-results" style="display:none" class="card">
    <div class="card-title">Share Messages</div>
    <div id="dist-messages"></div>
  </div>
</div>

<!-- ============================================================ TAB: REVENUE -->
<div class="tab-content" id="pane-revenue">
  <h2 style="font-size:1.3rem;color:#fff;margin-bottom:1.2rem">&#x1F4B0; Revenue Intelligence</h2>

  <div class="card">
    <div class="card-title">Project Revenue Report</div>
    <label>Select Project</label>
    <select id="revenue-project-select">
      <option value="">Loading projects...</option>
    </select>
    <div class="btn-row">
      <button class="btn btn-primary" id="getReportBtn" onclick="getRevenueReport()">&#x1F4CA; Get Report</button>
      <button class="btn btn-ghost" id="bizOutputBtn" onclick="getBusinessOutput()">&#x1F4CB; Business Output</button>
    </div>
    <div class="error-box" id="revenueError"></div>
  </div>

  <div id="revenue-result" style="display:none" class="card">
    <div class="card-title">Report</div>
    <pre id="revenue-content" style="font-size:.82rem;color:#ccc;white-space:pre-wrap;word-break:break-word"></pre>
  </div>
</div>

<footer>AI-DAN Managing Director v{version} &mdash; Monetization-first decision engine</footer>

<script>
/* ============================================================ GLOBALS */
var _lastAnalysis=null;
var _dashRefreshTimer=null;

/* ============================================================ TAB SWITCHING */
function switchTab(name){
  document.querySelectorAll('.tab-content').forEach(function(el){el.classList.remove('active')});
  document.querySelectorAll('.tabbar button').forEach(function(el){el.classList.remove('active')});
  document.getElementById('pane-'+name).classList.add('active');
  document.getElementById('tab-'+name).classList.add('active');
  if(name==='dashboard'){loadDashboard();startDashRefresh()}else{stopDashRefresh()}
  if(name==='portfolio'){loadPortfolio()}
  if(name==='factory'){loadFactory()}
  if(name==='revenue'){loadRevenueProjects()}
}

/* ============================================================ TOAST */
function toast(msg,type){
  type=type||'info';
  var c=document.getElementById('toast-container');
  var t=document.createElement('div');
  t.className='toast '+type;
  t.textContent=msg;
  c.appendChild(t);
  setTimeout(function(){if(t.parentNode)t.parentNode.removeChild(t)},3000);
}

/* ============================================================ HELPERS */
function esc(s){if(!s)return'';var d=document.createElement('div');
  d.appendChild(document.createTextNode(String(s)));return d.innerHTML}
var escapeHtml=esc;

function statusBadge(s){
  var map={idea:'badge-idea',validated:'badge-validated',approved:'badge-approved',
    building:'badge-building',launched:'badge-launched',failed:'badge-failed',
    hold:'badge-hold',queued:'badge-hold'};
  var cls=map[(s||'').toLowerCase()]||'badge-idea';
  return '<span class="badge '+cls+'">'+esc(s||'unknown')+'</span>';
}

function btnSpin(id,show){
  var b=document.getElementById(id);if(!b)return;
  if(show){b.disabled=true;b._orig=b.innerHTML;
    b.innerHTML='<span class="spinner"></span> Working...'}
  else{b.disabled=false;if(b._orig)b.innerHTML=b._orig}
}

/* ============================================================ DASHBOARD */
function loadDashboard(){
  fetch('/portfolio/projects').then(function(r){return r.ok?r.json():[]}).then(function(projects){
    var counts={total:0,idea:0,approved:0,building:0,launched:0,failed:0};
    projects.forEach(function(p){
      counts.total++;
      var s=(p.status||'idea').toLowerCase();
      if(s==='idea'||s==='validated')counts.idea++;
      else if(s==='approved')counts.approved++;
      else if(s==='building'||s==='queued')counts.building++;
      else if(s==='launched'||s==='deployed'||s==='live')counts.launched++;
      else if(s==='failed')counts.failed++;
    });
    document.getElementById('stat-total').textContent=counts.total;
    document.getElementById('stat-idea').textContent=counts.idea;
    document.getElementById('stat-approved').textContent=counts.approved;
    document.getElementById('stat-building').textContent=counts.building;
    document.getElementById('stat-launched').textContent=counts.launched;
    document.getElementById('stat-failed').textContent=counts.failed;

    /* Health indicator */
    var hi=document.getElementById('health-indicator');
    if(counts.failed>0){hi.className='health red';hi.textContent='\\u25CF '+counts.failed+' Failed'}
    else if(counts.building>0){hi.className='health yellow';hi.textContent='\\u25CF Building'}
    else if(counts.launched>0){hi.className='health green';hi.textContent='\\u25CF '+counts.launched+' Live'}
    else{hi.className='health green';hi.textContent='\\u25CF Healthy'}

    /* Recent projects table */
    var wrap=document.getElementById('dash-projects-wrap');
    if(!projects.length){wrap.innerHTML='<div class="empty-state">No projects yet. Analyze an idea to get started.</div>';return}
    var recent=projects.slice(-5).reverse();
    var h='<div class="tbl-wrap"><table><thead><tr><th>Name</th><th>Status</th><th>Actions</th></tr></thead><tbody>';
    recent.forEach(function(p){
      h+='<tr><td>'+esc(p.name||p.project_id)+'</td>';
      h+='<td>'+statusBadge(p.status)+'</td>';
      h+='<td><div style="display:flex;gap:.35rem;flex-wrap:wrap">';
      h+='<button class="btn btn-ghost" style="padding:.25rem .6rem;font-size:.78rem" onclick="switchTab(\'portfolio\')">&#x1F4CB; View</button>';
      h+='</div></td></tr>';
    });
    h+='</tbody></table></div>';
    wrap.innerHTML=h;
  }).catch(function(){
    document.getElementById('dash-projects-wrap').innerHTML='<div class="empty-state" style="color:#666">Could not load projects.</div>';
  });
}

function startDashRefresh(){
  stopDashRefresh();
  _dashRefreshTimer=setInterval(loadDashboard,30000);
}
function stopDashRefresh(){
  if(_dashRefreshTimer){clearInterval(_dashRefreshTimer);_dashRefreshTimer=null}
}

/* ============================================================ ANALYZE */
async function analyze(){
  var idea=document.getElementById('idea').value.trim();
  if(!idea){
    var e=document.getElementById('errorBox');
    e.textContent='Please enter an idea.';e.style.display='block';return;
  }
  btnSpin('analyzeBtn',true);
  document.getElementById('loading').style.display='block';
  document.getElementById('analyze-result').style.display='none';
  document.getElementById('analyze-actions').style.display='none';
  document.getElementById('errorBox').style.display='none';

  var body={
    idea:idea,
    problem:document.getElementById('problem').value.trim(),
    target_user:document.getElementById('target_user').value.trim(),
    monetization_model:document.getElementById('monetization_model').value,
    competition_level:document.getElementById('competition_level').value,
    difficulty:document.getElementById('difficulty').value,
    time_to_revenue:document.getElementById('time_to_revenue').value,
    differentiation:document.getElementById('differentiation').value.trim()
  };

  try{
    var resp=await fetch('/api/analyze/',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!resp.ok){var er=await resp.json();throw new Error(er.detail||resp.statusText)}
    var d=await resp.json();
    _lastAnalysis=d;
    renderAnalysisResult(d);
    document.getElementById('analyze-actions').style.display='block';
  }catch(err){
    var eb=document.getElementById('errorBox');
    eb.textContent='Error: '+err.message;eb.style.display='block';
  }finally{
    btnSpin('analyzeBtn',false);
    document.getElementById('loading').style.display='none';
  }
}

function renderAnalysisResult(d){
  var r=document.getElementById('analyze-result');
  var sc=d.total_score||0;
  var pct=(sc/10*100).toFixed(0);
  var cls=sc>=8?'high':sc>=6?'med':'low';
  var dec=d.final_decision||'UNKNOWN';

  var h='<div class="card">';
  h+='<div style="display:flex;justify-content:space-between;align-items:center">';
  h+='<span class="decision-badge decision-'+dec+'">'+dec+'</span>';
  h+='<span style="font-size:1.4rem;font-weight:700">'+sc.toFixed(1)+'<span style="font-size:.85rem;color:#888">/10</span></span>';
  h+='</div>';
  h+='<div class="score-bar"><div class="score-fill score-'+cls+'" style="width:'+pct+'%"></div></div>';
  h+='<p style="font-size:.82rem;color:#aaa;margin-top:.3rem">'+esc(d.score_decision_reason||d.next_step||'')+'</p>';

  if(d.validation_blocking&&d.validation_blocking.length){
    h+='<div class="section"><h3>&#x1F6D1; Blocking Issues</h3>';
    d.validation_blocking.forEach(function(b){h+='<p class="blocking">• '+esc(b)+'</p>'});
    h+='</div>';
  }
  if(d.validation_reasons&&d.validation_reasons.length){
    h+='<div class="section"><h3>&#x2705; Validation</h3>';
    d.validation_reasons.forEach(function(v){h+='<p class="reason-line">• '+esc(v)+'</p>'});
    h+='</div>';
  }
  if(d.score_dimensions&&d.score_dimensions.length){
    h+='<div class="section"><h3>&#x1F4CA; Score Breakdown</h3>';
    d.score_dimensions.forEach(function(dim){
      var dp=(dim.score/2*100).toFixed(0);
      var dc=dim.score>=1.5?'high':dim.score>=1?'med':'low';
      h+='<div class="detail-row"><span class="detail-label">'+esc(dim.name)+'</span><span class="detail-value">'+dim.score.toFixed(1)+'/2</span></div>';
      h+='<div class="score-bar"><div class="score-fill score-'+dc+'" style="width:'+dp+'%"></div></div>';
      h+='<p style="font-size:.78rem;color:#666;margin-bottom:.3rem">'+esc(dim.reason)+'</p>';
    });
    h+='</div>';
  }
  var o=d.offer||{};
  if(o.decision==='generated'){
    h+='<div class="section"><h3>&#x1F4B0; Offer</h3>';
    h+=dRow('Pricing',o.pricing);h+=dRow('Model',o.pricing_model);
    h+=dRow('Delivery',o.delivery_method);h+=dRow('Value',o.value_proposition);
    h+=dRow('CTA',o.cta);h+='</div>';
  }
  var di=d.distribution||{};
  if(di.decision==='generated'){
    h+='<div class="section"><h3>&#x1F680; Distribution</h3>';
    h+=dRow('Channel',di.primary_channel);h+=dRow('Acquisition',di.acquisition_method);
    h+=dRow('First 10 Users',di.first_10_users_plan);h+=dRow('Messaging',di.messaging);
    h+='</div>';
  }
  h+='<div class="section"><h3>&#x27A1;&#xFE0F; Next Step</h3>';
  h+='<p style="font-size:.85rem">'+esc(d.next_step||'Awaiting analysis.')+'</p></div>';
  h+='</div>';
  r.innerHTML=h;r.style.display='block';
}

function dRow(l,v){if(!v)return'';
  return'<div class="detail-row"><span class="detail-label">'+esc(l)+'</span><span class="detail-value">'+esc(v)+'</span></div>'}

async function createProjectFromAnalysis(){
  if(!_lastAnalysis){toast('Run analysis first','error');return}
  btnSpin('createProjectBtn',true);
  document.getElementById('actionError').style.display='none';
  document.getElementById('actionInfo').style.display='none';
  var name=document.getElementById('idea').value.trim().slice(0,80)||'Untitled';
  try{
    var resp=await fetch('/portfolio/projects',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name:name,description:document.getElementById('problem').value.trim(),
        status:'idea',metadata:{analysis:_lastAnalysis}})});
    if(!resp.ok){var e=await resp.json();throw new Error(e.detail||resp.statusText)}
    var p=await resp.json();
    var ib=document.getElementById('actionInfo');
    ib.textContent='Project created: '+p.project_id;ib.style.display='block';
    toast('Project created!','success');
  }catch(err){
    var eb=document.getElementById('actionError');
    eb.textContent='Error: '+err.message;eb.style.display='block';
    toast('Failed: '+err.message,'error');
  }finally{btnSpin('createProjectBtn',false)}
}

async function saveDraftFromAnalysis(){
  if(!_lastAnalysis){toast('Run analysis first','error');return}
  btnSpin('saveDraftBtn',true);
  try{
    var key='aidan_draft_'+Date.now();
    localStorage.setItem(key,JSON.stringify({idea:document.getElementById('idea').value,
      analysis:_lastAnalysis,saved:new Date().toISOString()}));
    toast('Draft saved to browser storage','success');
    var ib=document.getElementById('actionInfo');
    ib.textContent='Draft saved locally (key: '+key+').';ib.style.display='block';
  }catch(err){
    toast('Save failed: '+err.message,'error');
  }finally{btnSpin('saveDraftBtn',false)}
}

/* ============================================================ PORTFOLIO */
function loadPortfolio(){
  var wrap=document.getElementById('portfolio-wrap');
  wrap.innerHTML='<div class="empty-state"><span class="spinner"></span> Loading...</div>';
  fetch('/portfolio/projects').then(function(r){return r.ok?r.json():[]}).then(function(projects){
    if(!projects.length){wrap.innerHTML='<div class="empty-state">No projects yet. Add one below.</div>';return}
    var h='<div class="tbl-wrap"><table><thead><tr>';
    h+='<th>Name</th><th>Status</th><th>Description</th><th>Created</th><th>Actions</th>';
    h+='</tr></thead><tbody>';
    projects.forEach(function(p){
      var created=p.created_at?new Date(p.created_at).toLocaleDateString():'—';
      h+='<tr>';
      h+='<td style="font-weight:500">'+esc(p.name||p.project_id)+'</td>';
      h+='<td>'+statusBadge(p.status)+'</td>';
      h+='<td style="color:#888;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(p.description||'—')+'</td>';
      h+='<td style="color:#666;font-size:.8rem">'+esc(created)+'</td>';
      h+='<td><div style="display:flex;gap:.3rem;flex-wrap:wrap">';
      var s=(p.status||'').toLowerCase();
      if(s==='idea'||s==='validated')
        h+='<button class="btn btn-success" style="padding:.25rem .55rem;font-size:.75rem" onclick="approveProject(\''+esc(p.project_id)+'\')">&#x2714; Approve</button>';
      if(s==='approved'||s==='validated'||s==='idea')
        h+='<button class="btn btn-warning" style="padding:.25rem .55rem;font-size:.75rem" onclick="buildProject(\''+esc(p.project_id)+'\')">&#x1F680; Build</button>';
      h+='<button class="btn btn-ghost" style="padding:.25rem .55rem;font-size:.75rem" onclick="shareProject(\''+esc(p.name||p.project_id)+'\')">&#x1F4E3; Share</button>';
      if(p.repo_url)h+='<a href="'+esc(p.repo_url)+'" target="_blank" class="btn btn-ghost" style="padding:.25rem .55rem;font-size:.75rem">&#x1F517; Repo</a>';
      if(p.deploy_url)h+='<a href="'+esc(p.deploy_url)+'" target="_blank" class="btn btn-ghost" style="padding:.25rem .55rem;font-size:.75rem">&#x1F310; Deploy</a>';
      h+='</div></td></tr>';
    });
    h+='</tbody></table></div>';
    wrap.innerHTML=h;
  }).catch(function(){
    wrap.innerHTML='<div class="empty-state" style="color:#666">Could not load portfolio.</div>';
  });
}

async function approveProject(pid){
  try{
    var resp=await fetch('/portfolio/projects/'+encodeURIComponent(pid)+'/transition',
      {method:'POST',headers:{'Content-Type':'application/json'},
       body:JSON.stringify({status:'approved'})});
    if(!resp.ok){var e=await resp.json();throw new Error(e.detail||resp.statusText)}
    toast('Project approved!','success');loadPortfolio();loadDashboard();
  }catch(err){toast('Approve failed: '+err.message,'error')}
}

async function buildProject(pid){
  try{
    var resp=await fetch('/portfolio/projects',{method:'GET'});
    var projects=resp.ok?await resp.json():[];
    switchTab('factory');
    document.getElementById('factory-project-id').value=pid;
    document.getElementById('factory-dry-run').checked=false;
    toast('Project loaded in Factory tab. Click Trigger Build.','info');
  }catch(err){toast('Error: '+err.message,'error')}
}

function shareProject(name){
  switchTab('distribution');
  document.getElementById('dist-project-name').value=name;
  toast('Fill in the share form and generate messages.','info');
}

async function addProject(){
  var name=document.getElementById('new-proj-name').value.trim();
  if(!name){
    var e=document.getElementById('addProjError');
    e.textContent='Project name is required.';e.style.display='block';return;
  }
  btnSpin('addProjBtn',true);
  document.getElementById('addProjError').style.display='none';
  try{
    var resp=await fetch('/portfolio/projects',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name:name,description:document.getElementById('new-proj-desc').value.trim(),
        status:'idea'})});
    if(!resp.ok){var e=await resp.json();throw new Error(e.detail||resp.statusText)}
    toast('Project added!','success');
    document.getElementById('new-proj-name').value='';
    document.getElementById('new-proj-desc').value='';
    loadPortfolio();loadDashboard();
  }catch(err){
    var eb=document.getElementById('addProjError');
    eb.textContent='Error: '+err.message;eb.style.display='block';
    toast('Failed: '+err.message,'error');
  }finally{btnSpin('addProjBtn',false)}
}

/* ============================================================ FACTORY */
function loadFactory(){
  var wrap=document.getElementById('factory-runs-wrap');
  wrap.innerHTML='<div class="empty-state"><span class="spinner"></span> Loading...</div>';
  fetch('/factory/runs').then(function(r){return r.ok?r.json():[]}).then(function(runs){
    if(!runs.length){wrap.innerHTML='<div class="empty-state">No factory runs yet.</div>';return}
    var h='<div class="tbl-wrap"><table><thead><tr>';
    h+='<th>Run ID</th><th>Project</th><th>Status</th><th>Repo</th><th>Deploy</th>';
    h+='</tr></thead><tbody>';
    runs.forEach(function(r){
      h+='<tr>';
      h+='<td style="font-size:.78rem;color:#888">'+esc((r.run_id||'').slice(0,12))+'…</td>';
      h+='<td>'+esc(r.project_id||'—')+'</td>';
      h+='<td>'+statusBadge(r.status)+'</td>';
      h+='<td>'+(r.repo_url?'<a href="'+esc(r.repo_url)+'" target="_blank" class="btn btn-ghost" style="padding:.2rem .5rem;font-size:.75rem">&#x1F517; Repo</a>':'—')+'</td>';
      h+='<td>'+(r.deploy_url?'<a href="'+esc(r.deploy_url)+'" target="_blank" class="btn btn-ghost" style="padding:.2rem .5rem;font-size:.75rem">&#x1F310; Deploy</a>':'—')+'</td>';
      h+='</tr>';
    });
    h+='</tbody></table></div>';
    wrap.innerHTML=h;
  }).catch(function(){
    wrap.innerHTML='<div class="empty-state" style="color:#666">Could not load factory runs.</div>';
  });
}

async function triggerBuild(){
  var pid=document.getElementById('factory-project-id').value.trim();
  if(!pid){
    var e=document.getElementById('factoryError');
    e.textContent='Project ID is required.';e.style.display='block';return;
  }
  btnSpin('triggerBuildBtn',true);
  document.getElementById('factoryError').style.display='none';
  document.getElementById('factoryInfo').style.display='none';
  var template=document.getElementById('factory-template').value;
  var dryRun=document.getElementById('factory-dry-run').checked;

  try{
    var brief={
      project_id:pid,idea_id:'idea-'+pid,hypothesis:'Build '+pid,
      target_user:'operator',problem:'Build request',solution:'Factory build',
      mvp_scope:['Core build'],acceptance_criteria:['Build completes'],
      landing_page_requirements:['CTA present'],cta:'Get Started',
      pricing_hint:'TBD',deployment_target:'vercel',
      command_bundle:{template:template},
      feature_flags:{dry_run:dryRun,live_factory:!dryRun}
    };
    var resp=await fetch('/factory/runs',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({build_brief:brief,dry_run:dryRun})});
    if(!resp.ok){var er=await resp.json();throw new Error(er.detail||resp.statusText)}
    var result=await resp.json();
    var ib=document.getElementById('factoryInfo');
    ib.textContent='Build triggered! Run ID: '+(result.run_id||'unknown')+' — Status: '+result.status;
    ib.style.display='block';
    toast('Build triggered!','success');
    loadFactory();
  }catch(err){
    var eb=document.getElementById('factoryError');
    eb.textContent='Error: '+err.message;eb.style.display='block';
    toast('Build failed: '+err.message,'error');
  }finally{btnSpin('triggerBuildBtn',false)}
}

/* ============================================================ DISTRIBUTION */
async function generateShareMessages(){
  var name=document.getElementById('dist-project-name').value.trim();
  var vp=document.getElementById('dist-value-prop').value.trim();
  if(!name||!vp){
    var e=document.getElementById('distError');
    e.textContent='Project name and value proposition are required.';e.style.display='block';return;
  }
  btnSpin('genShareBtn',true);
  document.getElementById('distError').style.display='none';
  document.getElementById('dist-results').style.display='none';

  var body={
    project_name:name,
    value_proposition:vp,
    target_audience:document.getElementById('dist-audience').value.trim(),
    cta_url:document.getElementById('dist-cta-url').value.trim()
  };

  try{
    var resp=await fetch('/api/distribution/share-messages',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!resp.ok){var er=await resp.json();throw new Error(er.detail||resp.statusText)}
    var data=await resp.json();
    renderShareMessages(data);
  }catch(err){
    var eb=document.getElementById('distError');
    eb.textContent='Error: '+err.message;eb.style.display='block';
    toast('Failed: '+err.message,'error');
  }finally{btnSpin('genShareBtn',false)}
}

function renderShareMessages(data){
  var container=document.getElementById('dist-messages');
  var messages=data.messages||data.platforms||data||{};
  var h='';
  var entries=Array.isArray(messages)?messages:Object.entries(messages).map(function(kv){return{platform:kv[0],message:kv[1]}});
  entries.forEach(function(item){
    var platform=item.platform||item.channel||'Platform';
    var msg=item.message||item.content||item.text||JSON.stringify(item);
    var uid='copy-'+platform.replace(/\\W/g,'');
    h+='<div class="platform-block">';
    h+='<div style="display:flex;justify-content:space-between;align-items:center">';
    h+='<div class="platform-name">'+esc(platform)+'</div>';
    h+='<button class="copy-btn" id="'+uid+'" data-msg="'+esc(msg)+'" onclick="copyMsgById(\''+uid+'\')">Copy</button>';
    h+='</div>';
    h+='<div class="platform-msg" id="msg-'+uid+'">'+esc(msg)+'</div>';
    h+='</div>';
  });
  if(!h)h='<p style="color:#666;font-size:.85rem">No messages returned.</p>';
  container.innerHTML=h;
  document.getElementById('dist-results').style.display='block';
}

function copyMsgById(uid){
  var btn=document.getElementById(uid);
  var text=btn?btn.getAttribute('data-msg'):'';
  navigator.clipboard.writeText(text).then(function(){
    if(btn){var orig=btn.textContent;btn.textContent='Copied!';
      setTimeout(function(){btn.textContent=orig},1500)}
    toast('Copied to clipboard','success');
  }).catch(function(){toast('Copy failed','error')});
}

function copyMsg(uid,text){
  navigator.clipboard.writeText(text).then(function(){
    var b=document.getElementById(uid);
    if(b){var orig=b.textContent;b.textContent='Copied!';
      setTimeout(function(){b.textContent=orig},1500)}
    toast('Copied to clipboard','success');
  }).catch(function(){toast('Copy failed','error')});
}

/* ============================================================ REVENUE */
function loadRevenueProjects(){
  var sel=document.getElementById('revenue-project-select');
  fetch('/portfolio/projects').then(function(r){return r.ok?r.json():[]}).then(function(projects){
    sel.innerHTML='<option value="">Select a project...</option>';
    projects.forEach(function(p){
      var opt=document.createElement('option');
      opt.value=p.project_id;
      opt.textContent=(p.name||p.project_id);
      sel.appendChild(opt);
    });
  }).catch(function(){sel.innerHTML='<option value="">Could not load projects</option>'});
}

async function getRevenueReport(){
  var pid=document.getElementById('revenue-project-select').value;
  if(!pid){toast('Select a project first','error');return}
  btnSpin('getReportBtn',true);
  document.getElementById('revenueError').style.display='none';
  try{
    var resp=await fetch('/revenue/'+encodeURIComponent(pid)+'/learning-report');
    if(!resp.ok){var e=await resp.json();throw new Error(e.detail||resp.statusText)}
    var data=await resp.json();
    document.getElementById('revenue-content').textContent=JSON.stringify(data,null,2);
    document.getElementById('revenue-result').style.display='block';
  }catch(err){
    var eb=document.getElementById('revenueError');
    eb.textContent='Error: '+err.message;eb.style.display='block';
    toast('Failed: '+err.message,'error');
  }finally{btnSpin('getReportBtn',false)}
}

async function getBusinessOutput(){
  var pid=document.getElementById('revenue-project-select').value;
  if(!pid){toast('Select a project first','error');return}
  btnSpin('bizOutputBtn',true);
  document.getElementById('revenueError').style.display='none';
  try{
    var resp=await fetch('/revenue/'+encodeURIComponent(pid)+'/business-output');
    if(!resp.ok){var e=await resp.json();throw new Error(e.detail||resp.statusText)}
    var data=await resp.json();
    document.getElementById('revenue-content').textContent=JSON.stringify(data,null,2);
    document.getElementById('revenue-result').style.display='block';
  }catch(err){
    var eb=document.getElementById('revenueError');
    eb.textContent='Error: '+err.message;eb.style.display='block';
    toast('Failed: '+err.message,'error');
  }finally{btnSpin('bizOutputBtn',false)}
}

/* ============================================================ INIT */
loadDashboard();
startDashRefresh();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def root_ui() -> HTMLResponse:
    """Serve the root idea-analysis UI."""
    html = _ROOT_HTML.replace("{version}", _VERSION)
    return HTMLResponse(content=html)
