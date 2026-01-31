# AURENET Architecture

**Version:** 2.0 (Refactored)
**Last Updated:** January 2026

## Overview

AURENET is an event-driven RGB keyboard controller with integrated CheckMK monitoring, audio visualization, and custom effects. The architecture follows the **Hexagonal Architecture** pattern with dependency injection and event-driven communication.

## Design Principles

1. **Separation of Concerns** - Each component has a single, well-defined responsibility
2. **Dependency Inversion** - Components depend on abstractions (protocols), not implementations
3. **Event-Driven** - Loose coupling via publish-subscribe event bus
4. **Thread Safety** - All shared state protected with locks
5. **Testability** - All external dependencies abstracted and mockable

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         ShutdownCoordinator (Resource Mgmt)            │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Event Bus (Core)                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  KEY_PRESSED │ EFFECT_CHANGED │ MONITORING_UPDATE      │ │
│  │  KEY_RELEASED │ SPEED_CHANGED │ ANIMATION_TRIGGERED    │ │
│  │  BRIGHTNESS_CHANGED │ SHUTDOWN_REQUESTED  │ ...        │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
           │                  │                  │
     ┌─────┴──────┐    ┌─────┴──────┐    ┌─────┴──────┐
     │            │    │            │    │            │
     ▼            ▼    ▼            ▼    ▼            ▼
┌─────────┐  ┌─────────────┐  ┌──────────┐  ┌───────────┐
│  Input  │  │    Effect   │  │ Monitor  │  │  Output   │
│ Handler │  │ Orchestrator│  │ Provider │  │ Renderer  │
└─────────┘  └─────────────┘  └──────────┘  └───────────┘
     │            │                  │              │
     ▼            ▼                  ▼              ▼
