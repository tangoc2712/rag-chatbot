from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", "8000"))  # Cloud Run injects PORT
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")
    
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
    # For Cloud SQL, DB_HOST can be:
    # - Unix socket: /cloudsql/PROJECT:REGION:INSTANCE
    # - Cloud SQL Proxy: localhost or cloud sql proxy address
    # - Public IP (not recommended for production)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "password"
    DB_NAME: str = "ecommerce_rag"
    
    # Cloud SQL connection settings
    # Set to True if using Unix socket connection to Cloud SQL
    USE_CLOUD_SQL_SOCKET: bool = os.getenv("USE_CLOUD_SQL_SOCKET", "false").lower() == "true"
    CLOUD_SQL_CONNECTION_NAME: Optional[str] = None  # Format: project:region:instance
    
    # Development Settings
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    RELOAD: bool = False  # Never use reload in production (Cloud Run)
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")  # development, staging, production
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra fields from .env
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT == "production"
    
    @property
    def database_url(self) -> str:
        """Get database connection URL"""
        if self.USE_CLOUD_SQL_SOCKET and self.CLOUD_SQL_CONNECTION_NAME:
            # Unix socket connection for Cloud SQL
            socket_path = f"/cloudsql/{self.CLOUD_SQL_CONNECTION_NAME}"
            return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@/{self.DB_NAME}?host={socket_path}"
        else:
            # Standard TCP connection
            return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
