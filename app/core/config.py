import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote_plus

class Settings(BaseSettings):
    # API Settings
    PROJECT_NAME: str = "Blockchain PDF Verification"
    API_V1_STR: str = "/api/v1"
    
    #postgresSQL connection credentials from .env file  
    DB_USER : str = "postgres",
    DB_PASSWORD : str = "",
    DB_HOST : str = "localhost",
    DB_PORT : str = "5432",
    DB_NAME : str = "docs_bct"

    # Database Configuration (PostgreSQL)
    DATABASE_URL: str = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    model_config = SettingsConfigDict(env_file="app/.env", case_sensitive=True, extra="ignore")

    # Security / JWT Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "YOUR_SUPER_SECRET_KEY_CHANGE_IN_PRODUCTION")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Hyperledger Fabric / Blockchain Configs
    FABRIC_MSPID: str = "Org1MSP"
    FABRIC_CRYPTO_PATH: str = "/path/to/crypto-config"
    FABRIC_CHANNEL_NAME: str = "mychannel"
    FABRIC_CHAINCODE_NAME: str = "pdf_verification"

settings = Settings()