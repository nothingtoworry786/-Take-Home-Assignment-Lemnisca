from typing import Optional
from models import QueryResponse


class CacheService:
    """
    Simple in-memory cache.
    Key: normalized question string
    Value: full QueryResponse object
    """

    def __init__(self):
        self._cache = {}

    def _normalize(self, question: str) -> str:
        """
        Normalize question to avoid duplicate cache misses
        caused by casing or spacing differences.
        """
        return question.strip().lower()

    def get(self, question: str) -> Optional[QueryResponse]:
        key = self._normalize(question)
        return self._cache.get(key)

    def set(self, question: str, response: QueryResponse) -> None:
        key = self._normalize(question)
        self._cache[key] = response