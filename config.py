"""
Configuration module for IoT Anomaly Detection.

Loads settings from config.yaml and provides typed access across
collection, preprocessing, feature engineering, training, evaluation,
and Streamlit dashboards.
"""

from pathlib import Path
import os
from typing import Any, Dict, Optional
import yaml


PROJECT_ROOT = Path(__file__).resolve().parent


def load_dotenv(env_path: Optional[Path] = None) -> None:
    """Load simple KEY=VALUE pairs from local .env without overriding shell variables."""
    target = PROJECT_ROOT / ".env" if env_path is None else env_path
    if not target.exists():
        return
    try:
        for raw in target.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except OSError:
        pass


load_dotenv()


class Config:
    """Configuration singleton loaded from config.yaml."""

    _instance: Optional["Config"] = None
    _data: Dict[str, Any] = {}

    def __new__(cls, config_path: Optional[Path] = None) -> "Config":
        if cls._instance is None or config_path is not None:
            instance = super().__new__(cls)
            instance._load(config_path)
            cls._instance = instance
        return cls._instance

    def _load(self, config_path: Optional[Path] = None) -> None:
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = PROJECT_ROOT / "config.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f) or {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get nested config value using dot notation (e.g., 'serial.port')."""
        keys = key.split(".")
        value = self._data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def __getattr__(self, name: str) -> Any:
        """Allow attribute access for top-level sections."""
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"Config has no section '{name}'")

    @property
    def serial_port(self) -> str:
        return str(self.get("serial.port", "COM19"))

    @property
    def baudrate(self) -> int:
        return int(self.get("serial.baudrate", 115200))

    @property
    def serial_timeout(self) -> float:
        return float(self.get("serial.timeout", 1.0))

    @property
    def sampling_interval_ms(self) -> int:
        return int(self.get("serial.sampling_interval_ms", 2000))

    @property
    def temp_bounds(self) -> tuple[float, float]:
        return (
            float(self.get("serial.temp_min", -10.0)),
            float(self.get("serial.temp_max", 65.0)),
        )

    @property
    def hum_bounds(self) -> tuple[float, float]:
        return (
            float(self.get("serial.hum_min", 0.0)),
            float(self.get("serial.hum_max", 100.0)),
        )

    @property
    def raw_dir(self) -> Path:
        return PROJECT_ROOT / self.get("data.raw_dir", "data/raw")

    @property
    def processed_dir(self) -> Path:
        return PROJECT_ROOT / self.get("data.processed_dir", "data/processed")

    @property
    def features_dir(self) -> Path:
        return PROJECT_ROOT / self.get("data.features_dir", "data/processed/features_v2")

    @property
    def benchmarks_dir(self) -> Path:
        return PROJECT_ROOT / self.get("data.benchmarks_dir", "data/benchmarks")

    @property
    def model_dir(self) -> Path:
        return PROJECT_ROOT / self.get("model_paths.model_dir", "models")

    @property
    def gap_threshold_sec(self) -> float:
        return float(self.get("features.gap_threshold_sec", 10))

    @property
    def roll_min(self) -> int:
        return int(self.get("features.roll_min", 2))

    @property
    def short_window_sec(self) -> int:
        return int(self.get("features.short_window_sec", 10))

    @property
    def long_window_sec(self) -> int:
        return int(self.get("features.long_window_sec", 30))

    @property
    def ewma_halflife_sec(self) -> int:
        return int(self.get("features.ewma_halflife_sec", 2400))

    @property
    def ewma_macro_gap_sec(self) -> int:
        return int(self.get("features.ewma_macro_gap_sec", 1800))

    @property
    def contamination(self) -> Any:
        return self.get("model.contamination", "auto")


# Global config instance
config = Config()


def get_config(config_path: Optional[Path] = None) -> Config:
    """Get or reload the global config instance."""
    global config
    if config_path is not None:
        config = Config(config_path)
    return config
