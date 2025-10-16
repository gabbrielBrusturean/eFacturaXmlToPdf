from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "xmlToPdf"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8080

    noauth_base: str = "https://webservicesp.anaf.ro/prod/FCTEL/rest/transformare"
    oauth_base: str = "https://api.anaf.ro/prod/FCTEL/rest/transformare"

    timeout: int = 60

    class Config:
        env_file = ".env"

settings = Settings()