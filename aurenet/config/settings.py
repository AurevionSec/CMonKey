"""
AURENET - Configuration Management

Handles application configuration from environment variables and files.
"""

import os
from dataclasses import dataclass
from typing import Optional
import yaml
import json


@dataclass
class AppConfig:
    """Main application configuration."""

    # CheckMK settings
    checkmk_url: str = "http://192.168.10.66:5000/cmk"
    checkmk_user: str = "keyboard"
    checkmk_secret: str = ""

    # Trigger file paths
    task_complete_file: str = "/tmp/aurenet_task_complete.txt"
    codex_complete_file: str = "/tmp/aurenet_codex_complete.txt"
    theme_file: str = "/tmp/aurenet_theme.txt"

    # Application settings
    update_interval: float = 10.0  # CheckMK poll interval in seconds
    fps: int = 30  # Frames per second for rendering

    # Effect settings
    default_effect: str = "checkmk"
    default_speed: float = 1.0
    default_brightness: float = 1.0

    # Hardware settings
    num_leds: int = 120  # Number of LEDs on keyboard
    device_name: str = "Roccat Vulcan AIMO"

    @classmethod
    def from_env(cls) -> "AppConfig":
        """
        Load configuration from environment variables.

        Environment variables:
        - CHECKMK_URL: CheckMK server URL
        - CHECKMK_USER: CheckMK automation user
        - CHECKMK_SECRET: CheckMK automation secret
        - AURENET_UPDATE_INTERVAL: Monitoring update interval (seconds)
        - AURENET_FPS: Rendering frames per second
        """
        return cls(
            checkmk_url=os.environ.get("CHECKMK_URL", cls.checkmk_url),
            checkmk_user=os.environ.get("CHECKMK_USER", cls.checkmk_user),
            checkmk_secret=os.environ.get("CHECKMK_SECRET", cls.checkmk_secret),
            update_interval=float(os.environ.get("AURENET_UPDATE_INTERVAL", cls.update_interval)),
            fps=int(os.environ.get("AURENET_FPS", cls.fps)),
        )

    @classmethod
    def from_file(cls, path: str) -> "AppConfig":
        """
        Load configuration from YAML or JSON file.

        Args:
            path: Path to configuration file (.yaml, .yml, or .json)

        Returns:
            AppConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file format is invalid
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path, "r") as f:
            if path.endswith((".yaml", ".yml")):
                data = yaml.safe_load(f)
            elif path.endswith(".json"):
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {path}")

        return cls(**data)

    @classmethod
    def load(cls, config_file: Optional[str] = None) -> "AppConfig":
        """
        Load configuration with priority: file > env > defaults.

        Args:
            config_file: Optional path to configuration file

        Returns:
            AppConfig instance
        """
        # Start with environment variables
        config = cls.from_env()

        # Override with file if provided
        if config_file and os.path.exists(config_file):
            file_config = cls.from_file(config_file)
            # Merge: file config takes precedence
            for key, value in file_config.__dict__.items():
                setattr(config, key, value)

        return config

    def validate(self) -> None:
        """
        Validate configuration values.

        Raises:
            ValueError: If configuration is invalid
        """
        if self.update_interval <= 0:
            raise ValueError("update_interval must be positive")

        if self.fps <= 0 or self.fps > 120:
            raise ValueError("fps must be between 1 and 120")

        if self.num_leds <= 0:
            raise ValueError("num_leds must be positive")

        if not self.checkmk_url:
            raise ValueError("checkmk_url is required")
