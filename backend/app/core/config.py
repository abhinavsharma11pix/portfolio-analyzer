import os
from functools import lru_cache
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    app_name:    str  = "AI Portfolio Analyzer"
    app_version: str  = "5.0.0"
    debug:       bool = False
    environment: str  = "development"

    # Paths
    data_dir:    Path = Path("data")
    cache_dir:   Path = Path("data/cache")
    db_path:     str  = "data/portfolio.db"

    # Cache TTLs (seconds)
    price_cache_ttl:      int = 30
    analytics_cache_ttl:  int = 600
    benchmark_cache_ttl:  int = 3600
    prediction_cache_ttl: int = 21600
    symbol_cache_ttl:     int = 604800  # 7 days

    # Price engine
    price_timeout:        int = 7
    price_max_workers:    int = 12
    price_batch_size:     int = 20

    # API
    max_holdings:         int = 100
    max_file_mb:          int = 10
    # Database 
    db_pool_size: int = 10 
    db_pool_timeout: int = 30

    # CORS
    allowed_origins: list = field(default_factory=lambda: [
        "http://localhost:5173",
        "http://localhost:3000",
    ])

    def __post_init__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings(
        debug=os.getenv("DEBUG", "false").lower() == "true",
        environment=os.getenv("ENVIRONMENT", "development"),
    )