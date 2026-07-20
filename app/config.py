from pathlib import Path

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore",
    )

    openai_api_key: str = Field(alias="OPENAI_API_KEY")

    model_provider: str = Field(default="openai", alias="MODEL_PROVIDER")

    llm_model: str = Field(
        default="gpt-4.1-mini",
        alias="LLM_MODEL",
    )

    embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="EMBEDDING_MODEL",
    )

    top_k: int = Field(default=3, alias="TOP_K")

    max_tool_calls: int = Field(default=8, alias="MAX_TOOL_CALLS")

    data_dir: str = Field(
        default=str(BASE_DIR / "data"),
        alias="DATA_DIR",
    )

    storage_dir: str = Field(
        default=str(BASE_DIR / "storage"),
        alias="STORAGE_DIR",
    )

    reports_dir: str = Field(
        default=str(BASE_DIR / "reports"),
        alias="REPORTS_DIR",
    )


def _load_config() -> Config:
    try:
        return Config()
    except ValidationError as exc:
        missing = {error["loc"][0] for error in exc.errors() if error["type"] == "missing"}
        if "OPENAI_API_KEY" in missing:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and add your "
                "OpenAI API key before running the application."
            ) from exc
        raise


config = _load_config()