# AI-DAN Managing Director

AI-DAN is a managing-director AI system that turns founder input into a structured strategic decision and machine-readable command set.

## What this project includes

### Backend (FastAPI)
- Thin route layer (`app/routes`)
- Reasoning layer (`app/reasoning`)
  - strategist
  - idea engine
  - evaluator
  - critic
- Planning layer (`app/planning`)
  - planner
  - command compiler
  - approval gate
- Integrations layer (`app/integrations`)
  - GitHub client
  - registry client
  - LLM client

The main flow is:

`input -> strategist -> idea generation -> evaluation -> critique -> plan -> commands -> founder response`

### Frontend (Streamlit)
A simple **AI-DAN Command Center** for non-technical users:
- One input: **Ask AI-DAN**
- One primary action: **Get Decision**
- Friendly response sections:
  - summary
  - decision
  - score
  - risks
  - suggested next action
  - commands (collapsed)
- Optional **Show technical details**
- Last 5 interactions

---

## One-click local startup (recommended)

### Mac/Linux

Run from the project root:

```bash
./scripts/start_local.sh
```

What this does:
- verifies Python + pip
- installs dependencies from `requirements.txt`
- starts backend with Uvicorn (`main:app`)
- starts frontend with Streamlit (`frontend/command_center.py`)

URLs:
- Frontend (AI-DAN Command Center): `http://localhost:8501`
- Backend API: `http://localhost:8000`
- Backend docs: `http://localhost:8000/docs`

Stop both services: press `Ctrl+C` in the terminal running the script.

### Windows

Run from the project root:

```bat
scripts\start_local.bat
```

What this does:
- verifies Python + pip
- installs dependencies from `requirements.txt`
- starts backend with Uvicorn (`main:app`)
- starts frontend with Streamlit (`frontend/command_center.py`)

URLs:
- Frontend (AI-DAN Command Center): `http://localhost:8501`
- Backend API: `http://localhost:8000`
- Backend docs: `http://localhost:8000/docs`

---

## Manual quickstart

### 1) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Run the backend

```bash
uvicorn main:app --reload
```

Backend runs at:
- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

### 3) Run the frontend

In a second terminal:

```bash
streamlit run frontend/command_center.py
```

By default, the frontend calls `http://localhost:8000`.
You can override backend URL in either:
- the app Settings panel, or
- env var:

```bash
export AIDAN_BACKEND_URL=http://localhost:8000
```

If you only want dependency setup without starting services:

- Mac/Linux:
  ```bash
  ./scripts/setup_env.sh
  ```
- Windows:
  ```bat
  scripts\setup_env.bat
  ```

---

## Core API response shape (`POST /chat/`)

`/chat/` returns a structured Pydantic response with:
- `summary`
- `decision`
- `score`
- `risks`
- `suggested_next_action`
- `commands`
- `strategy`

Commands are machine-readable and include canonical action metadata for downstream factory systems.

---

## Run tests

```bash
pytest
```
