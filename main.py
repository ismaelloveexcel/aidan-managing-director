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
<title>AI-DAN Command Center</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
background:#0a0a0a;color:#e0e0e0;min-height:100vh;display:flex;flex-direction:column}
header{background:#111;border-bottom:1px solid #222;padding:.8rem 1.5rem;
display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}
header h1{font-size:1.1rem;color:#fff;font-weight:700}
header span{color:#666;font-size:.8rem}
.nav{display:flex;gap:.2rem;background:#111;padding:.5rem 1.5rem;border-bottom:1px solid #1e1e1e;
overflow-x:auto;flex-shrink:0}
.nav button{background:none;border:none;color:#888;padding:.5rem .9rem;border-radius:6px;
cursor:pointer;font-size:.85rem;font-weight:500;white-space:nowrap;transition:all .15s}
.nav button:hover{color:#e0e0e0;background:#1e1e1e}
.nav button.active{color:#fff;background:#1a1a2e;border-bottom:2px solid #5b6ef7}
.tab{display:none;padding:1.5rem;flex:1}
.tab.active{display:block}
.card{background:#111;border:1px solid #222;border-radius:10px;padding:1.2rem;margin-bottom:1.2rem}
.card-title{font-size:.95rem;font-weight:600;color:#fff;margin-bottom:1rem;
display:flex;align-items:center;gap:.4rem}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:.8rem;margin-bottom:1.2rem}
.stat-box{background:#111;border:1px solid #222;border-radius:8px;padding:1rem;text-align:center}
.stat-num{font-size:1.8rem;font-weight:700;color:#5b6ef7}
.stat-label{font-size:.75rem;color:#888;margin-top:.2rem}
.health-dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:.4rem}
.health-green{background:#16a34a}
.health-yellow{background:#d97706}
.health-red{background:#dc2626}
label{display:block;font-size:.82rem;color:#aaa;margin-bottom:.3rem;margin-top:.8rem}
label:first-child{margin-top:0}
textarea,input,select{width:100%;padding:.55rem .75rem;border-radius:7px;border:1px solid #333;
background:#0d0d0d;color:#e0e0e0;font-size:.88rem;font-family:inherit}
textarea{resize:vertical;min-height:80px}
textarea:focus,input:focus,select:focus{outline:none;border-color:#5b6ef7}
.row{display:grid;grid-template-columns:1fr 1fr;gap:.8rem}
.row3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:.8rem}
button.btn{width:100%;padding:.7rem;border:none;border-radius:7px;font-size:.9rem;
font-weight:600;cursor:pointer;transition:all .2s}
button.btn-sm{width:auto;padding:.35rem .7rem;font-size:.78rem;font-weight:500;
border:none;border-radius:5px;cursor:pointer;transition:all .15s}
.btn-primary{background:#5b6ef7;color:#fff}
.btn-primary:hover{background:#4a5ce6}
.btn-primary:disabled{background:#222;color:#555;cursor:not-allowed}
.btn-success{background:#16a34a;color:#fff}
.btn-success:hover{background:#15803d}
.btn-danger{background:#dc2626;color:#fff}
.btn-danger:hover{background:#b91c1c}
.btn-secondary{background:#1e1e1e;color:#ccc;border:1px solid #333}
.btn-secondary:hover{background:#2a2a2a}
.btn-warning{background:#d97706;color:#fff}
.btn-warning:hover{background:#b45309}
table{width:100%;border-collapse:collapse;font-size:.83rem}
th{text-align:left;padding:.5rem .7rem;border-bottom:1px solid #222;color:#888;font-weight:500;font-size:.78rem}
td{padding:.5rem .7rem;border-bottom:1px solid #1a1a1a;vertical-align:middle}
tr:hover td{background:#131313}
.badge{display:inline-block;padding:.15rem .45rem;border-radius:4px;font-size:.72rem;font-weight:600}
.badge-approved{background:#14532d;color:#4ade80}
.badge-building{background:#1e3a5f;color:#60a5fa}
.badge-launched{background:#4a1d96;color:#c4b5fd}
.badge-idea{background:#292524;color:#d6d3d1}
.badge-hold{background:#451a03;color:#fbbf24}
.badge-rejected{background:#450a0a;color:#fca5a5}
.badge-succeeded{background:#14532d;color:#4ade80}
.badge-failed{background:#450a0a;color:#fca5a5}
.badge-pending{background:#292524;color:#d6d3d1}
.badge-running{background:#1e3a5f;color:#60a5fa}
.decision-badge{display:inline-block;padding:.3rem .8rem;border-radius:6px;
font-weight:700;font-size:.9rem;margin:.5rem 0}
.decision-APPROVED{background:#16a34a;color:#fff}
.decision-HOLD{background:#d97706;color:#fff}
.decision-REJECTED{background:#dc2626;color:#fff}
.score-bar{height:7px;border-radius:4px;background:#1e1e1e;margin:.3rem 0;overflow:hidden}
.score-fill{height:100%;border-radius:4px;transition:width .5s}
.score-high{background:#16a34a}
.score-med{background:#d97706}
.score-low{background:#dc2626}
.section{margin-top:1rem;padding-top:1rem;border-top:1px solid #222}
.section h3{font-size:.9rem;color:#aaa;margin-bottom:.5rem}
.detail-row{display:flex;justify-content:space-between;padding:.22rem 0;font-size:.83rem}
.detail-label{color:#777}
.detail-value{color:#e0e0e0;text-align:right;max-width:60%}
.error-box{background:#2d1111;border:1px solid #dc2626;border-radius:8px;padding:.9rem;
color:#fca5a5;margin-top:.8rem;display:none;font-size:.85rem}
.loading{display:none;text-align:center;padding:1.5rem;color:#888}
.spinner{display:inline-block;width:22px;height:22px;border:3px solid #222;
border-top-color:#5b6ef7;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.blocking{color:#fca5a5;font-size:.83rem;margin:.2rem 0}
.reason{color:#86efac;font-size:.83rem;margin:.2rem 0}
.share-block{background:#0d0d0d;border:1px solid #2a2a2a;border-radius:8px;
padding:.8rem 1rem;margin:.6rem 0}
.share-platform{font-size:.78rem;font-weight:600;color:#888;margin-bottom:.4rem}
.share-text{font-size:.82rem;color:#ccc;white-space:pre-wrap;word-break:break-word;
margin-bottom:.5rem}
.actions-row{display:flex;gap:.4rem;flex-wrap:wrap;align-items:center}
.empty-state{text-align:center;padding:2rem;color:#555;font-size:.88rem}
/* Toast */
#toast-container{position:fixed;top:1rem;right:1rem;z-index:9999;
display:flex;flex-direction:column;gap:.5rem}
.toast{padding:.65rem 1rem;border-radius:8px;font-size:.83rem;font-weight:500;
box-shadow:0 4px 12px rgba(0,0,0,.5);animation:fadeIn .25s ease}
.toast-success{background:#14532d;color:#4ade80;border:1px solid #166534}
.toast-error{background:#450a0a;color:#fca5a5;border:1px solid #7f1d1d}
.toast-info{background:#1e3a5f;color:#93c5fd;border:1px solid #1d4ed8}
@keyframes fadeIn{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}
footer{padding:.8rem 1.5rem;border-top:1px solid #1a1a1a;color:#444;font-size:.78rem;text-align:center}
@media(max-width:600px){
  .row,.row3{grid-template-columns:1fr}
  .stats-grid{grid-template-columns:1fr 1fr}
  .tab{padding:1rem}
}
</style>
</head>
<body>
<header>
  <h1>&#x1F9E0; AI-DAN Command Center</h1>
  <span id="headerStatus">&#x1F7E2; System Ready</span>
</header>

<nav class="nav" role="tablist">
  <button class="active" onclick="switchTab('dashboard',this)" role="tab">&#x1F4CA; Dashboard</button>
  <button onclick="switchTab('analyze',this)" role="tab">&#x1F4A1; Analyze Idea</button>
  <button onclick="switchTab('portfolio',this)" role="tab">&#x1F4E6; Portfolio</button>
  <button onclick="switchTab('factory',this)" role="tab">&#x1F3ED; Factory</button>
  <button onclick="switchTab('distribution',this)" role="tab">&#x1F4E3; Distribution</button>
  <button onclick="switchTab('revenue',this)" role="tab">&#x1F4B0; Revenue</button>
</nav>

<div id="toast-container"></div>

<!-- ====== TAB 1: DASHBOARD ====== -->
<div id="tab-dashboard" class="tab active">
  <div class="stats-grid" id="dashStats">
    <div class="stat-box"><div class="stat-num" id="st-total">—</div><div class="stat-label">Total Projects</div></div>
    <div class="stat-box"><div class="stat-num" id="st-approved" style="color:#4ade80">—</div><div class="stat-label">Approved</div></div>
    <div class="stat-box"><div class="stat-num" id="st-building" style="color:#60a5fa">—</div><div class="stat-label">Building</div></div>
    <div class="stat-box"><div class="stat-num" id="st-launched" style="color:#c4b5fd">—</div><div class="stat-label">Launched</div></div>
  </div>
  <div class="card">
    <div class="card-title">&#x1F4CC; System Health <span id="healthIndicator"></span></div>
    <div id="dashProjects"><div class="loading" style="display:block"><div class="spinner"></div></div></div>
    <div style="margin-top:1rem;display:flex;gap:.6rem;flex-wrap:wrap">
      <button class="btn btn-primary" style="width:auto;padding:.5rem 1rem" onclick="loadDashboard()">&#x1F504; Refresh</button>
      <button class="btn btn-secondary" style="width:auto;padding:.5rem 1rem" onclick="switchTab('analyze',document.querySelectorAll('.nav button')[1])">&#x2795; New Idea</button>
      <button class="btn btn-secondary" style="width:auto;padding:.5rem 1rem" onclick="switchTab('portfolio',document.querySelectorAll('.nav button')[2])">&#x1F4CB; Portfolio</button>
    </div>
  </div>
</div>

<!-- ====== TAB 2: ANALYZE IDEA ====== -->
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

<button class="btn btn-primary" id="analyzeBtn" onclick="analyze()">&#x1F50D; Analyze Idea</button>
</div>

<div class="loading" id="loading">
<div class="spinner"></div>
<p style="margin-top:.8rem">Running full pipeline analysis...</p>
</div>

<div class="error-box" id="errorBox"></div>

<div id="result" class="card" style="display:none"></div>
</div>

<!-- ====== TAB 3: PORTFOLIO ====== -->
<div id="tab-portfolio" class="tab">
  <div class="card">
    <div class="card-title" style="justify-content:space-between">
      <span>&#x1F4CB; Projects</span>
      <button class="btn btn-sm btn-primary" onclick="loadPortfolio()">&#x1F504; Refresh</button>
    </div>
    <div id="portfolioTable"><div class="loading" style="display:block"><div class="spinner"></div></div></div>
  </div>
  <div class="card">
    <div class="card-title">&#x2795; Add Project</div>
    <label for="pName">Name *</label>
    <input id="pName" placeholder="Project name"/>
    <label for="pDesc">Description *</label>
    <textarea id="pDesc" placeholder="What does this project do?" style="min-height:60px"></textarea>
    <button class="btn btn-primary" style="margin-top:.8rem" onclick="createProject()">Create Project</button>
  </div>
</div>

<!-- ====== TAB 4: FACTORY ====== -->
<div id="tab-factory" class="tab">
  <div class="card">
    <div class="card-title" style="justify-content:space-between">
      <span>&#x1F6E0; Build Runs</span>
      <button class="btn btn-sm btn-primary" onclick="loadRuns()">&#x1F504; Refresh</button>
    </div>
    <div id="runsTable"><div class="loading" style="display:block"><div class="spinner"></div></div></div>
  </div>
  <div class="card">
    <div class="card-title">&#x1F680; Verify Deployment</div>
    <label for="vProjectId">Project ID *</label>
    <input id="vProjectId" placeholder="e.g. prj-abc123"/>
    <label for="vDeployUrl">Deploy URL</label>
    <input id="vDeployUrl" placeholder="https://my-project.vercel.app"/>
    <label for="vRepoUrl">Repo URL</label>
    <input id="vRepoUrl" placeholder="https://github.com/org/repo"/>
    <button class="btn btn-primary" style="margin-top:.8rem" onclick="verifyDeployment()">&#x1F50E; Verify Deployment</button>
    <div id="verifyResult" style="margin-top:.8rem"></div>
  </div>
</div>

<!-- ====== TAB 5: DISTRIBUTION ====== -->
<div id="tab-distribution" class="tab">
  <div class="card">
    <div class="card-title">&#x1F4E3; Generate Share Messages</div>
    <label for="shareTitle">Product Title *</label>
    <input id="shareTitle" placeholder="My Awesome SaaS"/>
    <label for="shareUrl">Deploy URL *</label>
    <input id="shareUrl" placeholder="https://myproduct.vercel.app"/>
    <label for="shareDesc">Description *</label>
    <textarea id="shareDesc" placeholder="A one-sentence description of what this product does." style="min-height:60px"></textarea>
    <div class="row">
    <div>
    <label for="shareTarget">Target User *</label>
    <input id="shareTarget" placeholder="e.g. freelance developers"/>
    </div>
    <div>
    <label for="shareCta">Call to Action</label>
    <input id="shareCta" placeholder="Try it free" value="Try it free"/>
    </div>
    </div>
    <button class="btn btn-primary" style="margin-top:.8rem" id="shareBtn" onclick="generateShare()">&#x2728; Generate Share Messages</button>
  </div>
  <div class="loading" id="shareLoading">
    <div class="spinner"></div>
    <p style="margin-top:.8rem">Generating messages...</p>
  </div>
  <div id="shareResults"></div>
</div>

<!-- ====== TAB 6: REVENUE ====== -->
<div id="tab-revenue" class="tab">
  <div class="card">
    <div class="card-title">&#x1F4B0; Learning Report</div>
    <label for="revProjectId">Project ID *</label>
    <div style="display:flex;gap:.6rem;margin-top:.3rem">
      <input id="revProjectId" placeholder="e.g. prj-abc123" style="flex:1"/>
      <button class="btn btn-sm btn-primary" onclick="loadRevenueReport()">View Report</button>
    </div>
  </div>
  <div class="loading" id="revLoading">
    <div class="spinner"></div>
    <p style="margin-top:.8rem">Loading report...</p>
  </div>
  <div id="revResult"></div>
</div>

<footer>AI-DAN Command Center v{version} &mdash; Monetization-first decision engine</footer>

<script>
/* ── utilities ── */
function esc(s){if(s==null)return'';var d=document.createElement('div');
  d.appendChild(document.createTextNode(String(s)));return d.innerHTML}

function jsStr(s){if(s==null)return'';
  return String(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'").replace(/"/g,'\\"')
    .replace(/`/g,'\\`').replace(/</g,'\\x3c').replace(/>/g,'\\x3e')
    .replace(/&/g,'\\x26').replace(/\r/g,'\\r').replace(/\n/g,'\\n')}

function toast(msg,type){
  type=type||'info';
  var c=document.getElementById('toast-container');
  var t=document.createElement('div');
  t.className='toast toast-'+type;
  t.textContent=msg;
  c.appendChild(t);
  setTimeout(function(){t.style.opacity='0';t.style.transform='translateY(-8px)';
    t.style.transition='all .3s';setTimeout(function(){c.removeChild(t)},300)},3000);
}

function statusBadge(s){
  var m={approved:'badge-approved',building:'badge-building',launched:'badge-launched',
    idea:'badge-idea',hold:'badge-hold',rejected:'badge-rejected',
    succeeded:'badge-succeeded',failed:'badge-failed',pending:'badge-pending',running:'badge-running'};
  var cls=m[(s||'').toLowerCase()]||'badge-idea';
  return '<span class="badge '+cls+'">'+esc(s)+'</span>';
}

/* ── tab switching ── */
function switchTab(id,btn){
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active')});
  document.querySelectorAll('.nav button').forEach(function(b){b.classList.remove('active')});
  document.getElementById('tab-'+id).classList.add('active');
  if(btn)btn.classList.add('active');
  if(id==='dashboard')loadDashboard();
  if(id==='portfolio')loadPortfolio();
  if(id==='factory')loadRuns();
}

/* ── TAB 1: DASHBOARD ── */
async function loadDashboard(){
  document.getElementById('dashProjects').innerHTML=
    '<div class="loading" style="display:block"><div class="spinner"></div></div>';
  try{
    var resp=await fetch('/portfolio/projects');
    if(!resp.ok)throw new Error(resp.statusText);
    var projects=await resp.json();
    renderDashStats(projects);
    renderDashProjects(projects);
  }catch(e){
    document.getElementById('dashProjects').innerHTML=
      '<div class="empty-state">Could not load projects: '+esc(e.message)+'</div>';
    document.getElementById('healthIndicator').innerHTML=
      '<span class="health-dot health-red"></span><span style="font-size:.8rem;color:#888">Error</span>';
  }
}

function renderDashStats(projects){
  var total=projects.length;
  var approved=projects.filter(function(p){return(p.state||'').toLowerCase()==='approved'}).length;
  var building=projects.filter(function(p){return(p.state||'').toLowerCase()==='building'}).length;
  var launched=projects.filter(function(p){return(p.state||'').toLowerCase()==='launched'}).length;
  document.getElementById('st-total').textContent=total;
  document.getElementById('st-approved').textContent=approved;
  document.getElementById('st-building').textContent=building;
  document.getElementById('st-launched').textContent=launched;
  var health=total===0?'yellow':launched>0?'green':'yellow';
  document.getElementById('healthIndicator').innerHTML=
    '<span class="health-dot health-'+health+'"></span>';
  document.getElementById('headerStatus').textContent=
    health==='green'?'🟢 '+launched+' Live':'🟡 '+total+' Projects';
}

function renderDashProjects(projects){
  if(!projects.length){
    document.getElementById('dashProjects').innerHTML=
      '<div class="empty-state">No projects yet. Go to Analyze Idea to get started.</div>';
    return;
  }
  var recent=projects.slice(-5).reverse();
  var h='<table><thead><tr><th>Name</th><th>State</th><th>Created</th></tr></thead><tbody>';
  recent.forEach(function(p){
    h+='<tr><td>'+esc(p.name)+'</td><td>'+statusBadge(p.state)+'</td>';
    h+='<td style="color:#555;font-size:.78rem">'+(p.created_at||'').substring(0,10)+'</td></tr>';
  });
  h+='</tbody></table>';
  document.getElementById('dashProjects').innerHTML=h;
}

/* ── TAB 2: ANALYZE ── */
async function analyze(){
  var btn=document.getElementById('analyzeBtn');
  var loading=document.getElementById('loading');
  var result=document.getElementById('result');
  var errorBox=document.getElementById('errorBox');
  var idea=document.getElementById('idea').value.trim();
  if(!idea){errorBox.textContent='Please enter an idea.';errorBox.style.display='block';return}
  btn.disabled=true;loading.style.display='block';result.style.display='none';
  errorBox.style.display='none';
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
    if(!resp.ok){var e=await resp.json();throw new Error(e.detail||resp.statusText)}
    var d=await resp.json();
    renderResult(d);
    toast('Analysis complete: '+d.final_decision,
      d.final_decision==='APPROVED'?'success':d.final_decision==='HOLD'?'info':'error');
  }catch(err){
    errorBox.textContent='Error: '+err.message;errorBox.style.display='block';
    toast('Analysis failed: '+err.message,'error');
  }finally{btn.disabled=false;loading.style.display='none'}
}

function renderResult(d){
  var r=document.getElementById('result');
  var sc=d.total_score||0;
  var pct=(sc/10*100).toFixed(0);
  var cls=sc>=8?'high':sc>=6?'med':'low';
  var dec=d.final_decision||'UNKNOWN';
  var h='<div style="display:flex;justify-content:space-between;align-items:center">';
  h+='<div><span class="decision-badge decision-'+dec+'">'+dec+'</span></div>';
  h+='<div style="text-align:right;font-size:1.5rem;font-weight:700">'+sc.toFixed(1);
  h+='<span style="font-size:.9rem;color:#888">/10</span></div></div>';
  h+='<div class="score-bar"><div class="score-fill score-'+cls+'" style="width:'+pct+'%"></div></div>';
  h+='<p style="font-size:.85rem;color:#aaa;margin-top:.3rem">'+(d.score_decision_reason||d.next_step||'')+'</p>';
  if(d.validation_blocking&&d.validation_blocking.length){
    h+='<div class="section"><h3>&#x1F6D1; Blocking Issues</h3>';
    d.validation_blocking.forEach(function(b){h+='<p class="blocking">• '+esc(b)+'</p>'});
    h+='</div>';
  }
  if(d.validation_reasons&&d.validation_reasons.length){
    h+='<div class="section"><h3>&#x2705; Validation</h3>';
    d.validation_reasons.forEach(function(v){h+='<p class="reason">• '+esc(v)+'</p>'});
    h+='</div>';
  }
  if(d.score_dimensions&&d.score_dimensions.length){
    h+='<div class="section"><h3>&#x1F4CA; Score Breakdown</h3>';
    d.score_dimensions.forEach(function(dim){
      var dp=(dim.score/2*100).toFixed(0);
      var dc=dim.score>=1.5?'high':dim.score>=1?'med':'low';
      h+='<div class="detail-row"><span class="detail-label">'+esc(dim.name)+
        '</span><span class="detail-value">'+dim.score.toFixed(1)+'/2</span></div>';
      h+='<div class="score-bar"><div class="score-fill score-'+dc+'" style="width:'+dp+'%"></div></div>';
      h+='<p style="font-size:.8rem;color:#777;margin-bottom:.3rem">'+esc(dim.reason)+'</p>';
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
    if(di.execution_steps&&di.execution_steps.length){
      h+='<p style="font-size:.85rem;color:#aaa;margin-top:.4rem">Steps:</p>';
      di.execution_steps.forEach(function(s,i){
        h+='<p style="font-size:.8rem;color:#ccc;margin-left:.5rem">'+(i+1)+'. '+esc(s)+'</p>'
      });
    }
    h+='</div>';
  }
  h+='<div class="section"><h3>&#x27A1;&#xFE0F; Next Step</h3>';
  h+='<p style="font-size:.9rem">'+esc(d.next_step||'Awaiting analysis.')+'</p>';
  h+='<p style="font-size:.8rem;color:#666;margin-top:.3rem">Stage: '+esc(d.pipeline_stage||'unknown')+'</p>';
  h+='</div>';
  r.innerHTML=h;r.style.display='block';
}

function detailRow(l,v){if(!v)return'';
  return'<div class="detail-row"><span class="detail-label">'+esc(l)+
    '</span><span class="detail-value">'+esc(v)+'</span></div>'}

/* ── TAB 3: PORTFOLIO ── */
async function loadPortfolio(){
  document.getElementById('portfolioTable').innerHTML=
    '<div class="loading" style="display:block"><div class="spinner"></div></div>';
  try{
    var resp=await fetch('/portfolio/projects');
    if(!resp.ok)throw new Error(resp.statusText);
    var projects=await resp.json();
    renderPortfolioTable(projects);
  }catch(e){
    document.getElementById('portfolioTable').innerHTML=
      '<div class="empty-state">Could not load: '+esc(e.message)+'</div>';
  }
}

function renderPortfolioTable(projects){
  if(!projects.length){
    document.getElementById('portfolioTable').innerHTML=
      '<div class="empty-state">No projects yet. Use Analyze Idea to create your first one.</div>';
    return;
  }
  var h='<table><thead><tr><th>Name</th><th>State</th><th>Created</th><th>Actions</th></tr></thead><tbody>';
  projects.forEach(function(p){
    h+='<tr><td><strong>'+esc(p.name)+'</strong><br><span style="color:#555;font-size:.75rem">'+esc(p.project_id)+'</span></td>';
    h+='<td>'+statusBadge(p.state)+'</td>';
    h+='<td style="color:#555;font-size:.78rem">'+(p.created_at||'').substring(0,10)+'</td>';
    h+='<td><div class="actions-row">';
    var s=(p.state||'').toLowerCase();
    if(s==='idea'||s==='hold'){
      h+='<button class="btn btn-sm btn-success" onclick="approveProject(\''+jsStr(p.project_id)+'\')">&#x2705; Approve</button>';
      h+='<button class="btn btn-sm btn-danger" onclick="rejectProject(\''+jsStr(p.project_id)+'\')">&#x274C; Reject</button>';
    }
    if(s==='approved'){
      h+='<button class="btn btn-sm btn-warning" onclick="buildProject(\''+jsStr(p.project_id)+'\',\''+jsStr(p.name)+'\')">&#x1F680; Build</button>';
    }
    h+='<button class="btn btn-sm btn-secondary" onclick="shareProject(\''+jsStr(p.project_id)+'\',\''+jsStr(p.name)+'\')">&#x1F4E3; Share</button>';
    h+='</div></td></tr>';
  });
  h+='</tbody></table>';
  document.getElementById('portfolioTable').innerHTML=h;
}

async function approveProject(id){
  try{
    var resp=await fetch('/portfolio/projects/'+encodeURIComponent(id)+'/transition',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({new_state:'approved',event_type:'manual_approve'})
    });
    if(!resp.ok)throw new Error((await resp.json()).detail||resp.statusText);
    toast('Project approved','success');loadPortfolio();loadDashboard();
  }catch(e){toast('Approve failed: '+e.message,'error')}
}

async function rejectProject(id){
  try{
    var resp=await fetch('/portfolio/projects/'+encodeURIComponent(id)+'/transition',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({new_state:'rejected',event_type:'manual_reject'})
    });
    if(!resp.ok)throw new Error((await resp.json()).detail||resp.statusText);
    toast('Project rejected','info');loadPortfolio();
  }catch(e){toast('Reject failed: '+e.message,'error')}
}

async function buildProject(id,name){
  var distBtn=document.querySelector('.nav button[onclick*="distribution"]');
  switchTab('distribution',distBtn||document.querySelectorAll('.nav button')[4]);
  document.getElementById('shareTitle').value=name;
  toast('Switch to Factory tab to trigger a build for '+name,'info');
}

function shareProject(id,name){
  var distBtn=document.querySelector('.nav button[onclick*="distribution"]');
  switchTab('distribution',distBtn||document.querySelectorAll('.nav button')[4]);
  document.getElementById('shareTitle').value=name;
}

async function createProject(){
  var name=document.getElementById('pName').value.trim();
  var desc=document.getElementById('pDesc').value.trim();
  if(!name||!desc){toast('Name and description are required','error');return}
  try{
    var resp=await fetch('/portfolio/projects',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name:name,description:desc})
    });
    if(!resp.ok)throw new Error((await resp.json()).detail||resp.statusText);
    toast('Project created','success');
    document.getElementById('pName').value='';document.getElementById('pDesc').value='';
    loadPortfolio();
  }catch(e){toast('Create failed: '+e.message,'error')}
}

/* ── TAB 4: FACTORY ── */
async function loadRuns(){
  document.getElementById('runsTable').innerHTML=
    '<div class="loading" style="display:block"><div class="spinner"></div></div>';
  try{
    var resp=await fetch('/factory/runs');
    if(!resp.ok)throw new Error(resp.statusText);
    var runs=await resp.json();
    renderRunsTable(runs);
  }catch(e){
    document.getElementById('runsTable').innerHTML=
      '<div class="empty-state">Could not load runs: '+esc(e.message)+'</div>';
  }
}

function renderRunsTable(runs){
  if(!runs.length){
    document.getElementById('runsTable').innerHTML=
      '<div class="empty-state">No factory runs yet.</div>';
    return;
  }
  var h='<table><thead><tr><th>Run ID</th><th>Project</th><th>Status</th><th>Dry Run</th><th>Created</th></tr></thead><tbody>';
  runs.slice().reverse().forEach(function(r){
    h+='<tr><td style="font-size:.75rem;font-family:monospace;color:#777">'+esc(r.run_id).substring(0,12)+'…</td>';
    h+='<td>'+esc(r.project_id)+'</td>';
    h+='<td>'+statusBadge(r.status)+'</td>';
    h+='<td style="font-size:.78rem;color:#777">'+(r.dry_run?'Yes':'No')+'</td>';
    h+='<td style="font-size:.78rem;color:#555">'+(r.created_at||'').substring(0,16)+'</td>';
    h+='</tr>';
  });
  h+='</tbody></table>';
  document.getElementById('runsTable').innerHTML=h;
}

async function verifyDeployment(){
  var pid=document.getElementById('vProjectId').value.trim();
  var url=document.getElementById('vDeployUrl').value.trim();
  var repo=document.getElementById('vRepoUrl').value.trim();
  if(!pid){toast('Project ID is required','error');return}
  var div=document.getElementById('verifyResult');
  div.innerHTML='<div class="loading" style="display:block"><div class="spinner"></div></div>';
  try{
    var resp=await fetch('/factory/verify-deployment',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({project_id:pid,deploy_url:url,repo_url:repo})
    });
    if(!resp.ok)throw new Error((await resp.json()).detail||resp.statusText);
    var d=await resp.json();
    var color=d.status==='healthy'?'#4ade80':d.status==='degraded'?'#fbbf24':'#fca5a5';
    var h='<div style="padding:.8rem;background:#0d0d0d;border:1px solid #2a2a2a;border-radius:8px">';
    h+='<div style="font-weight:600;color:'+color+'">'+esc(d.status.toUpperCase())+'</div>';
    if(d.issues&&d.issues.length){
      h+='<ul style="margin-top:.5rem;padding-left:1rem">';
      d.issues.forEach(function(i){h+='<li style="font-size:.82rem;color:#fca5a5">'+esc(i)+'</li>'});
      h+='</ul>';
    } else {
      h+='<p style="font-size:.82rem;color:#86efac;margin-top:.3rem">No issues detected.</p>';
    }
    h+='</div>';
    div.innerHTML=h;
    toast('Verification: '+d.status,d.status==='healthy'?'success':d.status==='degraded'?'info':'error');
  }catch(e){
    div.innerHTML='<div class="error-box" style="display:block">'+esc(e.message)+'</div>';
    toast('Verify failed: '+e.message,'error');
  }
}

/* ── TAB 5: DISTRIBUTION ── */
async function generateShare(){
  var btn=document.getElementById('shareBtn');
  var loading=document.getElementById('shareLoading');
  var results=document.getElementById('shareResults');
  var title=document.getElementById('shareTitle').value.trim();
  var url=document.getElementById('shareUrl').value.trim();
  var desc=document.getElementById('shareDesc').value.trim();
  var target=document.getElementById('shareTarget').value.trim();
  var cta=document.getElementById('shareCta').value.trim()||'Try it free';
  if(!title||!url||!desc||!target){
    toast('Title, URL, description and target user are required','error');return;
  }
  btn.disabled=true;loading.style.display='block';results.innerHTML='';
  try{
    var resp=await fetch('/api/distribution/share-messages',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({title:title,url:url,description:desc,target_user:target,cta:cta})
    });
    if(!resp.ok)throw new Error((await resp.json()).detail||resp.statusText);
    var d=await resp.json();
    renderShareResults(d);
    toast('Share messages generated','success');
  }catch(e){
    results.innerHTML='<div class="error-box" style="display:block">'+esc(e.message)+'</div>';
    toast('Generate failed: '+e.message,'error');
  }finally{btn.disabled=false;loading.style.display='none'}
}

function renderShareResults(d){
  var platforms=[
    ['twitter','&#x1D54F; Twitter/X',d.twitter],
    ['linkedin','&#x1F516; LinkedIn',d.linkedin],
    ['whatsapp','&#x1F4F1; WhatsApp',d.whatsapp],
    ['email','&#x1F4E7; Email Subject',d.email_subject],
    ['sms','&#x1F4AC; SMS',d.sms],
    ['reddit','&#x1F4DD; Reddit',d.reddit],
    ['product_hunt','&#x1F431; Product Hunt',d.product_hunt]
  ];
  var h='';
  platforms.forEach(function(p){
    if(!p[2])return;
    h+='<div class="share-block">';
    h+='<div class="share-platform">'+p[1]+'</div>';
    h+='<div class="share-text" id="sb-'+p[0]+'">'+esc(p[2])+'</div>';
    h+='<button class="btn btn-sm btn-secondary" onclick="copyShare(\''+jsStr(p[0])+'\')">&#x1F4CB; Copy</button>';
    h+='</div>';
  });
  document.getElementById('shareResults').innerHTML=h||'<div class="empty-state">No messages generated.</div>';
}

function copyShare(id){
  var el=document.getElementById('sb-'+id);
  if(!el)return;
  navigator.clipboard.writeText(el.textContent).then(function(){
    toast('Copied to clipboard','success');
  }).catch(function(){toast('Copy failed – please select and copy manually','error')});
}

/* ── TAB 6: REVENUE ── */
async function loadRevenueReport(){
  var pid=document.getElementById('revProjectId').value.trim();
  if(!pid){toast('Enter a project ID','error');return}
  var loading=document.getElementById('revLoading');
  var result=document.getElementById('revResult');
  loading.style.display='block';result.innerHTML='';
  try{
    var resp=await fetch('/revenue/projects/'+encodeURIComponent(pid)+'/learning-report');
    if(!resp.ok)throw new Error((await resp.json()).detail||resp.statusText);
    var d=await resp.json();
    renderRevenueReport(d);
    toast('Report loaded','success');
  }catch(e){
    result.innerHTML='<div class="error-box" style="display:block">'+esc(e.message)+'</div>';
    toast('Load failed: '+e.message,'error');
  }finally{loading.style.display='none'}
}

function renderRevenueReport(d){
  var h='<div class="card">';
  h+='<div class="card-title">&#x1F4CA; Learning Report — '+esc(d.project_id)+'</div>';
  h+=detailRow('Total Outcomes',d.total_outcomes);
  h+=detailRow('Success Rate',d.success_rate!=null?(d.success_rate*100).toFixed(1)+'%':null);
  h+=detailRow('Recommendation',d.recommendation);
  if(d.insights&&d.insights.length){
    h+='<div class="section"><h3>Insights</h3>';
    d.insights.forEach(function(i){h+='<p class="reason">• '+esc(i)+'</p>'});
    h+='</div>';
  }
  if(d.risks&&d.risks.length){
    h+='<div class="section"><h3>Risks</h3>';
    d.risks.forEach(function(r){h+='<p class="blocking">• '+esc(r)+'</p>'});
    h+='</div>';
  }
  h+='</div>';
  document.getElementById('revResult').innerHTML=h;
}

/* ── init ── */
loadDashboard();
setInterval(loadDashboard,30000);
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def root_ui() -> HTMLResponse:
    """Serve the root idea-analysis UI."""
    html = _ROOT_HTML.replace("{version}", _VERSION)
    return HTMLResponse(content=html)
