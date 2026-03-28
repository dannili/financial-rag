from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    openai_api_key: str
    database_url: str = "postgresql://rag:rag@postgres:5432/rag"
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    chunk_size: int = 512
    chunk_overlap: int = 64
    retrieval_top_k: int = 5

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
