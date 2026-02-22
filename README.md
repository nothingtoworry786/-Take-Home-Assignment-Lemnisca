# ClearPath RAG Chatbot

A RAG-powered customer support chatbot for **Clearpath** (project management SaaS). It answers questions by retrieving from 30 PDF docs and generating responses with Groq LLMs, using a rule-based router and an output evaluator.

---

## Table of contents

- [Quick start](#quick-start)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Environment variables](#environment-variables)
- [Usage](#usage)
- [Groq models](#groq-models)
- [Testing](#testing)
- [Project structure](#project-structure)
- [Bonus challenges](#bonus-challenges)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Known limitations](#known-limitations)
- [References](#references)

---

## Quick start

From the **project root**:

```bash
# 1. Create .env in project root with GROQ_API_KEY=gsk_...
# 2. Backend
cd backend && pip install -r ../requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000

# 3. In another terminal: Frontend
cd frontend && pnpm install && pnpm dev
```

Open **http://localhost:3000** for the chat UI and **http://localhost:8000/docs** for the API.

---

## Prerequisites

| Requirement | Version / notes |
|-------------|-----------------|
| Python      | 3.10+ (backend) |
| Node.js     | 18+ (frontend)  |
| pnpm        | For frontend install/run |
| Groq API key| [Get one](https://console.groq.com) (free, no credit card) |

---

## Setup

### Backend

1. From the **project root**, create and activate a virtual environment (recommended):

   ```bash
   python -m venv venv
   # Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # macOS / Linux:
   source venv/bin/activate
   ```

2. Install dependencies and run the API:

   ```bash
   pip install -r requirements.txt
   cd backend
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

   The API will be at **http://localhost:8000**. Interactive docs: **http://localhost:8000/docs**.

### Frontend

In a **separate terminal** from the project root:

```bash
cd frontend
pnpm install
pnpm dev
```

The app will be at **http://localhost:3000**. It talks to the backend at `http://localhost:8000` by default. To use another API URL, set `NEXT_PUBLIC_API_URL` in `frontend/.env.local`.

---

## Environment variables

| Variable | Where | Required | Description |
|----------|--------|----------|-------------|
| `GROQ_API_KEY` | Project root `.env` or Render | Yes | Your [Groq](https://console.groq.com) API key. |
| `NEXT_PUBLIC_API_URL` | `frontend/.env.local` or Vercel | No | Backend URL (default: `http://localhost:8000`). Set to your Render URL in production. |
| `CORS_ORIGINS` | Backend env (e.g. Render) | No | Comma-separated list of allowed frontend origins (e.g. `https://your-app.vercel.app`). Localhost is allowed by default. |
| `PORT` | Backend env | No | Port for uvicorn (default: `8000`). Render sets this automatically. |

Create a `.env` file in the **project root** (same folder as `backend/` and `frontend/`):

```env
GROQ_API_KEY=gsk_your_key_here
```

---

## Usage

- **Chat UI:** Open http://localhost:3000 and type in the input. Responses stream by default. Use **New conversation** to start a fresh thread (conversation memory is kept per thread).
- **Non-streaming API:** `POST http://localhost:8000/query` with JSON body `{"question": "Your question", "conversation_id": "optional-id"}`.
- **Streaming API:** `POST http://localhost:8000/query/stream` with the same body for Server-Sent Events.

See [API_CONTRACT.md](API_CONTRACT.md) for the full request/response spec.

---

## Groq models

| Use case | Model |
|----------|--------|
| Simple (greetings, short lookups, yes/no) | `llama-3.1-8b-instant` |
| Complex (multi-step, reasoning, ambiguous) | `llama-3.3-70b-versatile` |

Routing is rule-based (keywords, query length, number of questions). Models are configured in `backend/config.py`.

---

## Testing

- **Manual testing:** See [TESTING.md](TESTING.md) for scenarios and how to check the router, evaluator, and cache.
- **Feature script:** From project root: `python scripts/test_features.py` (requires backend running).
- **Eval harness:** From project root (or from `backend/`: `python ../scripts/run_eval.py`):

  ```bash
  python scripts/run_eval.py
  python scripts/run_eval.py --output eval_report.md
  ```

  Backend must be running. Cases are defined in `scripts/eval_cases.json`.

---

## Project structure

```
.
├── clearpath_docs/       # 30 Clearpath PDF documents
├── backend/              # FastAPI app
│   ├── main.py           # App entry, routes
│   ├── config.py         # GROQ models, chunk size, TOP_K
│   ├── models.py         # Pydantic request/response models
│   ├── logger.py         # Routing decision logs (JSON)
│   ├── rag/              # Retrieval (FAISS, sentence-transformers, pypdf)
│   ├── routing/          # Rule-based simple/complex router
│   ├── llm/              # Groq LLM (generate + stream)
│   ├── evaluation/       # Response evaluator (no-context, refusal, domain checks)
│   └── services/         # Query orchestration, cache, conversation store
├── frontend/             # Next.js chat UI (streaming, conversation memory)
├── scripts/
│   ├── test_features.py  # Quick API smoke test
│   ├── eval_cases.json   # Eval harness test cases
│   └── run_eval.py       # Eval harness runner
├── API_CONTRACT.md       # API specification
├── TESTING.md            # Testing guide
├── requirements.txt      # Python dependencies
└── README.md
```

---

## Bonus challenges (optional)

These match the assignment’s optional bonus challenges. Which were attempted:

| Challenge | Description | Attempted | Where to find it |
|-----------|-------------|-----------|-------------------|
| **Conversation memory** | Chatbot maintains conversation memory across turns. | ✅ Yes | `backend/services/conversation_store.py` (in-memory, last 5 turns). History passed to LLM in `llm/groq_llm_service.py`. Cache skipped when `conversation_id` is present. Design and token tradeoff: see [written_answers.md § Bonus](written_answers.md#bonus---conversation-memory-and-streaming). |
| **Streaming** | Stream the response token-by-token. | ✅ Yes | `POST /query/stream` (SSE), `backend/llm/groq_llm_service.py` (`generate_stream`), frontend consumes in `frontend/app/page.tsx`. Where structured output parsing breaks: see [written_answers.md § Bonus](written_answers.md#bonus---conversation-memory-and-streaming). |
| **Eval harness** | Own test queries with expected answers; run system and report pass/fail. | ✅ Yes | `scripts/eval_cases.json` (cases), `scripts/run_eval.py` (runner). Run: `python scripts/run_eval.py` or `python scripts/run_eval.py --output eval_report.md`. |
| **Live deploy** | Deploy to a public URL (Vercel, Railway, GCP, AWS, etc.). | ✅ Planned | Backend → **Render**; frontend → **Vercel**. See [Deployment](#deployment) below. |

---

## Deployment

This project is set up to deploy **backend on Render** and **frontend on Vercel**.

### Backend on Render

1. **Create a Web Service** at [dashboard.render.com](https://dashboard.render.com). Connect your repo.
2. **Build & start (no blueprint):**
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Root directory:** leave blank (so `clearpath_docs/` and `backend/` are both in the build).
3. **Environment variables:**
   - `GROQ_API_KEY` — your Groq API key (required).
   - `CORS_ORIGINS` — your Vercel app URL so the browser can call the API, e.g. `https://your-app.vercel.app` (optional; add multiple origins comma-separated if needed).
4. Deploy. Note the backend URL (e.g. `https://clearpath-chatbot-api.onrender.com`).

**Or use the blueprint:** If your repo has `render.yaml` at the root, you can use Render’s Blueprint to create the service from it; then set `GROQ_API_KEY` and `CORS_ORIGINS` in the dashboard.

**Note:** On Render’s free tier the service may spin down after inactivity; the first request after that can be slow.

### Frontend on Vercel

1. **Import the project** at [vercel.com](https://vercel.com). Point it at your repo; set **Root Directory** to `frontend`.
2. **Environment variable:**
   - `NEXT_PUBLIC_API_URL` — your Render backend URL (e.g. `https://clearpath-chatbot-api.onrender.com`). No trailing slash.
3. Deploy. The app will call the backend at that URL.

**Build:** Vercel will run `pnpm build` (or `npm run build`) in the frontend root. No extra config needed if the repo has `frontend/package.json`.

### After both are live

- Open the Vercel app URL; the chat should use the Render API.
- If you see CORS errors, add the exact Vercel URL (including `https://`) to **CORS_ORIGINS** on the Render service and redeploy the backend.

---

## Troubleshooting

| Issue | What to try |
|-------|--------------|
| `GROQ_API_KEY is not set` | Locally: create a `.env` in the **project root** with `GROQ_API_KEY=gsk_...`. On Render: add `GROQ_API_KEY` in the service **Environment**. |
| `can't open file '...scripts/run_eval.py'` | Run from the project root: `python scripts/run_eval.py`, or from `backend/`: `python ../scripts/run_eval.py`. |
| Connection refused to backend | Start the backend first (`cd backend && uvicorn main:app --host 0.0.0.0 --port 8000`). |
| CORS errors in browser | Backend allows `http://localhost:3000` and `http://127.0.0.1:3000`; if using another origin, add it in `backend/main.py` CORS config or set `CORS_ORIGINS` (e.g. on Render). |
| **Render: “No open ports detected”** | Set **Root directory** to `backend`, **Start command** to `python main.py`, and add **GROQ_API_KEY** in Environment. If the key is missing, the app exits before binding to a port. |
| Routing logs not found | Ensure `backend/logs/` exists; the logger creates it on first write. |

---

## Known limitations

- **Conversation history** is in-memory only and is lost on backend restart.
- **Cache** is in-memory and unbounded.
- **Routing logs** are written to `backend/logs/routing_logs.json`.
- **Eval harness** uses the non-streaming `POST /query` endpoint.

---

## References

- [API_CONTRACT.md](API_CONTRACT.md) — Request/response format and field specs.
- [TESTING.md](TESTING.md) — How to test router, evaluator, cache, and streaming.
- [Written answers](written_answers.md) — Assignment Q1–Q4 (add when ready).
- Assignment brief: [Google Doc](https://docs.google.com/document/d/1vuc5E7j6zm1xrs1JvUGhW93cNbmL9gp2/edit) (if applicable).
