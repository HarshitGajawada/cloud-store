"""
Configuration module for loading and validating environment variables
"""

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    database_url: str
    
    # JWT Authentication
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    
    # MinIO Configuration
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_secure: bool = False
    
    # AWS S3 Configuration
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-1"
    s3_bucket: str
    
    # Sync Job Configuration
    sync_batch_size: int = 10
    delete_from_minio_after_sync: bool = False
    sync_log_file: str = "/var/log/hybrid-storage/sync.log"
    
    # File Upload Configuration
    max_file_size_mb: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    """
    Get application settings
    
    Raises:
        ValidationError: If required configuration is missing
    """
    try:
        return Settings()
    except Exception as e:
        raise RuntimeError(f"Configuration error: {str(e)}. Please check your environment variables.")


# Validate settings on import
try:
    settings = get_settings()
except RuntimeError as e:
    print(f"ERROR: {e}")
    raise
