from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DATABASE_URL: str = "sqlite:///./ai_panel_studio.db"
    MOCK_LLM: str = "false"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
