# AURENET Testing Guide

This document describes how to run tests, write new tests, and understand the testing infrastructure.

## Quick Start

```bash
# Run all tests
python -m pytest aurenet/tests/

# Run with coverage
python -m pytest aurenet/tests/ --cov=aurenet --cov-report=html

# Run specific test file
python -m pytest aurenet/tests/unit/test_events.py -v

# Run specific test
python -m pytest aurenet/tests/unit/test_events.py::TestEventBus::test_subscribe_and_publish -v
```

## Test Structure

```
aurenet/tests/
├── unit/                    # Unit tests (isolated components)
│   ├── test_events.py      # Event system
│   ├── test_orchestrator.py # Application orchestrator
│   ├── test_input.py       # Keyboard mapping
│   ├── test_input_handler.py # Input handling
│   ├── test_monitoring.py  # CheckMK monitor
│   ├── test_shutdown.py    # Shutdown coordinator
│   ├── test_thread_safety.py # Concurrent access
│   ├── test_config.py      # Configuration loading
│   ├── test_infrastructure.py # HTTP, filesystem, triggers
│   └── test_effects.py     # Effect rendering
├── integration/             # Integration tests
│   ├── test_effect_switching.py
│   ├── test_monitoring_integration.py
│   └── test_input_pipeline.py
└── fixtures/                # Shared test fixtures
    ├── __init__.py
    └── mocks.py            # Mock implementations
```

## Unit Tests

### Philosophy

- **Isolation:** Test one component at a time
- **Mocking:** Mock all external dependencies
- **Fast:** Should run in milliseconds
- **Deterministic:** No flaky tests, no timing dependencies

### Example: Testing EventBus

```python
from aurenet.core.events import EventBus, Event, EventType

def test_subscribe_and_publish():
    bus = EventBus()
    received_events = []

    def handler(event: Event):
        received_events.append(event)

    bus.subscribe(EventType.EFFECT_CHANGED, handler)
    bus.publish(Event.create(EventType.EFFECT_CHANGED, effect="rainbow"))

    assert len(received_events) == 1
    assert received_events[0].data["effect"] == "rainbow"
```

### Mock Objects

#### MockHttpClient

```python
from aurenet.infrastructure.http import MockHttpClient

# Setup mock responses
mock_http = MockHttpClient(responses={
    "http://monitoring/api": {
        "result": [
            {"host": "server1", "state": 0}  # OK
        ]
    }
})

# Use in tests
monitor = CheckMKMonitor(config, mock_http, mock_triggers)
hosts = monitor.get_hosts()
assert hosts[0].name == "server1"
```

#### MockFileSystem

```python
from aurenet.infrastructure.filesystem import MockFileSystem

# Setup mock filesystem
mock_fs = MockFileSystem({
    "/tmp/trigger.txt": "task_complete"
})

# Use in tests
triggers = TriggerFileSystem(mock_fs, "/tmp")
result = triggers.check_trigger("trigger.txt")
assert result == "task_complete"
```

### Thread Safety Tests

Test concurrent access to shared state:

```python
import threading

def test_concurrent_publish():
    bus = EventBus()
    received_events = []
    lock = threading.Lock()

    def handler(event):
        with lock:
            received_events.append(event)

    bus.subscribe(EventType.EFFECT_CHANGED, handler)

    # Publish from 10 threads concurrently
    threads = []
    for i in range(10):
        t = threading.Thread(
            target=lambda i=i: bus.publish(
                Event.create(EventType.EFFECT_CHANGED, value=i)
            )
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # All events should be received
    assert len(received_events) == 10
```

## Integration Tests

### Philosophy

- **Real Interactions:** Components work together
- **Mocked Boundaries:** External systems (hardware, network) still mocked
- **Slower:** Can take seconds
- **End-to-End:** Test full workflows

### Example: Effect Switching

```python
def test_effect_switching_pipeline():
    # Setup
    bus = EventBus()
    config = AppConfig(...)
    orchestrator = ApplicationOrchestrator(bus, config)
    mapper = KeyboardMapper()
    handler = InputHandler(bus, mapper)

    # Simulate F1 key press (audio effect)
    handler.handle_key(ecodes.KEY_F1, True)

    # Verify effect changed
    effect_config = orchestrator.get_effect_config()
    assert effect_config.effect == "audio"
```

## Coverage Analysis

### Running Coverage

```bash
# Generate coverage report
python -m pytest aurenet/tests/ --cov=aurenet --cov-report=html

# View report
open htmlcov/index.html
```

### Coverage Configuration

`.coveragerc`:
```ini
[run]
source = aurenet
omit =
    */tests/*
    */test_*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    if __name__ == .__main__.:
    @abstractmethod
```

### Coverage Goals

- **Overall:** >80% line coverage
- **Core modules:** >90% (events, types, shutdown)
- **Infrastructure:** >70% (mocks cover most code)
- **Effects:** >60% (visual code, harder to test)

### Current Coverage (76%)

```
Module                      Coverage
─────────────────────────────────────
core/events.py              95%  ✅
core/orchestrator.py        88%  ✅
core/shutdown.py            92%  ✅
input/keyboard_mapping.py   51%  ⚠️
monitoring/checkmk.py       10%  ❌
infrastructure/*            40%  ⚠️
```

## Writing New Tests

### Test Naming

