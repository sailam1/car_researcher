# Carsresearcher

Carsresearcher is a vehicle research assistant: users chat about what they need, the system narrows a catalog of 12k+ vehicles, and the UI shows a live shortlist (target **5–7** cars) with filters, specs, and owner-feedback highlights.


**what is this tool?**
a research platform through chat where user chats in the right chat panel and simultaniously, AI shortlists the vehicles as per the conversation. asks, answers, understands, searchs, aggrigates, does various level calculations to get right and correct response to the user.


**why build a tool in this way**

- if a user has no understanding/little understanding/clear understanding, tool can pick up the user intent and shortlist right from their.
- if initial two types of users are using platform, the ai starts with vague queries or very broad intent queries.
- user can initiate very vaguely and AI still understand what it need to do
- good for going from "I don't know what to buy" -> "yup, i am clear why i shortlisted these"


$${\color{red}Note: }$$ :backend or api takes ~1 min to load. please wait


**Live split deploy (typical):**

- Frontend: [Netlify](https://carsresearcher.netlify.app) — React/Vite
- API: [Render](https://car-researcher.onrender.com) — FastAPI + LangGraph
- LLM:
    1. deployed tool uses: openrouter
    2. development/ localhost uses: ollama+langchain

---


### Deliberately cut

1. data source research: 
    - for research,accurate and prod purposes, would have used teambhp data for getting user feedbacks. 
    - vehicle dataset from cardekho or some api services to get all releavent information.
    - current dataset lacks, price data of the vehicles & variants
    - data-source is crucial to get proper and accurate ai responses in this tool.

2. micro-web search agent:
    - if some information about vehicle or variant is not available, web serach engine would have done great job.
3. accuracy of responses of each agent. fine-tunning each and every agent prompt to stop agent-leakage problem
4. architecture has "why recommendation agent" , not fully used in current tool.
5. better UX: what is rendered, how it is rendered, wy it is rendered.
    - helps in keeping user onboard and engaged
    - to assist user on getting all understanding at single glance.
6. pushing data sources to prod like sql-server.

---

## Tech stack (and why)

| Layer | Choice | Why |
|-------|--------|-----|
| **UI** | React 19, TypeScript, Vite, Zustand, React Router | Fast dev server, proxy to API locally, minimal state for session + UI payload |
| **API** | FastAPI, Pydantic v2, SSE streaming | Typed contracts, easy `StreamingResponse`, good fit for agent steps + `ui_update` events |
| **Orchestration** | LangGraph (`StateGraph`) | Clear branches: `general_qa` vs discovery subgraph (preference → search → question or finalize) |
| **LLM** | OpenRouter (`qwen3-8b` chat, `qwen3-coder-next` fast/structured) | No local GPU; one API key; cheap/fast models for router and SQL |
| **Data** | DuckDB + pandas ingest of `cardata/*.csv` | Analytical queries and true `COUNT(*)` on filters; in-memory mode avoids Windows file locks with `--reload` |
| **Sessions** | SQLite (`sessions.db`) | Persist messages, filters, vehicles, discovery phase across refreshes |
| **Observability** | Per-session JSONL under `backend/runtime/session_logs/` | Debug agent I/O without a full tracing product |

---


## What did you delegate to AI tools vs. do manually?
1. built complete architecture from scratch
2. first commit development delegated to AI tool
3. promblem statement -> solution ideation, done from scratch
4. deployment done manually
5. took ai assistance to do research

## Where did the tools help most? 
1. developing initial framework done pretty well with tools.
2. research assistance and loop holes detection done well with chatgpt.

## Where did they get in the way?
1. confusion between agents due to inaccurate prompts in terms of input and response format.
2. inaccurate use of tools by agents or the way they deduce which agent should access which tools and how.
3. incorrect way of building or developing tools.
4. logical misinterpretation of framework's working.


## If you had another 4 hours, what would you add?
1. delebrately missed points
2. architecture improvement to consider more user scope
3. agent prompt fixing to get correct and accurate reponse
4. modification in UI state builder logic to handle responses correctly.
5. standard query format for each specific type of query (ex: options, radio buttons,slider, range-bar)
6. correct implementation of "why recommendation"
7. improved chatflow to cover vague to precise: user-queries, ai-queries and responses. (importent upgrade)
8. improved response time when using agent framework by tool
9. cards rendering:
    - does not contain (why this vehicle was shortlisted?)
    - how much implementation as per user requirements is statisfied
10. vehicle reviews data (drastically improves tool satisfaction index):
    - for each review extracting categorical rating (ex: seat comfert, driving comfert, maintainance, insurace, etc..). for each category how much user is statisfied.
    - single summary for each vehicle variant, vehicle category & maker
    - aggrigated categorical reviews system at vehicle variant level & maker level.


## Local development

### Prerequisites

- Python 3.12+, Node 20+
- OpenRouter API key: https://openrouter.ai/keys
- Data: `cardata/cars_details.csv`, `cardata/feedbacks.csv` (repo-relative to `backend`)

### Backend

```cmd
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
.env setup
uvicorn app.main:app --reload --port 4000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` → `http://127.0.0.1:4000`. Open http://localhost:5173.

### Production env

| Where | Variable | Purpose |
|-------|----------|---------|
| Render | `OPENROUTER_API_KEY` | LLM calls |
| Netlify | `VITE_API_BASE_URL` | e.g. `https://car-researcher.onrender.com` |

---

