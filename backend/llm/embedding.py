"""Embedding 客户端：支持本地 sentence-transformers 与 OpenAI 兼容 API。"""

from functools import lru_cache

from backend.config import settings


class EmbeddingClient:
    def __init__(self) -> None:
        self.provider = settings.embedding_provider.lower()
        self._local_model = None

    def _ensure_local(self):
        if self._local_model is None:
            from fastembed import TextEmbedding

            self._local_model = TextEmbedding(model_name=settings.embedding_model)
        return self._local_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.provider == "api":
            return self._embed_api(texts)
        return self._embed_local(texts)

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        model = self._ensure_local()
        return [vec.tolist() for vec in model.embed(texts)]

    def _embed_api(self, texts: list[str]) -> list[list[float]]:
        if not settings.embedding_api_key:
            raise RuntimeError("EMBEDDING_API_KEY 未配置，无法使用 API embedding")

        import httpx
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_api_base.rstrip("/"),
            http_client=httpx.Client(timeout=60, trust_env=False),
        )
        resp = client.embeddings.create(model=settings.embedding_api_model, input=texts)
        return [item.embedding for item in resp.data]


@lru_cache
def get_embedding_client() -> EmbeddingClient:
    return EmbeddingClient()
