from typing import List, Dict
from evaluation.evaluator_interface import Evaluator


class ResponseEvaluator(Evaluator):
    """
    Evaluates LLM responses and flags potential issues.
    """

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

        # ==============================
        # 1️⃣ No Context Flag
        # ==============================
        if len(retrieved_chunks) == 0 and not any(
            phrase in answer_lower for phrase in self.REFUSAL_PHRASES
        ):
            flags.append("no_context")

        # ==============================
        # 2️⃣ Refusal Flag
        # ==============================
        if any(phrase in answer_lower for phrase in self.REFUSAL_PHRASES):
            flags.append("refusal")

        # ==============================
        # 3️⃣ Custom Domain Flag
        # Example: conflicting pricing information
        # ==============================
        if "price" in answer_lower or "pricing" in answer_lower:
            # If multiple sources retrieved and pricing mentioned
            if len(retrieved_chunks) > 1:
                flags.append("multiple_conflicting_sources")

        return flags