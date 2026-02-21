from abc import ABC, abstractmethod
from typing import List, Dict


class Evaluator(ABC):
    @abstractmethod
    def evaluate(
        self,
        answer: str,
        retrieved_chunks: List[Dict]
    ) -> List[str]:
        pass
