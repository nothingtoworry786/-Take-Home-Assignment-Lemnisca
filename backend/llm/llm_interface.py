from abc import ABC, abstractmethod
from typing import Tuple


class LLMService(ABC):
    """
    Abstract base class for LLM providers.
    """

    @abstractmethod
    def generate(
        self,
        model: str,
        context: str,
        question: str,
        classification: str = "simple"
    ) -> Tuple[str, int, int]:
        pass
    