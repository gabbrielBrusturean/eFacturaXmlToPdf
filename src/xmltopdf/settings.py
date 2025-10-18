from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    use_oauth: bool = False           # dacă folosești endpoint-ul cu OAuth2
    bearer_token: str | None = None   # token pt. OAuth2
    val1: str = "FACT1"               # "FACT1" (factură) sau "FCN" (credit note)
    novld: bool = True                # val2 = "DA" (nu validează înainte de transformare)
    timeout: int = 60
    sleep_between: float = 0.0        # secunde între request-uri (evită rate-limit)

    class Config:
        env_prefix = "XMLTOPDF_"
        env_file = ".env"

settings = Settings()
