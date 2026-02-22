from pathlib import Path


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from models import QueryRequest, QueryResponse
from config import Config

# Project root (parent of backend/) — docs path works no matter where you run from
DOCS_PATH = Path(__file__).resolve().parent.parent / "clearpath_docs"

# Services
from services.cache_service import CacheService
from services.conversation_store import ConversationStore
from services.query_service import QueryService

# Router
from routing.RuleBasedRouter import RuleBasedRouter

# RAG
from rag.retrieval_service import RetrievalService

# LLM
from llm.groq_llm_service import GroqLLMService

# Evaluator
from evaluation.response_evaluator import ResponseEvaluator

# Logger
from logger import RoutingLogger


# ==============================
# FastAPI App
# ==============================

app = FastAPI(title="ClearPath Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "https://take-home-assignment-lemnisca.vercel.app"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ==============================
# Dependency Wiring
# ==============================

if not Config.GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY is not set. Add it to .env in the project root, e.g. GROQ_API_KEY=gsk_..."
    )

cache_service = CacheService()
conversation_store = ConversationStore()
router = RuleBasedRouter()
retriever = RetrievalService(docs_path=str(DOCS_PATH))
llm_service = GroqLLMService(api_key=Config.GROQ_API_KEY)
evaluator = ResponseEvaluator()
logger = RoutingLogger()

query_service = QueryService(
    router=router,
    retriever=retriever,
    llm=llm_service,
    evaluator=evaluator,
    cache=cache_service,
    conversation_store=conversation_store,
    logger=logger,
)


# ==============================
# API Endpoint
# ==============================

@app.post("/query", response_model=QueryResponse)
def query_endpoint(request: QueryRequest):
    return query_service.handle_query(request)


@app.post("/query/stream")
def query_stream_endpoint(request: QueryRequest):
    return StreamingResponse(
        query_service.handle_query_stream(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
@app.get("/health")
def health_endpoint():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=Config.PORT,
        reload=False,
    )