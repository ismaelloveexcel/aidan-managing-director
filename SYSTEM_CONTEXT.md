# AIDAN System — Connection Context

This document explains how this service fits into the larger AIDAN autonomous product pipeline.

## Full System Architecture

```
You (browser)
     │
     ▼
┌─────────────────┐     webhook      ┌─────────────────┐
│  IDEA FACTORY   │ ───────────────► │  AIDAN BRIDGE   │
│  Validates &    │                  │  Orchestration  │
│  scores ideas   │ ◄── polls 60s ── │  hub            │
└─────────────────┘                  └────────┬────────┘
                                              │ brief
                                              ▼
                                     ┌─────────────────┐     GitHub     ┌─────────────────┐
                                     │  AIDAN MANAGING │   Actions job  │  AI-DAN FACTORY │
                                     │  DIRECTOR       │ ─────────────► │  Builds &       │
                                     │  Evaluates &    │                │  deploys product│
                                     │  dispatches     │                └─────────────────┘
                                     └─────────────────┘
                                              │
                                              ▼
                                     📱 Telegram notification
                                        with live product URL
```

## Service Registry

| Service | Repo | Live URL |
|---------|------|----------|
| Idea Factory | `ismaelloveexcel/idea-factory` | `idea-factory-production-3ada.up.railway.app` |
| AIDAN Bridge | `ismaelloveexcel/claude-bridge` | `aidan-bridge-production.up.railway.app` |
| AIDAN Managing Director | `ismaelloveexcel/aidan-managing-director` | `aidan-managing-director-production.up.railway.app` |
| AI-DAN Factory | `ismaelloveexcel/ai-dan-factory` | `ai-dan-factory-production.up.railway.app` |

## Shared Secrets (must stay in sync)

| Secret | Used by | Purpose |
|--------|---------|---------|
| `BRIDGE_WEBHOOK_SECRET` | Idea Factory + AIDAN Bridge | Signs/verifies idea webhooks |
| `FACTORY_CALLBACK_SECRET` | Managing Director | Signs Factory dispatch calls |
| `TELEGRAM_BOT_TOKEN` | Bridge + Managing Director | Bot auth |
| `TELEGRAM_CHAT_ID` | Bridge + Managing Director | Notification target |

> ⚠️ If you regenerate any shared secret, update it on ALL services listed and redeploy them.

## Scoring Gates

| Gate | Threshold | Set on |
|------|-----------|--------|
| Idea Factory → Bridge | Score ≥ 70 | `MIN_GO_SCORE` on Bridge |
| Bridge → Factory (via MD) | MD score ≥ 8.0 | `MIN_DIRECTOR_SCORE` on Bridge |

## Full documentation

See [ARCHITECTURE.md](https://github.com/ismaelloveexcel/claude-bridge/blob/main/ARCHITECTURE.md) in the `claude-bridge` repo for the complete system reference.
