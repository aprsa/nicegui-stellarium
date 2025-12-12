# External Dependencies

This directory contains external dependencies for nicegui-stellarium that must be fetched separately.

## stellarium-web-engine

The `stellarium/` directory should contain [stellarium-web-engine](https://github.com/Stellarium/stellarium-web-engine), a WebGL-based planetarium renderer.

**This is not included in the repository.** You must fetch it before using the widget.

### Quick Setup

Run the included script to clone and build stellarium-web-engine:

```bash
nicegui-stellarium-fetch-engine
```

This will:
1. Clone the repository into `extern/stellarium/`
2. Display instructions for building (requires Emscripten)

### Manual Setup

Alternatively, clone it manually:

```bash
cd extern
git clone https://github.com/Stellarium/stellarium-web-engine.git stellarium
```

### Building

Building requires [Emscripten](https://emscripten.org/) and [SCons](https://scons.org/).

#### Prerequisites

1. **Install Emscripten SDK:**
   ```bash
   git clone https://github.com/emscripten-core/emsdk.git
   cd emsdk
   ./emsdk install latest
   ./emsdk activate latest
   ```

2. **Install SCons:**
   ```bash
   pip install scons
   ```

#### Build Commands

```bash
cd extern/stellarium

# Activate Emscripten environment
source /path/to/emsdk/emsdk_env.sh

# Build release version
make js

# Or build debug version (larger, with debug symbols)
make js-debug
```

Output files will be in `build/`:
- `stellarium-web-engine.js` - JavaScript loader
- `stellarium-web-engine.wasm` - WebAssembly binary

### Sky Data

The sky data files in `stellarium/apps/test-skydata/` include:
- `stars/` - Star catalogs
- `skycultures/` - Constellation definitions  
- `dso/` - Deep sky objects
- `landscapes/` - Horizon images
- `surveys/` - HiPS survey data (Milky Way)

These are loaded at runtime by the widget.

### License

stellarium-web-engine is licensed under AGPL-3.0. See `stellarium/LICENSE-AGPL-3.0.txt`.
