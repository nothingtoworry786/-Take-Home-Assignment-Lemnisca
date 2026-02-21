from abc import abstractmethod ,ABC
from typing import Tuple

class Router(ABC):
    @abstractmethod
    def classify(self, query:str) -> Tuple[str, str]:
        pass