from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel, Field


class RewriteError(Exception):
    pass


class RewriteParams(BaseModel):
    tone: str = Field(default="neutral", description="neutral | formal | casual | engaging")
    length: str = Field(default="similar", description="shorter | similar | longer")
    language: str = Field(default="ru")
    style_notes: str | None = None


class RewriteResult(BaseModel):
    rewritten_text: str
    summary: str
    raw_response: dict[str, Any] | None = None


def _build_prompt(title: str, text: str, params: RewriteParams) -> str:
    return (
        "Ты редактор новостного издания. Перепиши статью своими словами, "
        "сохраняя факты и смысл, но избегая прямого заимствования формулировок.\n\n"
        f"Тон: {params.tone}\n"
        f"Длина: {params.length}\n"
        f"Язык: {params.language}\n"
        + (f"Дополнительные указания: {params.style_notes}\n" if params.style_notes else "")
        + "\n"
        "Верни строго JSON без markdown-обёртки в формате:\n"
        '{"rewritten_text": "...", "summary": "1-2 предложения краткого содержания"}\n\n'
        f"Заголовок: {title}\n\n"
        f"Текст:\n{text}"
    )


class LLMProvider(ABC):
    @abstractmethod
    async def rewrite(self, title: str, text: str, params: RewriteParams) -> RewriteResult: ...

    @abstractmethod
    async def close(self) -> None: ...


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, timeout: float = 60.0):
        self.api_key = api_key
        self.model = model
        self._client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def rewrite(self, title: str, text: str, params: RewriteParams) -> RewriteResult:
        if not self.api_key:
            raise RewriteError("OpenAI API ключ не задан")

        prompt = _build_prompt(title, text, params)
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
        }
        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RewriteError(f"OpenAI API error: {exc}") from exc

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return _parse_llm_json(content, raw=data)


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, timeout: float = 60.0):
        self.api_key = api_key
        self.model = model
        self._client = httpx.AsyncClient(
            base_url="https://api.anthropic.com/v1",
            timeout=timeout,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def rewrite(self, title: str, text: str, params: RewriteParams) -> RewriteResult:
        if not self.api_key:
            raise RewriteError("Anthropic API ключ не задан")

        prompt = _build_prompt(title, text, params)
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        try:
            response = await self._client.post("/messages", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RewriteError(f"Anthropic API error: {exc}") from exc

        data = response.json()
        content = data["content"][0]["text"]
        return _parse_llm_json(content, raw=data)


def _parse_llm_json(content: str, raw: dict[str, Any]) -> RewriteResult:
    import json

    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RewriteError(f"LLM вернул невалидный JSON: {content[:200]}") from exc

    if "rewritten_text" not in parsed or "summary" not in parsed:
        raise RewriteError(f"В ответе LLM нет нужных полей: {parsed}")

    return RewriteResult(
        rewritten_text=parsed["rewritten_text"],
        summary=parsed["summary"],
        raw_response=raw,
    )


def build_llm_provider(provider: str, api_key: str, model: str) -> LLMProvider:
    if provider == "openai":
        return OpenAIProvider(api_key, model)
    if provider == "anthropic":
        return AnthropicProvider(api_key, model)
    raise RewriteError(f"Неизвестный LLM-провайдер: {provider}")
