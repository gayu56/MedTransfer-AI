from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_secret_key: str = "dev-secret-key-change-in-production"

    database_url: str = "sqlite+aiosqlite:///./iptc.db"  # Override with DATABASE_URL env var for PostgreSQL

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment_name: str = "gpt-4"
    azure_openai_api_version: str = "2024-06-01"

    # OpenRouter (free models — no billing required)
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct:free"
    openrouter_tool_model: str = "meta-llama/llama-3.1-8b-instruct:free"

    # LLM timeout in seconds (falls back to template/deterministic if exceeded)
    llm_timeout_sbar: int = 30
    llm_timeout_call_sim: int = 30
    llm_timeout_specialty: int = 15

    # Standard OpenAI fallback
    openai_api_key: str = ""

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
