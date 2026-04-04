"""
main.py – FastAPI application entry point for AI-DAN Managing Director.

Registers all route modules, serves the embedded UI at root,
and configures the application for deployment.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.routes import (
    analytics,
    analyze,
    approvals,
    chat,
    commands,
    control,
    factory,
    feedback,
    ideas,
    intelligence,
    memory,
    portfolio,
    projects,
)

_VERSION = "0.2.0"

app = FastAPI(
    title="AI-DAN Managing Director",
    description=(
        "Core managing director layer for strategy, idea generation, "
        "portfolio control, approvals, and command routing to the GitHub Factory."
    ),
    version=_VERSION,
)

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
app.include_router(control.router, prefix="/control", tags=["Control"])


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Return a simple health-check response."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Root UI – embedded single-page application
# ---------------------------------------------------------------------------

_UI_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>AI-DAN Managing Director</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
background:#0a0a0f;color:#e0e0e0;min-height:100vh;display:flex;flex-direction:column;align-items:center}
.container{max-width:860px;width:100%;padding:24px 20px}
header{text-align:center;padding:48px 0 24px}
header h1{font-size:2rem;font-weight:700;background:linear-gradient(135deg,#60a5fa,#a78bfa);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}
header p{color:#9ca3af;font-size:1rem}
.input-section{background:#111118;border:1px solid #1e1e2e;border-radius:12px;padding:24px;margin-bottom:24px}
textarea{width:100%;min-height:100px;background:#0a0a0f;border:1px solid #2a2a3e;border-radius:8px;
color:#e0e0e0;padding:14px;font-size:1rem;resize:vertical;font-family:inherit}
textarea:focus{outline:none;border-color:#60a5fa}
textarea::placeholder{color:#6b7280}
.btn{display:inline-flex;align-items:center;justify-content:center;width:100%;padding:14px 24px;
margin-top:14px;background:linear-gradient(135deg,#3b82f6,#7c3aed);color:#fff;border:none;
border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;transition:opacity .2s}
.btn:hover{opacity:.9}.btn:disabled{opacity:.5;cursor:not-allowed}
.loading{display:none;text-align:center;padding:40px 0;color:#9ca3af}
.loading.active{display:block}
.spinner{display:inline-block;width:32px;height:32px;border:3px solid #2a2a3e;
border-top-color:#60a5fa;border-radius:50%;animation:spin 1s linear infinite;margin-bottom:12px}
@keyframes spin{to{transform:rotate(360deg)}}
.result{display:none;margin-top:8px}
.result.active{display:block}
.card{background:#111118;border:1px solid #1e1e2e;border-radius:12px;padding:24px;margin-bottom:16px}
.card h2{font-size:1.25rem;font-weight:600;margin-bottom:16px;color:#f0f0f0}
.card h3{font-size:1rem;font-weight:600;margin:16px 0 8px;color:#d0d0d0}
.verdict{display:inline-block;padding:6px 16px;border-radius:20px;font-weight:700;font-size:.9rem;margin-bottom:12px}
.verdict-approve{background:#064e3b;color:#34d399}.verdict-hold{background:#78350f;color:#fbbf24}
.verdict-reject{background:#7f1d1d;color:#f87171}
.score-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:12px 0}
.score-item{background:#0a0a0f;border:1px solid #1e1e2e;border-radius:8px;padding:14px;text-align:center}
.score-item .label{font-size:.8rem;color:#9ca3af;margin-bottom:4px}
.score-item .value{font-size:1.5rem;font-weight:700;color:#60a5fa}
.field{margin-bottom:12px}.field .label{font-size:.8rem;color:#9ca3af;text-transform:uppercase;
letter-spacing:.5px;margin-bottom:4px}.field .value{font-size:.95rem;line-height:1.5}
.research-box{background:#0a0a0f;border:1px solid #1e1e2e;border-radius:8px;padding:16px;
font-size:.9rem;line-height:1.6;white-space:pre-wrap;max-height:300px;overflow-y:auto;color:#b0b0c0}
.error-box{display:none;background:#7f1d1d;border:1px solid #991b1b;border-radius:8px;
padding:16px;color:#fca5a5;margin-top:16px}
.error-box.active{display:block}
.badge{display:inline-block;padding:3px 10px;border-radius:12px;font-size:.75rem;font-weight:600;margin-left:8px}
.badge-ai{background:#1e3a5f;color:#60a5fa}.badge-stub{background:#2a2a3e;color:#9ca3af}
footer{text-align:center;padding:24px;color:#6b7280;font-size:.85rem}
</style>
</head>
<body>
<div class="container">
<header>
<h1>&#x1F9ED; AI-DAN Managing Director</h1>
<p>AI-powered business idea analysis &amp; monetization engine</p>
</header>

<div class="input-section">
<textarea id="idea-input" placeholder="Describe your business idea...&#10;&#10;Example: I want to build a SaaS tool that helps freelancers track their invoices and get paid faster"></textarea>
<button class="btn" id="submit-btn" onclick="analyzeIdea()">
&#x1F680; Analyze Idea
</button>
</div>

<div class="loading" id="loading">
<div class="spinner"></div>
<p>AI-DAN is researching &amp; analyzing your idea...</p>
</div>

<div class="error-box" id="error-box"></div>

<div class="result" id="result">
<div class="card" id="verdict-card">
<h2>&#x1F3AF; Verdict <span class="badge" id="ai-badge"></span></h2>
<div id="verdict-tag"></div>
<div class="field"><div class="label">Why Now</div><div class="value" id="why-now"></div></div>
<div class="field"><div class="label">Main Risk</div><div class="value" id="main-risk"></div></div>
<div class="field"><div class="label">Recommended Next Move</div><div class="value" id="next-move"></div></div>
</div>

<div class="card">
<h2>&#x1F4CA; Scores</h2>
<div class="score-grid" id="score-grid"></div>
</div>

<div class="card">
<h2>&#x1F4A1; Business Idea</h2>
<div class="field"><div class="label">Title</div><div class="value" id="title"></div></div>
<div class="field"><div class="label">Problem</div><div class="value" id="problem"></div></div>
<div class="field"><div class="label">Target User</div><div class="value" id="target-user"></div></div>
<div class="field"><div class="label">Solution</div><div class="value" id="solution"></div></div>
</div>

<div class="card">
<h2>&#x1F4B0; Monetization</h2>
<div class="field"><div class="label">Method</div><div class="value" id="monetization"></div></div>
<div class="field"><div class="label">Pricing</div><div class="value" id="pricing"></div></div>
<div class="field"><div class="label">Competitive Edge</div><div class="value" id="edge"></div></div>
</div>

<div class="card">
<h2>&#x1F4E3; Distribution</h2>
<div class="field"><div class="label">Distribution Plan</div><div class="value" id="distribution"></div></div>
<div class="field"><div class="label">First 10 Users</div><div class="value" id="first-users"></div></div>
</div>

<div class="card" id="research-card" style="display:none">
<h2>&#x1F50D; Market Research</h2>
<div class="research-box" id="research-content"></div>
</div>
</div>
</div>

<footer>AI-DAN Managing Director &middot; Strategic Decision Engine &middot; v{version}</footer>

<script>
async function analyzeIdea(){
  const input=document.getElementById('idea-input');
  const idea=input.value.trim();
  if(!idea){input.focus();return}

  const btn=document.getElementById('submit-btn');
  const loading=document.getElementById('loading');
  const result=document.getElementById('result');
  const errorBox=document.getElementById('error-box');

  btn.disabled=true;
  loading.classList.add('active');
  result.classList.remove('active');
  errorBox.classList.remove('active');

  try{
    const resp=await fetch('/api/analyze/',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({idea:idea})
    });
    if(!resp.ok){
      const errText=await resp.text();
      throw new Error('Server error '+resp.status+': '+errText);
    }
    const data=await resp.json();
    if(!data.success){throw new Error(data.error||'Analysis failed')}
    renderResult(data.analysis);
  }catch(err){
    errorBox.textContent='Error: '+err.message;
    errorBox.classList.add('active');
  }finally{
    btn.disabled=false;
    loading.classList.remove('active');
  }
}

function renderResult(a){
  const result=document.getElementById('result');

  // AI badge
  const badge=document.getElementById('ai-badge');
  badge.textContent=a.ai_powered?'AI-Powered':'Deterministic';
  badge.className='badge '+(a.ai_powered?'badge-ai':'badge-stub');

  // Verdict
  const vt=document.getElementById('verdict-tag');
  const v=(a.verdict||'HOLD').toUpperCase();
  const vc=v==='APPROVE'?'approve':(v==='REJECT'?'reject':'hold');
  vt.innerHTML='<span class="verdict verdict-'+vc+'">'+v+'</span>';

  setText('why-now',a.why_now);
  setText('main-risk',a.main_risk);
  setText('next-move',a.recommended_next_move);

  // Scores
  const sg=document.getElementById('score-grid');
  sg.innerHTML='';
  const scores=[
    ['Overall',a.overall_score],
    ['Feasibility',a.feasibility_score],
    ['Profitability',a.profitability_score],
    ['Speed',a.speed_score],
    ['Competition',a.competition_score]
  ];
  scores.forEach(function(s){
    const val=Number(s[1])||0;
    const d=document.createElement('div');
    d.className='score-item';
    d.innerHTML='<div class="label">'+s[0]+'</div><div class="value">'+val.toFixed(1)+'</div>';
    sg.appendChild(d);
  });

  // Idea
  setText('title',a.title);
  setText('problem',a.problem);
  setText('target-user',a.target_user);
  setText('solution',a.solution);

  // Monetization
  setText('monetization',a.monetization_method);
  setText('pricing',a.pricing_suggestion);
  setText('edge',a.competitive_edge);

  // Distribution
  setText('distribution',a.distribution_plan);
  setText('first-users',a.first_10_users);

  // Research
  const rc=document.getElementById('research-card');
  if(a.market_research){
    rc.style.display='block';
    document.getElementById('research-content').textContent=a.market_research;
  }else{rc.style.display='none'}

  result.classList.add('active');
  result.scrollIntoView({behavior:'smooth'});
}

function setText(id,val){document.getElementById(id).textContent=val||'N/A'}

document.getElementById('idea-input').addEventListener('keydown',function(e){
  if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){analyzeIdea()}
});
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def root_ui() -> HTMLResponse:
    """Serve the AI-DAN Managing Director web interface."""
    html = _UI_HTML.replace("{version}", _VERSION)
    return HTMLResponse(content=html)
