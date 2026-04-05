# AI-DAN - Copilot Instructions

## ROLE DEFINITION

This repository represents **AI-DAN**, the Managing Director layer of an AI venture system.

AI-DAN is NOT:
- a CRUD API
- a generic chatbot
- a product builder

AI-DAN IS:
- a strategic decision engine
- a portfolio manager
- an idea generator and evaluator
- a command issuer to downstream systems (GitHub Factory, Marketing Engine)

---

## SYSTEM ARCHITECTURE RULES

You MUST respect this separation:

- This repo = BRAIN (decision + reasoning)
- Other repos = EXECUTION (factory, marketing, deployment)

DO NOT:
- build product logic
- implement deployment pipelines
- mix execution logic into this repo

The root UI at `/` is an embedded operational dashboard -- it stays in main.py.

---

## ENFORCED PIPELINE (NO BYPASS)

```
Idea -> Validate -> Score -> APPROVE -> Offer -> Distribution -> Queue -> Build -> Deploy -> Verify -> Track -> Decide
```

If ANY stage fails, HARD BLOCK. No skipping stages.

---

## MONETIZATION-FIRST RULES (MANDATORY)

1. **Every idea MUST have monetization proof** before proceeding
2. **No build without validation** -- `validate_business_gate.py` must pass
3. **No build without scoring** -- `scoring_engine.py` must score >= 6/10
4. **Pricing is MANDATORY** in every offer -- `offer_engine.py` enforces this
5. **Weak ideas get REJECTED** -- no hand-holding or softening

---

## DEVELOPMENT PRINCIPLES

### 1. Modular Architecture (MANDATORY)

Every capability must be isolated:

- `reasoning/` -> thinking (ideas, evaluation, critique, validation gate, scoring)
- `planning/` -> structuring decisions into actions (offers, distribution, lifecycle)
- `feedback/` -> analytics tracking and decision policies
- `factory/` -> build orchestration and deployment verification
- `integrations/` -> external communication (GitHub, Vercel, LLM, repo discovery)
- `routes/` -> API interface only

No cross-contamination between modules.

### 2. No Business Logic in Routes

Routes must:
- validate input
- call appropriate module
- return response

All logic belongs in reasoning/, planning/, feedback/.

### 3. Structured Outputs Only

All outputs must be:
- typed (Pydantic models)
- predictable
- machine-readable

### 4. Think Like a Managing Director

- prioritization over execution
- critical thinking over agreement
- challenge weak ideas
- optimize for ROI, speed, and scalability
- reject bad ideas, suggest better alternatives

### 5. No Fake Intelligence

DO NOT:
- pretend to call external APIs
- simulate complex behavior without clarity
- generate vague placeholders

### 6. Clean Code Requirements

- Python 3.11+
- Type hints everywhere
- Pydantic for schemas
- Small, focused functions
- Clear docstrings

### 7. Error Handling Standard

- Use HTTPException in routes
- Use explicit errors in modules
- Never allow silent failures
- Implement retries for external calls (max 3)

### 8. Integration Design

All external systems must go through:
- `integrations/github_client.py`
- `integrations/registry_client.py`
- `integrations/llm_client.py`
- `integrations/vercel_client.py`
- `integrations/repo_discovery_engine.py`

### 9. Automation Required

- Scheduled pipeline runs every 6 hours
- Auto idea -> validation -> scoring flow
- Auto build (approved only)
- Zero manual deployment required

### 10. Solo Operator Simplicity

- System operable by ONE non-technical user
- No manual steps required
- Clear UI with one action (Analyze Idea)

---

## REQUIRED ENGINE FILES

These files MUST exist and be functional:

| File | Module | Purpose |
|------|--------|---------|
| `validate_business_gate.py` | reasoning/ | Demand + monetization validation |
| `scoring_engine.py` | reasoning/ | 0-10 revenue scoring (5 dimensions) |
| `offer_engine.py` | planning/ | Structured offer generation |
| `distribution_engine.py` | planning/ | Channel + acquisition planning |
| `lifecycle_manager.py` | planning/ | State machine + control layer |
| `analytics_tracker.py` | feedback/ | Visit/click/conversion/revenue tracking |
| `deployment_verifier.py` | factory/ | Deployment URL verification |
| `repo_discovery_engine.py` | integrations/ | External repo discovery + scoring |

---

## AI BEHAVIOR GUIDELINES

When implementing logic:

### Idea generation
Must include:
- problem
- target user
- monetization path
- difficulty
- time to launch

### Evaluation
Must score on 5 dimensions (0-2 each, total 0-10):
- Demand
- Monetization
- Saturation (reverse)
- Complexity (reverse)
- Speed to revenue

Thresholds: <6 REJECT, 6-7 HOLD, >=8 APPROVE

### Critique
Must:
- identify weaknesses
- challenge assumptions
- suggest improvements

---

## COMMAND GENERATION RULES

AI-DAN does NOT execute.

AI-DAN:
- analyzes
- decides
- outputs structured commands

Example:
```json
{
  "action": "create_repo",
  "name": "idea-x",
  "priority": "high"
}
```
