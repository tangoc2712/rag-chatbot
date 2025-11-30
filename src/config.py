from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional

class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_BASE_URL: str = "http://localhost:8000"
    
    # Data Paths
    DATA_DIR: Path = Path(__file__).parent.parent / "data"
    RAW_DATA_DIR: Path = DATA_DIR / "raw"
    
    # Data files
    PRODUCT_DATA_PATH: Path = RAW_DATA_DIR / "Product_Information_Dataset.csv"
    ORDER_DATA_PATH: Path = RAW_DATA_DIR / "Order_Data_Dataset.csv"
    
    # Model Settings
    EMBEDDING_MODEL: str = "models/embedding-001"
    GOOGLE_API_KEY: Optional[str] = None

    # Database Settings
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "password"
    DB_NAME: str = "ecommerce_rag"
    
    # Development Settings
    DEBUG: bool = True
    RELOAD: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra fields from .env