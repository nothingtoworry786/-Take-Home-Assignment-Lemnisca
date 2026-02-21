from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

class QueryRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None

class TokenUsage(BaseModel):
    model_config = ConfigDict(serialize_by_alias=True)
    input_tokens: int = Field(serialization_alias="input")
    output_tokens: int = Field(serialization_alias="output")

class Metadata(BaseModel):
    model_used: str
    classification: str
    tokens: TokenUsage
    latency_ms: int
    chunks_retrieved: int
    evaluator_flags: List[str]
    evaluator_message: Optional[str] = None  # e.g. "Low confidence — please verify with support." when flags set
    cache_hit: bool = False  

class Source(BaseModel):
    document: str
    page: Optional[int] = None
    relevance_score: Optional[float] = None


class QueryResponse(BaseModel):
    answer: str
    metadata: Metadata
    sources: List[Source]
    conversation_id: str