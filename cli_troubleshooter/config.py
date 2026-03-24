from __future__ import annotations
import pathlib
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CT_",
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    default_profile: str = "quick"
    data_dir: pathlib.Path = ROOT_DIR / "data"
    port: int = 8080
    host: str = "127.0.0.1"
    default_timeout: int = 10
    data_retention_days: int = 90
    ping_count: int = 10
    port_scan_ports: list[int] = [21, 22, 25, 53, 80, 443, 465, 587, 993, 995, 3306, 5432, 6379, 8080, 8443]

    @property
    def db_path(self) -> pathlib.Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "troubleshooter.db"


_settings: Optional[Settings] = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
