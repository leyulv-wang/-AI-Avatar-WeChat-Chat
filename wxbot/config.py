from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    wxbot_host: str = "0.0.0.0"
    wxbot_port: int = 8000

    wxbot_data_dir: str = "data"
    wxbot_secrets_dir: str = "secrets"
    wxbot_backup_dir: str = "backups"

    wxbot_master_key: str | None = None

    wxbot_storage_encryption: str = "on"

    wxbot_context_messages: int = 20
    wxbot_candidate_count: int = 4
    wxbot_reply_timeout_sec: int = 5

    wxbot_cache_max_messages: int = 200

    wxbot_llm_provider: str = "ollama"
    wxbot_ollama_base_url: str = "http://localhost:11434"
    wxbot_ollama_model: str = "llama3"

    wxbot_llm_base_url: str | None = None
    wxbot_llm_api_key: str | None = None
    wxbot_llm_model: str | None = None
    wxbot_llm_chat_completions_path: str | None = None

    weflow_base_url: str | None = None
    weflow_token: str | None = None
    weflow_sse_path: str | None = None
    weflow_messages_path: str | None = None
    weflow_send_path: str | None = None

    @field_validator(
        "wxbot_llm_base_url",
        "wxbot_llm_chat_completions_path",
        "weflow_base_url",
        "weflow_sse_path",
        "weflow_messages_path",
        "weflow_send_path",
        mode="before",
    )
    @classmethod
    def _sanitize_text(cls, v):
        if v is None:
            return None
        if not isinstance(v, str):
            return v
        s = v.strip()
        if len(s) >= 2 and ((s[0] == s[-1] and s[0] in ('"', "'", "`"))):
            s = s[1:-1].strip()
        return s


def get_settings() -> Settings:
    return Settings()
