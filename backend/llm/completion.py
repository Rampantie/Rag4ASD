"""LLM 聊天客户端：OpenAI 兼容接口（DeepSeek 等）。"""

from functools import lru_cache
from typing import Any

import httpx

from backend.config import settings


def _build_http_client() -> httpx.Client:
    kwargs: dict[str, Any] = {
        "timeout": settings.llm_timeout,
        "trust_env": settings.llm_trust_env,
    }
    if settings.llm_http_proxy:
        kwargs["proxy"] = settings.llm_http_proxy
    return httpx.Client(**kwargs)


class ChatClient:
    def __init__(self) -> None:
        if not settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY 未配置，请在 .env 中设置")

        from openai import OpenAI

        self._http = _build_http_client()
        self._client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_api_base.rstrip("/"),
            http_client=self._http,
        )
        self.default_model = settings.llm_model

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        response_format: dict[str, str] | None = None,
        temperature: float = 0.3,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            kwargs["response_format"] = response_format

        try:
            resp = self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            hint = ""
            if "Connection error" in str(exc) or "ConnectError" in type(exc).__name__:
                hint = "（提示：若使用代理，可在 .env 设置 LLM_HTTP_PROXY；或确认 LLM_TRUST_ENV 配置）"
            raise RuntimeError(f"无法连接 LLM 服务{hint}: {exc}") from exc

        content = resp.choices[0].message.content
        if not content:
            raise RuntimeError("LLM 返回空内容")
        return content


@lru_cache
def get_chat_client() -> ChatClient:
    return ChatClient()
