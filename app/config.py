from functools import lru_cache
import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Environment
    ENV: str = "development"
    
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "FastAPI Backend"
    
    # Database settings
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_SERVER: str = "db"  # 'db' for Docker, 'localhost' for local dev
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "app_db"
    
    # JWT settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Cloudinary settings
    CLOUDINARY_CLOUD_NAME: str = "sigma-firework"
    CLOUDINARY_API_KEY: str = "289391612899492"
    CLOUDINARY_API_SECRET: str = "BVKP5iDjqZa_HFoUB2zyEnTcZTA"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    class Config:
        env_file = f".env.{os.environ.get('ENV', 'development')}"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Singleton pattern for settings"""
    return Settings()