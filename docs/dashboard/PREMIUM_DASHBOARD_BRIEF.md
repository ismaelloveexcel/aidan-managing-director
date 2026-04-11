# Premium Dashboard Brief

## Goal
Create a premium founder dashboard for a solo non-technical user.

## Repos
- aidan-managing-director (control plane)
- ai-dan-factory (execution plane)

## Must support
- Venture Mode (monetizable ideas, public launch, pricing, GTM)
- Personal Mode (private/internal apps, personal utility, no monetization pressure)

## Dashboard Views
1. **Command Center** — single dominant input, mode toggle, stats, recent activity
2. **Analyze** — idea scoring with advanced fields, score visualization, decision badges
3. **Build & Deploy** — system health checks, build runs, deployment status
4. **Projects** — full portfolio manager with type filtering (venture/personal)
5. **Issues & Health** — flagged gaps, severity, plain-language actions
6. **Launch & Outputs** — venture launch assets / personal deployment status

## Architecture
- Static frontend: `static/dashboard.html`, `static/css/dashboard.css`, `static/js/dashboard.js`
- Backend API: `GET /api/dashboard/summary`, `PATCH /api/dashboard/projects/{id}/type`
- Served at: `GET /dashboard`
- Legacy UI preserved at: `GET /`

## Important
- Desktop-first, responsive-aware
- Premium dark theme, calm and trustworthy
- Clear loading/empty/error states
- No technical jargon in main views
