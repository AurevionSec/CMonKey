"""
Thread safety tests for concurrent access.
"""

import threading
import time

from aurenet.config.settings import AppConfig
from aurenet.core.events import Event, EventBus, EventType
from aurenet.core.orchestrator import ApplicationOrchestrator


class TestEventBusThreadSafety:
    """Thread safety tests for EventBus."""

    def test_concurrent_subscribe(self):
        """Test concurrent subscriptions don't corrupt handler list."""
        bus = EventBus()
        handlers_added = []

        def subscribe_handler(handler_id):
            def handler(event):
                pass

            bus.subscribe(EventType.EFFECT_CHANGED, handler)
            handlers_added.append(handler_id)

        # Subscribe from 10 threads concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=subscribe_handler, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All handlers should be added
        assert len(handlers_added) == 10

    def test_concurrent_publish(self):
        """Test concurrent publishes don't lose events."""
        bus = EventBus()
        received_events = []
        lock = threading.Lock()

        def handler(event):
            with lock:
                received_events.append(event.data["value"])

        bus.subscribe(EventType.EFFECT_CHANGED, handler)

        # Publish from 10 threads concurrently
        def publish_event(value):
            bus.publish(Event.create(EventType.EFFECT_CHANGED, value=value))

        threads = []
        for i in range(10):
            thread = threading.Thread(target=publish_event, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All events should be received
        assert len(received_events) == 10
        assert set(received_events) == set(range(10))

    def test_subscribe_during_publish(self):
        """Test subscribing while events are being published."""
        bus = EventBus()
        publish_count = [0]
        subscribe_done = threading.Event()

        def slow_handler(event):
            time.sleep(0.01)
            publish_count[0] += 1

        bus.subscribe(EventType.EFFECT_CHANGED, slow_handler)

        def publish_loop():
            for i in range(20):
                bus.publish(Event.create(EventType.EFFECT_CHANGED, value=i))

        def subscribe_during_publish():
            time.sleep(0.05)  # Let some publishes happen

            def new_handler(event):
                pass

            bus.subscribe(EventType.EFFECT_CHANGED, new_handler)
            subscribe_done.set()

        pub_thread = threading.Thread(target=publish_loop)
        sub_thread = threading.Thread(target=subscribe_during_publish)

        pub_thread.start()
        sub_thread.start()

        pub_thread.join()
        sub_thread.join()

        # Should have published all events
        assert publish_count[0] == 20
        assert subscribe_done.is_set()


class TestOrchestratorThreadSafety:
    """Thread safety tests for ApplicationOrchestrator."""

    def test_concurrent_config_updates(self):
        """Test concurrent updates to effect config."""
        bus = EventBus()
        config = AppConfig(
            checkmk_url="http://test",
            checkmk_user="test",
            checkmk_secret="test",
        )
        orchestrator = ApplicationOrchestrator(bus, config)

        # Publish speed changes from multiple threads
        def adjust_speed(delta):
            for _ in range(10):
                bus.publish(Event.create(EventType.SPEED_CHANGED, delta=delta))

        threads = [
            threading.Thread(target=adjust_speed, args=(0.1,)),
            threading.Thread(target=adjust_speed, args=(-0.05,)),
            threading.Thread(target=adjust_speed, args=(0.02,)),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Final speed should be clamped properly
        final_config = orchestrator.get_effect_config()
        assert 0.1 <= final_config.speed <= 5.0

    def test_read_during_write(self):
        """Test reading config while it's being updated."""
        bus = EventBus()
        config = AppConfig(
            checkmk_url="http://test",
            checkmk_user="test",
            checkmk_secret="test",
        )
        orchestrator = ApplicationOrchestrator(bus, config)

        configs_read = []
        stop_reading = threading.Event()

        def read_config():
            while not stop_reading.is_set():
                cfg = orchestrator.get_effect_config()
                configs_read.append(cfg)
                time.sleep(0.001)

        def write_config():
            for i in range(20):
                bus.publish(Event.create(EventType.SPEED_CHANGED, delta=0.1))
                bus.publish(Event.create(EventType.BRIGHTNESS_CHANGED, delta=0.05))
                time.sleep(0.005)

        read_thread = threading.Thread(target=read_config)
        write_thread = threading.Thread(target=write_config)

        read_thread.start()
        write_thread.start()

        write_thread.join()
        stop_reading.set()
        read_thread.join()

        # Should have read many configs without crashing
        assert len(configs_read) > 0

        # All configs should be valid
        for cfg in configs_read:
            assert 0.0 <= cfg.brightness <= 1.0
            assert 0.1 <= cfg.speed <= 5.0

    def test_config_copy_isolation(self):
        """Test that returned config is isolated from orchestrator state."""
        bus = EventBus()
        config = AppConfig(
            checkmk_url="http://test",
            checkmk_user="test",
            checkmk_secret="test",
        )
        orchestrator = ApplicationOrchestrator(bus, config)

        # Get config
        cfg1 = orchestrator.get_effect_config()
        original_speed = cfg1.speed

        # Modify the returned copy
        cfg1.speed = 999.0

        # Get config again
        cfg2 = orchestrator.get_effect_config()

        # Should not be affected by external modification
        assert cfg2.speed == original_speed
        assert cfg2.speed != 999.0