┌─────────┐  ┌─────────────┐  ┌──────────┐  ┌───────────┐
│  evdev  │  │   Effects   │  │ CheckMK  │  │  OpenRGB  │
│ Keyboard│  │   Registry  │  │   API    │  │ Hardware  │
└─────────┘  └─────────────┘  └──────────┘  └───────────┘
```

## Component Layers

### 1. Core Layer (`aurenet/core/`)

**Purpose:** Fundamental building blocks used by all other components.

#### EventBus (`events.py`)
- **Responsibility:** Pub/sub event messaging system
- **Thread Safety:** RLock for concurrent subscribe/publish
- **Key Design:** Handlers copied under lock, called outside lock (prevents deadlocks)
- **Events:** 9 types (KEY_PRESSED, EFFECT_CHANGED, MONITORING_UPDATE, etc.)

#### ShutdownCoordinator (`shutdown.py`)
- **Responsibility:** Graceful shutdown of all components
- **Pattern:** Stoppable protocol for uniform interface
- **Features:**
  - LIFO shutdown order (last started, first stopped)
  - Error isolation (one component failure doesn't prevent others)
  - Blocking wait_for_shutdown()
  - Context manager support

#### ApplicationOrchestrator (`orchestrator.py`)
- **Responsibility:** Coordinates effect configuration via events
- **Thread Safety:** RLock, returns config copies
- **Manages:**
  - Effect selection
  - Speed (0.1-5.0, clamped)
  - Brightness (0.0-1.0, clamped)
  - Theme selection

#### Types (`types.py`)
- **Responsibility:** Shared dataclasses and enums
- **Contents:**
  - `EffectConfig` - Speed, brightness, effect, theme
  - `HostState` - CheckMK host status
  - `AnimationType` - Supernova, Phoenix, Blackhole, etc.
  - `AnimationEvent` - Animation trigger data

### 2. Configuration Layer (`aurenet/config/`)

**Purpose:** Application and effect configuration management.

#### AppConfig (`settings.py`)
- **Responsibility:** Load configuration from files/environment
- **Sources:**
  - YAML/JSON config files
  - Environment variables
  - Defaults
- **Contains:**
  - CheckMK API credentials
  - Trigger file paths
  - Update intervals
  - FPS, LED count

#### Themes (`themes.py`)
- **Responsibility:** Color palette definitions
- **Themes:** Default, Sunset, Ocean, Fire, Matrix, etc.
- **Interface:** `ColorProvider` protocol

### 3. Input Layer (`aurenet/input/`)

**Purpose:** Keyboard input handling and mapping.

#### InputHandler (`handler.py`)
- **Responsibility:** Monitor evdev keyboard input, publish events
- **Threading:** Runs in separate daemon thread
- **Features:**
  - Auto device discovery and reconnection
  - ESC long-press for shutdown (configurable duration)
  - Tracks pressed keys for reactive effects
  - Context manager support
- **Events Published:**
  - KEY_PRESSED/KEY_RELEASED (with LED index)
  - EFFECT_CHANGED, SPEED_CHANGED, BRIGHTNESS_CHANGED
  - SHUTDOWN_REQUESTED (on ESC hold)

#### KeyboardMapper (`keyboard_mapping.py`)
- **Responsibility:** Map keycodes to actions and LED indices
- **Mappings:**
  - 100+ keys → LED indices (0-99)
  - F1-F8 → Effects
  - F9/F10 → Speed adjust
  - F11/F12 → Brightness adjust
  - Space → Test animation
  - Right CTRL → Show hostlist

### 4. Effects Layer (`aurenet/effects/`)

**Purpose:** Visual effects rendering.

#### Effect Base (`base.py`)
- **Pattern:** Abstract base class with `render()` method
- **Interface:**
  ```python
  class Effect(ABC):
      @abstractmethod
      def render(self, state: KeyboardState) -> List[RGBColor]:
          pass
  ```
- **Shared Features:**
  - `get_elapsed()` - Time-based animations
  - Configuration (speed, brightness)
  - LED count

#### Effect Registry
- **Responsibility:** Register and instantiate effects by name
- **Pattern:** Factory pattern
- **Usage:**
  ```python
  effect = registry.create("rainbow", config, num_leds)
  colors = effect.render(keyboard_state)
  ```

#### Effect Categories

**Audio Effects** (`effects/audio/`):
- `AudioEffect` - Equalizer visualization
- `AudioPulseEffect` - Bass pulse
- `AudioWaveEffect` - Waveform display

**Ambient Effects** (`effects/ambient/`):
- `RainbowEffect` - Color wheel
- `BreathingEffect` - Gentle fade
- `AuroraEffect` - Northern lights simulation
- `SunsetEffect` - Sunset colors
- `OceanEffect` - Ocean wave simulation

**Interactive Effects** (`effects/interactive/`):
- `FireEffect` - Fire simulation with heat diffusion
- `MatrixEffect` - Matrix digital rain

**Monitoring Effects** (`effects/monitoring/`):
- `CheckMKEffect` - Host status visualization with animations

### 5. Monitoring Layer (`aurenet/monitoring/`)

**Purpose:** External monitoring system integration.

#### MonitoringProvider (`base.py`)
- **Pattern:** Protocol for monitoring backends
- **Interface:**
  ```python
  class MonitoringProvider(Protocol):
      def get_hosts(self) -> List[HostState]
      def get_animation_events(self) -> List[AnimationEvent]
      def start() -> None
      def stop() -> None
  ```

#### CheckMKMonitor (`checkmk.py`)
- **Responsibility:** Fetch host states from CheckMK API
- **Threading:** Background thread with 10s polling
- **Thread Safety:** RLock for hosts and animations
- **Features:**
  - Retry logic with exponential backoff (3 attempts, 1s/2s delays)
  - Zone-based coloring (dev/prod/database zones)
  - Priority sorting (CRITICAL → WARNING → OK)
  - Animation triggers:
    - SUPERNOVA - Host goes CRITICAL
    - PHOENIX - Host recovers to OK
    - WARNING - Host goes to WARNING
    - BLACKHOLE - Host disappears
    - SPAWN - New host appears
    - CELEBRATION - All hosts OK
- **Test Triggers:** File-based triggers for developer notifications
- **Context Manager:** Auto start/stop

### 6. Output Layer (`aurenet/output/`)

**Purpose:** Render colors to hardware.

#### Hardware (`hardware.py`)
- **Responsibility:** OpenRGB hardware abstraction
- **Interface:** Connect to RGB devices, set colors

#### Renderer (`renderer.py`)
- **Responsibility:** Orchestrate rendering pipeline
- **Pipeline:**
  1. Get current effect from registry
  2. Build keyboard state (audio, pressed keys, monitoring)
  3. Call effect.render(state)
  4. Apply overlays (task complete, codex complete)
  5. Send to hardware

### 7. Infrastructure Layer (`aurenet/infrastructure/`)

**Purpose:** Abstract external dependencies.

#### FileSystemAdapter (`filesystem.py`)
- **Protocol:** exists(), read(), write(), delete()
- **Implementations:** RealFileSystem, MockFileSystem (tests)

#### HttpClient (`http.py`)
- **Protocol:** get(url, headers, params, timeout)
- **Implementations:** RealHttpClient (requests), MockHttpClient (tests)

#### TriggerFileSystem (`triggers.py`)
- **Responsibility:** Check and clear trigger files
- **Usage:** Developer task completion notifications
- **Files:**
  - `/tmp/aurenet_task_complete.txt` - Orange fade-in/blink/fade-out
  - `/tmp/aurenet_codex_complete.txt` - White-blue animation

## Data Flow

### Input Event Flow

```
Keyboard Press
      ↓
