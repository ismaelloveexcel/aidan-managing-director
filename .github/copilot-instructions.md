# AI-DAN — Copilot Instructions

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

🚫 DO NOT:
- build product logic
- create UI/frontend
- implement deployment pipelines
- mix execution logic into this repo

---

## DEVELOPMENT PRINCIPLES

### 1. Modular Architecture (MANDATORY)

Every capability must be isolated:

- reasoning/ → thinking (ideas, evaluation, critique)
- planning/ → structuring decisions into actions
- routes/ → API interface only
- integrations/ → external communication only

🚫 No cross-contamination between modules

---

### 2. No Business Logic in Routes

Routes must:
- validate input
- call appropriate module
- return response

All logic belongs in:
- reasoning/
- planning/

---

### 3. Structured Outputs Only

All outputs must be:
- typed (Pydantic models)
- predictable
- machine-readable

Avoid:
- long unstructured text
- conversational fluff

---

### 4. Think Like a Managing Director

All logic must reflect:

- prioritization over execution
- critical thinking over agreement
- challenge weak ideas
- optimize for ROI, speed, and scalability

AI-DAN should:
- question assumptions
- reject bad ideas
- suggest better alternatives

---

### 5. No Fake Intelligence

🚫 DO NOT:
- pretend to call external APIs
- simulate complex behavior without clarity
- generate vague placeholders

If logic is not implemented:
→ return structured placeholder or raise controlled exception

---

### 6. Clean Code Requirements

- Python 3.11+
- Type hints everywhere
- Pydantic for schemas
- Small, focused functions
- Clear docstrings explaining intent (not obvious comments)

---

### 7. Error Handling Standard

- Use HTTPException in routes
- Use explicit errors in modules
- Never allow silent failures

---

### 8. Integration Design

All external systems must go through:

- integrations/github_client.py
- integrations/registry_client.py
- integrations/llm_client.py

🚫 No direct external calls elsewhere

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
Must score:
- feasibility
- profitability
- speed
- competition

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
