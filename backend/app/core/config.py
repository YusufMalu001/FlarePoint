from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./flarepoint.db"
    demo_mode: bool = True
    nasa_firms_map_key: str = ""
    nasa_firms_default_source: str = "VIIRS_SNPP_NRT"
    nasa_firms_default_bbox: str = "-180,-90,180,90"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Clustering defaults (Stage 1 & 2)
    dbscan_eps_km: float = 5.0
    dbscan_min_samples: int = 3
    incident_association_radius_km: float = 10.0


settings = Settings()
