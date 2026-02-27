from typing import List, Dict
from evaluation.evaluator_interface import Evaluator

class ResponseEvaluator(Evaluator):
    """
    Evaluates LLM responses and flags potential issues.
    """

    # Minimum relevance score; if all chunks are below this, treat as no useful context
    LOW_RELEVANCE_THRESHOLD = 0.35
    REFUSAL_PHRASES = [
        "i cannot",
        "i don't know",
        "i do not know",
        "not mentioned",
        "cannot find",
        "not available in the documentation"
    ]

    def evaluate(
        self,
        answer: str,
        retrieved_chunks: List[Dict]
    ) -> List[str]:

        flags = []
        answer_lower = answer.lower()

        if len(retrieved_chunks) == 0 and not any(
            phrase in answer_lower for phrase in self.REFUSAL_PHRASES
        ):
            flags.append("no_context")
        elif len(retrieved_chunks) > 0:
            scores = [
                c.get("relevance_score", 0)
                for c in retrieved_chunks
            ]
            if all(s < self.LOW_RELEVANCE_THRESHOLD for s in scores) and not any(
                phrase in answer_lower for phrase in self.REFUSAL_PHRASES
            ):
                flags.append("no_context")
        if any(phrase in answer_lower for phrase in self.REFUSAL_PHRASES):
            flags.append("refusal")
        if "price" in answer_lower or "pricing" in answer_lower:
            distinct_docs = {c.get("document") for c in retrieved_chunks if c.get("document")}
            if len(distinct_docs) > 1:
                flags.append("multiple_conflicting_sources")
        return flags