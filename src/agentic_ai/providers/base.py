from typing import Protocol

class LLMProvider(Protocol):
    def generate(self, *, system: str, user: str) -> str: ...
