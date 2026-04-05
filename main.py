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
<title>AI-DAN Managing Director</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
background:#0a0a0a;color:#e0e0e0;min-height:100vh;display:flex;flex-direction:column}
/* Tab bar */
.tabbar{position:sticky;top:0;z-index:100;background:#111;border-bottom:1px solid #333;
display:flex;overflow-x:auto;white-space:nowrap;padding:0 1rem}
.tabbar button{background:none;border:none;color:#888;padding:.75rem 1rem;font-size:.9rem;
cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap;transition:all .2s}
.tabbar button:hover{color:#e0e0e0}
.tabbar button.active{color:#5b6ef7;border-bottom-color:#5b6ef7}
/* Layout */
.page{flex:1;padding:1.5rem 1rem;max-width:1100px;width:100%;margin:0 auto}
.header{text-align:center;padding:1rem 0 1.5rem}
.header h1{font-size:1.6rem;color:#fff;margin-bottom:.2rem}
.header p{color:#888;font-size:.9rem}
/* Tabs */
.tab{display:none}.tab.active{display:block}
/* Cards */
.card{background:#1a1a2e;border:1px solid #333;border-radius:12px;padding:1.5rem;margin-bottom:1.2rem}
.card-title{font-size:1rem;font-weight:600;margin-bottom:1rem;color:#e0e0e0}
/* Stat cards */
.stats{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:.8rem;margin-bottom:1.2rem}
.stat{background:#1a1a2e;border:1px solid #333;border-radius:10px;padding:1rem;text-align:center}
.stat-val{font-size:2rem;font-weight:700;color:#5b6ef7}
.stat-lbl{font-size:.8rem;color:#888;margin-top:.2rem}
.health{display:flex;align-items:center;gap:.5rem;font-size:.95rem;margin-bottom:1.2rem}
/* Quick actions */
.quick-actions{display:flex;gap:.8rem;flex-wrap:wrap}
/* Forms */
label{display:block;font-size:.85rem;color:#aaa;margin-bottom:.3rem;margin-top:.8rem}
label:first-child{margin-top:0}
textarea,input,select{width:100%;padding:.6rem .8rem;border-radius:8px;border:1px solid #444;
background:#111;color:#e0e0e0;font-size:.9rem;font-family:inherit}
textarea{resize:vertical;min-height:80px}
textarea:focus,input:focus,select:focus{outline:none;border-color:#5b6ef7}
.row{display:grid;grid-template-columns:1fr 1fr;gap:.8rem}
/* Buttons */
.btn{padding:.55rem 1rem;border:none;border-radius:8px;font-size:.88rem;font-weight:600;
cursor:pointer;transition:all .2s;display:inline-flex;align-items:center;gap:.4rem}
.btn:disabled{background:#333!important;color:#666!important;cursor:not-allowed}
.btn-primary{background:#5b6ef7;color:#fff}
.btn-primary:hover:not(:disabled){background:#4a5ce6}
.btn-success{background:#16a34a;color:#fff}
.btn-success:hover:not(:disabled){background:#15803d}
.btn-warning{background:#d97706;color:#fff}
.btn-warning:hover:not(:disabled){background:#b45309}
.btn-danger{background:#dc2626;color:#fff}
.btn-danger:hover:not(:disabled){background:#b91c1c}
.btn-ghost{background:#222;color:#ccc;border:1px solid #444}
.btn-ghost:hover:not(:disabled){background:#333}
.btn-full{width:100%;justify-content:center;margin-top:1rem}
/* Tables */
.tbl{width:100%;border-collapse:collapse;font-size:.875rem}
.tbl th{text-align:left;padding:.6rem .8rem;color:#888;border-bottom:1px solid #333;font-weight:500}
.tbl td{padding:.6rem .8rem;border-bottom:1px solid #222;vertical-align:middle}
.tbl tr:last-child td{border-bottom:none}
.tbl-wrap{overflow-x:auto}
.empty{text-align:center;color:#666;padding:2rem;font-size:.9rem}
/* Badges */
.badge{display:inline-block;padding:.2rem .55rem;border-radius:5px;font-size:.75rem;font-weight:600}
.badge-idea{background:#333;color:#aaa}
.badge-review{background:#444;color:#bbb}
.badge-approved{background:#1e3a6e;color:#93c5fd}
.badge-queued{background:#1e3a6e;color:#93c5fd}
.badge-building{background:#422006;color:#fcd34d}
.badge-launched{background:#14532d;color:#86efac}
.badge-killed{background:#450a0a;color:#fca5a5}
.badge-succeeded{background:#14532d;color:#86efac}
.badge-failed{background:#450a0a;color:#fca5a5}
.badge-running{background:#422006;color:#fcd34d}
.badge-dry_run{background:#333;color:#aaa}
/* Result / analyze */
.decision-badge{display:inline-block;padding:.3rem .8rem;border-radius:6px;
font-weight:700;font-size:.9rem;margin:.5rem 0}
.decision-APPROVED{background:#16a34a;color:#fff}
.decision-HOLD{background:#d97706;color:#fff}
.decision-REJECTED{background:#dc2626;color:#fff}
.score-bar{height:8px;border-radius:4px;background:#333;margin:.3rem 0;overflow:hidden}
.score-fill{height:100%;border-radius:4px;transition:width .5s}
.score-high{background:#16a34a}.score-med{background:#d97706}.score-low{background:#dc2626}
.section{margin-top:1rem;padding-top:1rem;border-top:1px solid #333}
.section h3{font-size:.95rem;color:#aaa;margin-bottom:.5rem}
.detail-row{display:flex;justify-content:space-between;padding:.25rem 0;font-size:.85rem}
.detail-label{color:#888}.detail-value{color:#e0e0e0;text-align:right;max-width:60%}
.error-box{background:#2d1111;border:1px solid #dc2626;border-radius:8px;padding:1rem;
color:#fca5a5;margin-top:1rem;display:none}
.loading{display:none;text-align:center;padding:2rem;color:#888}
.loading .spinner{display:inline-block;width:24px;height:24px;border:3px solid #333;
border-top-color:#5b6ef7;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.tag{display:inline-block;background:#222;border:1px solid #444;border-radius:4px;
padding:.15rem .4rem;font-size:.75rem;margin:.15rem .1rem;color:#ccc}
.blocking{color:#fca5a5;font-size:.85rem;margin:.2rem 0}
.reason{color:#86efac;font-size:.85rem;margin:.2rem 0}
/* Platform cards */
.platform-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:.8rem}
.platform-card{background:#111;border:1px solid #333;border-radius:8px;padding:1rem}
.platform-name{font-size:.8rem;font-weight:700;color:#5b6ef7;text-transform:uppercase;
letter-spacing:.05em;margin-bottom:.5rem}
.platform-text{font-size:.85rem;color:#ccc;white-space:pre-wrap;word-break:break-word;
max-height:120px;overflow-y:auto}
/* Toast */
#toastContainer{position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;
display:flex;flex-direction:column;gap:.5rem;max-width:320px}
.toast{padding:.75rem 1rem;border-radius:8px;font-size:.88rem;animation:fadein .2s ease}
.toast-success{background:#14532d;border:1px solid #16a34a;color:#86efac}
.toast-error{background:#450a0a;border:1px solid #dc2626;color:#fca5a5}
@keyframes fadein{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
/* Inline form */
.inline-form{background:#111;border:1px solid #333;border-radius:8px;padding:1rem;margin-top:.8rem;display:none}
/* Spinner inside button */
.btn-spinner{display:none;width:14px;height:14px;border:2px solid rgba(255,255,255,.3);
border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite}
/* Footer */
footer{text-align:center;color:#555;font-size:.8rem;padding:1.5rem;border-top:1px solid #1a1a1a}
/* Mobile */
@media(max-width:600px){
  .row{grid-template-columns:1fr}
  .stats{grid-template-columns:1fr 1fr}
  .quick-actions{flex-direction:column}
  .platform-grid{grid-template-columns:1fr}
}
</style>
</head>
<body>
<nav class="tabbar">
  <button class="active" onclick="showTab('dashboard')">&#x1F4CA; Dashboard</button>
  <button onclick="showTab('analyze')">&#x1F4A1; Analyze Idea</button>
  <button onclick="showTab('portfolio')">&#x1F4E6; Portfolio</button>
  <button onclick="showTab('factory')">&#x1F3ED; Factory</button>
  <button onclick="showTab('distribution')">&#x1F4E3; Distribution</button>
  <button onclick="showTab('revenue')">&#x1F4B0; Revenue</button>
</nav>

<div class="page">
<div class="header">
  <h1>&#x1F9E0; AI-DAN Managing Director</h1>
  <p>Idea &rarr; Validate &rarr; Score &rarr; Decide &rarr; Offer &rarr; Distribute</p>
</div>

<!-- ===== DASHBOARD TAB ===== -->
<div id="tab-dashboard" class="tab active">
  <div id="statsGrid" class="stats">
    <div class="stat"><div class="stat-val" id="statTotal">-</div><div class="stat-lbl">Total Projects</div></div>
    <div class="stat"><div class="stat-val" id="statApproved">-</div><div class="stat-lbl">Approved</div></div>
    <div class="stat"><div class="stat-val" id="statBuilding">-</div><div class="stat-lbl">Building</div></div>
    <div class="stat"><div class="stat-val" id="statLaunched">-</div><div class="stat-lbl">Launched</div></div>
  </div>
  <div class="health" id="healthIndicator"><span>&#x26AA;</span><span>Loading system health...</span></div>
  <div class="quick-actions">
    <button class="btn btn-primary" onclick="showTab('analyze')">&#x2B50; New Idea</button>
    <button class="btn btn-ghost" onclick="showTab('portfolio')">&#x1F4E6; View Projects</button>
    <button class="btn btn-ghost" onclick="showTab('factory')">&#x1F3ED; Factory Runs</button>
  </div>
</div>

<!-- ===== ANALYZE TAB ===== -->
<div id="tab-analyze" class="tab">
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

<button class="btn btn-primary btn-full" id="analyzeBtn" onclick="analyze()">
  <span class="btn-spinner" id="analyzeSpinner"></span>&#x1F50D; Analyze Idea
</button>
</div>

<div class="loading" id="loading">
<div class="spinner"></div>
<p style="margin-top:.8rem">Running full pipeline analysis...</p>
</div>

<div class="error-box" id="errorBox"></div>

<div id="result" class="card" style="display:none"></div>
<div id="analyzeActions" style="display:none;margin-top:.5rem">
  <div style="display:flex;gap:.8rem;flex-wrap:wrap">
    <button class="btn btn-success" onclick="createProject()">&#x2705; Create Project</button>
    <button class="btn btn-ghost" onclick="saveDraft()">&#x1F4BE; Save Draft</button>
  </div>
</div>
</div>

<!-- ===== PORTFOLIO TAB ===== -->
<div id="tab-portfolio" class="tab">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;flex-wrap:wrap;gap:.5rem">
    <span style="font-size:1.1rem;font-weight:600">Projects</span>
    <button class="btn btn-primary" onclick="toggleAddProject()">&#x2B;  Add Project</button>
  </div>
  <div id="addProjectForm" class="inline-form">
    <label for="newProjName">Project Name</label>
    <input id="newProjName" placeholder="My SaaS idea"/>
    <label for="newProjDesc">Description</label>
    <textarea id="newProjDesc" placeholder="Brief description..." style="min-height:60px"></textarea>
    <div style="display:flex;gap:.6rem;margin-top:.8rem">
      <button class="btn btn-primary" onclick="addProject()">Create</button>
      <button class="btn btn-ghost" onclick="toggleAddProject()">Cancel</button>
    </div>
  </div>
  <div class="card" style="padding:0">
    <div class="tbl-wrap">
      <table class="tbl" id="portfolioTable">
        <thead><tr>
          <th>Name</th><th>Status</th><th>Description</th><th>Created</th><th>Actions</th>
        </tr></thead>
        <tbody id="portfolioBody"><tr><td colspan="5" class="empty">Loading...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- ===== FACTORY TAB ===== -->
<div id="tab-factory" class="tab">
  <div class="card">
    <div class="card-title">Trigger Build</div>
    <label for="buildProjectId">Project ID</label>
    <input id="buildProjectId" placeholder="prj-abc123"/>
    <label for="buildTemplate">Template</label>
    <select id="buildTemplate">
      <option value="saas-template">SaaS Template</option>
      <option value="landing-page">Landing Page</option>
    </select>
    <div style="display:flex;align-items:center;gap:.5rem;margin-top:.8rem">
      <input type="checkbox" id="buildDryRun" checked style="width:auto"/>
      <label for="buildDryRun" style="margin:0;font-size:.9rem;color:#ccc">Dry Run (safe test)</label>
    </div>
    <button class="btn btn-primary btn-full" id="triggerBuildBtn" onclick="triggerBuild()">
      <span class="btn-spinner" id="buildSpinner"></span>&#x1F680; Trigger Build
    </button>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.8rem">
    <span style="font-size:1rem;font-weight:600">Recent Runs</span>
    <button class="btn btn-ghost" onclick="loadFactoryRuns()">&#x1F504; Refresh</button>
  </div>
  <div class="card" style="padding:0">
    <div class="tbl-wrap">
      <table class="tbl" id="factoryTable">
        <thead><tr><th>Run ID</th><th>Project</th><th>Status</th><th>Deploy URL</th><th>Error</th></tr></thead>
        <tbody id="factoryBody"><tr><td colspan="5" class="empty">Loading...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- ===== DISTRIBUTION TAB ===== -->
<div id="tab-distribution" class="tab">
  <div class="card">
    <div class="card-title">Generate Share Messages</div>
    <label for="distTitle">Product Title *</label>
    <input id="distTitle" placeholder="My SaaS Product"/>
    <label for="distUrl">URL</label>
    <input id="distUrl" placeholder="https://myproduct.com"/>
    <label for="distDesc">Description *</label>
    <textarea id="distDesc" placeholder="What does it do?" style="min-height:60px"></textarea>
    <div class="row">
      <div>
        <label for="distTargetUser">Target User</label>
        <input id="distTargetUser" placeholder="indie founders"/>
      </div>
      <div>
        <label for="distCta">CTA</label>
        <input id="distCta" placeholder="Try it free"/>
      </div>
    </div>
    <button class="btn btn-primary btn-full" id="distBtn" onclick="generateMessages()">
      <span class="btn-spinner" id="distSpinner"></span>&#x1F4E3; Generate Messages
    </button>
  </div>
  <div id="distResults" style="display:none">
    <div class="card-title" style="margin-bottom:.5rem">Share Messages</div>
    <div class="platform-grid" id="platformGrid"></div>
  </div>
</div>

<!-- ===== REVENUE TAB ===== -->
<div id="tab-revenue" class="tab">
  <div class="card">
    <div class="card-title">Revenue Intelligence</div>
    <label for="revProjectId">Project</label>
    <select id="revProjectId"><option value="">Select a project...</option></select>
    <label for="revPaymentLink">Payment Link (optional)</label>
    <input id="revPaymentLink" placeholder="https://stripe.com/..."/>
    <div style="display:flex;gap:.8rem;flex-wrap:wrap;margin-top:1rem">
      <button class="btn btn-primary" id="revReportBtn" onclick="getRevenueReport()">
        <span class="btn-spinner" id="revReportSpinner"></span>&#x1F4C8; Get Report
      </button>
      <button class="btn btn-ghost" id="revOutputBtn" onclick="getBusinessOutput()">
        <span class="btn-spinner" id="revOutputSpinner"></span>&#x1F4CB; Business Output
      </button>
    </div>
  </div>
  <div id="revResults" class="card" style="display:none"></div>
</div>

</div><!-- end .page -->

<div id="toastContainer"></div>

<footer>AI-DAN Managing Director v{version} &mdash; Monetization-first decision engine</footer>

<script>
// ---------------------------------------------------------------------------
// Core utilities
// ---------------------------------------------------------------------------
var activeTab = 'dashboard';
var _lastAnalysisIdea = '';

function showTab(name) {
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active')});
  document.querySelectorAll('.tabbar button').forEach(function(b){b.classList.remove('active')});
  var tab = document.getElementById('tab-' + name);
  if (tab) tab.classList.add('active');
  var tabs = ['dashboard','analyze','portfolio','factory','distribution','revenue'];
  var idx = tabs.indexOf(name);
  if (idx >= 0) document.querySelectorAll('.tabbar button')[idx].classList.add('active');
  activeTab = name;
  if (name === 'dashboard') refreshDashboard();
  if (name === 'portfolio') loadPortfolio();
  if (name === 'factory') loadFactoryRuns();
  if (name === 'revenue') loadRevProjectList();
}

async function apiFetch(path, options) {
  options = options || {};
  var headers = Object.assign({'Content-Type':'application/json'}, options.headers || {});
  var res = await fetch(path, Object.assign({}, options, {headers: headers}));
  if (!res.ok) {
    var err;
    try { err = await res.json(); } catch(e) { err = {detail: res.statusText}; }
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

function showToast(message, type) {
  var c = document.getElementById('toastContainer');
  var t = document.createElement('div');
  t.className = 'toast toast-' + (type || 'success');
  t.textContent = message;
  c.appendChild(t);
  setTimeout(function() { if (t.parentNode) t.parentNode.removeChild(t); }, 3000);
}

function escapeHtml(s) {
  if (!s) return '';
  var d = document.createElement('div');
  d.appendChild(document.createTextNode(String(s)));
  return d.innerHTML;
}

function truncate(s, n) { s = String(s||''); return s.length > n ? s.slice(0,n)+'...' : s; }

function statusBadge(st) {
  st = (st||'').toLowerCase();
  return '<span class="badge badge-' + st + '">' + escapeHtml(st) + '</span>';
}

function setBtnLoading(btnId, spinnerId, loading) {
  var btn = document.getElementById(btnId);
  var sp = document.getElementById(spinnerId);
  if (btn) btn.disabled = loading;
  if (sp) sp.style.display = loading ? 'inline-block' : 'none';
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
async function refreshDashboard() {
  try {
    var projects = await apiFetch('/portfolio/projects');
    var total = projects.length;
    var approved = projects.filter(function(p){return p.status==='approved'}).length;
    var building = projects.filter(function(p){return p.status==='building'||p.status==='queued'}).length;
    var launched = projects.filter(function(p){return p.status==='launched'}).length;
    document.getElementById('statTotal').textContent = total;
    document.getElementById('statApproved').textContent = approved;
    document.getElementById('statBuilding').textContent = building;
    document.getElementById('statLaunched').textContent = launched;
    var hi = document.getElementById('healthIndicator');
    if (launched > 0) {
      hi.innerHTML = '<span>&#x1F7E2;</span><span>System healthy &mdash; ' + launched + ' project(s) launched</span>';
    } else if (total > 0) {
      hi.innerHTML = '<span>&#x1F7E1;</span><span>Projects exist &mdash; none launched yet</span>';
    } else {
      hi.innerHTML = '<span>&#x1F534;</span><span>No projects &mdash; analyze an idea to get started</span>';
    }
  } catch(e) {
    document.getElementById('healthIndicator').innerHTML = '<span>&#x26AA;</span><span>Unable to load status</span>';
  }
}

setInterval(function() { if (activeTab === 'dashboard') refreshDashboard(); }, 30000);
refreshDashboard();

// ---------------------------------------------------------------------------
// Analyze
// ---------------------------------------------------------------------------
async function analyze() {
  var btn = document.getElementById('analyzeBtn');
  var loading = document.getElementById('loading');
  var result = document.getElementById('result');
  var errorBox = document.getElementById('errorBox');
  var idea = document.getElementById('idea').value.trim();

  if (!idea) { errorBox.textContent='Please enter an idea.'; errorBox.style.display='block'; return; }

  btn.disabled = true; loading.style.display = 'block'; result.style.display = 'none';
  document.getElementById('analyzeActions').style.display = 'none';
  errorBox.style.display = 'none';

  var body = {
    idea: idea,
    problem: document.getElementById('problem').value.trim(),
    target_user: document.getElementById('target_user').value.trim(),
    monetization_model: document.getElementById('monetization_model').value,
    competition_level: document.getElementById('competition_level').value,
    difficulty: document.getElementById('difficulty').value,
    time_to_revenue: document.getElementById('time_to_revenue').value,
    differentiation: document.getElementById('differentiation').value.trim()
  };

  try {
    var d = await apiFetch('/api/analyze/', {method:'POST', body:JSON.stringify(body)});
    _lastAnalysisIdea = idea;
    renderResult(d);
    document.getElementById('analyzeActions').style.display = 'block';
  } catch(err) {
    errorBox.textContent = 'Error: ' + err.message;
    errorBox.style.display = 'block';
  } finally {
    btn.disabled = false; loading.style.display = 'none';
  }
}

function renderResult(d) {
  var r = document.getElementById('result');
  var sc = d.total_score || 0;
  var pct = (sc/10*100).toFixed(0);
  var cls = sc>=8?'high':sc>=6?'med':'low';
  var dec = d.final_decision || 'UNKNOWN';

  var h = '<div style="display:flex;justify-content:space-between;align-items:center">';
  h += '<div><span class="decision-badge decision-' + dec + '">' + dec + '</span></div>';
  h += '<div style="text-align:right;font-size:1.5rem;font-weight:700">' + sc.toFixed(1);
  h += '<span style="font-size:.9rem;color:#888">/10</span></div></div>';
  h += '<div class="score-bar"><div class="score-fill score-' + cls + '" style="width:' + pct + '%"></div></div>';
  h += '<p style="font-size:.85rem;color:#aaa;margin-top:.3rem">' +
    (d.score_decision_reason||d.next_step||'') + '</p>';

  if (d.validation_blocking && d.validation_blocking.length) {
    h += '<div class="section"><h3>&#x1F6D1; Blocking Issues</h3>';
    d.validation_blocking.forEach(function(b){ h += '<p class="blocking">&#x2022; ' + escapeHtml(b) + '</p>'; });
    h += '</div>';
  }
  if (d.validation_reasons && d.validation_reasons.length) {
    h += '<div class="section"><h3>&#x2705; Validation</h3>';
    d.validation_reasons.forEach(function(v){ h += '<p class="reason">&#x2022; ' + escapeHtml(v) + '</p>'; });
    h += '</div>';
  }

  if (d.score_dimensions && d.score_dimensions.length) {
    h += '<div class="section"><h3>&#x1F4CA; Score Breakdown</h3>';
    d.score_dimensions.forEach(function(dim) {
      var dp = (dim.score/2*100).toFixed(0);
      var dc = dim.score>=1.5?'high':dim.score>=1?'med':'low';
      h += '<div class="detail-row"><span class="detail-label">' + escapeHtml(dim.name) +
        '</span><span class="detail-value">' + dim.score.toFixed(1) + '/2</span></div>';
      h += '<div class="score-bar"><div class="score-fill score-' + dc + '" style="width:' + dp + '%"></div></div>';
      h += '<p style="font-size:.8rem;color:#777;margin-bottom:.3rem">' + escapeHtml(dim.reason) + '</p>';
    });
    h += '</div>';
  }

  var o = d.offer || {};
  if (o.decision === 'generated') {
    h += '<div class="section"><h3>&#x1F4B0; Offer</h3>';
    h += detailRow('Pricing', o.pricing);
    h += detailRow('Model', o.pricing_model);
    h += detailRow('Delivery', o.delivery_method);
    h += detailRow('Value', o.value_proposition);
    h += detailRow('CTA', o.cta);
    h += '</div>';
  }

  var di = d.distribution || {};
  if (di.decision === 'generated') {
    h += '<div class="section"><h3>&#x1F680; Distribution</h3>';
    h += detailRow('Channel', di.primary_channel);
    h += detailRow('Acquisition', di.acquisition_method);
    h += detailRow('First 10 Users', di.first_10_users_plan);
    h += detailRow('Messaging', di.messaging);
    if (di.execution_steps && di.execution_steps.length) {
      h += '<p style="font-size:.85rem;color:#aaa;margin-top:.4rem">Steps:</p>';
      di.execution_steps.forEach(function(s,i) {
        h += '<p style="font-size:.8rem;color:#ccc;margin-left:.5rem">' + (i+1) + '. ' + escapeHtml(s) + '</p>';
      });
    }
    h += '</div>';
  }

  h += '<div class="section"><h3>&#x27A1;&#xFE0F; Next Step</h3>';
  h += '<p style="font-size:.9rem">' + escapeHtml(d.next_step||'Awaiting analysis.') + '</p>';
  h += '<p style="font-size:.8rem;color:#666;margin-top:.3rem">Stage: ' + escapeHtml(d.pipeline_stage||'unknown') + '</p>';
  h += '</div>';

  r.innerHTML = h; r.style.display = 'block';
}

function detailRow(l, v) {
  if (!v) return '';
  return '<div class="detail-row"><span class="detail-label">' + escapeHtml(l) +
    '</span><span class="detail-value">' + escapeHtml(v) + '</span></div>';
}

async function _saveIdeaAsProject(toastMsg) {
  var idea = _lastAnalysisIdea || document.getElementById('idea').value.trim();
  if (!idea) { showToast('No idea to save', 'error'); return; }
  try {
    await apiFetch('/portfolio/projects', {method:'POST',
      body:JSON.stringify({name:idea.slice(0,80), description:idea})});
    showToast(toastMsg, 'success');
  } catch(e) { showToast('Error: ' + e.message, 'error'); }
}

function createProject() { return _saveIdeaAsProject('Project created!'); }
function saveDraft() { return _saveIdeaAsProject('Draft saved!'); }

// ---------------------------------------------------------------------------
// Portfolio
// ---------------------------------------------------------------------------
async function loadPortfolio() {
  var tbody = document.getElementById('portfolioBody');
  tbody.innerHTML = '<tr><td colspan="5" class="empty">Loading...</td></tr>';
  try {
    var projects = await apiFetch('/portfolio/projects');
    if (!projects.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="empty">No projects yet. Analyze an idea to get started!</td></tr>';
      return;
    }
    tbody.innerHTML = '';
    projects.forEach(function(p) {
      var tr = document.createElement('tr');
      var meta = p.metadata || {};
      var repoLink = meta.repo_url ? '<a href="' + escapeHtml(meta.repo_url) + '" target="_blank" style="color:#5b6ef7;font-size:.8rem">Repo</a> ' : '';
      var deployLink = meta.deploy_url ? '<a href="' + escapeHtml(meta.deploy_url) + '" target="_blank" style="color:#5b6ef7;font-size:.8rem">Deploy</a> ' : '';
      var actions = '';
      var st = (p.status||'').toLowerCase();
      if (st==='idea'||st==='review') {
        actions += '<button class="btn btn-success" style="padding:.3rem .6rem;font-size:.78rem;margin:.1rem" onclick="approveProject(\'' + escapeHtml(p.project_id) + '\')">Approve</button> ';
      }
      if (st==='approved'||st==='queued') {
        actions += '<button class="btn btn-warning" style="padding:.3rem .6rem;font-size:.78rem;margin:.1rem" onclick="buildProject(\'' + escapeHtml(p.project_id) + '\',\'' + escapeHtml(p.name||'') + '\')">Build</button> ';
      }
      actions += '<button class="btn btn-ghost" style="padding:.3rem .6rem;font-size:.78rem;margin:.1rem" onclick="shareProject(\'' + escapeHtml(p.name||'') + '\')">Share</button>';
      var created = p.created_at ? new Date(p.created_at).toLocaleDateString() : '-';
      tr.innerHTML = '<td style="font-weight:500">' + escapeHtml(p.name||'-') + '</td>' +
        '<td>' + statusBadge(p.status) + '</td>' +
        '<td style="color:#888;font-size:.83rem">' + escapeHtml(truncate(p.description||'',60)) + '</td>' +
        '<td style="color:#666;font-size:.82rem">' + escapeHtml(created) + '</td>' +
        '<td>' + repoLink + deployLink + actions + '</td>';
      tbody.appendChild(tr);
    });
  } catch(e) {
    tbody.innerHTML = '<tr><td colspan="5" class="empty">Error loading projects: ' + escapeHtml(e.message) + '</td></tr>';
  }
}

function toggleAddProject() {
  var f = document.getElementById('addProjectForm');
  f.style.display = f.style.display === 'none' ? 'block' : 'none';
}

async function addProject() {
  var name = document.getElementById('newProjName').value.trim();
  var desc = document.getElementById('newProjDesc').value.trim();
  if (!name) { showToast('Project name is required', 'error'); return; }
  try {
    await apiFetch('/portfolio/projects', {method:'POST',
      body:JSON.stringify({name:name, description:desc})});
    showToast('Project added!', 'success');
    document.getElementById('newProjName').value = '';
    document.getElementById('newProjDesc').value = '';
    toggleAddProject();
    loadPortfolio();
  } catch(e) { showToast('Error: ' + e.message, 'error'); }
}

async function approveProject(id) {
  try {
    await apiFetch('/portfolio/projects/' + id + '/transition', {method:'POST',
      body:JSON.stringify({new_state:'approved'})});
    showToast('Project approved!', 'success');
    loadPortfolio();
  } catch(e) { showToast('Error: ' + e.message, 'error'); }
}

async function buildProject(id, name) {
  try {
    var brief = {
      project_id: id, name: name||id, hypothesis: name||id,
      target_user: 'users', problem: 'TBD', solution: 'TBD',
      mvp_scope: ['MVP'], acceptance_criteria: ['Deploys'],
      landing_page_requirements: ['CTA visible'], cta: 'Get started',
      pricing_hint: 'subscription', deployment_target: 'vercel',
      command_bundle: {}, feature_flags: {dry_run: true}
    };
    await apiFetch('/factory/runs', {method:'POST',
      body:JSON.stringify({build_brief:brief, dry_run:true})});
    showToast('Build triggered!', 'success');
    loadFactoryRuns();
  } catch(e) { showToast('Error: ' + e.message, 'error'); }
}

function shareProject(name) {
  showTab('distribution');
  setTimeout(function() { document.getElementById('distTitle').value = name||''; }, 50);
}

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------
async function loadFactoryRuns() {
  var tbody = document.getElementById('factoryBody');
  tbody.innerHTML = '<tr><td colspan="5" class="empty">Loading...</td></tr>';
  try {
    var runs = await apiFetch('/factory/runs');
    if (!runs.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="empty">No runs yet.</td></tr>';
      return;
    }
    tbody.innerHTML = '';
    runs.forEach(function(r) {
      var tr = document.createElement('tr');
      var deployCell = r.deploy_url ? '<a href="' + escapeHtml(r.deploy_url) + '" target="_blank" style="color:#5b6ef7;font-size:.82rem">' + escapeHtml(truncate(r.deploy_url,30)) + '</a>' : '-';
      tr.innerHTML = '<td style="font-size:.82rem;font-family:monospace">' + escapeHtml((r.run_id||'').slice(0,12)) + '</td>' +
        '<td style="font-size:.83rem">' + escapeHtml(r.project_id||'-') + '</td>' +
        '<td>' + statusBadge(r.status) + '</td>' +
        '<td>' + deployCell + '</td>' +
        '<td style="color:#fca5a5;font-size:.8rem">' + escapeHtml(truncate(r.error||'',40)) + '</td>';
      tbody.appendChild(tr);
    });
  } catch(e) {
    tbody.innerHTML = '<tr><td colspan="5" class="empty">Error: ' + escapeHtml(e.message) + '</td></tr>';
  }
}

async function triggerBuild() {
  setBtnLoading('triggerBuildBtn', 'buildSpinner', true);
  var projectId = document.getElementById('buildProjectId').value.trim();
  var template = document.getElementById('buildTemplate').value;
  var dryRun = document.getElementById('buildDryRun').checked;
  if (!projectId) { showToast('Project ID is required', 'error'); setBtnLoading('triggerBuildBtn','buildSpinner',false); return; }
  var brief = {
    project_id: projectId, name: projectId, hypothesis: projectId,
    target_user: 'users', problem: 'TBD', solution: 'TBD',
    mvp_scope: ['MVP'], acceptance_criteria: ['Deploys'],
    landing_page_requirements: ['CTA visible'], cta: 'Get started',
    pricing_hint: 'subscription', deployment_target: 'vercel',
    command_bundle: {template: template}, feature_flags: {dry_run: dryRun}
  };
  try {
    var r = await apiFetch('/factory/runs', {method:'POST',
      body:JSON.stringify({build_brief:brief, dry_run:dryRun})});
    showToast('Build triggered: ' + (r.run_id||'').slice(0,8), 'success');
    loadFactoryRuns();
  } catch(e) { showToast('Error: ' + e.message, 'error'); }
  finally { setBtnLoading('triggerBuildBtn','buildSpinner',false); }
}

// ---------------------------------------------------------------------------
// Distribution
// ---------------------------------------------------------------------------
async function generateMessages() {
  setBtnLoading('distBtn','distSpinner',true);
  var payload = {
    title: document.getElementById('distTitle').value.trim(),
    url: document.getElementById('distUrl').value.trim(),
    description: document.getElementById('distDesc').value.trim(),
    target_user: document.getElementById('distTargetUser').value.trim(),
    cta: document.getElementById('distCta').value.trim()
  };
  if (!payload.title || !payload.description) {
    showToast('Title and description are required', 'error');
    setBtnLoading('distBtn','distSpinner',false); return;
  }
  try {
    var d = await apiFetch('/api/distribution/share-messages', {method:'POST', body:JSON.stringify(payload)});
    renderMessages(d);
  } catch(e) { showToast('Error: ' + e.message, 'error'); }
  finally { setBtnLoading('distBtn','distSpinner',false); }
}

function renderMessages(d) {
  var grid = document.getElementById('platformGrid');
  grid.innerHTML = '';
  var platforms = [
    ['twitter','Twitter/X',d.twitter],['linkedin','LinkedIn',d.linkedin],
    ['whatsapp','WhatsApp',d.whatsapp],['email','Email Subject',d.email_subject],
    ['email_body','Email Body',d.email_body],['sms','SMS',d.sms],
    ['reddit','Reddit',d.reddit],['product_hunt','Product Hunt',d.product_hunt]
  ];
  platforms.forEach(function(pl) {
    if (!pl[2]) return;
    var card = document.createElement('div');
    card.className = 'platform-card';
    card.innerHTML = '<div class="platform-name">' + escapeHtml(pl[1]) + '</div>' +
      '<div class="platform-text" id="pt-' + pl[0] + '">' + escapeHtml(pl[2]) + '</div>' +
      '<button class="btn btn-ghost" style="margin-top:.5rem;padding:.3rem .7rem;font-size:.8rem" ' +
      'onclick="copyText(\'' + pl[0] + '\')">&#x1F4CB; Copy</button>';
    grid.appendChild(card);
  });
  document.getElementById('distResults').style.display = 'block';
}

function copyText(id) {
  var el = document.getElementById('pt-' + id);
  if (!el) return;
  if (navigator.clipboard) {
    navigator.clipboard.writeText(el.textContent).then(function() {
      showToast('Copied!', 'success');
    }).catch(function() { showToast('Copy failed', 'error'); });
  } else {
    showToast('Clipboard not available', 'error');
  }
}

// ---------------------------------------------------------------------------
// Revenue
// ---------------------------------------------------------------------------
async function loadRevProjectList() {
  try {
    var projects = await apiFetch('/portfolio/projects');
    var sel = document.getElementById('revProjectId');
    var cur = sel.value;
    while (sel.options.length > 1) sel.remove(1);
    projects.forEach(function(p) {
      var opt = document.createElement('option');
      opt.value = p.project_id;
      opt.textContent = (p.name||p.project_id);
      sel.appendChild(opt);
    });
    if (cur) sel.value = cur;
  } catch(e) {}
}

async function getRevenueReport() {
  var id = document.getElementById('revProjectId').value;
  if (!id) { showToast('Select a project first', 'error'); return; }
  setBtnLoading('revReportBtn','revReportSpinner',true);
  try {
    var d = await apiFetch('/revenue/projects/' + id + '/learning-report');
    renderRevResults(d);
  } catch(e) { showToast('Error: ' + e.message, 'error'); }
  finally { setBtnLoading('revReportBtn','revReportSpinner',false); }
}

async function getBusinessOutput() {
  var id = document.getElementById('revProjectId').value;
  var link = document.getElementById('revPaymentLink').value.trim();
  if (!id) { showToast('Select a project first', 'error'); return; }
  setBtnLoading('revOutputBtn','revOutputSpinner',true);
  try {
    var body = {};
    if (link) body.payment_link = link;
    var d = await apiFetch('/revenue/projects/' + id + '/business-output', {method:'POST', body:JSON.stringify(body)});
    renderRevResults(d);
  } catch(e) { showToast('Error: ' + e.message, 'error'); }
  finally { setBtnLoading('revOutputBtn','revOutputSpinner',false); }
}

function renderRevResults(d) {
  var el = document.getElementById('revResults');
  var h = '';
  if (typeof d === 'object' && d !== null) {
    Object.keys(d).forEach(function(k) {
      var v = d[k];
      if (v === null || v === undefined) return;
      h += '<div class="detail-row"><span class="detail-label">' + escapeHtml(k) +
        '</span><span class="detail-value" style="max-width:70%">' +
        escapeHtml(typeof v === 'object' ? JSON.stringify(v) : String(v)) + '</span></div>';
    });
  } else {
    h = '<p>' + escapeHtml(String(d)) + '</p>';
  }
  el.innerHTML = h || '<p style="color:#666">No data returned.</p>';
  el.style.display = 'block';
}
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def root_ui() -> HTMLResponse:
    """Serve the root idea-analysis UI."""
    html = _ROOT_HTML.replace("{version}", _VERSION)
    return HTMLResponse(content=html)
