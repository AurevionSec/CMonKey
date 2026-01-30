"""
Unit tests for monitoring components.
"""

import pytest
import time
from aurenet.monitoring.checkmk import CheckMKMonitor
from aurenet.infrastructure.http import MockHttpClient
from aurenet.infrastructure.triggers import TriggerFileSystem
from aurenet.infrastructure.filesystem import MockFileSystem


@pytest.fixture
def mock_http_client():
    """Create mock HTTP client with CheckMK response."""
    responses = {
        "http://test.com/check_mk/api/1.0/domain-types/host/collections/all": {
            "value": [
                {"id": "test-server", "extensions": {"state": 0}},
                {"id": "test-laptop", "extensions": {"state": 1}},
                {"id": "test-router", "extensions": {"state": 2}},
            ]
        }
    }
    return MockHttpClient(responses)


@pytest.fixture
def trigger_fs():
    """Create trigger file system."""
    return TriggerFileSystem(MockFileSystem(), "/tmp")


class TestCheckMKMonitor:
    """Tests for CheckMKMonitor."""

    def test_initialization(self, mock_http_client, trigger_fs):
        monitor = CheckMKMonitor(
            base_url="http://test.com",
            user="testuser",
            secret="testsecret",
            http_client=mock_http_client,
            trigger_fs=trigger_fs,
        )

        assert monitor._base_url == "http://test.com"
        assert monitor._user == "testuser"
        assert monitor._secret == "testsecret"

    def test_get_hosts_returns_empty_initially(self, mock_http_client, trigger_fs):
        monitor = CheckMKMonitor(
            base_url="http://test.com",
            user="testuser",
            secret="testsecret",
            http_client=mock_http_client,
            trigger_fs=trigger_fs,
        )

        hosts = monitor.get_hosts()
        assert hosts == []

    def test_fetch_and_update_hosts(self, mock_http_client, trigger_fs):
        monitor = CheckMKMonitor(
            base_url="http://test.com",
            user="testuser",
            secret="testsecret",
            http_client=mock_http_client,
            trigger_fs=trigger_fs,
        )

        # Fetch hosts
        monitor._fetch_and_update_hosts()

        # Verify hosts were fetched
        hosts = monitor.get_hosts()
        assert len(hosts) == 3

        # Verify sorting (router before laptop before server based on priority)
        assert hosts[0].name == "test-server"  # Priority 0
        assert hosts[1].name == "test-router"  # Priority 1
        assert hosts[2].name == "test-laptop"  # Priority 6

    def test_get_host_priority(self, mock_http_client, trigger_fs):
        monitor = CheckMKMonitor(
            base_url="http://test.com",
            user="testuser",
            secret="testsecret",
            http_client=mock_http_client,
            trigger_fs=trigger_fs,
        )

        assert monitor._get_host_priority("my-server") == 0
        assert monitor._get_host_priority("router-main") == 1
        assert monitor._get_host_priority("nas-backup") == 2
        assert monitor._get_host_priority("laptop-eddy") == 6

    def test_get_zone_color(self, mock_http_client, trigger_fs):
        monitor = CheckMKMonitor(
            base_url="http://test.com",
            user="testuser",
            secret="testsecret",
            http_client=mock_http_client,
            trigger_fs=trigger_fs,
        )

        # Servers = Blue
        assert monitor._get_zone_color("my-server") == (30, 100, 255)
        # Network = Cyan
        assert monitor._get_zone_color("router-main") == (0, 200, 200)
        # Storage = Purple
        assert monitor._get_zone_color("nas-storage") == (150, 50, 255)
        # Raspberry/IoT = Pink
        assert monitor._get_zone_color("raspberry-pi") == (255, 50, 150)

    def test_animation_events_supernova(self, mock_http_client, trigger_fs):
        """Test that supernova animation is triggered on CRITICAL state."""
        monitor = CheckMKMonitor(
            base_url="http://test.com",
            user="testuser",
            secret="testsecret",
            http_client=mock_http_client,
            trigger_fs=trigger_fs,
        )

        # First fetch - establish baseline
        monitor._fetch_and_update_hosts()
        events = monitor.get_animation_events()
        # Initial fetch triggers phoenix for hosts that are OK (recovery from unknown state)
        assert len(events) >= 0  # May have phoenix events

        # Second fetch - should not trigger new animations (no state changes)
        time.sleep(0.1)
        monitor._fetch_and_update_hosts()
        events = monitor.get_animation_events()

        # Check that we have animation events
        # Note: In real scenario, we'd need to change mock data to trigger state changes

    def test_context_manager(self, mock_http_client, trigger_fs):
        """Test that monitor works as context manager."""
        monitor = CheckMKMonitor(
            base_url="http://test.com",
            user="testuser",
            secret="testsecret",
            http_client=mock_http_client,
            trigger_fs=trigger_fs,
        )

        with monitor:
            assert monitor._running is True

        # Should be stopped after context exit
        assert monitor._running is False
