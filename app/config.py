from pydantic import BaseSettings, AnyUrl

class Settings(BaseSettings):
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    env: str = "development"

    database_url: str
    mollie_api_key: str
    mollie_api_base: str = "https://api.mollie.com/v2"

    service_api_key: str
    frontend_return_url: str = "https://your-frontend.com/pay-return"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