- **Test files:** `test_<module>.py`
- **Test classes:** `Test<ComponentName>`
- **Test methods:** `test_<what_it_tests>`

Examples:
- `test_events.py::TestEventBus::test_subscribe_and_publish`
- `test_input.py::TestKeyboardMapper::test_get_action_effect_change`

### Test Structure

Use Arrange-Act-Assert (AAA) pattern:

```python
def test_speed_adjustment():
    # Arrange - Setup
    bus = EventBus()
    config = AppConfig(...)
    orchestrator = ApplicationOrchestrator(bus, config)

    # Act - Execute
    bus.publish(Event.create(EventType.SPEED_CHANGED, delta=0.5))

    # Assert - Verify
    effect_config = orchestrator.get_effect_config()
    assert effect_config.speed == 1.5
```

### Fixtures

Use pytest fixtures for shared setup:

```python
import pytest

@pytest.fixture
def event_bus():
    """Create a fresh event bus for each test."""
    return EventBus()

@pytest.fixture
def mock_http():
    """Create mock HTTP client with default responses."""
    return MockHttpClient(responses={
        "http://test/api": {"result": []}
    })

def test_with_fixtures(event_bus, mock_http):
    # event_bus and mock_http injected automatically
    monitor = CheckMKMonitor(config, mock_http, triggers)
    ...
```

## Debugging Tests

### Verbose Output

```bash
# Show test names and results
python -m pytest aurenet/tests/ -v

# Show print statements
python -m pytest aurenet/tests/ -s

# Stop on first failure
python -m pytest aurenet/tests/ -x

# Drop into debugger on failure
python -m pytest aurenet/tests/ --pdb
```

### Logging

Enable logging in tests:

```python
import logging

def test_with_logging(caplog):
    caplog.set_level(logging.DEBUG)

    # Run test
    monitor.start()

    # Check logs
    assert "Starting monitoring" in caplog.text
```

## Continuous Integration

### GitHub Actions Workflow

`.github/workflows/test.yml`:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests
        run: |
          pytest aurenet/tests/ --cov=aurenet --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Performance Testing

### Benchmark Tests

```python
import time

def test_render_performance():
    effect = RainbowEffect(config, num_leds=120)
    state = KeyboardState(...)

    start = time.time()
    for _ in range(1000):
        colors = effect.render(state)
    elapsed = time.time() - start

    # Should render 1000 frames in <2s (30 FPS = 33ms per frame)
    assert elapsed < 2.0
```

### Memory Profiling

```bash
# Install memory profiler
pip install memory-profiler

# Profile test
python -m memory_profiler tests/performance/test_memory.py
```

## Common Testing Patterns

### Testing Exceptions

```python
import pytest

def test_invalid_effect_raises_error():
    registry = EffectRegistry()

    with pytest.raises(ValueError, match="Unknown effect"):
        registry.create("nonexistent", config, 120)
```

### Testing Async/Threading

```python
import threading
import time

def test_background_thread():
    handler = InputHandler(bus, mapper)

    # Start in background
    handler.start()

    try:
        # Wait for thread to start
        time.sleep(0.1)
        assert handler._running
    finally:
        # Clean up
        handler.stop()
```

### Parameterized Tests

```python
import pytest

@pytest.mark.parametrize("keycode,expected_effect", [
    (ecodes.KEY_F1, "audio"),
    (ecodes.KEY_F2, "audio_pulse"),
    (ecodes.KEY_F3, "audio_wave"),
    (ecodes.KEY_F4, "aurora"),
])
def test_effect_keys(keycode, expected_effect):
    mapper = KeyboardMapper()
    action = mapper.get_action(keycode)
    assert action.effect_name == expected_effect
```

## Test-Driven Development (TDD)

### Red-Green-Refactor Cycle

1. **Red:** Write failing test first
   ```python
   def test_new_animation_trigger():
       monitor = CheckMKMonitor(...)
       events = monitor.get_animation_events()
       # Will fail - not implemented yet
       assert any(e.type == AnimationType.CELEBRATION for e in events)
   ```

2. **Green:** Implement minimal code to pass
   ```python
   def get_animation_events(self):
       # Add CELEBRATION detection
       if all(h.state == 0 for h in self._hosts):
           return [AnimationEvent(type=AnimationType.CELEBRATION, ...)]
       return []
   ```

3. **Refactor:** Clean up while keeping tests green
   ```python
   def _check_celebration(self) -> Optional[AnimationEvent]:
       """Extract celebration check into method."""
       if all(h.state == 0 for h in self._hosts):
           return AnimationEvent(...)
       return None
   ```

## Troubleshooting

### Tests Pass Locally But Fail in CI

- **Timing issues:** Use explicit waits instead of sleep()
- **Environment differences:** Check Python version, OS
- **Missing dependencies:** Update requirements.txt

### Flaky Tests

- **Race conditions:** Add proper synchronization
- **External state:** Use fresh fixtures for each test
- **Time-dependent:** Mock time.time() for determinism

### Slow Tests

- **Too many iterations:** Reduce loop counts
- **Real I/O:** Mock filesystem/network
- **Missing parallelization:** Use pytest-xdist

```bash
# Run tests in parallel
pip install pytest-xdist
pytest aurenet/tests/ -n auto
```

---

**Current Status:** 91 tests, 76% coverage
**Target:** >80% coverage for all modules
**CI:** GitHub Actions (pytest + coverage)