evdev Device (OS)
      ↓
InputHandler._input_loop() [Thread]
      ↓
KeyboardMapper.get_action(keycode)
      ↓
EventBus.publish(Event)
      ↓
ApplicationOrchestrator._on_effect_changed()
      ↓
Update EffectConfig
```

### Rendering Flow

```
Main Loop (30 FPS)
      ↓
Orchestrator.get_effect_config() [Copy]
      ↓
EffectRegistry.create(name, config, num_leds)
      ↓
Effect.render(KeyboardState)
      │
      ├─ Audio bands (if audio effect)
      ├─ Pressed keys (if interactive)
      ├─ Host states (if monitoring)
      └─ Animations (supernova, phoenix, etc.)
      ↓
Apply overlays (triggers)
      ↓
Hardware.set_colors(colors)
      ↓
OpenRGB → LED Controller → Keyboard LEDs
```

### Monitoring Flow

```
CheckMKMonitor._monitoring_loop() [Thread]
      ↓
HTTP GET CheckMK API (with retry)
      ↓
Parse JSON → List[HostState]
      ↓
Compare with previous state
      ↓
Detect state changes → AnimationEvents
      ↓
Store with RLock protection
      ↓
CheckMKEffect.render() reads hosts
      ↓
Trigger animations (SUPERNOVA, PHOENIX, etc.)
```

## Thread Safety Model

### Shared State Protection

1. **EventBus**
   - `_handlers` dictionary protected by RLock
   - Handlers copied under lock before invocation
   - Prevents deadlocks (handlers called outside lock)

2. **ApplicationOrchestrator**
   - `_effect_config` protected by RLock
   - Returns copies to prevent external mutation
   - All event handlers acquire lock

3. **CheckMKMonitor**
   - `_hosts` and `_animation_queue` protected by RLock
   - All getters return copies
   - Update methods acquire lock

4. **InputHandler**
   - `_pressed_keys` set protected by Lock
   - Device access serialized

### Lock Hierarchy

```
EventBus (RLock)
    └─ No nested locks (handlers called outside lock)

ApplicationOrchestrator (RLock)
    └─ No nested locks

CheckMKMonitor (RLock)
    └─ No nested locks

InputHandler (Lock)
    └─ No nested locks
