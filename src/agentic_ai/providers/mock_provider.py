"""Offline provider implementing the existing protocol; never makes network calls."""


class DeterministicMockProvider:
    def generate(self, *, system: str, user: str) -> str:
        return "MOCK_ONLY: no LLM call or agent action was executed."
