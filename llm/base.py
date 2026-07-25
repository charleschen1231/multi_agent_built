from abc import ABC, abstractmethod

class BaseLLM(ABC):
    @abstractmethod
    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        pass