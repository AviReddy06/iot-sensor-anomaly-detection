"""
Configuration module for IoT Anomaly Detection.

Loads settings from config.yaml and provides typed access.
"""
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


class Config:
    """Configuration singleton loaded from config.yaml."""
    
    _instance: Optional["Config"] = None
    _data: Dict[str, Any] = {}
    
    def __new__(cls, config_path: Optional[Path] = None) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load(config_path)
        return cls._instance
    
    def _load(self, config_path: Optional[Path] = None) -> None:
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"
        
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
        return self.get("serial.port", "COM19")
    
    @property
    def baudrate(self) -> int:
        return self.get("serial.baudrate", 115200)
    
    @property
    def sampling_interval_ms(self) -> int:
        return self.get("serial.sampling_interval_ms", 2000)
    
    @property
    def raw_dir(self) -> Path:
        return Path(self.get("data.raw_dir", "data/raw"))
    
    @property
    def processed_dir(self) -> Path:
        return Path(self.get("data.processed_dir", "data/processed"))
    
    @property
    def model_dir(self) -> Path:
        return Path(self.get("model_paths.model_dir", "models"))
    
    @property
    def contamination(self) -> float:
        return self.get("model.contamination", 0.01)


# Global config instance
config = Config()


def get_config(config_path: Optional[Path] = None) -> Config:
    """Get or create the global config instance."""
    global config
    if config_path is not None:
        config = Config(config_path)
    return config