from abc import ABC, abstractmethod
from typing import Iterator, List, Tuple


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
        classification: str = "simple",
        history: List[dict] | None = None,
    ) -> Tuple[str, int, int]:
        pass

    def generate_stream(
        self,
        model: str,
        context: str,
        question: str,
        classification: str = "simple",
        history: List[dict] | None = None,
    ) -> Iterator[Tuple[str, int, int]]:
        """
        Stream text chunks. Yields (chunk, 0, 0) for each delta; final yield is ("", input_tokens, output_tokens).
        Default implementation falls back to generate() and yields once.
        """
        full_answer, tokens_in, tokens_out = self.generate(
            model=model,
            context=context,
            question=question,
            classification=classification,
            history=history,
        )
        if full_answer:
            yield full_answer, 0, 0
        yield "", tokens_in, tokens_out
