"""Tavily 网络补充检索（方案 B）。"""

import logging
from typing import Any

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

TAVILY_URL = "https://api.tavily.com/search"


def search_web(query: str, *, max_results: int | None = None) -> list[dict[str, Any]]:
    """
    调用 Tavily 搜索，返回统一结构。
    无 Key 或请求失败时返回 []，不抛异常。
    """
    if not settings.tavily_api_key:
        logger.info("TAVILY_API_KEY 未配置，跳过网络检索")
        return []

    limit = max_results or settings.web_search_max_results
    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "max_results": limit,
        "search_depth": "basic",
    }

    try:
        with httpx.Client(timeout=30, trust_env=False) as client:
            resp = client.post(TAVILY_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("Tavily 搜索失败: %s", exc)
        return []

    hits: list[dict[str, Any]] = []
    for i, item in enumerate(data.get("results") or [], start=1):
        title = str(item.get("title") or "未知标题").strip()
        url = str(item.get("url") or "").strip()
        snippet = str(item.get("content") or item.get("snippet") or "").strip()
        if not snippet and not title:
            continue
        hits.append(
            {
                "id": f"W{i}",
                "title": title,
                "url": url,
                "snippet": snippet[:800],
            }
        )
    return hits
