/* ═══════════════════════════════════════════════════════════════════════════
   AI-DAN Launch Engine — JavaScript
   Single flow: Idea → Analyze → Decision → Build → Live
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // ─── State ───────────────────────────────────────────────────────────────
  var state = {
    mode: 'venture',
    projects: [],
    health: null,
    stats: {},
    builds: [],
    issues: [],
    analyzeResult: null,
  };

  // ─── Helpers ─────────────────────────────────────────────────────────────
  function $(id) { return document.getElementById(id); }

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = String(s || '');
    return d.innerHTML;
  }

  function toast(msg, type) {
    type = type || 'info';
    var el = document.createElement('div');
    el.className = 'toast ' + type;
    el.textContent = msg;
    var c = $('toast-container');
    if (c) {
      c.appendChild(el);
      setTimeout(function () {
        el.style.opacity = '0';
        el.style.transition = 'opacity .3s';
        setTimeout(function () { el.remove(); }, 300);
      }, 3000);
    }
  }

  function scoreColor(s) {
    if (s >= 7) return 'score-high';
    if (s >= 4) return 'score-med';
    return 'score-low';
  }

  function scoreTextClass(s) {
    if (s >= 7) return 'high';
    if (s >= 4) return 'med';
    return 'low';
  }

  // ─── API ─────────────────────────────────────────────────────────────────
  function api(path, opts) {
    opts = opts || {};
    var headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
    var mergedOpts = Object.assign({}, opts, { headers: headers });
    return fetch(path, mergedOpts).then(function (r) {
      if (!r.ok) return r.text().then(function (t) {
        var msg = t;
        try { var d = JSON.parse(t); msg = d.detail || d.message || t; } catch (e) { /* ignore */ }
        throw new Error(msg);
      });
      return r.text().then(function (t) {
        if (!t) return {};
        try { return JSON.parse(t); } catch (e) { throw new Error('Invalid JSON response'); }
      });
    });
  }

  // ─── Mode Toggle ─────────────────────────────────────────────────────────
  function setMode(mode) {
    state.mode = mode;
    document.querySelectorAll('.mode-btn').forEach(function (el) {
      var isActive = el.dataset.mode === mode;
      el.classList.toggle('active', isActive);
      el.classList.toggle('personal', isActive && mode === 'personal');
    });
  }

  // ─── Load Data ───────────────────────────────────────────────────────────
  function loadDashboardData() {
    return api('/api/dashboard/summary').then(function (data) {
      state.projects = data.projects || [];
      state.health = data.health || null;
      state.stats = data.stats || {};
      state.builds = data.recent_builds || [];
      state.issues = data.issues || [];
      renderPipeline();
      return data;
    }).catch(function (err) {
      console.error('Failed to load data:', err);
    });
  }

  // ─── Render Pipeline ────────────────────────────────────────────────────
  function renderPipeline() {
    // Status bar
    var dot = $('status-dot');
    var text = $('status-text');
    if (state.health) {
      var h = state.health.health_status;
      if (dot) dot.className = 'status-dot ' + (h === 'GREEN' ? 'green' : h === 'AMBER' ? 'amber' : 'red');
      if (text) text.textContent = state.health.summary || h;
    }

    // Project pipeline
    var listEl = $('pipeline-list');
    if (listEl) {
      if (!state.projects.length) {
        listEl.innerHTML = '<div class="pipeline-empty">Analyze an idea to start your pipeline</div>';
      } else {
        var html = '';
        state.projects.forEach(function (p) {
          var color = p.status === 'launched' ? 'var(--success)' :
                      p.status === 'building' ? 'var(--accent)' :
                      p.status === 'approved' ? 'var(--warning)' :
                      'var(--text-faint)';
          html += '<div class="pipeline-item">' +
            '<span class="pipeline-dot" style="background:' + color + '"></span>' +
            '<span class="pipeline-name">' + esc(p.name) + '</span>' +
            '<span class="badge ' + (p.project_type === 'personal' ? 'badge-personal' : 'badge-venture') + '">' + esc(p.project_type) + '</span>' +
            '<span class="pipeline-status">' + esc(p.status) + '</span>' +
          '</div>';
        });
        listEl.innerHTML = html;
      }
    }

    // Issues
    var issuesSection = $('issues-section');
    var issuesList = $('issues-list');
    if (issuesSection && issuesList) {
      if (state.issues.length) {
        issuesSection.style.display = 'block';
        var ihtml = '';
        state.issues.forEach(function (issue) {
          var dotClass = issue.severity === 'critical' ? 'critical' : issue.severity === 'warning' ? 'warning' : 'info';
          ihtml += '<div class="pipeline-issue">' +
            '<span class="pipeline-issue-dot ' + dotClass + '"></span>' +
            '<div>' +
            '<div class="pipeline-issue-text">' + esc(issue.title) + '</div>' +
            '<div class="pipeline-issue-action">' + esc(issue.recommended_action) + '</div>' +
            '</div></div>';
        });
        issuesList.innerHTML = ihtml;
      } else {
        issuesSection.style.display = 'none';
      }
    }
  }

  // ─── Submit Analysis ─────────────────────────────────────────────────────
  function submitFromHero() {
    var input = $('hero-input');
    if (!input || !input.value.trim()) {
      toast('Describe what you want to build', 'error');
      return;
    }

    var idea = input.value.trim();
    var btn = $('hero-submit');
    var resultsSection = $('results-section');
    var resultsInner = $('results-inner');

    if (btn) { btn.disabled = true; btn.textContent = 'Analyzing...'; }
    if (resultsSection) resultsSection.style.display = 'block';
    if (resultsInner) resultsInner.innerHTML = '<div style="padding:2rem;text-align:center"><span class="spinner"></span><div style="margin-top:0.75rem;font-size:0.72rem;color:var(--text-faint)">Scoring your idea...</div></div>';

    var payload = { idea: idea };

    api('/api/analyze/', { method: 'POST', body: JSON.stringify(payload) })
      .then(function (data) {
        state.analyzeResult = data;
        renderResult(data, idea);
      })
      .catch(function (err) {
        if (resultsInner) resultsInner.innerHTML = '<div style="padding:1.5rem"><div class="result-blockers">' + esc(err.message) + '</div></div>';
        toast('Analysis failed', 'error');
      })
      .finally(function () {
        if (btn) { btn.disabled = false; btn.textContent = 'Analyze'; }
      });
  }

  // ─── Render Result ───────────────────────────────────────────────────────
  function renderResult(d, idea) {
    var el = $('results-inner');
    if (!el) return;

    var decision = (d.final_decision || d.score_decision || 'HOLD').toUpperCase();
    var scores = d.score_breakdown || {};
    var overall = d.total_score || 0;
    var decClass = decision === 'APPROVED' ? 'decision-approved' : decision === 'REJECTED' ? 'decision-rejected' : 'decision-hold';

    var offerTitle = (d.offer || {}).title || idea || 'Your idea';

    var html = '';

    // Decision header
    html += '<div class="result-decision">';
    html += '<span class="decision-badge ' + decClass + '">' + esc(decision) + '</span>';
    html += '<span class="decision-title">' + esc(offerTitle) + '</span>';
    html += '<span class="decision-score ' + scoreTextClass(overall) + '">' + (parseFloat(overall) || 0).toFixed(1) + '</span>';
    html += '</div>';

    // Body
    html += '<div class="result-body">';

    // Blockers
    var blockers = d.validation_blocking || [];
    if (blockers.length) {
      html += '<div class="result-blockers"><strong>Blockers:</strong>';
      blockers.forEach(function (b) { html += '<br>\u2022 ' + esc(b); });
      html += '</div>';
    }

    // Score bars (2-column grid)
    var scoreFields = [
      ['Feasibility', scores.feasibility || 0],
      ['Profitability', scores.profitability || 0],
      ['Speed', scores.speed_to_revenue || 0],
      ['Competition', scores.competition || 0],
    ];

    html += '<div class="result-scores">';
    scoreFields.forEach(function (sf) {
      var val = parseFloat(sf[1]) || 0;
      var pct = (val / 10) * 100;
      html += '<div class="score-row">' +
        '<div class="score-label-row"><span>' + esc(sf[0]) + '</span><span>' + val.toFixed(1) + '</span></div>' +
        '<div class="score-bar"><div class="score-fill ' + scoreColor(val) + '" style="width:' + pct + '%"></div></div></div>';
    });
    html += '</div>';

    // Next step
    html += '<div class="result-next">' + esc(d.next_step || 'Review scores and decide your next move.') + '</div>';

    // Action buttons
    html += '<div class="result-actions">';
    if (decision === 'APPROVED') {
      html += '<button class="btn btn-success" onclick="window.AIDAN.triggerBuild()">Build Now</button>';
    }
    html += '<button class="btn btn-secondary" onclick="window.AIDAN.saveForLater()">Save</button>';
    html += '<button class="btn btn-ghost" onclick="window.AIDAN.clearResult()">Clear</button>';
    html += '</div>';

    html += '</div>';

    el.innerHTML = html;

    // Scroll to result
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // ─── Actions ─────────────────────────────────────────────────────────────
  function triggerBuild() {
    if (!state.analyzeResult) { toast('No analysis to build from', 'error'); return; }
    var name = (state.analyzeResult.offer || {}).title || 'new-project';
    var safeName = name.replace(/[^a-z0-9_-]/gi, '_').toLowerCase();

    toast('Triggering build for ' + safeName + '...', 'info');
    api('/factory/trigger', { method: 'POST', body: JSON.stringify({ project_name: safeName, dry_run: false }) })
      .then(function () {
        toast('Build started: ' + safeName, 'success');
        loadDashboardData();
      })
      .catch(function (e) { toast('Build failed: ' + e.message, 'error'); });
  }

  function saveForLater() {
    toast('Saved to pipeline', 'success');
  }

  function clearResult() {
    var s = $('results-section');
    if (s) s.style.display = 'none';
    state.analyzeResult = null;
    var input = $('hero-input');
    if (input) { input.value = ''; input.focus(); }
  }

  // ─── Init ────────────────────────────────────────────────────────────────
  function init() {
    // Mode toggle
    document.querySelectorAll('.mode-btn').forEach(function (el) {
      el.addEventListener('click', function () { setMode(el.dataset.mode); });
    });

    // Hero submit
    var heroInput = $('hero-input');
    if (heroInput) {
      heroInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          submitFromHero();
        }
      });
    }
    var heroBtn = $('hero-submit');
    if (heroBtn) heroBtn.addEventListener('click', submitFromHero);

    // Load pipeline data
    loadDashboardData();
  }

  // ─── Public API ──────────────────────────────────────────────────────────
  window.AIDAN = {
    triggerBuild: triggerBuild,
    saveForLater: saveForLater,
    clearResult: clearResult,
    setMode: setMode,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
