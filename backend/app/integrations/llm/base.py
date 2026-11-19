from abc import ABC, abstractmethod

class BaseLLMClient(ABC):
    def __init__(self, model: str):
        self._model = model

    @property
    def model(self) -> str:
        """LLM model"""
        return self._model

    @abstractmethod
    def chat(self, message: str, system_prompt: str | None = None) -> str:
        pass