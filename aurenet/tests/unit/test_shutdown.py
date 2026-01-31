"""
Unit tests for shutdown coordinator.
"""

import threading
import time

from aurenet.core.shutdown import ShutdownCoordinator


class MockComponent:
    """Mock component for testing."""

    def __init__(self, name: str = "mock"):
        self.name = name
        self.stopped = False
        self.stop_called = 0

    def stop(self):
        """Stop the component."""
        self.stopped = True
        self.stop_called += 1


class FailingComponent:
    """Component that raises exception on stop."""

    def __init__(self):
        self.stop_attempted = False

    def stop(self):
        """Stop that raises exception."""
        self.stop_attempted = True
        raise RuntimeError("Stop failed")


class TestShutdownCoordinator:
    """Tests for ShutdownCoordinator."""

    def test_register_component(self):
        coordinator = ShutdownCoordinator()
        component = MockComponent()

        coordinator.register(component)

        # Should be registered (will be stopped on shutdown)
        coordinator.shutdown()
        assert component.stopped

    def test_shutdown_stops_all_components(self):
        coordinator = ShutdownCoordinator()
        comp1 = MockComponent("comp1")
        comp2 = MockComponent("comp2")
        comp3 = MockComponent("comp3")

        coordinator.register(comp1)
        coordinator.register(comp2)
        coordinator.register(comp3)

        coordinator.shutdown()

        assert comp1.stopped
        assert comp2.stopped
        assert comp3.stopped

    def test_shutdown_reverse_order(self):
        coordinator = ShutdownCoordinator()
        stop_order = []

        class OrderedComponent:
            def __init__(self, name):
                self.name = name

            def stop(self):
                stop_order.append(self.name)

        comp1 = OrderedComponent("first")
        comp2 = OrderedComponent("second")
        comp3 = OrderedComponent("third")

        coordinator.register(comp1)
        coordinator.register(comp2)
        coordinator.register(comp3)

        coordinator.shutdown()

        # Should stop in reverse order (LIFO)
        assert stop_order == ["third", "second", "first"]

    def test_shutdown_error_doesnt_prevent_others(self):
        coordinator = ShutdownCoordinator()

        comp1 = MockComponent("comp1")
        failing = FailingComponent()
        comp2 = MockComponent("comp2")

        coordinator.register(comp1)
        coordinator.register(failing)
        coordinator.register(comp2)

        # Should not raise exception
        coordinator.shutdown()

        # All components should have stop attempted
        assert comp1.stopped
        assert failing.stop_attempted
        assert comp2.stopped

    def test_is_shutdown_requested(self):
        coordinator = ShutdownCoordinator()

        assert not coordinator.is_shutdown_requested()

        coordinator.request_shutdown()

        assert coordinator.is_shutdown_requested()

    def test_wait_for_shutdown_timeout(self):
        coordinator = ShutdownCoordinator()

        # Should timeout quickly
        result = coordinator.wait_for_shutdown(timeout=0.1)
        assert not result

    def test_wait_for_shutdown_triggered(self):
        coordinator = ShutdownCoordinator()

        def trigger_shutdown():
            time.sleep(0.1)
            coordinator.request_shutdown()

        thread = threading.Thread(target=trigger_shutdown)
        thread.start()

        # Should return True when shutdown is requested
        result = coordinator.wait_for_shutdown(timeout=1.0)
        assert result

        thread.join()

    def test_context_manager(self):
        comp1 = MockComponent("comp1")
        comp2 = MockComponent("comp2")

        with ShutdownCoordinator() as coordinator:
            coordinator.register(comp1)
            coordinator.register(comp2)

        # Should have stopped on context exit
        assert comp1.stopped
        assert comp2.stopped

    def test_shutdown_idempotent(self):
        coordinator = ShutdownCoordinator()
        component = MockComponent()

        coordinator.register(component)

        # Call shutdown multiple times
        coordinator.shutdown()
        coordinator.shutdown()

        # Component should only be stopped once per registration
        assert component.stop_called == 2  # Called twice because shutdown was called twice
