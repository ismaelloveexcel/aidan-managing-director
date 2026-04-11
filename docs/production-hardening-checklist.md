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
| Add `FACTORY_SECRET` validation step in workflow | ✅ | `.github/workflows/factory-build.yml` |
| Explicit WARNING on local orchestrator fallback | ✅ | `app/factory/factory_client.py` |
| Fix `PersistentFactoryRunStore.reset()` | ✅ | `app/factory/persistent_store.py` |
| Fix test FK constraint failures | ✅ | `tests/test_callback_correlation_turso.py`, `tests/test_factory_routes.py` |

### Acceptance Criteria

- [x] Missing secrets → system fails to start (when `STRICT_PROD=true`)
- [x] Callback requires `X-Factory-Secret` in production
- [x] No unauthenticated webhook endpoint
- [x] `correlation_id` required for factory dispatch
- [x] Tests pass: 589 passed (5 pre-existing UI failures unrelated)

---

## Phase 2 — Remove Fake Success Paths (7d)

### Required Fixes

| Fix | Status | Details |
|-----|--------|---------|
| Disable stub fallbacks in live mode (`github_client`) | ⬜ | `create_repo()`, `upsert_file()`, `get_repo_status()` return stubs unconditionally |
| Disable stub fallbacks in live mode (`vercel_client`) | ⬜ | All methods are stubs |
| Disable stub fallbacks in live mode (`registry_client`) | ⬜ | All methods are stubs |
| Remove local orchestrator fallback in live mode | ⬜ | `factory_client.py:129` should fail-fast when `STRICT_PROD=true` |
| Standardize on `/factory/callback` only | ✅ | Legacy `/webhook` removed |
| Fix reconciliation with `correlation_id` end-to-end | ⬜ | Ensure factory sends correlation_id in all callbacks |
| Add cross-repo contract tests | ⬜ | Dispatch → execution → callback → state update |

### Acceptance Criteria

- [ ] No fake success in live mode
- [ ] Single callback contract
- [ ] Correct run reconciliation via correlation_id
- [ ] Integration tests pass

---

## Phase 3 — Solo Founder Ops Layer (30d)

### Required Additions

| Addition | Status | Details |
|----------|--------|---------|
| Dead-letter queue for failed callbacks | ⬜ | Store failed callbacks, retry + alert |
| Idempotency ledger | ⬜ | Dedupe by correlation_id/run_id |
| Readiness gate | ⬜ | Validate secrets, callback roundtrip, dispatch health |
| Minimal SLO dashboard | ⬜ | Dispatch success rate, callback success rate, stuck jobs |

### Acceptance Criteria

- [ ] Failures visible + recoverable
- [ ] No silent drift
- [ ] Solo operator can debug fast

---

## Required Environment Variables (Production)

| Variable | Required When | Purpose |
|----------|--------------|---------|
| `STRICT_PROD=true` | Production | Enables fail-fast on missing secrets |
| `APP_ENV=production` | Production | Marks environment as production |
| `GITHUB_TOKEN` | `STRICT_PROD=true` | GitHub API access for workflow dispatch |
| `FACTORY_CALLBACK_SECRET` | `STRICT_PROD=true` or `APP_ENV=production` | Callback authentication |
| `PUBLIC_BASE_URL` | `STRICT_PROD=true` | Callback URL base for factory |
| `VERCEL_TOKEN` | `STRICT_PROD=true` | Vercel deployment |
| `FACTORY_SECRET` | Factory workflow | Callback auth header sent by factory |

---

## Test Commands

```bash
# Full test suite
python -m pytest tests/ -v --tb=short

# Factory-specific tests
python -m pytest tests/test_callback_correlation_turso.py tests/test_factory_routes.py -v

# E2E pipeline test
python -m pytest tests/test_e2e_pipeline.py -v
```

---

## Definition of Done

System is production-ready ONLY when:

- [x] Dispatch → execution → callback is authenticated
- [x] No silent failures (STRICT_PROD enforces)
- [ ] No fake success in live mode (Phase 2)
- [x] Strict production mode enforced
- [ ] System can run without manual debugging (Phase 3)