```

**Deadlock Prevention:** No component acquires multiple locks or calls other components while holding a lock.

## Error Handling

### Retry Logic

**CheckMKMonitor:**
```python
for attempt in range(3):
    try:
        response = http.get(...)
        return process(response)
    except RequestException:
        if attempt == 2:
            raise MonitoringError()
        time.sleep(2 ** attempt)  # 1s, 2s
```

### Error Isolation

**EventBus:**
- Exceptions in handlers caught and logged
- Other handlers still execute

**ShutdownCoordinator:**
- Exceptions in component.stop() caught and logged
- Other components still stopped

**InputHandler:**
- Device errors trigger reconnection attempt
- Unexpected errors logged, loop continues

## Configuration

### Loading Order

1. Defaults (hardcoded)
2. Config file (YAML/JSON)
3. Environment variables
4. Command-line arguments (highest priority)

### Environment Variables

```bash
AURENET_CHECKMK_URL=http://monitoring.example.com
AURENET_CHECKMK_USER=automation
AURENET_CHECKMK_SECRET=secret123
AURENET_FPS=60
AURENET_BRIGHTNESS=0.8
```

### Config File Example

```yaml
checkmk:
  url: http://monitoring.example.com
  user: automation
  secret: secret123

triggers:
  task_complete: /tmp/aurenet_task_complete.txt
  codex_complete: /tmp/aurenet_codex_complete.txt

application:
  update_interval: 10.0
  fps: 30
  num_leds: 120

effects:
  default: checkmk
  speed: 1.0
  brightness: 1.0
```

## Testing Strategy

### Unit Tests (76% coverage)

- **Mocking:** All external dependencies (HTTP, filesystem, evdev)
- **Isolation:** Each component tested independently
- **Thread Safety:** Concurrent access tests

### Integration Tests

- **Effect Switching:** Keyboard input → effect change → visual output
- **Monitoring:** CheckMK API → host colors → animations
- **Input Pipeline:** Key press → event → config update

### Test Fixtures

```python
MockHttpClient - Predefined HTTP responses
MockFileSystem - In-memory filesystem
MockKeyboard - Captures color output
```

## Deployment

### Dependencies

```
python >= 3.10
evdev >= 1.9.2
openrgb-python >= 0.2.15
requests >= 2.28.0
pyyaml >= 6.0
numpy >= 1.24.0 (for audio)
```

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python rgb_keyboard.py

# Run with custom config
python rgb_keyboard.py --config myconfig.yaml
```

### Systemd Service

```ini
[Unit]
Description=AURENET RGB Keyboard Controller
After=network.target

[Service]
Type=simple
User=aurenet
Environment=AURENET_CONFIG=/etc/aurenet/config.yaml
ExecStart=/usr/bin/python3 /opt/aurenet/rgb_keyboard.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Performance

### Benchmarks (Ryzen 5 5600X)

- **Render time:** ~2ms per frame (30 FPS = 33ms budget)
- **CheckMK poll:** ~50ms (every 10s)
- **Memory:** ~40MB RSS
- **CPU:** <5% average, ~15% during effects

### Optimization Strategies

1. **Effect caching:** Pre-compute gradients, patterns
2. **Minimal locking:** Hold locks for shortest time possible
3. **Event batching:** Coalesce rapid key events
4. **Lazy loading:** Only load active effect modules

## Future Enhancements

1. **Plugin System:** Dynamic effect loading
2. **Web UI:** Browser-based configuration
3. **Audio Sync:** Advanced beat detection
4. **Multi-Device:** Support for multiple keyboards
5. **Recording:** Capture and replay LED sequences
6. **Cloud Sync:** Share effects across devices

---

**Refactoring Completed:** Phase 6/6
**Original Size:** 3,717 lines (monolithic)
**New Size:** ~2,000 lines (modular)
**Test Coverage:** 76%
**Components:** 15 modules, 91 tests
