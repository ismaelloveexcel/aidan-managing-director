# AI-DAN Managing Director

AI-DAN core managing director layer for strategy, idea generation, portfolio control, approvals, and command routing to the GitHub Factory.

## Overview

This service is the central intelligence layer of the AI-DAN ecosystem. It exposes a **Python FastAPI** backend that handles:

- **Conversational interaction** (`/chat`) – dialogue interface for AI-DAN
- **Idea generation** (`/ideas`) – LLM-powered proposal and brainstorming
- **Project portfolio management** (`/projects`) – track and control active projects
- **Approval workflows** (`/approvals`) – human-in-the-loop gate for high-impact actions
- **Command dispatch** (`/commands`) – compile and route structured commands to the GitHub Factory

## Project Structure

```
aidan-managing-director/
├── main.py                        # FastAPI application entry point
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variable template
└── app/
    ├── routes/                    # HTTP route handlers
    │   ├── chat.py
    │   ├── ideas.py
    │   ├── projects.py
    │   ├── approvals.py
    │   └── commands.py
    ├── core/                      # Shared configuration and utilities
    ├── reasoning/                 # AI reasoning modules
    │   ├── strategist.py          # High-level strategic direction
    │   ├── idea_engine.py         # Generative idea production
    │   ├── evaluator.py           # Objective scoring and ranking
    │   └── critic.py              # Adversarial critique and risk identification
    ├── planning/                  # Plan compilation and gating
    │   ├── command_compiler.py    # Translate plans into dispatchable commands
    │   └── approval_gate.py      # Human-in-the-loop approval lifecycle
    ├── memory/                    # Context and memory management
    ├── skills/                    # Discrete reusable capability modules
    └── integrations/              # External API clients
        ├── github_client.py       # GitHub REST API
        ├── registry_client.py     # AI-DAN service registry
        └── llm_client.py          # LLM provider (OpenAI, Anthropic, etc.)
```

## Getting Started

### Prerequisites

- Python 3.11+

### Installation

```bash
# Clone the repository
git clone https://github.com/ismaelloveexcel/aidan-managing-director.git
cd aidan-managing-director

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and fill in your API keys
```

### Running the server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

## Development Notes

- All business logic is **scaffolded only** – methods raise `NotImplementedError` pending implementation.
- All modules use **typed Python** (`from __future__ import annotations` where needed, Pydantic models for I/O).
- The architecture is intentionally **modular**: each concern lives in its own file and folder.
- No frontend is included in this service.
