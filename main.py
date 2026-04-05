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
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#0a0a0a;color:#e0e0e0;min-height:100vh}
a{color:#5b6ef7;text-decoration:none}
a:hover{text-decoration:underline}
/* Layout */
.app-header{background:#0f0f1a;border-bottom:1px solid #222;padding:.75rem 1.5rem;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}
.app-header h1{font-size:1.2rem;color:#fff;display:flex;align-items:center;gap:.5rem}
.health-dot{width:10px;height:10px;border-radius:50%;background:#16a34a;display:inline-block}
.health-dot.yellow{background:#d97706}
.health-dot.red{background:#dc2626}
/* Tabs */
.tab-bar{background:#0f0f1a;border-bottom:1px solid #222;padding:0 1.5rem;display:flex;gap:.25rem;overflow-x:auto}
.tab-btn{padding:.7rem 1rem;border:none;background:none;color:#888;cursor:pointer;font-size:.88rem;font-weight:500;border-bottom:2px solid transparent;white-space:nowrap;transition:all .15s}
.tab-btn.active{color:#5b6ef7;border-bottom-color:#5b6ef7}
.tab-btn:hover{color:#e0e0e0}
.tab-content{display:none;padding:1.5rem;max-width:1100px;margin:0 auto}
.tab-content.active{display:block}
/* Cards */
.card{background:#1a1a2e;border:1px solid #2a2a4a;border-radius:12px;padding:1.25rem;margin-bottom:1.25rem}
.card-title{font-size:.95rem;font-weight:600;color:#ccc;margin-bottom:1rem;display:flex;align-items:center;gap:.4rem}
/* Stats grid */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:1rem;margin-bottom:1.25rem}
.stat-card{background:#1a1a2e;border:1px solid #2a2a4a;border-radius:12px;padding:1.2rem;text-align:center}
.stat-num{font-size:2rem;font-weight:700;color:#5b6ef7}
.stat-label{font-size:.8rem;color:#888;margin-top:.25rem}
/* Form elements */
label{display:block;font-size:.83rem;color:#aaa;margin-bottom:.3rem;margin-top:.8rem}
label:first-child{margin-top:0}
textarea,input[type=text],input[type=url],select{width:100%;padding:.55rem .75rem;border-radius:8px;border:1px solid #333;background:#111;color:#e0e0e0;font-size:.88rem;font-family:inherit}
textarea{resize:vertical;min-height:80px}
textarea:focus,input:focus,select:focus{outline:none;border-color:#5b6ef7}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:.75rem}
.row3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:.75rem}
/* Buttons */
.btn{padding:.55rem 1rem;border:none;border-radius:8px;font-size:.88rem;font-weight:600;cursor:pointer;transition:all .15s;display:inline-flex;align-items:center;gap:.35rem}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btn-primary{background:#5b6ef7;color:#fff}
.btn-primary:hover:not(:disabled){background:#4a5ce6}
.btn-success{background:#16a34a;color:#fff}
.btn-success:hover:not(:disabled){background:#15803d}
.btn-danger{background:#dc2626;color:#fff}
.btn-danger:hover:not(:disabled){background:#b91c1c}
.btn-ghost{background:#222;color:#ccc;border:1px solid #444}
.btn-ghost:hover:not(:disabled){background:#333}
.btn-sm{padding:.35rem .7rem;font-size:.8rem}
.btn-full{width:100%;justify-content:center;margin-top:.75rem}
/* Table */
.tbl{width:100%;border-collapse:collapse;font-size:.85rem}
.tbl th{text-align:left;padding:.55rem .75rem;color:#888;font-weight:500;border-bottom:1px solid #2a2a4a;white-space:nowrap}
.tbl td{padding:.55rem .75rem;border-bottom:1px solid #1e1e38;vertical-align:middle}
.tbl tr:hover td{background:#1e1e38}
.tbl-wrap{overflow-x:auto}
/* Badges */
.badge{display:inline-block;padding:.2rem .55rem;border-radius:20px;font-size:.75rem;font-weight:600}
.badge-gray{background:#333;color:#aaa}
.badge-blue{background:#1e3a8a;color:#93c5fd}
.badge-yellow{background:#78350f;color:#fcd34d}
.badge-green{background:#14532d;color:#86efac}
.badge-red{background:#7f1d1d;color:#fca5a5}
/* Decision badges */
.decision-badge{display:inline-block;padding:.3rem .8rem;border-radius:6px;font-weight:700;font-size:.9rem;margin:.5rem 0}
.decision-APPROVED{background:#16a34a;color:#fff}
.decision-HOLD{background:#d97706;color:#fff}
.decision-REJECTED{background:#dc2626;color:#fff}
/* Score bars */
.score-bar{height:7px;border-radius:4px;background:#2a2a4a;margin:.25rem 0;overflow:hidden}
.score-fill{height:100%;border-radius:4px;transition:width .5s}
.score-high{background:#16a34a}
.score-med{background:#d97706}
.score-low{background:#dc2626}
/* Sections inside cards */
.section{margin-top:.9rem;padding-top:.9rem;border-top:1px solid #2a2a4a}
.section h3{font-size:.9rem;color:#aaa;margin-bottom:.4rem}
.detail-row{display:flex;justify-content:space-between;padding:.2rem 0;font-size:.83rem}
.detail-label{color:#888}
.detail-value{color:#e0e0e0;text-align:right;max-width:65%}
/* Misc */
.blocking{color:#fca5a5;font-size:.83rem;margin:.15rem 0}
.reason{color:#86efac;font-size:.83rem;margin:.15rem 0}
.empty-state{text-align:center;padding:3rem 1rem;color:#555}
.spinner{display:inline-block;width:18px;height:18px;border:2px solid #333;border-top-color:#5b6ef7;border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-block{text-align:center;padding:2rem;color:#666}
.copy-btn{padding:.2rem .5rem;font-size:.75rem;border-radius:5px;background:#222;color:#aaa;border:1px solid #444;cursor:pointer}
.copy-btn:hover{background:#333}
/* Share result cards */
.platform-card{background:#111;border:1px solid #2a2a4a;border-radius:8px;padding:.9rem;margin-bottom:.7rem}
.platform-name{font-size:.8rem;font-weight:600;color:#5b6ef7;margin-bottom:.35rem;display:flex;justify-content:space-between}
.platform-msg{font-size:.83rem;color:#ccc;white-space:pre-wrap;word-break:break-word}
/* Toast */
#toast-container{position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;display:flex;flex-direction:column;gap:.5rem}
.toast{padding:.75rem 1.1rem;border-radius:8px;font-size:.85rem;font-weight:500;min-width:220px;max-width:360px;opacity:0;transition:opacity .2s;pointer-events:none}
.toast.show{opacity:1;pointer-events:auto}
.toast-success{background:#14532d;border:1px solid #16a34a;color:#86efac}
.toast-error{background:#7f1d1d;border:1px solid #dc2626;color:#fca5a5}
/* Quick actions */
.quick-actions{display:flex;gap:.75rem;flex-wrap:wrap;margin-bottom:1.25rem}
/* Revenue result */
.rev-result{background:#111;border:1px solid #2a2a4a;border-radius:8px;padding:1rem;margin-top:.75rem;font-size:.85rem;white-space:pre-wrap;word-break:break-word;color:#ccc}
/* Checkbox row */
.chk-row{display:flex;align-items:center;gap:.5rem;margin-top:.75rem;font-size:.88rem;color:#ccc}
.chk-row input[type=checkbox]{width:auto}
/* Responsive */
@media(max-width:600px){
  .row2,.row3{grid-template-columns:1fr}
  .stats-grid{grid-template-columns:1fr 1fr}
  .tab-btn{padding:.6rem .7rem;font-size:.82rem}
}
footer{padding:1.5rem;text-align:center;color:#444;font-size:.78rem;border-top:1px solid #1a1a2e;margin-top:2rem}
</style>
</head>
<body>

<div class="app-header">
  <h1>&#x1F9E0; AI-DAN <span style="color:#5b6ef7">Command Center</span></h1>
  <div style="display:flex;align-items:center;gap:.75rem">
    <span id="healthIndicator" style="font-size:.8rem;color:#888">&#x25CF; checking...</span>
    <span style="font-size:.78rem;color:#555">v{version}</span>
  </div>
</div>

<div class="tab-bar">
  <button class="tab-btn active" onclick="switchTab('dashboard')">&#x1F4CA; Dashboard</button>
  <button class="tab-btn" onclick="switchTab('analyze')">&#x1F4A1; Analyze Idea</button>
  <button class="tab-btn" onclick="switchTab('portfolio')">&#x1F4E6; Portfolio</button>
  <button class="tab-btn" onclick="switchTab('factory')">&#x1F3ED; Factory</button>
  <button class="tab-btn" onclick="switchTab('distribution')">&#x1F4E3; Distribution</button>
  <button class="tab-btn" onclick="switchTab('revenue')">&#x1F4B0; Revenue</button>
</div>

<!-- ===================== TAB 1: DASHBOARD ===================== -->
<div id="tab-dashboard" class="tab-content active">
  <div class="stats-grid" id="statsGrid">
    <div class="stat-card"><div class="stat-num" id="statTotal">—</div><div class="stat-label">Total Projects</div></div>
    <div class="stat-card"><div class="stat-num" id="statApproved" style="color:#93c5fd">—</div><div class="stat-label">Approved</div></div>
    <div class="stat-card"><div class="stat-num" id="statBuilding" style="color:#fcd34d">—</div><div class="stat-label">Building</div></div>
    <div class="stat-card"><div class="stat-num" id="statLaunched" style="color:#86efac">—</div><div class="stat-label">Launched</div></div>
  </div>

  <div class="quick-actions">
    <button class="btn btn-primary" onclick="switchTab('analyze')">&#x2B; New Idea</button>
    <button class="btn btn-ghost" onclick="switchTab('portfolio')">&#x1F4E6; View Projects</button>
    <button class="btn btn-ghost" onclick="switchTab('factory')">&#x1F3ED; Factory Runs</button>
    <button class="btn btn-ghost" onclick="loadDashboard()">&#x21BA; Refresh</button>
  </div>

  <div class="card">
    <div class="card-title">&#x1F4CB; Recent Projects</div>
    <div class="tbl-wrap" id="dashRecentProjects">
      <div class="loading-block"><span class="spinner"></span><p style="margin-top:.5rem">Loading...</p></div>
    </div>
  </div>
</div>

<!-- ===================== TAB 2: ANALYZE IDEA ===================== -->
<div id="tab-analyze" class="tab-content">
  <div class="card">
    <div class="card-title">&#x1F4A1; Analyze New Idea</div>
    <label for="idea">Your Idea *</label>
    <textarea id="idea" placeholder="Describe your idea in detail..."></textarea>
    <div class="row2">
      <div><label for="problem">Problem</label><input type="text" id="problem" placeholder="What problem does it solve?"/></div>
      <div><label for="target_user">Target User</label><input type="text" id="target_user" placeholder="Who is this for?"/></div>
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
    <input type="text" id="differentiation" placeholder="What makes this unique?"/>
    <button class="btn btn-primary btn-full" id="analyzeBtn" onclick="analyze()">&#x1F50D; Analyze Idea</button>
  </div>

  <div id="analyzeLoading" style="display:none" class="loading-block"><span class="spinner"></span><p style="margin-top:.5rem">Running full pipeline analysis...</p></div>
  <div id="analyzeError" style="display:none;background:#2d1111;border:1px solid #dc2626;border-radius:8px;padding:1rem;color:#fca5a5;margin-bottom:1rem"></div>
  <div id="analyzeResult" style="display:none"></div>
</div>

<!-- ===================== TAB 3: PORTFOLIO ===================== -->
<div id="tab-portfolio" class="tab-content">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
    <h2 style="font-size:1rem;color:#ccc">&#x1F4E6; Projects</h2>
    <button class="btn btn-primary btn-sm" onclick="toggleAddProject()">&#x2B; Add Project</button>
  </div>

  <div id="addProjectForm" class="card" style="display:none">
    <div class="card-title">New Project</div>
    <div class="row2">
      <div><label>Name *</label><input type="text" id="newProjName" placeholder="e.g. SaaS Idea X"/></div>
      <div><label>Status</label>
        <select id="newProjStatus">
          <option value="idea">idea</option>
          <option value="approved">approved</option>
        </select>
      </div>
    </div>
    <label>Description</label>
    <textarea id="newProjDesc" placeholder="Short description..."></textarea>
    <div style="display:flex;gap:.5rem;margin-top:.75rem">
      <button class="btn btn-success btn-sm" id="addProjBtn" onclick="addProject()">&#x2713; Save</button>
      <button class="btn btn-ghost btn-sm" onclick="toggleAddProject()">Cancel</button>
    </div>
  </div>

  <div class="card" style="padding:0">
    <div class="tbl-wrap" id="portfolioTable">
      <div class="loading-block" style="padding:2rem"><span class="spinner"></span></div>
    </div>
  </div>
</div>

<!-- ===================== TAB 4: FACTORY ===================== -->
<div id="tab-factory" class="tab-content">
  <div class="row2" style="margin-bottom:1.25rem">
    <div class="card" style="margin-bottom:0">
      <div class="card-title">&#x1F680; Launch Build</div>
      <label>Project ID *</label>
      <input type="text" id="buildProjectId" placeholder="e.g. prj-abc123"/>
      <label>Template</label>
      <select id="buildTemplate">
        <option value="saas-template">SaaS Template</option>
        <option value="landing-page">Landing Page</option>
      </select>
      <div class="chk-row"><input type="checkbox" id="buildDryRun" checked/><span>Dry Run (safe — no real deployment)</span></div>
      <button class="btn btn-primary btn-full" id="launchBuildBtn" onclick="launchBuild()">&#x1F680; Launch Build</button>
    </div>
    <div class="card" style="margin-bottom:0">
      <div class="card-title">&#x1F50D; Verify Deployment</div>
      <label>Project ID *</label>
      <input type="text" id="verifyProjectId" placeholder="e.g. prj-abc123"/>
      <label>Deploy URL *</label>
      <input type="url" id="verifyDeployUrl" placeholder="https://..."/>
      <label>Repo URL</label>
      <input type="url" id="verifyRepoUrl" placeholder="https://github.com/..."/>
      <button class="btn btn-ghost btn-full" id="verifyBtn" onclick="verifyDeployment()">&#x1F50D; Verify</button>
      <div id="verifyResult" style="margin-top:.75rem;font-size:.83rem"></div>
    </div>
  </div>
  <div class="card" style="padding:0">
    <div style="padding:.9rem 1rem .5rem;display:flex;justify-content:space-between;align-items:center">
      <span style="font-size:.9rem;font-weight:600;color:#ccc">&#x1F4CB; Factory Runs</span>
      <button class="btn btn-ghost btn-sm" onclick="loadFactoryRuns()">&#x21BA; Refresh</button>
    </div>
    <div class="tbl-wrap" id="factoryRunsTable">
      <div class="loading-block"><span class="spinner"></span></div>
    </div>
  </div>
</div>

<!-- ===================== TAB 5: DISTRIBUTION ===================== -->
<div id="tab-distribution" class="tab-content">
  <div class="card">
    <div class="card-title">&#x1F4E3; Generate Share Messages</div>
    <div class="row2">
      <div><label>Title *</label><input type="text" id="shareTitle" placeholder="Product name"/></div>
      <div><label>URL *</label><input type="url" id="shareUrl" placeholder="https://your-product.com"/></div>
    </div>
    <label>Description *</label>
    <textarea id="shareDesc" placeholder="What does it do?"></textarea>
    <div class="row3">
      <div><label>Target User</label><input type="text" id="shareTarget" placeholder="Who is this for?"/></div>
      <div><label>CTA</label><input type="text" id="shareCta" placeholder="e.g. Try free today"/></div>
      <div><label>Price (optional)</label><input type="text" id="sharePrice" placeholder="e.g. $29/mo"/></div>
    </div>
    <button class="btn btn-primary btn-full" id="shareBtn" onclick="generateShareMessages()">&#x1F4E3; Generate Messages</button>
  </div>
  <div id="shareLoading" style="display:none" class="loading-block"><span class="spinner"></span><p style="margin-top:.5rem">Generating...</p></div>
  <div id="shareResults" style="display:none"></div>
</div>

<!-- ===================== TAB 6: REVENUE ===================== -->
<div id="tab-revenue" class="tab-content">
  <div class="card">
    <div class="card-title">&#x1F4B0; Revenue Intelligence</div>
    <label>Project ID</label>
    <input type="text" id="revProjectId" placeholder="e.g. prj-abc123"/>
    <div style="display:flex;gap:.5rem;margin-top:.75rem;flex-wrap:wrap">
      <button class="btn btn-primary btn-sm" id="revLearningBtn" onclick="getRevenueLearning()">&#x1F4C8; Get Learning Report</button>
      <button class="btn btn-ghost btn-sm" id="revOutputBtn" onclick="generateBusinessOutput()">&#x1F4CA; Generate Business Output</button>
    </div>
  </div>
  <div id="revLoading" style="display:none" class="loading-block"><span class="spinner"></span></div>
  <div id="revResult"></div>
</div>

<footer>AI-DAN Managing Director v{version} &mdash; Monetization-first decision engine</footer>

<div id="toast-container"></div>

<script>
/* ── Utilities ──────────────────────────────────────────── */
function escapeHtml(s){if(!s)return'';var d=document.createElement("div");d.appendChild(document.createTextNode(String(s)));return d.innerHTML}
function toast(msg,type){
  var c=document.getElementById("toast-container");
  var t=document.createElement("div");
  t.className="toast toast-"+(type||"success");
  t.textContent=msg;
  c.appendChild(t);
  requestAnimationFrame(function(){t.classList.add("show")});
  setTimeout(function(){t.classList.remove("show");setTimeout(function(){c.removeChild(t)},300)},3000);
}
function setBtnLoading(id,loading,label){
  var b=document.getElementById(id);
  if(!b)return;
  b.disabled=loading;
  if(loading){b.dataset.orig=b.innerHTML;b.innerHTML='<span class="spinner"></span> '+label}
  else{b.innerHTML=b.dataset.orig||label}
}
function statusBadge(s){
  var m={idea:"badge-gray",approved:"badge-blue",building:"badge-yellow",launched:"badge-green",killed:"badge-red"};
  return'<span class="badge '+(m[s]||"badge-gray")+'">'+escapeHtml(s)+'</span>';
}
function detailRow(l,v){if(!v)return'';return'<div class="detail-row"><span class="detail-label">'+escapeHtml(l)+'</span><span class="detail-value">'+escapeHtml(v)+'</span></div>'}

/* ── Tab switching ───────────────────────────────────────── */
var _activeTab="dashboard";
function switchTab(name){
  document.querySelectorAll(".tab-content").forEach(function(el){el.classList.remove("active")});
  document.querySelectorAll(".tab-btn").forEach(function(el){el.classList.remove("active")});
  var content=document.getElementById("tab-"+name);
  if(content)content.classList.add("active");
  var btns=document.querySelectorAll(".tab-btn");
  var tabNames=["dashboard","analyze","portfolio","factory","distribution","revenue"];
  var idx=tabNames.indexOf(name);
  if(idx>=0&&btns[idx])btns[idx].classList.add("active");
  _activeTab=name;
  if(name==="portfolio")loadPortfolio();
  if(name==="factory")loadFactoryRuns();
}

/* ── Health check ────────────────────────────────────────── */
function updateHealth(projects){
  var hi=document.getElementById("healthIndicator");
  if(!projects||projects.length===0){hi.innerHTML='<span class="health-dot yellow"></span> No projects';return}
  var failed=projects.filter(function(p){return p.status==="killed"}).length;
  var launched=projects.filter(function(p){return p.status==="launched"}).length;
  if(failed>launched){hi.innerHTML='<span class="health-dot red"></span> Issues detected'}
  else if(launched>0){hi.innerHTML='<span class="health-dot"></span> Healthy'}
  else{hi.innerHTML='<span class="health-dot yellow"></span> Building'}
}

/* ── Dashboard ───────────────────────────────────────────── */
function loadDashboard(){
  fetch("/portfolio/projects").then(function(r){return r.json()}).then(function(projects){
    var total=projects.length;
    var approved=projects.filter(function(p){return p.status==="approved"}).length;
    var building=projects.filter(function(p){return p.status==="building"}).length;
    var launched=projects.filter(function(p){return p.status==="launched"}).length;
    document.getElementById("statTotal").textContent=total;
    document.getElementById("statApproved").textContent=approved;
    document.getElementById("statBuilding").textContent=building;
    document.getElementById("statLaunched").textContent=launched;
    updateHealth(projects);
    var recent=projects.slice(-5).reverse();
    var wrap=document.getElementById("dashRecentProjects");
    if(!recent.length){wrap.innerHTML='<div class="empty-state">No projects yet. Analyze an idea to get started.</div>';return}
    var h='<table class="tbl"><thead><tr><th>Name</th><th>Status</th><th>Deploy URL</th><th>Created</th></tr></thead><tbody>';
    recent.forEach(function(p){
      var url=p.deploy_url?'<a href="'+escapeHtml(p.deploy_url)+'" target="_blank">&#x1F517; Open</a>':'<span style="color:#555">—</span>';
      var created=p.created_at?new Date(p.created_at).toLocaleDateString():"—";
      h+='<tr><td>'+escapeHtml(p.name||p.project_id)+'</td><td>'+statusBadge(p.status)+'</td><td>'+url+'</td><td>'+created+'</td></tr>';
    });
    h+='</tbody></table>';
    wrap.innerHTML=h;
  }).catch(function(){document.getElementById("dashRecentProjects").innerHTML='<div class="empty-state" style="color:#dc2626">Failed to load projects.</div>'});
}

/* ── Analyze ─────────────────────────────────────────────── */
var _lastAnalysisData=null;
function analyze(){
  var idea=document.getElementById("idea").value.trim();
  if(!idea){
    document.getElementById("analyzeError").textContent="Please enter an idea.";
    document.getElementById("analyzeError").style.display="block";return
  }
  setBtnLoading("analyzeBtn",true,"Analyzing...");
  document.getElementById("analyzeLoading").style.display="block";
  document.getElementById("analyzeResult").style.display="none";
  document.getElementById("analyzeError").style.display="none";
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
  fetch("/api/analyze/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})
    .then(function(r){if(!r.ok)return r.json().then(function(e){throw new Error(e.detail||r.statusText)});return r.json()})
    .then(function(d){_lastAnalysisData=d;renderAnalysisResult(d)})
    .catch(function(err){document.getElementById("analyzeError").textContent="Error: "+err.message;document.getElementById("analyzeError").style.display="block"})
    .finally(function(){setBtnLoading("analyzeBtn",false,"&#x1F50D; Analyze Idea");document.getElementById("analyzeLoading").style.display="none"});
}

function renderAnalysisResult(d){
  var r=document.getElementById("analyzeResult");
  var sc=d.total_score||0;
  var pct=(sc/10*100).toFixed(0);
  var cls=sc>=8?"high":sc>=6?"med":"low";
  var dec=d.final_decision||"UNKNOWN";
  var h='<div class="card">';
  h+='<div style="display:flex;justify-content:space-between;align-items:center">';
  h+='<span class="decision-badge decision-'+dec+'">'+dec+'</span>';
  h+='<span style="font-size:1.5rem;font-weight:700">'+sc.toFixed(1)+'<span style="font-size:.85rem;color:#888">/10</span></span></div>';
  h+='<div class="score-bar"><div class="score-fill score-'+cls+'" style="width:'+pct+'%"></div></div>';
  h+='<p style="font-size:.83rem;color:#aaa;margin-top:.3rem">'+escapeHtml(d.score_decision_reason||d.next_step||"")+'</p>';
  if(d.validation_blocking&&d.validation_blocking.length){
    h+='<div class="section"><h3>&#x1F6D1; Blocking Issues</h3>';
    d.validation_blocking.forEach(function(b){h+='<p class="blocking">• '+escapeHtml(b)+'</p>'});h+='</div>'
  }
  if(d.validation_reasons&&d.validation_reasons.length){
    h+='<div class="section"><h3>&#x2705; Validation</h3>';
    d.validation_reasons.forEach(function(v){h+='<p class="reason">• '+escapeHtml(v)+'</p>'});h+='</div>'
  }
  if(d.score_dimensions&&d.score_dimensions.length){
    h+='<div class="section"><h3>&#x1F4CA; Score Breakdown</h3>';
    d.score_dimensions.forEach(function(dim){
      var dp=(dim.score/2*100).toFixed(0);var dc=dim.score>=1.5?"high":dim.score>=1?"med":"low";
      h+='<div class="detail-row"><span class="detail-label">'+escapeHtml(dim.name)+'</span><span class="detail-value">'+dim.score.toFixed(1)+'/2</span></div>';
      h+='<div class="score-bar"><div class="score-fill score-'+dc+'" style="width:'+dp+'%"></div></div>';
      h+='<p style="font-size:.78rem;color:#666;margin-bottom:.25rem">'+escapeHtml(dim.reason)+'</p>';
    });h+='</div>'
  }
  var o=d.offer||{};
  if(o.decision==="generated"){
    h+='<div class="section"><h3>&#x1F4B0; Offer</h3>';
    h+=detailRow("Pricing",o.pricing);h+=detailRow("Model",o.pricing_model);
    h+=detailRow("Delivery",o.delivery_method);h+=detailRow("Value",o.value_proposition);
    h+=detailRow("CTA",o.cta);h+='</div>'
  }
  var di=d.distribution||{};
  if(di.decision==="generated"){
    h+='<div class="section"><h3>&#x1F680; Distribution</h3>';
    h+=detailRow("Channel",di.primary_channel);h+=detailRow("Acquisition",di.acquisition_method);
    h+=detailRow("First 10 Users",di.first_10_users_plan);h+=detailRow("Messaging",di.messaging);
    if(di.execution_steps&&di.execution_steps.length){
      h+='<p style="font-size:.83rem;color:#aaa;margin-top:.35rem">Steps:</p>';
      di.execution_steps.forEach(function(s,i){h+='<p style="font-size:.8rem;color:#ccc;margin-left:.5rem">'+(i+1)+'. '+escapeHtml(s)+'</p>'})
    }
    h+='</div>'
  }
  h+='<div class="section"><h3>&#x27A1;&#xFE0F; Next Step</h3>';
  h+='<p style="font-size:.88rem">'+escapeHtml(d.next_step||"Awaiting analysis.")+'</p>';
  h+='<p style="font-size:.78rem;color:#555;margin-top:.25rem">Stage: '+escapeHtml(d.pipeline_stage||"unknown")+'</p></div>';
  if(dec==="APPROVED"){
    h+='<div class="section" style="display:flex;gap:.5rem;flex-wrap:wrap">';
    h+='<button class="btn btn-success btn-sm" onclick="approveAndCreateProject()">&#x2705; Approve &amp; Create Project</button>';
    h+='<button class="btn btn-ghost btn-sm" onclick="saveDraft()">&#x1F4BE; Save as Draft</button>';
    h+='</div>'
  }
  h+='</div>';
  r.innerHTML=h;r.style.display="block";
}

function approveAndCreateProject(){
  if(!_lastAnalysisData){toast("No analysis data available","error");return}
  var d=_lastAnalysisData;
  var idea=document.getElementById("idea").value.trim();
  var body={
    name:idea.substring(0,60),
    status:"approved",
    description:idea,
    metadata:{analysis:d}
  };
  fetch("/portfolio/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})
    .then(function(r){if(!r.ok)return r.json().then(function(e){throw new Error(e.detail||r.statusText)});return r.json()})
    .then(function(){toast("Project created and approved!","success");switchTab("portfolio")})
    .catch(function(err){toast("Failed: "+err.message,"error")});
}

function saveDraft(){
  if(!_lastAnalysisData){toast("No analysis data available","error");return}
  var idea=document.getElementById("idea").value.trim();
  var body={
    name:idea.substring(0,60),
    status:"idea",
    description:idea,
    metadata:{analysis:_lastAnalysisData}
  };
  fetch("/portfolio/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})
    .then(function(r){if(!r.ok)return r.json().then(function(e){throw new Error(e.detail||r.statusText)});return r.json()})
    .then(function(){toast("Saved as draft!","success")})
    .catch(function(err){toast("Failed: "+err.message,"error")});
}

/* ── Portfolio ───────────────────────────────────────────── */
var _portfolioData=[];
function loadPortfolio(){
  document.getElementById("portfolioTable").innerHTML='<div class="loading-block"><span class="spinner"></span></div>';
  fetch("/portfolio/projects").then(function(r){return r.json()}).then(function(projects){
    _portfolioData=projects;
    renderPortfolioTable(projects);
  }).catch(function(){document.getElementById("portfolioTable").innerHTML='<div class="empty-state" style="color:#dc2626;padding:2rem">Failed to load projects.</div>'});
}

function renderPortfolioTable(projects){
  var wrap=document.getElementById("portfolioTable");
  if(!projects||!projects.length){wrap.innerHTML='<div class="empty-state" style="padding:2rem">No projects yet. Click "+ Add Project" or analyze an idea to get started.</div>';return}
  var h='<table class="tbl"><thead><tr><th>Name</th><th>Status</th><th>Repo</th><th>Deploy</th><th>Created</th><th>Actions</th></tr></thead><tbody>';
  projects.forEach(function(p){
    var id=p.project_id;
    var repo=p.repo_url?'<a href="'+escapeHtml(p.repo_url)+'" target="_blank">&#x1F517; Repo</a>':'<span style="color:#555">—</span>';
    var deploy=p.deploy_url?'<a href="'+escapeHtml(p.deploy_url)+'" target="_blank">&#x1F310; Deploy</a>':'<span style="color:#555">—</span>';
    var created=p.created_at?new Date(p.created_at).toLocaleDateString():"—";
    var actions='<div style="display:flex;gap:.3rem;flex-wrap:wrap">';
    if(p.status==="idea")actions+='<button class="btn btn-success btn-sm" onclick="transitionProject(\''+id+'\',\'approved\')">&#x2705; Approve</button>';
    if(p.status==="approved")actions+='<button class="btn btn-primary btn-sm" onclick="buildProject(\''+id+'\')">&#x1F680; Build</button>';
    if(p.status!=="killed")actions+='<button class="btn btn-danger btn-sm" onclick="transitionProject(\''+id+'\',\'killed\')">&#x274C; Kill</button>';
    actions+='<button class="btn btn-ghost btn-sm" onclick="openDistribution(\''+escapeHtml(p.name||id)+'\')">&#x1F4E3; Share</button>';
    actions+='</div>';
    h+='<tr><td>'+escapeHtml(p.name||id)+'<br><span style="font-size:.75rem;color:#555">'+id+'</span></td><td>'+statusBadge(p.status)+'</td><td>'+repo+'</td><td>'+deploy+'</td><td>'+created+'</td><td>'+actions+'</td></tr>';
  });
  h+='</tbody></table>';
  wrap.innerHTML=h;
}

function transitionProject(id,status){
  fetch("/portfolio/projects/"+id+"/transition",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({status:status})})
    .then(function(r){if(!r.ok)return r.json().then(function(e){throw new Error(e.detail||r.statusText)});return r.json()})
    .then(function(){toast("Status updated to "+status,"success");loadPortfolio()})
    .catch(function(err){toast("Failed: "+err.message,"error")});
}

function buildProject(id){
  document.getElementById("buildProjectId").value=id;
  switchTab("factory");
  setTimeout(function(){document.getElementById("launchBuildBtn").scrollIntoView({behavior:"smooth"})},100);
}

function openDistribution(name){
  document.getElementById("shareTitle").value=name;
  switchTab("distribution");
}

function toggleAddProject(){
  var f=document.getElementById("addProjectForm");
  f.style.display=f.style.display==="none"?"block":"none";
}

function addProject(){
  var name=document.getElementById("newProjName").value.trim();
  if(!name){toast("Name is required","error");return}
  setBtnLoading("addProjBtn",true,"Saving...");
  var body={name:name,status:document.getElementById("newProjStatus").value,description:document.getElementById("newProjDesc").value.trim()};
  fetch("/portfolio/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})
    .then(function(r){if(!r.ok)return r.json().then(function(e){throw new Error(e.detail||r.statusText)});return r.json()})
    .then(function(){toast("Project added!","success");document.getElementById("addProjectForm").style.display="none";document.getElementById("newProjName").value="";document.getElementById("newProjDesc").value="";loadPortfolio()})
    .catch(function(err){toast("Failed: "+err.message,"error")})
    .finally(function(){setBtnLoading("addProjBtn",false,"&#x2713; Save")});
}

/* ── Factory ─────────────────────────────────────────────── */
function loadFactoryRuns(){
  document.getElementById("factoryRunsTable").innerHTML='<div class="loading-block"><span class="spinner"></span></div>';
  fetch("/factory/runs").then(function(r){return r.json()}).then(function(runs){
    var wrap=document.getElementById("factoryRunsTable");
    if(!runs||!runs.length){wrap.innerHTML='<div class="empty-state" style="padding:2rem">No factory runs yet.</div>';return}
    var statusColor={pending:"badge-gray",running:"badge-yellow",succeeded:"badge-green",failed:"badge-red"};
    var h='<table class="tbl"><thead><tr><th>Run ID</th><th>Project</th><th>Status</th><th>Repo</th><th>Deploy</th><th>Error</th></tr></thead><tbody>';
    runs.forEach(function(r){
      var repo=r.repo_url?'<a href="'+escapeHtml(r.repo_url)+'" target="_blank">&#x1F517;</a>':'—';
      var deploy=r.deploy_url?'<a href="'+escapeHtml(r.deploy_url)+'" target="_blank">&#x1F310;</a>':'—';
      var err=r.error?'<span style="color:#fca5a5;font-size:.78rem">'+escapeHtml(r.error)+'</span>':'—';
      h+='<tr><td style="font-size:.78rem;color:#888">'+escapeHtml(r.run_id||"")+'</td>';
      h+='<td style="font-size:.8rem">'+escapeHtml(r.project_id||"")+'</td>';
      h+='<td><span class="badge '+(statusColor[r.status]||"badge-gray")+'">'+escapeHtml(r.status||"")+'</span></td>';
      h+='<td>'+repo+'</td><td>'+deploy+'</td><td>'+err+'</td></tr>';
    });
    h+='</tbody></table>';
    wrap.innerHTML=h;
  }).catch(function(){document.getElementById("factoryRunsTable").innerHTML='<div class="empty-state" style="color:#dc2626;padding:2rem">Failed to load runs.</div>'});
}

function launchBuild(){
  var projectId=document.getElementById("buildProjectId").value.trim();
  if(!projectId){toast("Project ID is required","error");return}
  var dryRun=document.getElementById("buildDryRun").checked;
  var template=document.getElementById("buildTemplate").value;
  setBtnLoading("launchBuildBtn",true,"Launching...");
  var brief={
    project_id:projectId,
    idea_id:"idea-"+projectId,
    hypothesis:"Build request from command center",
    target_user:"TBD",
    problem:"TBD",
    solution:"TBD",
    mvp_scope:["Core feature"],
    acceptance_criteria:["Deploys successfully"],
    landing_page_requirements:["Landing page"],
    cta:"Get started",
    pricing_hint:"TBD",
    deployment_target:"vercel",
    command_bundle:{template:template},
    feature_flags:{dry_run:dryRun,live_factory:!dryRun}
  };
  fetch("/factory/runs",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({build_brief:brief,dry_run:dryRun})})
    .then(function(r){if(!r.ok)return r.json().then(function(e){throw new Error(e.detail||r.statusText)});return r.json()})
    .then(function(d){toast("Build launched! Status: "+d.status,"success");loadFactoryRuns()})
    .catch(function(err){toast("Failed: "+err.message,"error")})
    .finally(function(){setBtnLoading("launchBuildBtn",false,"&#x1F680; Launch Build")});
}

function verifyDeployment(){
  var projectId=document.getElementById("verifyProjectId").value.trim();
  var deployUrl=document.getElementById("verifyDeployUrl").value.trim();
  if(!projectId||!deployUrl){toast("Project ID and Deploy URL are required","error");return}
  setBtnLoading("verifyBtn",true,"Verifying...");
  var body={project_id:projectId,deploy_url:deployUrl,repo_url:document.getElementById("verifyRepoUrl").value.trim()};
  fetch("/factory/verify-deployment",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})
    .then(function(r){if(!r.ok)return r.json().then(function(e){throw new Error(e.detail||r.statusText)});return r.json()})
    .then(function(d){
      var color=d.status==="healthy"?"#86efac":d.status==="degraded"?"#fcd34d":"#fca5a5";
      var h='<div style="padding:.75rem;background:#111;border-radius:8px;border:1px solid #2a2a4a">';
      h+='<div style="font-weight:600;color:'+color+'">'+escapeHtml(d.status.toUpperCase())+'</div>';
      h+='<div style="font-size:.78rem;color:#888;margin-top:.25rem">Checks: '+d.checks_performed.length+'</div>';
      if(d.issues.length)h+='<div style="color:#fca5a5;font-size:.78rem;margin-top:.25rem">Issues: '+d.issues.map(escapeHtml).join(", ")+'</div>';
      h+='</div>';
      document.getElementById("verifyResult").innerHTML=h;
    })
    .catch(function(err){toast("Failed: "+err.message,"error")})
    .finally(function(){setBtnLoading("verifyBtn",false,"&#x1F50D; Verify")});
}

/* ── Distribution ────────────────────────────────────────── */
function generateShareMessages(){
  var title=document.getElementById("shareTitle").value.trim();
  var url=document.getElementById("shareUrl").value.trim();
  var desc=document.getElementById("shareDesc").value.trim();
  if(!title||!url||!desc){toast("Title, URL and Description are required","error");return}
  setBtnLoading("shareBtn",true,"Generating...");
  document.getElementById("shareLoading").style.display="block";
  document.getElementById("shareResults").style.display="none";
  var body={
    title:title,url:url,description:desc,
    target_user:document.getElementById("shareTarget").value.trim(),
    cta:document.getElementById("shareCta").value.trim(),
    price:document.getElementById("sharePrice").value.trim()
  };
  fetch("/api/distribution/share-messages",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})
    .then(function(r){if(!r.ok)return r.json().then(function(e){throw new Error(e.detail||r.statusText)});return r.json()})
    .then(function(d){renderShareResults(d)})
    .catch(function(err){toast("Failed: "+err.message,"error")})
    .finally(function(){setBtnLoading("shareBtn",false,"&#x1F4E3; Generate Messages");document.getElementById("shareLoading").style.display="none"});
}

function renderShareResults(d){
  var container=document.getElementById("shareResults");
  var platforms=d.messages||d.platforms||d;
  if(!platforms||typeof platforms!=="object"){container.innerHTML='<div class="card"><p style="color:#888">No messages returned.</p></div>';container.style.display="block";return}
  var h='<div>';
  Object.keys(platforms).forEach(function(pName){
    var msg=platforms[pName];
    if(!msg)return;
    h+='<div class="platform-card">';
    h+='<div class="platform-name"><span>'+escapeHtml(pName.replace(/_/g," ").toUpperCase())+'</span>';
    h+='<button class="copy-btn" onclick="copyText(\'share-'+pName+'\')">Copy</button></div>';
    h+='<div class="platform-msg" id="share-'+pName+'">'+escapeHtml(typeof msg==="string"?msg:JSON.stringify(msg))+'</div>';
    h+='</div>';
  });
  h+='</div>';
  container.innerHTML=h;container.style.display="block";
}

function copyText(id){
  var el=document.getElementById(id);
  if(!el)return;
  navigator.clipboard.writeText(el.textContent).then(function(){toast("Copied!","success")}).catch(function(){toast("Copy failed","error")});
}

/* ── Revenue ─────────────────────────────────────────────── */
function getRevenueLearning(){
  var id=document.getElementById("revProjectId").value.trim();
  if(!id){toast("Project ID is required","error");return}
  setBtnLoading("revLearningBtn",true,"Loading...");
  document.getElementById("revLoading").style.display="block";
  fetch("/revenue/projects/"+encodeURIComponent(id)+"/learning-report")
    .then(function(r){if(!r.ok)return r.json().then(function(e){throw new Error(e.detail||r.statusText)});return r.json()})
    .then(function(d){
      document.getElementById("revResult").innerHTML='<div class="card"><div class="card-title">&#x1F4C8; Learning Report</div><div class="rev-result">'+escapeHtml(JSON.stringify(d,null,2))+'</div></div>';
    })
    .catch(function(err){toast("Failed: "+err.message,"error")})
    .finally(function(){setBtnLoading("revLearningBtn",false,"&#x1F4C8; Get Learning Report");document.getElementById("revLoading").style.display="none"});
}

function generateBusinessOutput(){
  var id=document.getElementById("revProjectId").value.trim();
  if(!id){toast("Project ID is required","error");return}
  setBtnLoading("revOutputBtn",true,"Generating...");
  document.getElementById("revLoading").style.display="block";
  fetch("/revenue/projects/"+encodeURIComponent(id)+"/business-output",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({})})
    .then(function(r){if(!r.ok)return r.json().then(function(e){throw new Error(e.detail||r.statusText)});return r.json()})
    .then(function(d){
      document.getElementById("revResult").innerHTML='<div class="card"><div class="card-title">&#x1F4CA; Business Output</div><div class="rev-result">'+escapeHtml(JSON.stringify(d,null,2))+'</div></div>';
    })
    .catch(function(err){toast("Failed: "+err.message,"error")})
    .finally(function(){setBtnLoading("revOutputBtn",false,"&#x1F4CA; Generate Business Output");document.getElementById("revLoading").style.display="none"});
}

/* ── Boot ────────────────────────────────────────────────── */
loadDashboard();
var _refreshInterval=setInterval(function(){if(_activeTab==="dashboard")loadDashboard()},30000);
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def root_ui() -> HTMLResponse:
    """Serve the root idea-analysis UI."""
    html = _ROOT_HTML.replace("{version}", _VERSION)
    return HTMLResponse(content=html)
