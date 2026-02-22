import json
import logging
import time
import uuid
from typing import Dict, Iterator, List

from models import (
    QueryRequest,
    QueryResponse,
    Metadata,
    TokenUsage,
    Source
)


class QueryService:
    def __init__(
        self,
        router,
        retriever,
        llm,
        evaluator,
        cache,
        conversation_store,
        logger
    ):
        self.router = router
        self.retriever = retriever
        self.llm = llm
        self.evaluator = evaluator
        self.cache = cache
        self.conversation_store = conversation_store
        self.logger = logger

    def handle_query(self, request: QueryRequest) -> QueryResponse:

        start_time = time.time()

        question = request.question.strip()
        conversation_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:8]}"

        if not request.conversation_id:
            cached_response = self.cache.get(question)
            if cached_response:
                logging.getLogger(__name__).info("CACHE HIT query=%r", question[:80] + ("..." if len(question) > 80 else ""))
                return cached_response.model_copy(
                    update={"metadata": cached_response.metadata.model_copy(update={"cache_hit": True}), "conversation_id": conversation_id}
                )

        classification, model_name = self.router.classify(question)
        retrieved_chunks: List[Dict] = self.retriever.retrieve(question)
        context = "\n\n".join(chunk["text"] for chunk in retrieved_chunks)
        history = self.conversation_store.get(conversation_id) if request.conversation_id else None

        answer, tokens_in, tokens_out = self.llm.generate(
            model=model_name,
            context=context,
            question=question,
            classification=classification,
            history=history,
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
            evaluator_message=evaluator_message,
            cache_hit=False
        )

        self.conversation_store.append(conversation_id, "user", question)
        self.conversation_store.append(conversation_id, "assistant", answer)

        response = QueryResponse(
            answer=answer,
            metadata=metadata,
            sources=sources,
            conversation_id=conversation_id
        )

        if not request.conversation_id:
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

    def _yield_sse(self, obj: dict) -> str:
        return f"data: {json.dumps(obj)}\n\n"

    def handle_query_stream(self, request: QueryRequest) -> Iterator[str]:
        """
        Stream the answer as SSE events. Yields "data: {json}\n\n".
        Events: {"type": "chunk", "content": "..."}; {"type": "done", ...}; or {"type": "error", "message": "..."}.
        """
        start_time = time.time()
        question = request.question.strip()
        conversation_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:8]}"
        log = logging.getLogger(__name__)

        try:
            if not request.conversation_id:
                cached_response = self.cache.get(question)
                if cached_response:
                    log.info("CACHE HIT query=%r", question[:80] + ("..." if len(question) > 80 else ""))
                    meta = cached_response.metadata.model_copy(update={"cache_hit": True})
                    yield self._yield_sse({"type": "chunk", "content": cached_response.answer})
                    yield self._yield_sse({"type": "done", "metadata": meta.model_dump(), "sources": [s.model_dump() for s in cached_response.sources], "conversation_id": conversation_id})
                    return

            classification, model_name = self.router.classify(question)
            retrieved_chunks: List[Dict] = self.retriever.retrieve(question)
            context = "\n\n".join(chunk["text"] for chunk in retrieved_chunks)
            history = self.conversation_store.get(conversation_id) if request.conversation_id else None

            answer_parts: List[str] = []
            tokens_in, tokens_out = 0, 0
            for chunk_text, ti, to in self.llm.generate_stream(
                model=model_name,
                context=context,
                question=question,
                classification=classification,
                history=history,
            ):
                if chunk_text:
                    answer_parts.append(chunk_text)
                    yield self._yield_sse({"type": "chunk", "content": chunk_text})
                else:
                    tokens_in, tokens_out = ti, to

            answer = "".join(answer_parts)
            self.conversation_store.append(conversation_id, "user", question)
            self.conversation_store.append(conversation_id, "assistant", answer)
            flags = self.evaluator.evaluate(answer, retrieved_chunks)
            evaluator_message = "Low confidence — please verify with support." if flags else None
            sources = [
                Source(document=chunk["document"], page=chunk["page"], relevance_score=chunk["relevance_score"])
                for chunk in retrieved_chunks
            ]
            latency_ms = int((time.time() - start_time) * 1000)
            metadata = Metadata(
                model_used=model_name,
                classification=classification,
                tokens=TokenUsage(input_tokens=tokens_in, output_tokens=tokens_out),
                latency_ms=latency_ms,
                chunks_retrieved=len(retrieved_chunks),
                evaluator_flags=flags,
                evaluator_message=evaluator_message,
                cache_hit=False
            )
            if not request.conversation_id:
                self.cache.set(question, QueryResponse(answer=answer, metadata=metadata, sources=sources, conversation_id=conversation_id))
            self.logger.log(query=question, classification=classification, model_used=model_name, tokens_input=tokens_in, tokens_output=tokens_out, latency_ms=latency_ms)
            yield self._yield_sse({"type": "done", "metadata": metadata.model_dump(), "sources": [s.model_dump() for s in sources], "conversation_id": conversation_id})
        except Exception as e:
            log.exception("Stream error for query=%r", question[:80])
            yield self._yield_sse({"type": "error", "message": str(e)})