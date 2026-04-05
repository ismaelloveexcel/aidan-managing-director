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

_VERSION = "0.2.0"


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
background:#0a0a0a;color:#e0e0e0;min-height:100vh;display:flex;flex-direction:column;
align-items:center;padding:2rem 1rem}
h1{font-size:1.8rem;margin-bottom:.3rem;color:#fff}
.subtitle{color:#888;margin-bottom:2rem;font-size:.95rem}
.container{width:100%;max-width:700px}
.card{background:#1a1a2e;border:1px solid #333;border-radius:12px;padding:1.5rem;margin-bottom:1.5rem}
label{display:block;font-size:.85rem;color:#aaa;margin-bottom:.3rem;margin-top:.8rem}
label:first-child{margin-top:0}
textarea,input,select{width:100%;padding:.6rem .8rem;border-radius:8px;border:1px solid #444;
background:#111;color:#e0e0e0;font-size:.9rem;font-family:inherit}
textarea{resize:vertical;min-height:80px}
textarea:focus,input:focus,select:focus{outline:none;border-color:#5b6ef7}
.row{display:grid;grid-template-columns:1fr 1fr;gap:.8rem}
button{width:100%;padding:.8rem;border:none;border-radius:8px;font-size:1rem;
font-weight:600;cursor:pointer;margin-top:1.2rem;transition:all .2s}
.btn-primary{background:#5b6ef7;color:#fff}
.btn-primary:hover{background:#4a5ce6}
.btn-primary:disabled{background:#333;color:#666;cursor:not-allowed}
#result{display:none}
.decision-badge{display:inline-block;padding:.3rem .8rem;border-radius:6px;
font-weight:700;font-size:.9rem;margin:.5rem 0}
.decision-APPROVED{background:#16a34a;color:#fff}
.decision-HOLD{background:#d97706;color:#fff}
.decision-REJECTED{background:#dc2626;color:#fff}
.score-bar{height:8px;border-radius:4px;background:#333;margin:.3rem 0;overflow:hidden}
.score-fill{height:100%;border-radius:4px;transition:width .5s}
.score-high{background:#16a34a}
.score-med{background:#d97706}
.score-low{background:#dc2626}
.section{margin-top:1rem;padding-top:1rem;border-top:1px solid #333}
.section h3{font-size:.95rem;color:#aaa;margin-bottom:.5rem}
.detail-row{display:flex;justify-content:space-between;padding:.25rem 0;font-size:.85rem}
.detail-label{color:#888}
.detail-value{color:#e0e0e0;text-align:right;max-width:60%}
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
footer{margin-top:2rem;color:#555;font-size:.8rem;text-align:center}
</style>
</head>
<body>
<header id="siteHeader" style="width:100%;padding:.75rem 1rem;background:linear-gradient(135deg,#2a0a0a,#1a1a2e);margin-bottom:1rem;border-bottom:1px solid #333;display:flex;align-items:center;justify-content:center;gap:.5rem">
<span id="healthDot" style="width:10px;height:10px;border-radius:50%;background:#dc2626;display:inline-block;flex-shrink:0"></span>
<span style="color:#e0e0e0;font-size:.85rem" id="healthSummary">Loading portfolio health...</span>
</header>
<h1>&#x1F9E0; AI-DAN Managing Director</h1>
<p class="subtitle">Idea → Validate → Score → Decide → Offer → Distribute</p>

<div class="container">
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

<button class="btn-primary" id="analyzeBtn" onclick="analyze()">&#x1F50D; Analyze Idea</button>
</div>

<div class="loading" id="loading">
<div class="spinner"></div>
<p style="margin-top:.8rem">Running full pipeline analysis...</p>
</div>

<div class="error-box" id="errorBox"></div>

<div id="result" class="card"></div>
</div>

<footer>AI-DAN Managing Director v{version} &mdash; Monetization-first decision engine</footer>

<script>
async function loadHealth(){
  try{
    const r=await fetch("/api/dashboard/health");
    if(!r.ok)return;
    const h=await r.json();
    const header=document.getElementById("siteHeader");
    const dot=document.getElementById("healthDot");
    const txt=document.getElementById("healthSummary");
    const gradients={
      GREEN:"linear-gradient(135deg,#0a2a0a,#1a1a2e)",
      AMBER:"linear-gradient(135deg,#2a2a0a,#1a1a2e)",
      RED:"linear-gradient(135deg,#2a0a0a,#1a1a2e)"
    };
    const dotColors={GREEN:"#16a34a",AMBER:"#d97706",RED:"#dc2626"};
    const status=h.health_status||"RED";
    if(header)header.style.background=gradients[status]||gradients.RED;
    if(dot)dot.style.background=dotColors[status]||dotColors.RED;
    if(txt)txt.textContent=h.summary||status;
  }catch(e){/* best-effort */}
}
loadHealth();

async function analyze(){
  const btn=document.getElementById("analyzeBtn");
  const loading=document.getElementById("loading");
  const result=document.getElementById("result");
  const errorBox=document.getElementById("errorBox");
  const idea=document.getElementById("idea").value.trim();

  if(!idea){errorBox.textContent="Please enter an idea.";errorBox.style.display="block";return}

  btn.disabled=true;loading.style.display="block";result.style.display="none";
  errorBox.style.display="none";

  const body={
    idea:idea,
    problem:document.getElementById("problem").value.trim(),
    target_user:document.getElementById("target_user").value.trim(),
    monetization_model:document.getElementById("monetization_model").value,
    competition_level:document.getElementById("competition_level").value,
    difficulty:document.getElementById("difficulty").value,
    time_to_revenue:document.getElementById("time_to_revenue").value,
    differentiation:document.getElementById("differentiation").value.trim()
  };

  try{
    const resp=await fetch("/api/analyze/",{method:"POST",
      headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    if(!resp.ok){const e=await resp.json();throw new Error(e.detail||resp.statusText)}
    const d=await resp.json();
    renderResult(d);
  }catch(err){
    errorBox.textContent="Error: "+err.message;errorBox.style.display="block";
  }finally{btn.disabled=false;loading.style.display="none"}
}

function renderResult(d){
  const r=document.getElementById("result");
  const sc=d.total_score||0;
  const pct=(sc/10*100).toFixed(0);
  const cls=sc>=8?"high":sc>=6?"med":"low";
  const dec=d.final_decision||"UNKNOWN";

  let h='<div style="display:flex;justify-content:space-between;align-items:center">';
  h+='<div><span class="decision-badge decision-'+dec+'">'+dec+'</span></div>';
  h+='<div style="text-align:right;font-size:1.5rem;font-weight:700">'+sc.toFixed(1);
  h+='<span style="font-size:.9rem;color:#888">/10</span></div></div>';

  h+='<div class="score-bar"><div class="score-fill score-'+cls+'" style="width:'+pct+'%"></div></div>';
  h+='<p style="font-size:.85rem;color:#aaa;margin-top:.3rem">'+
    (d.score_decision_reason||d.next_step||"")+'</p>';

  /* Validation */
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

  /* Score breakdown */
  if(d.score_dimensions&&d.score_dimensions.length){
    h+='<div class="section"><h3>&#x1F4CA; Score Breakdown</h3>';
    d.score_dimensions.forEach(function(dim){
      var dp=(dim.score/2*100).toFixed(0);
      var dc=dim.score>=1.5?"high":dim.score>=1?"med":"low";
      h+='<div class="detail-row"><span class="detail-label">'+escapeHtml(dim.name)+
        '</span><span class="detail-value">'+dim.score.toFixed(1)+'/2</span></div>';
      h+='<div class="score-bar"><div class="score-fill score-'+dc+'" style="width:'+dp+'%"></div></div>';
      h+='<p style="font-size:.8rem;color:#777;margin-bottom:.3rem">'+escapeHtml(dim.reason)+'</p>';
    });
    h+='</div>';
  }

  /* Offer */
  var o=d.offer||{};
  if(o.decision==="generated"){
    h+='<div class="section"><h3>&#x1F4B0; Offer</h3>';
    h+=detailRow("Pricing",o.pricing);
    h+=detailRow("Model",o.pricing_model);
    h+=detailRow("Delivery",o.delivery_method);
    h+=detailRow("Value",o.value_proposition);
    h+=detailRow("CTA",o.cta);
    h+='</div>';
  }

  /* Distribution */
  var di=d.distribution||{};
  if(di.decision==="generated"){
    h+='<div class="section"><h3>&#x1F680; Distribution</h3>';
    h+=detailRow("Channel",di.primary_channel);
    h+=detailRow("Acquisition",di.acquisition_method);
    h+=detailRow("First 10 Users",di.first_10_users_plan);
    h+=detailRow("Messaging",di.messaging);
    if(di.execution_steps&&di.execution_steps.length){
      h+='<p style="font-size:.85rem;color:#aaa;margin-top:.4rem">Steps:</p>';
      di.execution_steps.forEach(function(s,i){
        h+='<p style="font-size:.8rem;color:#ccc;margin-left:.5rem">'+(i+1)+'. '+escapeHtml(s)+'</p>'
      });
    }
    h+='</div>';
  }

  /* Next step */
  h+='<div class="section"><h3>&#x27A1;&#xFE0F; Next Step</h3>';
  h+='<p style="font-size:.9rem">'+escapeHtml(d.next_step||"Awaiting analysis.")+'</p>';
  h+='<p style="font-size:.8rem;color:#666;margin-top:.3rem">Stage: '+escapeHtml(d.pipeline_stage||"unknown")+'</p>';
  h+='</div>';

  r.innerHTML=h;r.style.display="block";
}

function detailRow(l,v){if(!v)return'';
  return'<div class="detail-row"><span class="detail-label">'+escapeHtml(l)+
    '</span><span class="detail-value">'+escapeHtml(v)+'</span></div>'}

function escapeHtml(s){if(!s)return'';var d=document.createElement("div");
  d.appendChild(document.createTextNode(String(s)));return d.innerHTML}
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def root_ui() -> HTMLResponse:
    """Serve the root idea-analysis UI."""
    html = _ROOT_HTML.replace("{version}", _VERSION)
    return HTMLResponse(content=html)
