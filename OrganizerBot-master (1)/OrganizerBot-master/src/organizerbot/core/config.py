"""
Configuration management for OrganizerBot
"""
import os
import json
from dataclasses import dataclass, asdict
from typing import List, Dict

@dataclass
class Config:
    """Configuration class"""
    watch_folder: str
    features: Dict[str, bool]
    source_folders: List[str]
    categories: List[str]

def get_config_path() -> str:
    """Get the path to the config file"""
    config_dir = os.path.expanduser("~/.organizerbot")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "config.json")

def load_config() -> Config:
    """Load configuration from file or create default"""
    config_path = get_config_path()
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                data = json.load(f)
                # Ensure all required fields are present
                required_fields = {"watch_folder", "features", "source_folders", "categories"}
                if not all(field in data for field in required_fields):
                    raise ValueError("Missing required fields in config file")
                return Config(**{k: v for k, v in data.items() if k in required_fields})
        except (json.JSONDecodeError, ValueError):
            os.remove(config_path)  # Remove invalid config file
    
    # Create default config
    config = Config(
        watch_folder=os.path.expanduser("~/Pictures"),
        features={
            "watermark_removal": True,
            "enhancement": False,
            "auto_upload": False
        },
        source_folders=[],
        categories=[
            "amateur", "professional", "asian", "european", "american",
            "lesbian", "gay", "trans", "fetish", "bdsm",
            "cosplay", "hentai", "manga", "vintage", "other"
        ]
    )
    
    # Save default config
    save_config(config)
    return config

def save_config(config: Config) -> None:
    """Save configuration to file"""
    config_path = get_config_path()
    with open(config_path, "w") as f:
        json.dump(asdict(config), f, indent=4) 