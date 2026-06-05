"""应用配置：路径、分块参数、embedding 提供方。"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CHROMA_DIR = DATA_DIR / "chroma"
DB_PATH = DATA_DIR / "app.db"

COLLECTION_NAME = "literature"

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 80

TAGS = ["行为干预", "语言沟通", "社交训练", "家庭训练", "感觉统合", "综合指南"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # embedding: local | api
    embedding_provider: str = "local"
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_api_base: str = "https://api.openai.com/v1"
    embedding_api_key: str = ""
    embedding_api_model: str = "text-embedding-3-small"

    # LLM（OpenAI 兼容，默认 DeepSeek）
    llm_provider: str = "deepseek"
    llm_api_base: str = "https://api.deepseek.com"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_timeout: float = 120.0
    # 是否读取系统代理；Windows 下系统代理常导致 httpx SSL 连接失败，默认关闭
    llm_trust_env: bool = False
    llm_http_proxy: str = ""

    default_top_k: int = 4
    # Chroma 余弦距离上限（越小越相似；超过则视为不相关）
    retrieval_max_distance: float = 0.55

    # Tavily 网络补充检索
    tavily_api_key: str = ""
    web_search_max_results: int = 3

    cors_origins: str = "http://localhost:5173"


settings = Settings()


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
