# Dashboard Audit Checklist

## Frontend
- [x] Identify current UI entrypoint (embedded HTML in main.py, ~1855 lines)
- [x] Identify current routing model (tab-based, JS switching)
- [x] Identify UX pain points (one giant HTML string, no modularity, developer-focused)
- [x] Identify state/loading/error issues (basic loading spinners, no error recovery)
- [x] Identify maintainability issues (all CSS/JS/HTML in one string variable)

## Connected flows
- [x] Analyze flow (`POST /api/analyze/` — works correctly)
- [x] Factory run flow (`POST /factory/runs`, `GET /factory/runs`)
- [x] Callback/status flow (callback via POST, polling via GET)
- [x] Repo/project visibility flow (`GET /portfolio/projects`)
- [x] Deployment visibility flow (via factory run results)

## Repo issues discovered
- [x] No project_type field (venture/personal) — added to metadata
- [x] No comprehensive dashboard summary endpoint — added
- [x] No static file serving — added
- [x] Frontend not modular — created separate static files
- [x] No mode toggle for venture/personal — implemented
- [x] No issue/health surfacing in dashboard — implemented
- [x] Missing project type filtering — added filter in Projects view
