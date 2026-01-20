"""
API Configuration
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"


class APIConfig:
    """API配置类"""
    
    # API Server
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_RELOAD: bool = os.getenv("API_RELOAD", "false").lower() == "true"
    
    # CORS
    # Allow common development ports (3000-3010 for Vite auto-port selection)
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3004",
        "http://localhost:3005",
        "http://localhost:5173",  # Vite default port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3003",
        "http://127.0.0.1:3004",
        "http://127.0.0.1:3005",
        "http://127.0.0.1:5173",
    ]
    
    # API Settings
    API_TITLE: str = "DAAS Alpha API"
    API_VERSION: str = "v1.3"
    API_DESCRIPTION: str = "DAAS Alpha量化选股系统API"
    
    # Request Settings
    REQUEST_TIMEOUT: int = 300  # 5 minutes for long-running operations
    
    # Database
    DATABASE_PATH: str = str(PROJECT_ROOT / "data" / "daas.db")
    
    # Config File
    CONFIG_FILE: str = str(CONFIG_PATH)
    
    @classmethod
    def get_cors_origins(cls) -> list:
        """获取CORS允许的源"""
        additional_origins = os.getenv("CORS_ORIGINS", "")
        if additional_origins:
            return cls.CORS_ORIGINS + [origin.strip() for origin in additional_origins.split(",")]
        return cls.CORS_ORIGINS
