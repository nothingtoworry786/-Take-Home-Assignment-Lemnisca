from typing import Tuple
from .router_interface import Router
from config import Config


class RuleBasedRouter(Router):
    SIMPLE_KEYWORDS = [
        "hi",
        "hello",
        "hey",
        "thanks",
        "thank you",
        "what is",
        "how many",
        "when is",
        "where is",
        "price",
        "pricing"
    ]
    COMPLEX_KEYWORDS = [
        "explain",
        "compare",
        "difference",
        "why",
        "how does",
        "how do i",
        "issue",
        "error",
        "problem",
        "not working",
        "doesn't work",
        "don't work",
        "failed",
        "multi-step",
        "step by step",
        "walk me through",
        "complaint",
        "unable to",
        "can't",
        "cannot get",
    ]
    
    def classify(self, query: str) -> Tuple[str, str]:
        query_clean = query.strip().lower()
        word_count = len(query_clean.split())
        question_marks = query_clean.count("?")

        # Complex rules first (multi-question, long, or complex keywords → big model)
        if question_marks > 1:
            return "complex", Config.BIG_MODEL
        if word_count > 20:
            return "complex", Config.BIG_MODEL
        if any(keyword in query_clean for keyword in self.COMPLEX_KEYWORDS):
            return "complex", Config.BIG_MODEL

        # Simple rules (short, greetings, basic lookup → small model)
        if word_count <= 8:
            return "simple", Config.SMALL_MODEL
        if any(keyword in query_clean for keyword in self.SIMPLE_KEYWORDS):
            return "simple", Config.SMALL_MODEL

        return "simple", Config.SMALL_MODEL