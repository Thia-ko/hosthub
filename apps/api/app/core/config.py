from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://hosthub:hosthub@db:5432/hosthub"
    JWT_SECRET: str = "change-me"
    COOKIE_SECURE: bool = True

    SEED_ADMIN_EMAIL: str = "admin@hosthub.local"
    SEED_ADMIN_PASSWORD: str = "change-me"

    AI_ASSIST_API_KEY: str = ""
    AI_ASSIST_BASE_URL: str = "https://api.openai.com/v1"
    AI_ASSIST_MODEL: str = "gpt-4o-mini"
    AI_ASSIST_TRANSCRIBE_MODEL: str = "whisper-1"
    AI_ASSIST_DAILY_TOKEN_LIMIT_DEFAULT: int = 50000
    DEMO_DAILY_TOKEN_LIMIT: int = 20000
    DEMO_REPLY_MAX_TOKENS: int = 220

    EVOLUTION_API_BASE_URL: str = ""
    EVOLUTION_API_KEY: str = ""

    WHATSBOTMAIS_API_BASE_URL: str = "https://api2.whatsbotmais.com.br"

    META_CLOUD_API_VERSION: str = "v23.0"

    TURNSTILE_SECRET_KEY: str = ""
    CF_ACCESS_TEAM_DOMAIN: str = ""


settings = Settings()
