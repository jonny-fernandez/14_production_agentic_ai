from openai import OpenAI

class OpenAIProvider:
    def __init__(self, client: OpenAI | None = None) -> None:
        self.client = client or OpenAI()

    def generate(self, *, system: str, user: str) -> str:
        raise NotImplementedError(
            "Implement only after deterministic routing/tool contracts and offline tests are validated."
        )
