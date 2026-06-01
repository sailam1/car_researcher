@echo off
REM Cardeko backend — requires backend\.env with OPENROUTER_API_KEY
cd /d "%~dp0"
set DUCKDB_IN_MEMORY=true
if not exist .env (
  echo ERROR: Missing backend\.env — copy .env.example and set OPENROUTER_API_KEY
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
echo DuckDB: in-memory ^| LLM: OpenRouter
uvicorn app.main:app --reload --port 4000
