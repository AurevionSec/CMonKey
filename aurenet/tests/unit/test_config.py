"""
Unit tests for configuration system.
"""

import os
import tempfile
import pytest
from aurenet.config.settings import AppConfig
from aurenet.config.themes import ColorTheme, THEMES, get_theme


class TestAppConfig:
    """Tests for AppConfig."""

    def test_default_values(self):
        config = AppConfig()
        assert config.checkmk_url == "http://192.168.10.66:5000/cmk"
        assert config.checkmk_user == "keyboard"
        assert config.update_interval == 10.0
        assert config.fps == 30

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("CHECKMK_URL", "http://test.com")
        monkeypatch.setenv("CHECKMK_USER", "testuser")
        monkeypatch.setenv("CHECKMK_SECRET", "testsecret")
        monkeypatch.setenv("AURENET_FPS", "60")

        config = AppConfig.from_env()
        assert config.checkmk_url == "http://test.com"
        assert config.checkmk_user == "testuser"
        assert config.checkmk_secret == "testsecret"
        assert config.fps == 60

    def test_from_yaml_file(self):
        # Create a temporary YAML file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
checkmk_url: http://yaml.com
checkmk_user: yamluser
checkmk_secret: yamlsecret
fps: 45
""")
            yaml_file = f.name

        try:
            config = AppConfig.from_file(yaml_file)
            assert config.checkmk_url == "http://yaml.com"
            assert config.checkmk_user == "yamluser"
            assert config.checkmk_secret == "yamlsecret"
            assert config.fps == 45
        finally:
            os.unlink(yaml_file)

    def test_from_json_file(self):
        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("""{
    "checkmk_url": "http://json.com",
    "checkmk_user": "jsonuser",
    "fps": 50
}""")
            json_file = f.name

        try:
            config = AppConfig.from_file(json_file)
            assert config.checkmk_url == "http://json.com"
            assert config.checkmk_user == "jsonuser"
            assert config.fps == 50
        finally:
            os.unlink(json_file)

    def test_from_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            AppConfig.from_file("/nonexistent/config.yaml")

    def test_validate_success(self):
        config = AppConfig()
        config.validate()  # Should not raise

    def test_validate_invalid_update_interval(self):
        config = AppConfig(update_interval=-1.0)
        with pytest.raises(ValueError, match="update_interval must be positive"):
            config.validate()

    def test_validate_invalid_fps(self):
        config = AppConfig(fps=0)
        with pytest.raises(ValueError, match="fps must be between"):
            config.validate()

    def test_validate_invalid_num_leds(self):
        config = AppConfig(num_leds=-5)
        with pytest.raises(ValueError, match="num_leds must be positive"):
            config.validate()


class TestColorTheme:
    """Tests for ColorTheme."""

    def test_default_theme_exists(self):
        assert "default" in THEMES
        assert THEMES["default"].name == "Default"

    def test_get_theme(self):
        theme = get_theme("default")
        assert isinstance(theme, ColorTheme)
        assert theme.name == "Default"

    def test_get_unknown_theme_raises_error(self):
        with pytest.raises(KeyError, match="Unknown theme"):
            get_theme("nonexistent")

    def test_all_themes_have_required_fields(self):
        for name, theme in THEMES.items():
            assert theme.name
            assert len(theme.gradient) >= 4
            assert theme.highlight
            assert theme.status_ok
            assert theme.status_warn
            assert theme.status_crit
            assert theme.status_unknown
