from typing import List, Optional
from pydantic import BaseModel

class QueryRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None

class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int

class Metadata(BaseModel):
    model_used: str
    classification: str
    tokens: TokenUsage
    latency_ms: int
    chunks_retrieved: int
    evaluator_flags: List[str]
    evaluator_message: Optional[str] = None  # e.g. "Low confidence — please verify with support." when flags set  

class Source(BaseModel):
    document: str
    page: Optional[int] = None
    relevance_score: Optional[float] = None


class QueryResponse(BaseModel):
    answer: str
    metadata: Metadata
    sources: List[Source]
    conversation_id: str