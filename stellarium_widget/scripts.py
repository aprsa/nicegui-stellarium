"""CLI scripts for nicegui-stellarium."""

import subprocess
import sys
from pathlib import Path


def fetch_engine():
    """Clone stellarium-web-engine into extern/stellarium."""
    # Find the extern directory relative to the package installation
    # or relative to the current working directory
    package_dir = Path(__file__).parent.parent
    extern_dir = package_dir / "extern"

    # If not found relative to package, try current directory
    if not extern_dir.exists():
        extern_dir = Path.cwd() / "extern"

    # If still not found, create it
    if not extern_dir.exists():
        print(f"Creating extern directory at: {extern_dir}")
        extern_dir.mkdir(parents=True)

    stellarium_dir = extern_dir / "stellarium"

    if stellarium_dir.exists():
        print(f"stellarium-web-engine already exists at: {stellarium_dir}")
        print("To re-fetch, remove the directory first:")
        print(f"  rm -rf {stellarium_dir}")
        sys.exit(1)

    print("Cloning stellarium-web-engine...")
    print(f"  Target: {stellarium_dir}")
    print()

    try:
        subprocess.run(
            [
                "git", "clone",
                "https://github.com/Stellarium/stellarium-web-engine.git",
                str(stellarium_dir)
            ],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: git is not installed or not in PATH")
        sys.exit(1)

    print()
    print("=" * 60)
    print("stellarium-web-engine cloned successfully!")
    print("=" * 60)
    print()
    print("Next steps - build the WebAssembly engine:")
    print()
    print("  1. Install Emscripten SDK:")
    print("     https://emscripten.org/docs/getting_started/downloads.html")
    print()
    print("  2. Install SCons:")
    print("     pip install scons")
    print()
    print("  3. Build:")
    print(f"     cd {stellarium_dir}")
    print("     source /path/to/emsdk/emsdk_env.sh")
    print("     make js")
    print()
    print("The build will create:")
    print(f"  {stellarium_dir / 'build' / 'stellarium-web-engine.js'}")
    print(f"  {stellarium_dir / 'build' / 'stellarium-web-engine.wasm'}")


if __name__ == "__main__":
    fetch_engine()
