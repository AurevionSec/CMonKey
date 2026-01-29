"""
Unit tests for infrastructure components.
"""

import pytest
from aurenet.infrastructure.filesystem import MockFileSystem
from aurenet.infrastructure.triggers import TriggerFileSystem
from aurenet.infrastructure.http import MockHttpClient


class TestMockFileSystem:
    """Tests for MockFileSystem."""

    def test_exists_returns_false_for_nonexistent_file(self):
        fs = MockFileSystem()
        assert fs.exists("/nonexistent.txt") is False

    def test_write_and_read(self):
        fs = MockFileSystem()
        fs.write("/test.txt", "Hello, World!")
        assert fs.read("/test.txt") == "Hello, World!"

    def test_exists_returns_true_after_write(self):
        fs = MockFileSystem()
        fs.write("/test.txt", "content")
        assert fs.exists("/test.txt") is True

    def test_delete(self):
        fs = MockFileSystem()
        fs.write("/test.txt", "content")
        fs.delete("/test.txt")
        assert fs.exists("/test.txt") is False

    def test_read_nonexistent_raises_error(self):
        fs = MockFileSystem()
        with pytest.raises(FileNotFoundError):
            fs.read("/nonexistent.txt")


class TestTriggerFileSystem:
    """Tests for TriggerFileSystem."""

    def test_check_trigger_returns_none_when_not_exists(self):
        fs = MockFileSystem()
        triggers = TriggerFileSystem(fs, trigger_dir="/tmp")

        result = triggers.check_trigger("task_complete")
        assert result is None

    def test_check_trigger_returns_content_when_exists(self):
        fs = MockFileSystem()
        fs.write("/tmp/aurenet_task_complete.txt", "✅")

        triggers = TriggerFileSystem(fs, trigger_dir="/tmp")
        result = triggers.check_trigger("task_complete")

        assert result == "✅"

    def test_clear_trigger_deletes_file(self):
        fs = MockFileSystem()
        fs.write("/tmp/aurenet_task_complete.txt", "✅")

        triggers = TriggerFileSystem(fs, trigger_dir="/tmp")
        triggers.clear_trigger("task_complete")

        assert fs.exists("/tmp/aurenet_task_complete.txt") is False

    def test_check_and_clear(self):
        fs = MockFileSystem()
        fs.write("/tmp/aurenet_codex_complete.txt", "✅")

        triggers = TriggerFileSystem(fs, trigger_dir="/tmp")
        result = triggers.check_and_clear("codex_complete")

        assert result is True
        assert fs.exists("/tmp/aurenet_codex_complete.txt") is False

    def test_check_and_clear_returns_false_when_not_exists(self):
        fs = MockFileSystem()
        triggers = TriggerFileSystem(fs, trigger_dir="/tmp")

        result = triggers.check_and_clear("nonexistent")
        assert result is False


class TestMockHttpClient:
    """Tests for MockHttpClient."""

    def test_get_returns_mock_response(self):
        client = MockHttpClient(responses={"http://example.com/api": {"status": "ok"}})

        response = client.get("http://example.com/api")
        assert response.status_code == 200

    def test_get_returns_404_for_unknown_url(self):
        client = MockHttpClient()
        response = client.get("http://unknown.com")
        assert response.status_code == 404

    def test_get_records_call_history(self):
        client = MockHttpClient()
        client.get("http://example.com/api", headers={"Authorization": "Bearer token"})

        history = client.get_call_history()
        assert len(history) == 1
        assert history[0][0] == "http://example.com/api"
        assert history[0][1] == {"Authorization": "Bearer token"}
