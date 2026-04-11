# Production Hardening Checklist — AI-DAN System

## System Architecture

```
┌──────────────────────────┐     dispatch_workflow()    ┌──────────────────────────┐
│  Managing Director (MD)  │ ─────────────────────────► │   Factory (ai-dan-factory)│
│  (Control Plane)         │                            │   (Execution Plane)       │
│                          │ ◄───────────────────────── │                           │
│  Decision Engine         │   POST /factory/callback   │   Repo Create + Deploy    │
│  Scoring + Validation    │   X-Factory-Secret header  │   Vercel Deployment       │
│  State Machine           │   correlation_id join key  │   Callback to MD          │
└──────────────────────────┘                            └──────────────────────────┘
```

---

## Phase 1 — Stop Data Loss + Auth Integrity ✅ DONE

### Fixes Applied

| Fix | Status | File(s) |
|-----|--------|---------|
| Add `STRICT_PROD` mode | ✅ | `app/core/config.py` |
| `validate_production_secrets()` method | ✅ | `app/core/config.py` |
| Fail-fast on missing secrets when `STRICT_PROD=true` | ✅ | `app/core/config.py` |
| Fix `RateLimitMiddleware.reset()` (test harness) | ✅ | `app/core/middleware.py` |
| Require `FACTORY_CALLBACK_SECRET` in production | ✅ | `app/routes/factory.py` |
| Remove legacy `/factory/webhook` (unauthenticated) | ✅ | `app/routes/factory.py` |
| Replace with 410 Gone tombstone | ✅ | `app/routes/factory.py` |
| Make `correlation_id` required in workflow | ✅ | `.github/workflows/factory-build.yml` |
| Make `callback_url` required in workflow | ✅ | `.github/workflows/factory-build.yml` |
| Add `FACTORY_SECRET` + inputs validation step in workflow | ✅ | `.github/workflows/factory-build.yml` |
| Explicit WARNING on local orchestrator fallback | ✅ | `app/factory/factory_client.py` |
| Fix `PersistentFactoryRunStore.reset()` | ✅ | `app/factory/persistent_store.py` |
| Fix test FK constraint failures | ✅ | `tests/test_callback_correlation_turso.py`, `tests/test_factory_routes.py` |

### Acceptance Criteria

- [x] Missing secrets → system fails to start (when `STRICT_PROD=true`)
- [x] Callback requires `X-Factory-Secret` in production
- [x] No unauthenticated webhook endpoint
- [x] `correlation_id` required for factory dispatch
- [x] Tests pass: 599 passed (5 pre-existing UI failures unrelated)

---

## Phase 2 — Remove Fake Success Paths ✅ DONE

### Fixes Applied

| Fix | Status | File(s) |
|-----|--------|---------|
| Disable stub fallbacks in live mode (`github_client`) | ✅ | `app/integrations/github_client.py` — `_reject_stub_in_production()` guard on `create_repo`, `create_issue`, `create_pr`, `create_repo_from_template`, `upsert_file`, `get_repo_status` |
| Disable stub fallbacks in live mode (`vercel_client`) | ✅ | `app/integrations/vercel_client.py` — guarded token-missing and API-error fallback paths |
| Disable stub fallbacks in live mode (`registry_client`) | ✅ | `app/integrations/registry_client.py` — guarded `register_service`, `discover`, `get_service` |
| Block local orchestrator fallback in live mode | ✅ | `app/factory/factory_client.py` — returns FAILED run when `is_production_mode()` and dispatch fails |
| Standardize on `/factory/callback` only | ✅ | Legacy `/webhook` removed (Phase 1) |
| Add cross-repo contract tests | ✅ | `tests/test_ops_phase3.py::TestCrossRepoContract` — dispatch → callback → state update |

### Acceptance Criteria

- [x] No fake success in live mode (all stubs guarded by `_reject_stub_in_production()`)
- [x] Single callback contract (`/factory/callback` only)
- [x] Correct run reconciliation via `correlation_id` (contract test validates)
- [x] Integration tests pass (599 passed)

---

## Phase 3 — Solo Founder Ops Layer ✅ DONE

### Additions Applied

| Addition | Status | File(s) |
|----------|--------|---------|
| Dead-letter queue for failed callbacks | ✅ | `app/factory/dead_letter.py` — enqueue/list/retry/resolve + DB schema |
| Ops event tracking (SLO data) | ✅ | `app/factory/ops_events.py` — dispatch/callback/deployment events |
| Readiness gate | ✅ | `GET /ops/ready` — validates secrets, DB, run store, callback config |
| SLO dashboard | ✅ | `GET /ops/slo` — success rates, stuck jobs, DLQ counts |
| DLQ visibility | ✅ | `GET /ops/dlq`, `POST /ops/dlq/{id}/resolve` |
| Idempotency ledger | ✅ | `idempotency_keys` table (existing) + `correlation_id` join in factory runs |
| DB schema extensions | ✅ | `dead_letter_callbacks` + `ops_events` tables in `schema.sql` |

### Acceptance Criteria

- [x] Failures visible + recoverable (DLQ + ops events)
- [x] No silent drift (orphan callbacks → DLQ, ops events → SLO)
- [x] Solo operator can debug fast (readiness gate, SLO dashboard, DLQ list)

---

## Required Environment Variables (Production)

| Variable | Required When | Purpose |
|----------|--------------|---------|
| `STRICT_PROD=true` | Production | Enables fail-fast on missing secrets + blocks stubs |
| `APP_ENV=production` | Production | Marks environment as production |
| `GITHUB_TOKEN` | `STRICT_PROD=true` | GitHub API access for workflow dispatch |
| `FACTORY_CALLBACK_SECRET` | `STRICT_PROD=true` or `APP_ENV=production` | Callback authentication |
| `PUBLIC_BASE_URL` | `STRICT_PROD=true` | Callback URL base for factory |
| `VERCEL_TOKEN` | `STRICT_PROD=true` | Vercel deployment |
| `FACTORY_SECRET` | Factory workflow | Callback auth header sent by factory |

---

## Operational Endpoints (Phase 3)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/ops/ready` | GET | Readiness gate — checks secrets, DB, run store |
| `/ops/slo` | GET | SLO dashboard — success rates, stuck jobs, DLQ |
| `/ops/slo?hours=N` | GET | SLO over custom time window |
| `/ops/dlq` | GET | List dead-letter queue entries |
| `/ops/dlq/{id}/resolve` | POST | Mark DLQ entry as resolved |

---

## Test Commands

```bash
# Full test suite
python -m pytest tests/ -v --tb=short

# Factory-specific tests
python -m pytest tests/test_callback_correlation_turso.py tests/test_factory_routes.py -v

# Phase 3 operational tests
python -m pytest tests/test_ops_phase3.py -v

# E2E pipeline test
python -m pytest tests/test_e2e_pipeline.py -v

# Cross-repo contract test
python -m pytest tests/test_ops_phase3.py::TestCrossRepoContract -v
```

---

## Definition of Done

System is production-ready ONLY when:

- [x] Dispatch → execution → callback is authenticated
- [x] No silent failures (STRICT_PROD enforces)
- [x] No fake success in live mode (Phase 2 — stubs blocked in production)
- [x] Strict production mode enforced
- [x] System can run without manual debugging (Phase 3 — readiness + SLO + DLQ)
