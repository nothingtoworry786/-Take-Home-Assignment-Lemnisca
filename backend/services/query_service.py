import time
import uuid
from typing import List, Dict

from models import (
    QueryRequest,
    QueryResponse,
    Metadata,
    TokenUsage,
    Source
)


class QueryService:
    """
    Orchestrates the full query flow:
    - Cache check
    - Routing
    - Retrieval (RAG)
    - LLM generation
    - Evaluation
    - Logging
    """

    def __init__(
        self,
        router,
        retriever,
        llm,
        evaluator,
        cache,
        logger
    ):
        self.router = router
        self.retriever = retriever
        self.llm = llm
        self.evaluator = evaluator
        self.cache = cache
        self.logger = logger

    def handle_query(self, request: QueryRequest) -> QueryResponse:

        start_time = time.time()

        question = request.question.strip()

        cached_response = self.cache.get(question)
        if cached_response:
            return cached_response


        classification, model_name = self.router.classify(question)


        retrieved_chunks: List[Dict] = self.retriever.retrieve(question)

        context = "\n\n".join(
            chunk["text"] for chunk in retrieved_chunks
        )


        answer, tokens_in, tokens_out = self.llm.generate(
            model=model_name,
            context=context,
            question=question,
            classification=classification
        )


        flags = self.evaluator.evaluate(answer, retrieved_chunks)
        evaluator_message = "Low confidence — please verify with support." if flags else None

        sources = [
            Source(
                document=chunk["document"],
                page=chunk["page"],
                relevance_score=chunk["relevance_score"]
            )
            for chunk in retrieved_chunks
        ]

        latency_ms = int((time.time() - start_time) * 1000)

        metadata = Metadata(
            model_used=model_name,
            classification=classification,
            tokens=TokenUsage(
                input_tokens=tokens_in,
                output_tokens=tokens_out
            ),
            latency_ms=latency_ms,
            chunks_retrieved=len(retrieved_chunks),
            evaluator_flags=flags,
            evaluator_message=evaluator_message
        )

        conversation_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:8]}"

        response = QueryResponse(
            answer=answer,
            metadata=metadata,
            sources=sources,
            conversation_id=conversation_id
        )

        self.cache.set(question, response)

        self.logger.log(
            query=question,
            classification=classification,
            model_used=model_name,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            latency_ms=latency_ms
        )

        return response