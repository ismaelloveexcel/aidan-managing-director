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
# Root UI – embedded HTML 6-tab command center for solo non-technical operator
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
/* ---------- tabs ---------- */
.topbar{background:#111;border-bottom:1px solid #222;padding:.5rem 1rem;
display:flex;align-items:center;gap:1rem;flex-wrap:wrap}
.topbar h1{font-size:1.1rem;color:#fff;white-space:nowrap}
.topbar .ver{font-size:.7rem;color:#555}
.tabs{display:flex;gap:.25rem;flex-wrap:wrap;flex:1}
.tab-btn{padding:.45rem .9rem;border:1px solid #333;border-radius:6px;background:transparent;
color:#888;cursor:pointer;font-size:.82rem;white-space:nowrap;transition:all .15s}
.tab-btn:hover{border-color:#5b6ef7;color:#ccc}
.tab-btn.active{background:#5b6ef7;border-color:#5b6ef7;color:#fff;font-weight:600}
.tab-pane{display:none;padding:1.5rem;max-width:1100px;margin:0 auto}
.tab-pane.active{display:block}
/* ---------- cards ---------- */
.card{background:#1a1a2e;border:1px solid #333;border-radius:12px;padding:1.25rem;margin-bottom:1.25rem}
.card-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem;margin-bottom:1.25rem}
.stat-card{background:#1a1a2e;border:1px solid #333;border-radius:10px;padding:1rem;text-align:center}
.stat-card .num{font-size:2.2rem;font-weight:700;color:#5b6ef7}
.stat-card .lbl{font-size:.8rem;color:#888;margin-top:.2rem}
/* ---------- forms ---------- */
label{display:block;font-size:.82rem;color:#aaa;margin-bottom:.25rem;margin-top:.75rem}
label:first-child{margin-top:0}
textarea,input,select{width:100%;padding:.55rem .75rem;border-radius:8px;border:1px solid #444;
background:#111;color:#e0e0e0;font-size:.88rem;font-family:inherit}
textarea{resize:vertical;min-height:72px}
textarea:focus,input:focus,select:focus{outline:none;border-color:#5b6ef7}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:.75rem}
.row3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:.75rem}
/* ---------- buttons ---------- */
.btn{display:inline-block;padding:.6rem 1.1rem;border:none;border-radius:8px;font-size:.88rem;
font-weight:600;cursor:pointer;transition:all .15s;white-space:nowrap}
.btn-primary{background:#5b6ef7;color:#fff}
.btn-primary:hover:not(:disabled){background:#4a5ce6}
.btn-success{background:#16a34a;color:#fff}
.btn-success:hover:not(:disabled){background:#15803d}
.btn-danger{background:#dc2626;color:#fff}
.btn-danger:hover:not(:disabled){background:#b91c1c}
.btn-outline{background:transparent;border:1px solid #444;color:#ccc}
.btn-outline:hover:not(:disabled){border-color:#5b6ef7;color:#fff}
.btn-sm{padding:.35rem .65rem;font-size:.78rem}
.btn:disabled{opacity:.4;cursor:not-allowed}
.btn-row{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:1rem}
/* ---------- table ---------- */
.tbl{width:100%;border-collapse:collapse;font-size:.85rem}
.tbl th{padding:.55rem .75rem;text-align:left;color:#888;font-weight:500;border-bottom:1px solid #333}
.tbl td{padding:.55rem .75rem;border-bottom:1px solid #222;vertical-align:middle}
.tbl tr:last-child td{border-bottom:none}
/* ---------- badges ---------- */
.badge{display:inline-block;padding:.15rem .5rem;border-radius:4px;font-size:.73rem;font-weight:600}
.badge-idea{background:#333;color:#aaa}
.badge-review{background:#1e3a5f;color:#93c5fd}
.badge-approved{background:#1e3a5f;color:#60a5fa}
.badge-queued{background:#2d1e5f;color:#c4b5fd}
.badge-building{background:#3b2d00;color:#fbbf24}
.badge-launched{background:#14532d;color:#86efac}
.badge-monitoring{background:#14532d;color:#86efac}
.badge-scaled{background:#0e3a1a;color:#4ade80}
.badge-killed{background:#450a0a;color:#fca5a5}
/* ---------- misc ---------- */
.section-title{font-size:1rem;font-weight:600;color:#fff;margin-bottom:.75rem}
.sub-title{font-size:.88rem;color:#888;margin-bottom:.5rem}
.empty-state{text-align:center;padding:2.5rem;color:#555;font-size:.9rem}
.health-dot{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:.35rem}
.health-green{background:#16a34a}
.health-yellow{background:#d97706}
.health-red{background:#dc2626}
.msg-box{background:#111;border:1px solid #333;border-radius:8px;padding:.85rem;margin-bottom:.5rem}
.msg-box .plat{font-size:.75rem;color:#888;margin-bottom:.25rem;font-weight:600;text-transform:uppercase}
.msg-box pre{font-size:.82rem;color:#d4d4d4;white-space:pre-wrap;word-break:break-word;font-family:inherit}
.copy-btn{float:right;padding:.2rem .55rem;font-size:.72rem}
/* ---------- toast ---------- */
#toast-container{position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;display:flex;
flex-direction:column;gap:.5rem}
.toast{padding:.7rem 1.1rem;border-radius:8px;font-size:.85rem;max-width:320px;
box-shadow:0 4px 12px rgba(0,0,0,.4);animation:slideIn .2s ease}
.toast-ok{background:#14532d;color:#86efac;border:1px solid #16a34a}
.toast-err{background:#450a0a;color:#fca5a5;border:1px solid #dc2626}
.toast-info{background:#1e3a5f;color:#93c5fd;border:1px solid #1d4ed8}
@keyframes slideIn{from{transform:translateX(60px);opacity:0}to{transform:none;opacity:1}}
/* ---------- spinner ---------- */
.spinner{display:inline-block;width:18px;height:18px;border:2px solid #333;
border-top-color:#5b6ef7;border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-row{text-align:center;padding:1.5rem;color:#555;font-size:.88rem}
/* ---------- score / result ---------- */
.decision-badge{display:inline-block;padding:.3rem .8rem;border-radius:6px;
font-weight:700;font-size:.88rem;margin:.4rem 0}
.decision-APPROVED{background:#16a34a;color:#fff}
.decision-HOLD{background:#d97706;color:#fff}
.decision-REJECTED{background:#dc2626;color:#fff}
.score-bar{height:6px;border-radius:3px;background:#333;margin:.25rem 0;overflow:hidden}
.score-fill{height:100%;border-radius:3px;transition:width .5s}
.score-high{background:#16a34a}
.score-med{background:#d97706}
.score-low{background:#dc2626}
.detail-row{display:flex;justify-content:space-between;padding:.2rem 0;font-size:.83rem}
.detail-label{color:#888}
.detail-value{color:#e0e0e0;text-align:right;max-width:60%}
.section{margin-top:.85rem;padding-top:.85rem;border-top:1px solid #333}
.blocking{color:#fca5a5;font-size:.83rem;margin:.15rem 0}
.reason-ok{color:#86efac;font-size:.83rem;margin:.15rem 0}
.tag{display:inline-block;background:#222;border:1px solid #444;border-radius:4px;
padding:.1rem .35rem;font-size:.73rem;margin:.1rem .08rem;color:#ccc}
.error-box{background:#2d1111;border:1px solid #dc2626;border-radius:8px;padding:.85rem;
color:#fca5a5;margin-top:.75rem;display:none;font-size:.88rem}
@media(max-width:600px){
.row2,.row3{grid-template-columns:1fr}
.topbar{gap:.5rem}
.tabs{gap:.2rem}
}
</style>
</head>
<body>

<div class="topbar">
<h1>&#x1F9E0; AI-DAN <span class="ver">v{version}</span></h1>
<div class="tabs">
<button class="tab-btn active" onclick="switchTab('dashboard')">&#x1F4CA; Dashboard</button>
<button class="tab-btn" onclick="switchTab('analyze')">&#x1F4A1; Analyze Idea</button>
<button class="tab-btn" onclick="switchTab('portfolio')">&#x1F4E6; Portfolio</button>
<button class="tab-btn" onclick="switchTab('factory')">&#x1F3ED; Factory</button>
<button class="tab-btn" onclick="switchTab('distribution')">&#x1F4E3; Distribution</button>
<button class="tab-btn" onclick="switchTab('revenue')">&#x1F4B0; Revenue</button>
</div>
</div>

<div id="toast-container"></div>

<!-- ================================================================ TAB 1: DASHBOARD -->
<div id="tab-dashboard" class="tab-pane active">
<div id="dash-stats" class="card-grid">
<div class="stat-card"><div class="num" id="stat-total">–</div><div class="lbl">Total Projects</div></div>
<div class="stat-card"><div class="num" id="stat-approved" style="color:#60a5fa">–</div><div class="lbl">Approved</div></div>
<div class="stat-card"><div class="num" id="stat-building" style="color:#fbbf24">–</div><div class="lbl">Building</div></div>
<div class="stat-card"><div class="num" id="stat-launched" style="color:#86efac">–</div><div class="lbl">Launched</div></div>
</div>

<div class="card" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.75rem">
<div id="health-indicator" style="font-size:.9rem">
<span class="health-dot health-yellow"></span> Checking portfolio health…
</div>
<div style="font-size:.75rem;color:#555">Auto-refresh 30s &nbsp;<span id="refresh-countdown">30</span>s</div>
</div>

<div class="card">
<div class="section-title">Quick Actions</div>
<div class="btn-row">
<button class="btn btn-primary" onclick="switchTab('analyze')">&#x1F4A1; New Idea</button>
<button class="btn btn-outline" onclick="switchTab('portfolio')">&#x1F4E6; View Portfolio</button>
<button class="btn btn-outline" onclick="switchTab('factory')">&#x1F3ED; Factory Runs</button>
<button class="btn btn-outline" onclick="refreshDashboard()">&#x1F504; Refresh Now</button>
</div>
</div>

<div class="card">
<div class="section-title">Recent Projects</div>
<div id="dash-recent"><div class="loading-row"><span class="spinner"></span></div></div>
</div>
</div>

<!-- ================================================================ TAB 2: ANALYZE IDEA -->
<div id="tab-analyze" class="tab-pane">
<div class="card">
<div class="section-title">Analyze an Idea</div>

<label for="idea">Your Idea *</label>
<textarea id="idea" placeholder="Describe your idea in detail…"></textarea>

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

<div class="row2">
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
<button class="btn btn-primary" id="analyzeBtn" onclick="runAnalysis()">&#x1F50D; Analyze Idea</button>
</div>
</div>

<div class="error-box" id="analyzeError"></div>

<div id="analyzeLoading" style="display:none" class="loading-row"><span class="spinner"></span> Running full pipeline analysis…</div>

<div id="analyzeResult" style="display:none"></div>
</div>

<!-- ================================================================ TAB 3: PORTFOLIO -->
<div id="tab-portfolio" class="tab-pane">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.75rem;flex-wrap:wrap;gap:.5rem">
<div class="section-title" style="margin:0">Portfolio Projects</div>
<button class="btn btn-primary btn-sm" onclick="toggleAddProject()">&#x2B; Add Project</button>
</div>

<div id="add-project-form" class="card" style="display:none">
<div class="section-title">Add New Project</div>
<div class="row2">
<div>
<label>Name *</label>
<input id="np-name" placeholder="Project name"/>
</div>
<div>
<label>Status</label>
<select id="np-status">
<option value="idea">Idea</option>
<option value="review">Review</option>
<option value="approved">Approved</option>
</select>
</div>
</div>
<label>Description *</label>
<textarea id="np-desc" placeholder="Brief description…" style="min-height:60px"></textarea>
<div class="btn-row">
<button class="btn btn-success btn-sm" onclick="createProject()">Save Project</button>
<button class="btn btn-outline btn-sm" onclick="toggleAddProject()">Cancel</button>
</div>
</div>

<div id="portfolio-loading" class="loading-row"><span class="spinner"></span></div>
<div id="portfolio-table" style="display:none"></div>
<div id="portfolio-empty" class="empty-state" style="display:none">No projects yet. Add your first project above.</div>
</div>

<!-- ================================================================ TAB 4: FACTORY -->
<div id="tab-factory" class="tab-pane">
<div class="row2" style="margin-bottom:1.25rem">
<div class="card" style="margin:0">
<div class="section-title">Trigger Build</div>
<label>Project ID *</label>
<input id="fb-project-id" placeholder="e.g. prj-abc123"/>
<label>Template</label>
<select id="fb-template">
<option value="saas-template">SaaS Template</option>
<option value="landing-page">Landing Page</option>
</select>
<label style="display:flex;align-items:center;gap:.5rem;margin-top:.75rem;cursor:pointer">
<input type="checkbox" id="fb-dry-run" checked style="width:auto"/>
<span>Dry Run (no real deployment)</span>
</label>
<div class="btn-row">
<button class="btn btn-primary btn-sm" onclick="triggerBuild()">&#x1F680; Trigger Build</button>
</div>
</div>
<div class="card" style="margin:0">
<div class="section-title">Verify Deployment</div>
<label>Project ID *</label>
<input id="vd-project-id" placeholder="e.g. prj-abc123"/>
<label>Deploy URL</label>
<input id="vd-url" placeholder="https://your-app.vercel.app"/>
<div class="btn-row">
<button class="btn btn-outline btn-sm" onclick="verifyDeployment()">&#x1F50D; Verify</button>
</div>
<div id="vd-result" style="margin-top:.75rem;font-size:.83rem"></div>
</div>
</div>

<div class="card">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.75rem">
<div class="section-title" style="margin:0">Factory Runs</div>
<button class="btn btn-outline btn-sm" onclick="loadFactoryRuns()">&#x1F504; Refresh</button>
</div>
<div id="factory-loading" class="loading-row"><span class="spinner"></span></div>
<div id="factory-table" style="display:none"></div>
<div id="factory-empty" class="empty-state" style="display:none">No factory runs yet.</div>
</div>
</div>

<!-- ================================================================ TAB 5: DISTRIBUTION -->
<div id="tab-distribution" class="tab-pane">
<div class="card">
<div class="section-title">Generate Share Messages</div>
<div class="row2">
<div>
<label>Title *</label>
<input id="dist-title" placeholder="Product or project title"/>
</div>
<div>
<label>URL *</label>
<input id="dist-url" placeholder="https://…"/>
</div>
</div>
<label>Description *</label>
<textarea id="dist-desc" placeholder="Brief product description…" style="min-height:60px"></textarea>
<div class="row2">
<div>
<label>Target User</label>
<input id="dist-target" placeholder="Who is this for?"/>
</div>
<div>
<label>Call to Action</label>
<input id="dist-cta" placeholder="e.g. Try it free"/>
</div>
</div>
<div class="btn-row">
<button class="btn btn-primary" id="distBtn" onclick="generateShareMessages()">&#x1F4E3; Generate Messages</button>
</div>
</div>

<div class="error-box" id="distError"></div>
<div id="distLoading" style="display:none" class="loading-row"><span class="spinner"></span> Generating share messages…</div>
<div id="distResult" style="display:none"></div>
</div>

<!-- ================================================================ TAB 6: REVENUE -->
<div id="tab-revenue" class="tab-pane">
<div class="card">
<div class="section-title">Revenue Intelligence</div>
<div class="row2">
<div>
<label>Project ID *</label>
<input id="rev-project-id" placeholder="e.g. prj-abc123"/>
</div>
<div style="display:flex;align-items:flex-end;gap:.5rem">
<button class="btn btn-primary btn-sm" onclick="getRevenueReport()" style="margin-bottom:0">&#x1F4CA; Get Report</button>
</div>
</div>
</div>

<div id="revReportLoading" style="display:none" class="loading-row"><span class="spinner"></span> Loading report…</div>
<div id="revReport" style="display:none"></div>

<div class="card" style="margin-top:1.25rem">
<div class="section-title">Business Output Generator</div>
<label>Project ID *</label>
<input id="biz-project-id" placeholder="e.g. prj-abc123"/>
<label>Pricing Strategy</label>
<select id="biz-pricing">
<option value="default">Default</option>
<option value="freemium">Freemium</option>
<option value="premium">Premium</option>
<option value="usage-based">Usage-based</option>
</select>
<div class="btn-row">
<button class="btn btn-success btn-sm" onclick="generateBusinessOutput()">&#x26A1; Generate Output</button>
</div>
</div>

<div id="bizOutputLoading" style="display:none" class="loading-row"><span class="spinner"></span> Generating…</div>
<div id="bizOutput" style="display:none"></div>
</div>

<script>
/* ======================================================= UTILITIES */
function esc(s){if(s==null)return'';var d=document.createElement('div');
d.appendChild(document.createTextNode(String(s)));return d.innerHTML}

function toast(msg,type){
  var t=document.getElementById('toast-container');
  var d=document.createElement('div');
  d.className='toast toast-'+(type||'info');
  d.textContent=msg;
  t.appendChild(d);
  setTimeout(function(){if(d.parentNode)d.parentNode.removeChild(d)},3500)
}

function showSpinner(id){document.getElementById(id).style.display='block'}
function hideSpinner(id){document.getElementById(id).style.display='none'}

async function apiFetch(url,opts){
  var r=await fetch(url,opts);
  if(!r.ok){var e=await r.json().catch(function(){return{detail:r.statusText}});
    throw new Error(e.detail||r.statusText)}
  return r.json()
}

/* ======================================================= TABS */
function switchTab(name){
  document.querySelectorAll('.tab-pane').forEach(function(p){p.classList.remove('active')});
  document.querySelectorAll('.tab-btn').forEach(function(b){b.classList.remove('active')});
  document.getElementById('tab-'+name).classList.add('active');
  var btns=document.querySelectorAll('.tab-btn');
  var names=['dashboard','analyze','portfolio','factory','distribution','revenue'];
  btns[names.indexOf(name)].classList.add('active');
  if(name==='dashboard')refreshDashboard();
  if(name==='portfolio')loadPortfolio();
  if(name==='factory')loadFactoryRuns();
}

/* ======================================================= DASHBOARD */
var _refreshTimer=null;
var _countdown=30;

function startRefreshTimer(){
  clearInterval(_refreshTimer);
  _countdown=30;
  document.getElementById('refresh-countdown').textContent=30;
  _refreshTimer=setInterval(function(){
    _countdown--;
    var el=document.getElementById('refresh-countdown');
    if(el)el.textContent=_countdown;
    if(_countdown<=0){refreshDashboard()}
  },1000)
}

async function refreshDashboard(){
  _countdown=30;
  try{
    var projects=await apiFetch('/portfolio/projects');
    var total=projects.length;
    var approved=projects.filter(function(p){return p.status==='approved'}).length;
    var building=projects.filter(function(p){return p.status==='building'}).length;
    var launched=projects.filter(function(p){return['launched','monitoring','scaled'].indexOf(p.status)>=0}).length;
    document.getElementById('stat-total').textContent=total;
    document.getElementById('stat-approved').textContent=approved;
    document.getElementById('stat-building').textContent=building;
    document.getElementById('stat-launched').textContent=launched;

    var hi=document.getElementById('health-indicator');
    var dotCls,label;
    if(launched>0){dotCls='health-green';label='Portfolio healthy — '+launched+' live project'+(launched>1?'s':'')}
    else if(building>0){dotCls='health-yellow';label='Building — '+building+' project'+(building>1?'s':'')+' in progress'}
    else if(total>0){dotCls='health-yellow';label='Ideas in pipeline — none launched yet'}
    else{dotCls='health-red';label='Empty portfolio — add your first idea'}
    hi.innerHTML='<span class="health-dot '+dotCls+'"></span>'+esc(label);

    var recent=projects.slice(-6).reverse();
    var el=document.getElementById('dash-recent');
    if(recent.length===0){el.innerHTML='<div class="empty-state">No projects yet.</div>';return}
    var h='<table class="tbl"><thead><tr><th>Name</th><th>Status</th><th>Updated</th></tr></thead><tbody>';
    recent.forEach(function(p){
      h+='<tr><td>'+esc(p.name)+'</td><td>'+statusBadge(p.status)+'</td><td style="color:#666;font-size:.78rem">'+esc((p.updated_at||'').substring(0,10))+'</td></tr>'
    });
    h+='</tbody></table>';
    el.innerHTML=h;
  }catch(e){toast('Dashboard refresh failed: '+e.message,'err')}
  startRefreshTimer()
}

/* ======================================================= ANALYZE IDEA */
async function runAnalysis(){
  var btn=document.getElementById('analyzeBtn');
  var errBox=document.getElementById('analyzeError');
  var idea=document.getElementById('idea').value.trim();
  if(!idea){errBox.textContent='Please enter an idea.';errBox.style.display='block';return}
  errBox.style.display='none';
  btn.disabled=true;
  showSpinner('analyzeLoading');
  document.getElementById('analyzeResult').style.display='none';

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
    var d=await apiFetch('/api/analyze/',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    renderAnalysisResult(d);
    _lastAnalysis=d;
    _lastIdea=idea;
  }catch(err){
    errBox.textContent='Error: '+err.message;errBox.style.display='block';
  }finally{btn.disabled=false;hideSpinner('analyzeLoading')}
}

var _lastAnalysis=null;
var _lastIdea='';

function renderAnalysisResult(d){
  var sc=d.total_score||0;
  var pct=(sc/10*100).toFixed(0);
  var cls=sc>=8?'high':sc>=6?'med':'low';
  var dec=d.final_decision||'UNKNOWN';

  var h='<div class="card">';
  h+='<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem">';
  h+='<span class="decision-badge decision-'+dec+'">'+dec+'</span>';
  h+='<span style="font-size:1.4rem;font-weight:700">'+sc.toFixed(1)+'<span style="font-size:.85rem;color:#888">/10</span></span>';
  h+='</div>';
  h+='<div class="score-bar"><div class="score-fill score-'+cls+'" style="width:'+pct+'%"></div></div>';
  h+='<p style="font-size:.82rem;color:#aaa;margin-top:.25rem">'+esc(d.score_decision_reason||d.next_step||'')+'</p>';

  if(d.validation_blocking&&d.validation_blocking.length){
    h+='<div class="section"><p class="sub-title">&#x1F6D1; Blocking Issues</p>';
    d.validation_blocking.forEach(function(b){h+='<p class="blocking">• '+esc(b)+'</p>'});
    h+='</div>'
  }
  if(d.validation_reasons&&d.validation_reasons.length){
    h+='<div class="section"><p class="sub-title">&#x2705; Validation</p>';
    d.validation_reasons.forEach(function(v){h+='<p class="reason-ok">• '+esc(v)+'</p>'});
    h+='</div>'
  }
  if(d.score_dimensions&&d.score_dimensions.length){
    h+='<div class="section"><p class="sub-title">&#x1F4CA; Score Breakdown</p>';
    d.score_dimensions.forEach(function(dim){
      var dp=(dim.score/2*100).toFixed(0);
      var dc=dim.score>=1.5?'high':dim.score>=1?'med':'low';
      h+='<div class="detail-row"><span class="detail-label">'+esc(dim.name)+'</span><span class="detail-value">'+dim.score.toFixed(1)+'/2</span></div>';
      h+='<div class="score-bar"><div class="score-fill score-'+dc+'" style="width:'+dp+'%"></div></div>';
      h+='<p style="font-size:.78rem;color:#777;margin-bottom:.25rem">'+esc(dim.reason)+'</p>'
    });
    h+='</div>'
  }

  /* Create Project button – only for APPROVED/HOLD */
  if(dec==='APPROVED'||dec==='HOLD'){
    h+='<div class="section">';
    h+='<button class="btn btn-success btn-sm" onclick="createProjectFromAnalysis()">&#x1F4BE; Create Project from This Idea</button>';
    h+='</div>'
  }

  h+='</div>';
  var el=document.getElementById('analyzeResult');
  el.innerHTML=h;el.style.display='block'
}

async function createProjectFromAnalysis(){
  if(!_lastAnalysis){toast('Run analysis first','err');return}
  var body={
    name:_lastIdea.substring(0,80)||'Untitled Idea',
    description:_lastIdea,
    status:'idea'
  };
  try{
    var p=await apiFetch('/portfolio/projects',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    toast('Project created: '+p.project_id,'ok');
    switchTab('portfolio')
  }catch(e){toast('Failed to create project: '+e.message,'err')}
}

/* ======================================================= PORTFOLIO */
async function loadPortfolio(){
  var loading=document.getElementById('portfolio-loading');
  var table=document.getElementById('portfolio-table');
  var empty=document.getElementById('portfolio-empty');
  loading.style.display='block';table.style.display='none';empty.style.display='none';
  try{
    var projects=await apiFetch('/portfolio/projects');
    loading.style.display='none';
    if(!projects.length){empty.style.display='block';return}
    var h='<div class="card" style="padding:0;overflow:auto">';
    h+='<table class="tbl"><thead><tr>';
    h+='<th>Name</th><th>Status</th><th>Updated</th><th>Actions</th>';
    h+='</tr></thead><tbody>';
    projects.forEach(function(p){
      h+='<tr>';
      h+='<td><span style="color:#e0e0e0;font-weight:500">'+esc(p.name)+'</span>';
      h+='<br><span style="color:#555;font-size:.75rem">'+esc(p.project_id)+'</span></td>';
      h+='<td>'+statusBadge(p.status)+'</td>';
      h+='<td style="color:#666;font-size:.78rem">'+esc((p.updated_at||'').substring(0,10))+'</td>';
      h+='<td>';
      h+=actionBtns(p);
      h+='</td></tr>'
    });
    h+='</tbody></table></div>';
    table.innerHTML=h;table.style.display='block'
  }catch(e){
    loading.style.display='none';
    toast('Failed to load portfolio: '+e.message,'err')
  }
}

function statusBadge(s){
  var cls='badge-'+(s||'idea').toLowerCase();
  return'<span class="badge '+cls+'">'+esc(s||'idea')+'</span>'
}

function actionBtns(p){
  var h='<div style="display:flex;gap:.3rem;flex-wrap:wrap">';
  if(p.status==='idea'||p.status==='review'){
    h+='<button class="btn btn-success btn-sm" onclick="approveProject(\''+esc(p.project_id)+'\')">Approve</button>'
  }
  if(p.status==='approved'){
    h+='<button class="btn btn-primary btn-sm" onclick="buildProject(\''+esc(p.project_id)+'\')">&#x1F680; Build</button>'
  }
  h+='<button class="btn btn-outline btn-sm" onclick="shareProject(\''+esc(p.project_id)+'\',\''+esc(p.name)+'\')">&#x1F4E3; Share</button>';
  if(p.status!=='killed'){
    h+='<button class="btn btn-danger btn-sm" onclick="killProject(\''+esc(p.project_id)+'\')">Kill</button>'
  }
  h+='</div>';
  return h
}

async function approveProject(id){
  try{
    await apiFetch('/portfolio/projects/'+id+'/transition',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({new_state:'approved'})});
    toast('Project approved','ok');loadPortfolio()
  }catch(e){toast('Approve failed: '+e.message,'err')}
}

async function killProject(id){
  if(!confirm('Kill project '+id+'?'))return;
  try{
    await apiFetch('/portfolio/projects/'+id+'/transition',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({new_state:'killed'})});
    toast('Project killed','info');loadPortfolio()
  }catch(e){toast('Kill failed: '+e.message,'err')}
}

async function buildProject(id){
  try{
    var body={build_brief:{
      project_id:id,idea_id:'idea-'+id,
      hypothesis:'Build from portfolio',
      target_user:'operator',problem:'Build requested',solution:'Build requested',
      mvp_scope:['Core build'],acceptance_criteria:['Deployment passes'],
      landing_page_requirements:['Basic landing'],
      cta:'Get started',pricing_hint:'TBD',
      command_bundle:{source:'portfolio'},feature_flags:{dry_run:true,live_factory:false}
    },dry_run:true};
    var r=await apiFetch('/factory/runs',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    toast('Build triggered: '+r.run_id,'ok');switchTab('factory')
  }catch(e){toast('Build failed: '+e.message,'err')}
}

function shareProject(id,name){
  document.getElementById('dist-title').value=name;
  document.getElementById('dist-url').value='https://your-app.vercel.app/'+id;
  switchTab('distribution')
}

function toggleAddProject(){
  var f=document.getElementById('add-project-form');
  f.style.display=f.style.display==='none'?'block':'none'
}

async function createProject(){
  var name=document.getElementById('np-name').value.trim();
  var desc=document.getElementById('np-desc').value.trim();
  var status=document.getElementById('np-status').value;
  if(!name||!desc){toast('Name and description required','err');return}
  try{
    var p=await apiFetch('/portfolio/projects',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name:name,description:desc,status:status})});
    toast('Project created: '+p.project_id,'ok');
    toggleAddProject();
    document.getElementById('np-name').value='';
    document.getElementById('np-desc').value='';
    loadPortfolio()
  }catch(e){toast('Failed: '+e.message,'err')}
}

/* ======================================================= FACTORY */
async function loadFactoryRuns(){
  var loading=document.getElementById('factory-loading');
  var table=document.getElementById('factory-table');
  var empty=document.getElementById('factory-empty');
  loading.style.display='block';table.style.display='none';empty.style.display='none';
  try{
    var runs=await apiFetch('/factory/runs');
    loading.style.display='none';
    if(!runs.length){empty.style.display='block';return}
    var h='<div style="overflow:auto"><table class="tbl"><thead><tr>';
    h+='<th>Run ID</th><th>Project</th><th>Status</th><th>Deploy URL</th><th>Created</th>';
    h+='</tr></thead><tbody>';
    runs.forEach(function(r){
      var sc=r.status;
      var col=sc==='succeeded'?'#86efac':sc==='failed'?'#fca5a5':sc==='running'?'#fbbf24':'#aaa';
      h+='<tr>';
      h+='<td style="font-size:.75rem;color:#888">'+esc((r.run_id||'').substring(0,16))+'…</td>';
      h+='<td>'+esc(r.project_id||'–')+'</td>';
      h+='<td style="color:'+col+'">'+esc(sc||'–')+'</td>';
      h+='<td style="font-size:.78rem">'+(r.deploy_url?'<a href="'+esc(r.deploy_url)+'" target="_blank" style="color:#5b6ef7">'+esc(r.deploy_url.substring(0,40))+'</a>':'–')+'</td>';
      h+='<td style="color:#666;font-size:.78rem">'+esc((r.created_at||'').substring(0,16))+'</td>';
      h+='</tr>'
    });
    h+='</tbody></table></div>';
    table.innerHTML=h;table.style.display='block'
  }catch(e){
    loading.style.display='none';
    toast('Failed to load runs: '+e.message,'err')
  }
}

async function triggerBuild(){
  var id=document.getElementById('fb-project-id').value.trim();
  var tmpl=document.getElementById('fb-template').value;
  var dryRun=document.getElementById('fb-dry-run').checked;
  if(!id){toast('Project ID required','err');return}
  try{
    var body={build_brief:{
      project_id:id,idea_id:'idea-'+id,
      hypothesis:'Manual build trigger',
      target_user:'operator',problem:'Manual trigger',solution:'Manual trigger',
      mvp_scope:['Core build'],acceptance_criteria:['Deployment passes'],
      landing_page_requirements:['Template: '+tmpl],
      cta:'Get started',pricing_hint:'TBD',
      command_bundle:{source:'manual',template:tmpl},
      feature_flags:{dry_run:dryRun,live_factory:!dryRun}
    },dry_run:dryRun};
    var r=await apiFetch('/factory/runs',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    toast('Build triggered: '+r.run_id,'ok');loadFactoryRuns()
  }catch(e){toast('Build failed: '+e.message,'err')}
}

async function verifyDeployment(){
  var id=document.getElementById('vd-project-id').value.trim();
  var url=document.getElementById('vd-url').value.trim();
  if(!id){toast('Project ID required','err');return}
  var el=document.getElementById('vd-result');
  el.innerHTML='<span class="spinner"></span> Verifying…';
  try{
    var r=await apiFetch('/factory/verify-deployment',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({project_id:id,deploy_url:url})});
    var col=r.status==='healthy'?'#86efac':r.status==='degraded'?'#fbbf24':'#fca5a5';
    el.innerHTML='Status: <strong style="color:'+col+'">'+esc(r.status)+'</strong>'
      +(r.issues&&r.issues.length?'<br><span style="color:#fca5a5;font-size:.8rem">'+esc(r.issues.join(', '))+'</span>':'')
  }catch(e){el.innerHTML='<span style="color:#fca5a5">'+esc(e.message)+'</span>'}
}

/* ======================================================= DISTRIBUTION */
async function generateShareMessages(){
  var btn=document.getElementById('distBtn');
  var errBox=document.getElementById('distError');
  errBox.style.display='none';
  var title=document.getElementById('dist-title').value.trim();
  var url=document.getElementById('dist-url').value.trim();
  var desc=document.getElementById('dist-desc').value.trim();
  if(!title||!desc){errBox.textContent='Title and description are required.';errBox.style.display='block';return}
  btn.disabled=true;showSpinner('distLoading');
  document.getElementById('distResult').style.display='none';

  var body={
    title:title,url:url,description:desc,
    target_user:document.getElementById('dist-target').value.trim(),
    cta:document.getElementById('dist-cta').value.trim()
  };
  try{
    var d=await apiFetch('/api/distribution/share-messages',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    renderShareMessages(d);
    toast('Share messages generated','ok')
  }catch(e){errBox.textContent='Error: '+e.message;errBox.style.display='block'}
  finally{btn.disabled=false;hideSpinner('distLoading')}
}

function renderShareMessages(d){
  var messages=d.messages||[];
  if(!messages.length){document.getElementById('distResult').innerHTML='<div class="card">No messages generated.</div>';
    document.getElementById('distResult').style.display='block';return}
  var h='<div class="card">';
  messages.forEach(function(m){
    var txt=m.content||m.message||'';
    h+='<div class="msg-box">';
    h+='<div class="plat">'+esc(m.platform||m.channel||'')
      +'<button class="btn btn-outline btn-sm copy-btn" onclick="copyText(this,\''+esc(txt).replace(/'/g,"\\'").replace(/\\n/g,'\\n')+'\')">Copy</button></div>';
    h+='<pre>'+esc(txt)+'</pre>';
    h+='</div>'
  });
  h+='</div>';
  var el=document.getElementById('distResult');
  el.innerHTML=h;el.style.display='block'
}

function copyText(btn,text){
  navigator.clipboard.writeText(text).then(function(){
    btn.textContent='Copied!';setTimeout(function(){btn.textContent='Copy'},1500)
  }).catch(function(){toast('Copy failed — use Ctrl+C','err')})
}

/* ======================================================= REVENUE */
async function getRevenueReport(){
  var id=document.getElementById('rev-project-id').value.trim();
  if(!id){toast('Project ID required','err');return}
  showSpinner('revReportLoading');document.getElementById('revReport').style.display='none';
  try{
    var d=await apiFetch('/revenue/projects/'+id+'/learning-report');
    var h='<div class="card"><div class="section-title">Learning Report — '+esc(id)+'</div>';
    if(d.insights&&d.insights.length){
      h+='<div class="section"><p class="sub-title">Insights</p>';
      d.insights.forEach(function(ins){h+='<p class="reason-ok">• '+esc(ins)+'</p>'});
      h+='</div>'
    }
    if(d.recommendations&&d.recommendations.length){
      h+='<div class="section"><p class="sub-title">Recommendations</p>';
      d.recommendations.forEach(function(r){h+='<p style="font-size:.83rem;color:#e0e0e0;margin:.15rem 0">• '+esc(r)+'</p>'});
      h+='</div>'
    }
    if(d.revenue_estimate!=null){
      h+='<div class="detail-row" style="margin-top:.75rem"><span class="detail-label">Revenue Estimate</span><span class="detail-value" style="color:#86efac">'+esc(String(d.revenue_estimate))+'</span></div>'
    }
    h+='</div>';
    var el=document.getElementById('revReport');el.innerHTML=h;el.style.display='block'
  }catch(e){toast('Report failed: '+e.message,'err')}
  finally{hideSpinner('revReportLoading')}
}

async function generateBusinessOutput(){
  var id=document.getElementById('biz-project-id').value.trim();
  var pricing=document.getElementById('biz-pricing').value;
  if(!id){toast('Project ID required','err');return}
  showSpinner('bizOutputLoading');document.getElementById('bizOutput').style.display='none';
  try{
    var d=await apiFetch('/revenue/projects/'+id+'/business-output',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({pricing_strategy:pricing})});
    var h='<div class="card"><div class="section-title">Business Output — '+esc(id)+'</div>';
    if(d.offer){h+='<div class="detail-row"><span class="detail-label">Offer</span><span class="detail-value">'+esc(d.offer)+'</span></div>'}
    if(d.pricing_model){h+='<div class="detail-row"><span class="detail-label">Pricing Model</span><span class="detail-value">'+esc(d.pricing_model)+'</span></div>'}
    if(d.price_range){h+='<div class="detail-row"><span class="detail-label">Price Range</span><span class="detail-value" style="color:#86efac">'+esc(d.price_range)+'</span></div>'}
    if(d.gtm_strategy){h+='<div class="section"><p class="sub-title">GTM Strategy</p><p style="font-size:.83rem;color:#ccc">'+esc(d.gtm_strategy)+'</p></div>'}
    h+='</div>';
    var el=document.getElementById('bizOutput');el.innerHTML=h;el.style.display='block'
  }catch(e){toast('Business output failed: '+e.message,'err')}
  finally{hideSpinner('bizOutputLoading')}
}

/* ======================================================= INIT */
refreshDashboard();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def root_ui() -> HTMLResponse:
    """Serve the root command center dashboard UI."""
    html = _ROOT_HTML.replace("{version}", _VERSION)
    return HTMLResponse(content=html)
