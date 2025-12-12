# nicegui-stellarium

Interactive planetarium widget for [NiceGUI](https://nicegui.io/) based on [stellarium-web-engine](https://github.com/Stellarium/stellarium-web-engine).

![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)
![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-green.svg)

## Features

- WebGL-powered sky rendering with atmosphere simulation
- Star catalogs (Gaia database access)
- Constellations, deep sky objects, and planets
- Interactive pan/zoom controls
- Python API for programmatic control
- Multiple widget instances supported

## Installation

```bash
pip install nicegui-stellarium
```

Or install from source:

```bash
git clone https://github.com/aprsa/nicegui-stellarium.git
cd nicegui-stellarium
pip install -e .
```

### Fetching the Engine

The stellarium-web-engine is not included in this repository. Fetch and build it:

```bash
# Clone the engine
nicegui-stellarium-fetch-engine

# Build (requires Emscripten SDK)
cd extern/stellarium
source /path/to/emsdk/emsdk_env.sh
make js
```

See [extern/README.md](extern/README.md) for detailed build instructions.

## Quick Start

```python
from nicegui import ui
from stellarium_widget import StellariumWidget

@ui.page('/')
def main():
    stellarium = StellariumWidget(height="600px")
    stellarium.render()
    
    # Control the view programmatically
    stellarium.set_location(latitude=40.0, longitude=-75.0)
    stellarium.look_at_object("NAME Polaris")
    stellarium.set_constellation_lines(True)

ui.run()
```

## API Reference

### StellariumWidget

```python
widget = StellariumWidget(
    height="500px",           # CSS height
    show_controls=True,       # Show location/time controls
    show_status_bar=True,     # Show status bar
)
widget.render()
```

#### Location and Time

```python
widget.set_location(latitude=40.0, longitude=-75.0)
widget.set_datetime(datetime(2025, 6, 21, 12, 0, tzinfo=timezone.utc))
```

#### View Control

```python
widget.look_at_object("NAME Jupiter")  # Center on object
widget.set_fov(30.0)                   # Field of view in degrees
```

#### Layer Visibility

```python
widget.set_constellation_lines(True)
widget.set_atmosphere(True)
widget.set_landscape(True)
widget.set_azimuthal_grid(True)
widget.set_equatorial_grid(True)
```

#### Queries (async)

```python
altitude = await widget.get_object_altitude("NAME Sun")
```

### Object Naming

Stellarium uses prefixed object names:

- `"NAME Polaris"` - Stars
- `"NAME Jupiter"` - Planets  
- `"NAME Sun"` - Sun
- `"NAME Moon"` - Moon

## Configuration

By default, `StellariumWidget` auto-discovers the stellarium-web-engine files by looking for `extern/stellarium/` in parent directories.

### Explicit Path Configuration

```python
from stellarium_widget import StellariumWidget, StellariumConfig

config = StellariumConfig(
    build_dir="/path/to/stellarium/build",
    data_dir="/path/to/skydata",
)
stellarium = StellariumWidget(config=config)
stellarium.render()
```

## Building from Source

The stellarium-web-engine is pre-built in this repository. To rebuild it (requires Emscripten):

```bash
cd extern/stellarium
source $PATH_TO_EMSDK/emsdk_env.sh
make js          # Release build
make js-debug    # Debug build
```

## License

AGPL-3.0 License - see [LICENSE](LICENSE) for details.
