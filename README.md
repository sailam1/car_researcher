# Cardeko — Vehicle Research Platform

Research and shortlist 5–7 vehicles before you buy. Split UI: **UI Updater** (filters + cards) and **Chat Panel** (LLM-guided discovery).

## Stack

- **Frontend:** React + Vite + TypeScript
- **Backend:** FastAPI + LangGraph + LangChain tools + [OpenRouter](https://openrouter.ai/)
- **Data:** DuckDB over `cardata/cars_details.csv` and `cardata/feedbacks.csv`

## Prerequisites

- Python 3.11+
- Node.js 18+
- [OpenRouter](https://openrouter.ai/) API key (`OPENROUTER_API_KEY` in `backend/.env`)

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env
python scripts/generate_placeholders.py
uvicorn app.main:app --reload --port 4000
```

**Windows notes**

- Port **8000** is often blocked or in use (`WinError 10013`). Use **4000** (frontend proxy is set to `4000`).
- If DuckDB says the database file is **in use**, the server will **fall back to in-memory** data automatically (`DUCKDB_FALLBACK_MEMORY=true`). You can also end the old `python.exe` from Task Manager, or set `DUCKDB_IN_MEMORY=true` in `.env` to always avoid file locks.
- `generate_placeholders.py` does not need `PYTHONPATH`; it reads the CSV directly.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — API is proxied to `http://127.0.0.1:4000`.

**Production build** uses `frontend/.env.production`:

```bash
npm run build
```

API calls go to `https://car-researcher.onrender.com/api` (set `VITE_API_BASE_URL` in `.env.production` to change).

## Production deploy (Netlify + Render)

| Service | Host | Role |
|---------|------|------|
| **Render** | https://car-researcher.onrender.com | FastAPI API (`uvicorn`) |
| **Netlify** | your `*.netlify.app` URL | React static site (`frontend/dist`) |

### Render (API)

- **Root directory:** `backend`
- **Build:** `pip install -r requirements.txt`
- **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Env (required):** `OPENROUTER_API_KEY`, `DUCKDB_IN_MEMORY=true`
- **Env (CORS):** `CORS_ORIGINS=http://localhost:5173,https://YOUR-SITE.netlify.app`  
  Use your exact Netlify URL (and custom domain if any). Without this, the browser blocks API calls.

### Netlify (frontend)

- **Base directory:** `frontend`
- **Build:** `npm ci && npm run build` (or use `frontend/netlify.toml`)
- **Publish:** `dist`
- **Env:** `VITE_API_BASE_URL=https://car-researcher.onrender.com`

After deploy, open your Netlify site — Network tab should call `https://car-researcher.onrender.com/api/...`.

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/sessions` | Create session + welcome message |
| GET | `/api/sessions/{id}` | Restore session |
| POST | `/api/chat` | Send message |
| PATCH | `/api/sessions/{id}/filters` | Manual filter update |
| GET | `/api/compare?ids=` | Compare vehicles |
| GET | `/health` | Health check |
