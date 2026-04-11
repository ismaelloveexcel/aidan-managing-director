/* ═══════════════════════════════════════════════════════════════════════════
   AI-DAN Premium Dashboard — JavaScript
   Modular, clean, founder-focused operating layer.
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // ─── State ───────────────────────────────────────────────────────────────
  var state = {
    currentView: 'home',
    mode: 'venture',        // "venture" | "personal"
    projects: [],
    health: null,
    stats: {},
    builds: [],
    issues: [],
    loading: false,
    analyzeResult: null,
  };

  // ─── API Helper ──────────────────────────────────────────────────────────
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

  // ─── Utilities ───────────────────────────────────────────────────────────
  function esc(s) {
    var d = document.createElement('div');
    d.textContent = String(s || '');
    return d.innerHTML;
  }

  function $(id) { return document.getElementById(id); }

  function toast(msg, type) {
    type = type || 'info';
    var el = document.createElement('div');
    el.className = 'toast ' + type;
    el.textContent = msg;
    var c = $('toast-container');
    if (c) {
      c.appendChild(el);
      setTimeout(function () { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; setTimeout(function () { el.remove(); }, 300); }, 3200);
    }
  }

  function scoreColor(s) {
    if (s >= 7) return 'score-high';
    if (s >= 4) return 'score-med';
    return 'score-low';
  }

  function statusBadgeClass(status) {
    var s = (status || '').toLowerCase();
    if (['launched', 'monitoring', 'scaled', 'approved'].indexOf(s) >= 0) return 'badge-success';
    if (['building', 'queued'].indexOf(s) >= 0) return 'badge-accent';
    if (['killed'].indexOf(s) >= 0) return 'badge-danger';
    if (['review', 'hold'].indexOf(s) >= 0) return 'badge-warning';
    return 'badge-muted';
  }

  // ─── Navigation ──────────────────────────────────────────────────────────
  function navigate(view) {
    state.currentView = view;
    document.querySelectorAll('.nav-item').forEach(function (el) {
      el.classList.toggle('active', el.dataset.view === view);
    });
    document.querySelectorAll('.view-panel').forEach(function (el) {
      el.classList.toggle('active', el.id === 'view-' + view);
    });
    // Load data for the view
    if (view === 'home') loadHome();
    if (view === 'analyze') { /* form is static */ }
    if (view === 'projects') loadProjects();
    if (view === 'builds') loadBuilds();
    if (view === 'issues') loadIssues();
    if (view === 'launch') loadLaunch();
  }

  // ─── Mode Toggle ─────────────────────────────────────────────────────────
  function setMode(mode) {
    state.mode = mode;
    document.querySelectorAll('.mode-btn').forEach(function (el) {
      var isActive = el.dataset.mode === mode;
      el.classList.toggle('active', isActive);
      el.classList.toggle('personal', isActive && mode === 'personal');
    });
    // Refresh current view after mode change
    if (state.currentView === 'home') loadHome();
    if (state.currentView === 'projects') renderProjects();
    if (state.currentView === 'launch') renderLaunch();
  }

  // ─── Data Loading ────────────────────────────────────────────────────────
  function loadDashboardData() {
    return api('/api/dashboard/summary').then(function (data) {
      state.projects = data.projects || [];
      state.health = data.health || null;
      state.stats = data.stats || {};
      state.builds = data.recent_builds || [];
      state.issues = data.issues || [];
      updateSidebarHealth();
      return data;
    }).catch(function (err) {
      console.error('Failed to load dashboard data:', err);
      toast('Failed to load dashboard data', 'error');
    });
  }

  function updateSidebarHealth() {
    var dot = $('sidebar-health-dot');
    var text = $('sidebar-health-text');
    if (!state.health) return;
    var h = state.health.health_status;
    if (dot) {
      dot.className = 'sidebar-health-dot ' + (h === 'GREEN' ? 'green' : h === 'AMBER' ? 'amber' : 'red');
    }
    if (text) {
      text.textContent = state.health.summary || h;
    }
  }

  // ─── HOME / COMMAND CENTER ───────────────────────────────────────────────
  function loadHome() {
    loadDashboardData().then(function () { renderHome(); });
  }

  function renderHome() {
    // Stats
    var s = state.stats;
    var statsEl = $('home-stats');
    if (statsEl) {
      statsEl.innerHTML =
        '<div class="stat-card"><div class="stat-value accent">' + (s.total_projects || 0) + '</div><div class="stat-label">Total Projects</div></div>' +
        '<div class="stat-card"><div class="stat-value success">' + (s.approved_count || 0) + '</div><div class="stat-label">Approved</div></div>' +
        '<div class="stat-card"><div class="stat-value">' +
        (state.mode === 'venture' ? '$' + ((s.revenue_total || 0).toLocaleString()) : (s.personal_count || 0)) +
        '</div><div class="stat-label">' + (state.mode === 'venture' ? 'Revenue' : 'Personal Apps') + '</div></div>' +
        '<div class="stat-card"><div class="stat-value ' + (s.blocked_count > 0 ? 'danger' : 'success') + '">' +
        (s.blocked_count || 0) + '</div><div class="stat-label">Issues</div></div>';
    }

    // Recent projects
    var recentEl = $('home-recent-projects');
    if (recentEl) {
      var filtered = state.projects.filter(function (p) {
        return state.mode === 'all' || p.project_type === state.mode;
      });
      if (!filtered.length) {
        recentEl.innerHTML = '<div class="empty-state">' +
          '<div class="empty-state-icon">&mdash;</div>' +
          '<div class="empty-state-title">No projects yet</div>' +
          '<div class="empty-state-desc">Use the input above to analyze your first idea</div></div>';
      } else {
        var html = '';
        filtered.slice(0, 5).forEach(function (p) {
          var dotColor = p.status === 'launched' ? 'var(--success)' : p.status === 'building' ? 'var(--accent)' : 'var(--text-faint)';
          html += '<div style="display:flex;align-items:center;gap:0.75rem;padding:0.55rem 0;border-bottom:1px solid var(--border)">' +
            '<span style="width:6px;height:6px;border-radius:50%;background:' + dotColor + ';flex-shrink:0"></span>' +
            '<div style="flex:1"><div style="font-size:0.8rem;font-weight:600;color:var(--text-secondary)">' + esc(p.name) + '</div>' +
            '<div style="font-size:0.65rem;color:var(--text-faint)">' + esc(p.status) + '</div></div>' +
            '<span class="badge ' + (p.project_type === 'personal' ? 'badge-personal' : 'badge-venture') + '">' + esc(p.project_type) + '</span>' +
          '</div>';
        });
        recentEl.innerHTML = html;
      }
    }

    // Recent builds
    var buildsEl = $('home-recent-builds');
    if (buildsEl) {
      if (!state.builds.length) {
        buildsEl.innerHTML = '<div style="padding:1rem;text-align:center;color:var(--text-faint);font-size:0.75rem">No builds yet</div>';
      } else {
        var bhtml = '';
        state.builds.slice(0, 5).forEach(function (b) {
          bhtml += '<div class="build-progress">' +
            '<span class="badge ' + statusBadgeClass(b.status) + '">' + esc(b.status) + '</span>' +
            '<div class="build-progress-info">' +
            '<div class="build-progress-name">' + esc(b.project_id || '\u2014') + '</div>' +
            '<div class="build-progress-time">' + esc(b.created_at || '') + '</div>' +
            '</div>' +
            (b.deploy_url ? '<a href="' + esc(b.deploy_url) + '" target="_blank" class="btn btn-sm btn-success">Live \u2197</a>' : '') +
          '</div>';
        });
        buildsEl.innerHTML = bhtml;
      }
    }

    // Next action
    var nextEl = $('home-next-action');
    if (nextEl) {
      var action = '';
      if (!state.projects.length) {
        action = '<div class="alert alert-info"><strong>Get started:</strong> Describe what you want to build above and click Analyze.</div>';
      } else if (state.issues.length) {
        var topIssue = state.issues[0];
        action = '<div class="alert alert-' + (topIssue.severity === 'critical' ? 'danger' : topIssue.severity === 'warning' ? 'warning' : 'info') + '">' +
          '<strong>' + esc(topIssue.title) + ':</strong> ' + esc(topIssue.recommended_action) + '</div>';
      } else {
        action = '<div class="alert alert-success">Everything looks good. Keep building.</div>';
      }
      nextEl.innerHTML = action;
    }
  }

  // ─── ANALYZE ─────────────────────────────────────────────────────────────
  function submitAnalysis() {
    var desc = $('analyze-desc');
    if (!desc || !desc.value.trim()) { toast('Please describe your idea', 'error'); return; }

    var btn = $('analyze-submit');
    var resultsEl = $('analyze-results');
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner" style="width:14px;height:14px;border-width:2px"></span> Analyzing...'; }

    var payload = {
      idea: desc.value.trim(),
      problem: ($('analyze-problem') || {}).value || '',
      target_user: ($('analyze-user') || {}).value || '',
      monetization_model: ($('analyze-monetization') || {}).value || '',
      competition_level: ($('analyze-competition') || {}).value || '',
      time_to_revenue: ($('analyze-ttr') || {}).value || '',
      differentiation: ($('analyze-diff') || {}).value || '',
    };

    api('/api/analyze/', { method: 'POST', body: JSON.stringify(payload) })
      .then(function (data) {
        state.analyzeResult = data;
        renderAnalyzeResult(data);
      })
      .catch(function (err) {
        if (resultsEl) resultsEl.innerHTML = '<div class="alert alert-danger">' + esc(err.message) + '</div>';
        toast('Analysis failed: ' + err.message, 'error');
      })
      .finally(function () {
        if (btn) { btn.disabled = false; btn.innerHTML = 'Analyze Idea'; }
      });
  }

  function renderAnalyzeResult(d) {
    var resultsEl = $('analyze-results');
    if (!resultsEl) return;

    var decision = (d.final_decision || d.score_decision || 'HOLD').toUpperCase();
    var scores = d.score_breakdown || {};
    var overall = d.total_score || 0;
    var isPersonal = state.mode === 'personal';

    var decClass = decision === 'APPROVED' ? 'decision-approved' : decision === 'REJECTED' ? 'decision-rejected' : 'decision-hold';

    var html = '<div class="card result-card" style="margin-bottom:1rem">';
    html += '<div class="card-body">';
    html += '<div style="margin-bottom:1rem"><span class="decision-badge ' + decClass + '">' + esc(decision) + '</span></div>';

    // Blockers
    var blockers = d.validation_blocking || [];
    if (blockers.length) {
      html += '<div class="alert alert-danger"><strong>Blockers:</strong><ul style="margin:0.3rem 0 0 1rem;padding:0;list-style:none">';
      blockers.forEach(function (b) { html += '<li style="margin-bottom:0.15rem">\u2022 ' + esc(b) + '</li>'; });
      html += '</ul></div>';
    }

    // Score bars
    var scoreFields = [
      ['Overall', overall],
      ['Feasibility', scores.feasibility || 0],
      ['Profitability', scores.profitability || 0],
      ['Speed to Revenue', scores.speed_to_revenue || 0],
      ['Competition', scores.competition || 0],
    ];

    scoreFields.forEach(function (sf) {
      var val = parseFloat(sf[1]) || 0;
      var pct = (val / 10) * 100;
      html += '<div class="score-row">' +
        '<div class="score-label-row"><span>' + esc(sf[0]) + '</span><span>' + val.toFixed(1) + '/10</span></div>' +
        '<div class="score-bar"><div class="score-fill ' + scoreColor(val) + '" style="width:' + pct + '%"></div></div></div>';
    });

    // Personal mode: show utility instead of monetization
    if (isPersonal) {
      html += '<div class="section-sep"></div>';
      html += '<div style="font-size:0.78rem;color:var(--text-muted)">' +
        '<strong>Personal Utility:</strong> This idea would save you time and serve as a useful internal tool.' +
        '</div>';
    }

    // Offer brief
    var brief = d.offer || {};
    if (brief.title) {
      html += '<div class="section-sep"></div>';
      html += '<div style="font-size:0.82rem;font-weight:600;color:var(--text-secondary);margin-bottom:0.3rem">' + esc(brief.title) + '</div>';
      if (brief.target_user) html += '<div style="font-size:0.72rem;color:var(--text-faint);margin-bottom:0.15rem">Target: ' + esc(brief.target_user) + '</div>';
      if (brief.problem) html += '<div style="font-size:0.72rem;color:var(--text-faint)">Problem: ' + esc(brief.problem) + '</div>';
    }

    // Next step
    html += '<div class="section-sep"></div>';
    html += '<div style="font-size:0.75rem;color:var(--text-faint)">' + esc(d.next_step || 'Review the scores above and decide your next move.') + '</div>';

    // Action buttons
    html += '<div style="display:flex;gap:0.5rem;margin-top:1.2rem">';
    if (decision === 'APPROVED') {
      html += '<button class="btn btn-success" onclick="window.AIDAN.triggerBuild()">Build Now</button>';
    }
    html += '<button class="btn btn-secondary" onclick="window.AIDAN.saveForLater()">Save</button>';
    html += '<button class="btn btn-ghost" onclick="window.AIDAN.clearAnalysis()">Clear</button>';
    html += '</div>';

    html += '</div></div>';
    resultsEl.innerHTML = html;
  }

  function clearAnalysis() {
    ['analyze-desc', 'analyze-problem', 'analyze-user', 'analyze-diff'].forEach(function (id) {
      var el = $(id); if (el) el.value = '';
    });
    ['analyze-monetization', 'analyze-competition', 'analyze-ttr'].forEach(function (id) {
      var el = $(id); if (el) el.selectedIndex = 0;
    });
    var resultsEl = $('analyze-results');
    if (resultsEl) {
      resultsEl.innerHTML = '<div class="empty-state">' +
        '<div class="empty-state-icon">&mdash;</div>' +
        '<div class="empty-state-title">Ready to analyze</div>' +
        '<div class="empty-state-desc">Fill in your idea and click Analyze to see the score</div></div>';
    }
    state.analyzeResult = null;
  }

  function toggleAdvanced() {
    var el = $('analyze-advanced');
    if (el) {
      var visible = el.style.display !== 'none';
      el.style.display = visible ? 'none' : 'block';
      var toggle = $('analyze-advanced-toggle');
      if (toggle) toggle.textContent = visible ? 'Show advanced fields' : 'Hide advanced fields';
    }
  }

  // ─── PROJECTS ────────────────────────────────────────────────────────────
  function loadProjects() {
    loadDashboardData().then(function () { renderProjects(); });
  }

  function renderProjects() {
    var container = $('projects-list');
    if (!container) return;

    var filtered = state.projects;
    var filterType = $('projects-filter-type');
    if (filterType && filterType.value !== 'all') {
      filtered = filtered.filter(function (p) { return p.project_type === filterType.value; });
    }

    if (!filtered.length) {
      container.innerHTML = '<div class="empty-state">' +
        '<div class="empty-state-icon">&mdash;</div>' +
        '<div class="empty-state-title">No projects found</div>' +
        '<div class="empty-state-desc">Score an idea to create your first project</div></div>';
      return;
    }

    var html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:1rem">';
    filtered.forEach(function (p) {
      var isPersonal = p.project_type === 'personal';
      html += '<div class="project-card">';
      html += '<div class="project-card-header">';
      html += '<div class="project-card-name">' + esc(p.name) + '</div>';
      html += '<div style="display:flex;gap:0.3rem">';
      html += '<span class="badge ' + (isPersonal ? 'badge-personal' : 'badge-venture') + '">' + esc(p.project_type) + '</span>';
      html += '<span class="badge ' + statusBadgeClass(p.status) + '">' + esc(p.status) + '</span>';
      html += '</div></div>';
      html += '<div class="project-card-desc">' + esc(p.description) + '</div>';
      html += '<div class="project-card-meta">';
      if (p.repo_url) html += '<span><a href="' + esc(p.repo_url) + '" target="_blank">Repo</a></span>';
      if (p.deploy_url) html += '<span><a href="' + esc(p.deploy_url) + '" target="_blank">Live</a></span>';
      if (!isPersonal && p.revenue > 0) html += '<span>$' + p.revenue.toLocaleString() + '</span>';
      html += '<span>' + esc((p.created_at || '').split('T')[0]) + '</span>';
      html += '</div>';
      html += '<div class="project-card-actions">';
      if (p.repo_url) html += '<a href="' + esc(p.repo_url) + '" target="_blank" class="btn btn-sm btn-secondary">Open Repo</a>';
      if (p.deploy_url) html += '<a href="' + esc(p.deploy_url) + '" target="_blank" class="btn btn-sm btn-success">Open App \u2197</a>';
      html += '<button class="btn btn-sm btn-ghost" onclick="window.AIDAN.toggleProjectType(\'' + esc(p.project_id) + '\',\'' + (isPersonal ? 'venture' : 'personal') + '\')">' + (isPersonal ? 'To Venture' : 'To Personal') + '</button>';
      html += '</div></div>';
    });
    html += '</div>';
    container.innerHTML = html;
  }

  function toggleProjectType(projectId, newType) {
    api('/api/dashboard/projects/' + projectId + '/type', {
      method: 'PATCH',
      body: JSON.stringify({ project_type: newType }),
    }).then(function () {
      toast('Project type updated to ' + newType, 'success');
      loadProjects();
    }).catch(function (err) {
      toast('Failed to update type: ' + err.message, 'error');
    });
  }

  // ─── BUILDS ──────────────────────────────────────────────────────────────
  function loadBuilds() {
    loadDashboardData().then(function () { renderBuilds(); });
  }

  function renderBuilds() {
    var container = $('builds-list');
    if (!container) return;

    if (!state.builds.length) {
      container.innerHTML = '<div class="empty-state">' +
        '<div class="empty-state-icon">&mdash;</div>' +
        '<div class="empty-state-title">No builds yet</div>' +
        '<div class="empty-state-desc">Approve an idea and trigger a build to see it here</div></div>';
      return;
    }

    var html = '<table class="table"><thead><tr>' +
      '<th>Project</th><th>Status</th><th>Deployment</th><th>Created</th></tr></thead><tbody>';
    state.builds.forEach(function (b) {
      html += '<tr>';
      html += '<td style="font-weight:600">' + esc(b.project_id || '\u2014') + '</td>';
      html += '<td><span class="badge ' + statusBadgeClass(b.status) + '">' + esc(b.status || '\u2014') + '</span></td>';
      html += '<td>' + (b.deploy_url ? '<a href="' + esc(b.deploy_url) + '" target="_blank" class="badge badge-success">Live \u2197</a>' : '<span class="badge badge-muted">\u2014</span>') + '</td>';
      html += '<td style="color:var(--text-faint);font-size:0.7rem">' + esc(b.created_at || '') + '</td>';
      html += '</tr>';
    });
    html += '</tbody></table>';
    container.innerHTML = html;

    // System checks
    renderSystemChecks();
  }

  function renderSystemChecks() {
    var container = $('system-checks');
    if (!container || !state.health) return;

    var h = state.health;
    var checks = [
      { label: 'Portfolio DB', ok: h.total_projects !== undefined, info: (h.total_projects || 0) + ' projects tracked' },
      { label: 'System Health', ok: h.health_status !== 'RED', info: h.summary || h.health_status },
      { label: 'Build Pipeline', ok: state.builds.length > 0 || h.health_status !== 'RED', info: state.builds.length + ' recent builds' },
    ];

    var html = '';
    checks.forEach(function (c) {
      html += '<div style="display:flex;align-items:center;gap:0.6rem;padding:0.5rem 0;border-bottom:1px solid var(--border)">' +
        '<span class="health-dot ' + (c.ok ? 'green' : 'red') + '"></span>' +
        '<span style="flex:1;font-size:0.78rem;color:var(--text-muted)">' + esc(c.label) + '</span>' +
        '<span style="font-size:0.72rem;color:var(--text-faint)">' + esc(c.info) + '</span>' +
      '</div>';
    });
    container.innerHTML = html;
  }

  // ─── ISSUES ──────────────────────────────────────────────────────────────
  function loadIssues() {
    loadDashboardData().then(function () { renderIssues(); });
  }

  function renderIssues() {
    var container = $('issues-list');
    if (!container) return;

    if (!state.issues.length) {
      container.innerHTML = '<div class="empty-state">' +
        '<div class="empty-state-icon">&mdash;</div>' +
        '<div class="empty-state-title">All clear</div>' +
        '<div class="empty-state-desc">No issues or warnings detected</div></div>';
      return;
    }

    var html = '';
    state.issues.forEach(function (issue) {
      var iconClass = issue.severity === 'critical' ? 'critical' : issue.severity === 'warning' ? 'warning' : 'info';
      var icon = issue.severity === 'critical' ? '!' : issue.severity === 'warning' ? '!' : 'i';
      html += '<div class="issue-item">';
      html += '<div class="issue-icon ' + iconClass + '">' + icon + '</div>';
      html += '<div>';
      html += '<div class="issue-title">' + esc(issue.title) + '</div>';
      html += '<div class="issue-desc">' + esc(issue.description) + '</div>';
      html += '<div class="issue-action">' + esc(issue.recommended_action) + '</div>';
      html += '</div></div>';
    });
    container.innerHTML = html;
  }

  // ─── LAUNCH ──────────────────────────────────────────────────────────────
  function loadLaunch() {
    loadDashboardData().then(function () { renderLaunch(); });
  }

  function renderLaunch() {
    var container = $('launch-content');
    if (!container) return;

    var isPersonal = state.mode === 'personal';
    var projects = state.projects.filter(function (p) {
      return p.project_type === state.mode || state.mode === 'all';
    });

    if (!projects.length) {
      container.innerHTML = '<div class="empty-state">' +
        '<div class="empty-state-icon">&mdash;</div>' +
        '<div class="empty-state-title">No ' + (isPersonal ? 'personal' : 'venture') + ' projects yet</div>' +
        '<div class="empty-state-desc">Create and approve a project first</div></div>';
      return;
    }

    var html = '';
    projects.forEach(function (p) {
      html += '<div class="card" style="margin-bottom:1rem">';
      html += '<div class="card-header"><div class="card-title">' + esc(p.name) + '</div>';
      html += '<div class="card-actions"><span class="badge ' + statusBadgeClass(p.status) + '">' + esc(p.status) + '</span></div></div>';
      html += '<div class="card-body">';

      if (isPersonal) {
        html += '<div style="font-size:0.78rem;color:var(--text-muted);margin-bottom:0.75rem">' +
          '<strong>Purpose:</strong> ' + esc(p.description) + '</div>';
        html += '<div style="font-size:0.75rem;color:var(--text-faint);margin-bottom:0.5rem">' +
          'Private deployment \u2014 no public launch needed</div>';
        if (p.deploy_url) {
          html += '<div style="margin-bottom:0.5rem"><a href="' + esc(p.deploy_url) + '" target="_blank" class="btn btn-sm btn-success">Open App \u2197</a></div>';
        }
        html += '<div style="font-size:0.7rem;color:var(--text-faint)">Status: ' + esc(p.status) + ' \u00B7 Created: ' + esc((p.created_at || '').split('T')[0]) + '</div>';
      } else {
        html += '<div style="font-size:0.78rem;color:var(--text-muted);margin-bottom:0.75rem">' + esc(p.description) + '</div>';
        if (p.deploy_url) {
          html += '<div style="margin-bottom:0.5rem"><a href="' + esc(p.deploy_url) + '" target="_blank" class="btn btn-sm btn-success">Live Site \u2197</a></div>';
        }
        if (p.revenue > 0) {
          html += '<div style="font-size:0.78rem;color:var(--success);margin-bottom:0.5rem">Revenue: $' + p.revenue.toLocaleString() + '</div>';
        } else {
          html += '<div class="alert alert-warning" style="font-size:0.72rem">No revenue recorded yet. Set up payment collection to track revenue.</div>';
        }
      }

      html += '</div></div>';
    });
    container.innerHTML = html;
  }

  // ─── COMMAND CENTER INPUT ────────────────────────────────────────────────
  function handleCommandSubmit() {
    var input = $('command-input');
    if (!input || !input.value.trim()) return;

    var idea = input.value.trim();
    input.value = '';

    // Navigate to analyze and pre-fill
    navigate('analyze');
    var descEl = $('analyze-desc');
    if (descEl) {
      descEl.value = idea;
      submitAnalysis();
    }
  }

  function triggerBuild() {
    if (!state.analyzeResult) { toast('No analysis result to build from', 'error'); return; }
    var name = (state.analyzeResult.offer || {}).title || 'new-project';
    var safeName = name.replace(/[^a-z0-9_-]/gi, '_').toLowerCase();

    api('/factory/trigger', { method: 'POST', body: JSON.stringify({ project_name: safeName, dry_run: false }) })
      .then(function () { toast('Build triggered for: ' + safeName, 'success'); navigate('builds'); })
      .catch(function (e) { toast('Build trigger failed: ' + e.message, 'error'); });
  }

  function saveForLater() {
    toast('Idea saved to your pipeline', 'success');
  }

  // ─── INIT ────────────────────────────────────────────────────────────────
  function init() {
    // Navigation click handlers
    document.querySelectorAll('.nav-item').forEach(function (el) {
      el.addEventListener('click', function () {
        navigate(el.dataset.view);
      });
    });

    // Mode toggle
    document.querySelectorAll('.mode-btn').forEach(function (el) {
      el.addEventListener('click', function () {
        setMode(el.dataset.mode);
      });
    });

    // Command input
    var cmdInput = $('command-input');
    if (cmdInput) {
      cmdInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          handleCommandSubmit();
        }
      });
    }
    var cmdBtn = $('command-submit');
    if (cmdBtn) cmdBtn.addEventListener('click', handleCommandSubmit);

    // Analyze button
    var analyzeBtn = $('analyze-submit');
    if (analyzeBtn) analyzeBtn.addEventListener('click', submitAnalysis);

    // Advanced toggle
    var advToggle = $('analyze-advanced-toggle');
    if (advToggle) advToggle.addEventListener('click', toggleAdvanced);

    // Project filter
    var filterEl = $('projects-filter-type');
    if (filterEl) filterEl.addEventListener('change', renderProjects);

    // Load home
    navigate('home');
  }

  // ─── Public API ──────────────────────────────────────────────────────────
  window.AIDAN = {
    navigate: navigate,
    setMode: setMode,
    submitAnalysis: submitAnalysis,
    clearAnalysis: clearAnalysis,
    toggleAdvanced: toggleAdvanced,
    triggerBuild: triggerBuild,
    saveForLater: saveForLater,
    toggleProjectType: toggleProjectType,
    handleCommandSubmit: handleCommandSubmit,
  };

  // Boot
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
