from __future__ import annotations
import json
from typing import Generator
from django.conf import settings


class LLMProvider:
    def chat_stream(self, messages: list[dict]) -> Generator[str, None, None]:
        raise NotImplementedError

    def chat(self, messages: list[dict]) -> str:
        return "".join(self.chat_stream(messages))


class GroqProvider(LLMProvider):
    def __init__(self):
        from groq import Groq
        self._client = Groq(api_key=settings.GROQ_API_KEY)
        self._model = settings.GROQ_MODEL

    def chat_stream(self, messages: list[dict]) -> Generator[str, None, None]:
        stream = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=True,
            max_tokens=1024,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


class OllamaProvider(LLMProvider):
    def __init__(self):
        import requests
        self._requests = requests
        self._base_url = settings.OLLAMA_BASE_URL
        self._model = settings.OLLAMA_MODEL

    def chat_stream(self, messages: list[dict]) -> Generator[str, None, None]:
        resp = self._requests.post(
            f"{self._base_url}/api/chat",
            json={"model": self._model, "messages": messages, "stream": True},
            stream=True,
            timeout=60,
        )
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                data = json.loads(line)
                content = data.get("message", {}).get("content", "")
                if content:
                    yield content
                if data.get("done"):
                    break


def get_provider() -> LLMProvider:
    provider = getattr(settings, "LLM_PROVIDER", "groq")
    if provider == "ollama":
        return OllamaProvider()
    return GroqProvider()
