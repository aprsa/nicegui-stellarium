# Copilot Instructions for nicegui-stellarium

## Project Overview

A **standalone NiceGUI widget** wrapping the **Stellarium Web Engine** - a WebGL-based planetarium renderer. Bridges Python (NiceGUI) with JavaScript (WebGL engine) for interactive sky visualization.

## Architecture

```
     Python (NiceGUI)               JavaScript (Browser)
┌───────────────────────┐       ┌─────────────────────────┐
│ StellariumWidget      │──────▶│ stellarium_init.js      │
│   └─ StellariumBridge |       │   └─ StelWebEngine      │
└───────────────────────┘       │      (stellarium-web-   │
                                │       engine.wasm)      │
                                └─────────────────────────┘
```

### Key Components

- **`stellarium_widget/stellarium_widget.py`**: Main NiceGUI component. `StellariumConfig` handles path discovery and static file mounting. `StellariumWidget` renders the UI and coordinates with the JS bridge.
- **`stellarium_widget/stellarium_bridge.py`**: Python→JS bridge. All JavaScript generation is isolated here. Uses `ui.run_javascript()` for commands, async `_query()` for return values.
- **`stellarium_widget/stellarium_init.js`**: Browser-side initialization. Queues widget configs until WASM engine loads, then processes them.
- **`extern/stellarium/`**: Vendored stellarium-web-engine (C compiled to WASM via Emscripten).

## Development Patterns

### Python-to-JavaScript Communication
```python
# Commands (fire-and-forget) - use _run()
self._run(f'stel.core.fov = {fov_degrees} * stel.D2R;')

# Queries (need return value) - use async _query()
result = await self._query('return stel.observer.latitude / stel.D2R;')
```

### Widget Instance Isolation
Each widget gets a unique ID (`stel_<8-hex-chars>`) stored in `window.{widget_id}_stel` and `window.{widget_id}_ready` for multi-instance support.

### Configuration and Mounting
`StellariumConfig` uses a class-level singleton pattern. Static files are mounted automatically when `StellariumWidget.render()` is called. For explicit paths:
```python
config = StellariumConfig(build_dir=..., data_dir=...)
widget = StellariumWidget(config=config)
```

## Build Commands

### Building Stellarium Web Engine (only if modifying C/WASM code)
```bash
cd extern/stellarium
source $PATH_TO_EMSDK/emsdk_env.sh
make js          # Release build
make js-debug    # Debug build
```
Outputs: `build/stellarium-web-engine.js` and `.wasm`

### Running the NiceGUI App
```bash
# Requires nicegui package
pip install nicegui
python -m your_app  # Your app importing from stellarium_widget/
```

## Sky Data Structure

Located in `extern/stellarium/apps/test-skydata/`:
- `stars/` - Star catalogs
- `skycultures/` - Constellation definitions
- `dso/` - Deep sky objects
- `landscapes/` - Horizon images
- `surveys/` - HiPS survey data (Milky Way)

## Object Naming Convention

Stellarium uses prefixed names: `"NAME Polaris"`, `"NAME Jupiter"`, `"NAME Sun"`. Always use this format when calling `look_at_object()` or query functions.

## Adding New Engine Controls

1. Add method to `StellariumBridge` with appropriate `_run()` or `_query()` call
2. Add public wrapper method to `StellariumWidget` that updates state and calls bridge
3. Bridge handles all JS string escaping via `json.dumps()`

## Dependencies

- **Runtime**: `nicegui` package, WebGL-capable browser
- **Build** (optional): Emscripten SDK + SCons (only for rebuilding WASM)
