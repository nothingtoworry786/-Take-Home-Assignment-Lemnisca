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
| `GROQ_API_KEY` | Project root `.env` | Yes | Your [Groq](https://console.groq.com) API key. |
| `NEXT_PUBLIC_API_URL` | `frontend/.env.local` | No | Backend URL (default: `http://localhost:8000`). |
| `PORT` | Backend env | No | Port for uvicorn (default: `8000`). |

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

## Bonus challenges

| Challenge | Status | Notes |
|-----------|--------|--------|
| **Conversation memory** | ✅ Done | In-memory store per `conversation_id`; last 5 turns sent to the LLM. Cache skipped when continuing a conversation. |
| **Streaming** | ✅ Done | `POST /query/stream` returns SSE; UI consumes chunks and shows metadata in a final event. |
| **Eval harness** | ✅ Done | `scripts/eval_cases.json` + `scripts/run_eval.py`; optional `--output` for a markdown report. |
| **Live deploy** | ❌ Not done | Not deployed to a public URL. |

---

## Deployment

- **Backend:** Run `uvicorn main:app --host 0.0.0.0 --port $PORT` (e.g. Railway, Render, or a cloud VM). Set `GROQ_API_KEY` in the environment. Ensure the `clearpath_docs/` folder (or equivalent path) is available; the docs path is set in `backend/main.py`.
- **Frontend:** Run `pnpm build` and serve the output (e.g. Vercel, or static hosting). Set `NEXT_PUBLIC_API_URL` to the public backend URL so the client can reach the API.

---

## Troubleshooting

| Issue | What to try |
|-------|--------------|
| `GROQ_API_KEY is not set` | Create a `.env` file in the **project root** with `GROQ_API_KEY=gsk_...`. |
| `can't open file '...scripts/run_eval.py'` | Run from the project root: `python scripts/run_eval.py`, or from `backend/`: `python ../scripts/run_eval.py`. |
| Connection refused to backend | Start the backend first (`cd backend && uvicorn main:app --host 0.0.0.0 --port 8000`). |
| CORS errors in browser | Backend allows `http://localhost:3000` and `http://127.0.0.1:3000`; if using another origin, add it in `backend/main.py` CORS config. |
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
