"""Stellarium Widget Component

A NiceGUI component that embeds stellarium-web-engine for interactive sky visualization.

Usage:
    # Simple usage - auto-discovers paths
    stellarium = StellariumWidget()
    stellarium.render()

    # With explicit configuration
    config = StellariumConfig(
        build_dir="/path/to/stellarium/build",
        data_dir="/path/to/skydata",
    )
    stellarium = StellariumWidget(config=config)
    stellarium.render()

Requirements:
    - Built stellarium-web-engine (JS + WASM files)
    - Sky data directory (stars, landscapes, etc.)
"""

import json
import uuid
from pathlib import Path
from nicegui import ui, app
from dataclasses import dataclass, field
from typing import Optional, Callable, ClassVar
from datetime import datetime, timezone

from .stellarium_bridge import StellariumBridge


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class StellariumConfig:
    """
    Configuration for Stellarium widget paths.

    Handles path discovery, validation, and static file mounting for NiceGUI.
    Uses a class-level singleton pattern - only one config can be active at a time.

    Attributes:
        build_dir: Path to directory containing stellarium-web-engine.js and .wasm
        data_dir: Path to sky data directory (stars, landscapes, etc.)
        url_prefix: URL prefix for mounted static files (default: '/swe')
    """
    build_dir: Optional[Path] = None
    data_dir: Optional[Path] = None
    url_prefix: str = '/swe'

    # Resolved URLs (set after mounting)
    js_url: str = field(default='', init=False)
    wasm_url: str = field(default='', init=False)
    data_url: str = field(default='', init=False)
    init_script_url: str = field(default='', init=False)

    # Class-level active config (singleton pattern)
    _active: ClassVar[Optional['StellariumConfig']] = None
    _mounted: bool = field(default=False, init=False)

    def __post_init__(self):
        # Convert string paths to Path objects
        if isinstance(self.build_dir, str):
            self.build_dir = Path(self.build_dir)
        if isinstance(self.data_dir, str):
            self.data_dir = Path(self.data_dir)

    def validate(self) -> None:
        """Validate that required files exist."""
        if self.build_dir:
            js_file = self.build_dir / 'stellarium-web-engine.js'
            if not js_file.exists():
                raise FileNotFoundError(
                    f"stellarium-web-engine.js not found at {js_file}\n\n"
                    "The Stellarium Web Engine must be fetched and built separately.\n"
                    "Run these commands:\n\n"
                    "  nicegui-stellarium-fetch-engine\n"
                    "  cd extern/stellarium && make js\n\n"
                    "See https://github.com/nicegui-stellarium for details."
                )

    def _set_urls(self) -> None:
        """Set URL paths after mounting."""
        self.js_url = f"{self.url_prefix}/build/stellarium-web-engine.js"
        self.wasm_url = f"{self.url_prefix}/build/stellarium-web-engine.wasm"
        self.data_url = f"{self.url_prefix}/data/"
        self.init_script_url = f"{self.url_prefix}/components/stellarium_init.js"

    def mount(self) -> 'StellariumConfig':
        """
        Mount static files for serving via NiceGUI.

        This is called automatically when a StellariumWidget is rendered.
        Can be called manually if you need early initialization.

        Returns:
            self for chaining
        """
        # If already mounted, return self
        if self._mounted:
            return self

        # If another config is active, reuse it (singleton behavior)
        if StellariumConfig._active is not None:
            return StellariumConfig._active

        # Validate paths
        self.validate()

        # Mount static file directories
        app.add_static_files(f'{self.url_prefix}/build', str(self.build_dir))
        app.add_static_files(f'{self.url_prefix}/data', str(self.data_dir))

        # Mount the components directory (initialization scripts)
        components_dir = Path(__file__).parent
        app.add_static_files(f'{self.url_prefix}/components', str(components_dir))

        # Set URLs
        self._set_urls()

        # Mark as mounted and set as active
        self._mounted = True
        StellariumConfig._active = self

        print("[StellariumWidget] Mounted static files:")
        print(f"  Build: {self.build_dir}")
        print(f"  Data:  {self.data_dir}")

        return self

    @classmethod
    def get_active(cls) -> 'StellariumConfig':
        """Get the active configuration. Raises if none is mounted."""
        if cls._active is None:
            raise RuntimeError(
                "No Stellarium configuration is active. "
                "Create a StellariumWidget or call StellariumConfig().mount() first."
            )
        return cls._active

    @classmethod
    def auto_discover(cls) -> 'StellariumConfig':
        """
        Create a config by auto-discovering Stellarium paths.

        Searches parent directories for extern/stellarium/ structure.
        """
        current = Path(__file__).resolve()
        for parent in current.parents:
            stellarium_dir = parent / 'extern' / 'stellarium'
            if stellarium_dir.exists():
                return cls(
                    build_dir=stellarium_dir / 'build',
                    data_dir=stellarium_dir / 'apps' / 'test-skydata',
                )
        raise RuntimeError(
            "Could not auto-discover Stellarium paths. "
            "Please provide explicit build_dir and data_dir to StellariumConfig."
        )

    @classmethod
    def _reset(cls) -> None:
        """Reset the active config. For testing purposes only."""
        cls._active = None


# =============================================================================
# State Management
# =============================================================================

@dataclass
class StellariumState:
    """Tracks the current state of the Stellarium view."""
    latitude: float = 40.03784        # Default: Villanova
    longitude: float = -75.34238      # Default: Villanova
    altitude: float = 142.0           # Meters above sea level
    datetime_utc: Optional[datetime] = None  # current time
    fov: float = 60.0                 # Field of view in degrees

    # UI state
    is_loaded: bool = False
    is_ready: bool = False        # True when engine is fully initialized

    def __post_init__(self):
        if self.datetime_utc is None:
            self.datetime_utc = datetime.now(timezone.utc)


# =============================================================================
# Widget Implementation
# =============================================================================

class StellariumWidget:
    """
    A NiceGUI component that embeds stellarium-web-engine.

    Usage:
        # Simple - auto-discovers paths
        stellarium = StellariumWidget()
        stellarium.render()

        # With explicit config
        config = StellariumConfig(build_dir=..., data_dir=...)
        stellarium = StellariumWidget(config=config)
        stellarium.render()

        # Control the view
        stellarium.set_location(lat=40.0, lon=-75.0)
        stellarium.set_datetime(datetime(2025, 6, 21, 12, 0))
    """

    def __init__(
        self,
        height: str = "500px",
        show_controls: bool = True,
        show_status_bar: bool = True,
        config: Optional[StellariumConfig] = None,
        on_ready: Optional[Callable[['StellariumWidget'], None]] = None,
        on_object_click: Optional[Callable[[dict], None]] = None,
    ):
        """
        Initialize the Stellarium widget.

        Args:
            height: CSS height for the widget
            show_controls: Whether to show the control panel
            show_status_bar: Whether to show the status bar
            config: Optional StellariumConfig. If not provided, auto-discovers paths.
            on_ready: Callback when engine is ready for commands
            on_object_click: Callback when user clicks a celestial object
        """
        # Store or create config (will be mounted on render)
        if config is not None:
            self._config = config
        else:
            self._config = StellariumConfig.auto_discover()

        # Generate unique ID using short uuid (8 hex chars is enough for uniqueness)
        short_id = uuid.uuid4().hex[:8]
        self.widget_id = f"stel_{short_id}"
        self.canvas_id = f"{self.widget_id}_canvas"

        # Bridge for JS communication
        self._bridge = StellariumBridge(self.widget_id)

        self.state = StellariumState(latitude=40.03784, longitude=-75.34238)
        self.height = height
        self.show_controls = show_controls
        self.show_status_bar = show_status_bar
        self.on_ready = on_ready
        self.on_object_click = on_object_click

        # UI element references (populated during render)
        self._container: Optional[ui.element] = None
        self._status_label: Optional[ui.label] = None
        self._lat_input: Optional[ui.number] = None
        self._lon_input: Optional[ui.number] = None
        self._ready_indicator: Optional[ui.icon] = None
        self._check_timer: Optional[ui.timer] = None

    @property
    def canvas_html(self):
        return f'<canvas id="{self.canvas_id}" style="width: 100%; height: 100%; display: block;"></canvas>'

    def render(self) -> ui.element:
        """
        Render the Stellarium widget. Call this within a NiceGUI context.

        Returns:
            The container element for further customization
        """
        # Ensure static files are mounted
        self._config.mount()

        with ui.column().classes('w-full gap-2') as self._container:
            # Control bar (if enabled)
            if self.show_controls:
                self._render_control_bar()

            # Canvas container
            with ui.card().classes('w-full bg-black p-0 overflow-hidden').style(f'height: {self.height}'):
                # Create the canvas element
                ui.html(self.canvas_html, sanitize=False).classes('w-full h-full')

            # Status bar
            if self.show_status_bar:
                with ui.row().classes('w-full items-center justify-between px-2 text-sm'):
                    self._status_label = ui.label('Initializing Stellarium...').classes('text-gray-400')
                    with ui.row().classes('gap-4 text-gray-500'):
                        self._lat_label = ui.label(f'Lat: {self.state.latitude:.1f}°')
                        self._lon_label = ui.label(f'Lon: {self.state.longitude:.1f}°')

            # Inject the initialization script
            self._inject_init_script()

        return self._container

    def _render_control_bar(self):
        """Render the control bar with location/time inputs."""
        with ui.card().classes('w-full bg-gray-800 p-3'):
            with ui.row().classes('w-full items-center gap-4 flex-wrap'):
                # Location controls
                ui.label('Location:').classes('text-white font-medium')

                self._lat_input = ui.number(
                    label='Latitude',
                    value=self.state.latitude,
                    min=-90, max=90,
                    step=1,
                    format='%.1f',
                    on_change=lambda e: self._on_location_input_change()
                ).classes('w-28').props('dense')

                self._lon_input = ui.number(
                    label='Longitude',
                    value=self.state.longitude,
                    min=-180, max=180,
                    step=1,
                    format='%.1f',
                    on_change=lambda e: self._on_location_input_change()
                ).classes('w-28').props('dense')

                # Quick location presets
                ui.button(
                    'Villanova',
                    icon='location_on',
                    on_click=lambda: self.set_location(40.03784, -75.34238)
                ).props('flat dense').classes('text-xs')

                ui.button(
                    'North Pole',
                    icon='ac_unit',
                    on_click=lambda: self.set_location(90.0, 0.0)
                ).props('flat dense').classes('text-xs')

                ui.button(
                    'Equator',
                    icon='brightness_high',
                    on_click=lambda: self.set_location(0.0, 0.0)
                ).props('flat dense').classes('text-xs')

                # Spacer
                ui.element('div').classes('flex-grow')

                # Time controls
                ui.label('Time:').classes('text-white font-medium')
                ui.button('Now', icon='schedule', on_click=self._set_time_now).props('flat dense').classes('text-xs')
                ui.button('+1h', on_click=lambda: self._adjust_time(hours=1)).props('flat dense').classes('text-xs')
                ui.button('+1d', on_click=lambda: self._adjust_time(days=1)).props('flat dense').classes('text-xs')

                # # Status indicator
                # with ui.element('div').classes('flex items-center gap-1'):
                #     self._ready_indicator = ui.icon('circle', size='xs').classes('text-yellow-500')
                #     ui.label('Local Engine').classes('text-xs text-gray-400')

    def _inject_init_script(self):
        """Inject JavaScript to initialize the Stellarium engine."""
        config = self._config

        args = json.dumps({
            'widgetId': self.widget_id,
            'canvasId': self.canvas_id,
            'latitude': self.state.latitude,
            'longitude': self.state.longitude,
            'jsUrl': config.js_url,
            'wasmUrl': config.wasm_url,
            'dataUrl': config.data_url,
        })

        # Add script to head (NiceGUI deduplicates by content, so this is safe to call multiple times)
        ui.add_head_html(f'<script src="{config.init_script_url}"></script>')

        # Initialize the widget (the script handles queuing if not yet loaded)
        ui.run_javascript(f'initStellariumWidget({args});')

        # Set up a timer to check for ready state and update UI
        self._check_timer = ui.timer(0.5, self._check_engine_ready)

    async def _check_engine_ready(self):
        """Check if the engine is ready and update the UI accordingly."""
        try:
            if await self._bridge.is_ready():
                self.state.is_ready = True
                if self._status_label:
                    self._status_label.set_text('Stellarium ready')
                    self._status_label.classes('text-green-400', remove='text-gray-400')
                if self._ready_indicator:
                    self._ready_indicator.classes('text-green-500', remove='text-yellow-500')
                # Stop the timer
                if self._check_timer:
                    self._check_timer.cancel()
        except Exception as e:
            # Engine not ready yet, keep waiting
            pass

    def _on_location_input_change(self):
        """Handle manual location input changes."""
        if self._lat_input and self._lon_input:
            lat = self._lat_input.value or 0
            lon = self._lon_input.value or 0
            self.set_location(lat, lon)

    # =========================================================================
    # Public API - Location and Time Control
    # =========================================================================

    def set_location(self, latitude: float, longitude: float, altitude: float = 0.0):
        """
        Set the observer's location.

        Args:
            latitude: Latitude in degrees (-90 to 90)
            longitude: Longitude in degrees (-180 to 180)
            altitude: Altitude in meters above sea level
        """
        self.state.latitude = max(-90, min(90, latitude))
        self.state.longitude = max(-180, min(180, longitude))
        self.state.altitude = altitude

        # Update input fields if they exist
        if self._lat_input:
            self._lat_input.value = self.state.latitude
        if self._lon_input:
            self._lon_input.value = self.state.longitude

        # Update status labels
        if hasattr(self, '_lat_label') and self._lat_label:
            self._lat_label.set_text(f'Lat: {self.state.latitude:.1f}°')
        if hasattr(self, '_lon_label') and self._lon_label:
            self._lon_label.set_text(f'Lon: {self.state.longitude:.1f}°')

        # Send to Stellarium engine
        self._bridge.set_location(self.state.latitude, self.state.longitude)

    def set_datetime(self, dt: datetime):
        """
        Set the observation date/time.

        Args:
            dt: datetime object (will be converted to UTC)
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        self.state.datetime_utc = dt

        # Convert to timestamp for JavaScript
        timestamp_ms = dt.timestamp() * 1000
        self._bridge.set_datetime(timestamp_ms)

    def _set_time_now(self):
        """Set time to current real time."""
        self.set_datetime(datetime.now(timezone.utc))

    def _adjust_time(self, hours: int = 0, days: int = 0):
        """Adjust time by the specified amount."""
        from datetime import timedelta
        current = self.state.datetime_utc or datetime.now(timezone.utc)
        new_time = current + timedelta(hours=hours, days=days)
        self.set_datetime(new_time)

    # =========================================================================
    # Public API - View Control
    # =========================================================================

    def look_at_object(self, object_name: str):
        """
        Center the view on a named object.

        Args:
            object_name: Name of the object (e.g., "NAME Polaris", "NAME Jupiter")
        """
        self._bridge.look_at_object(object_name)

    def set_fov(self, fov_degrees: float):
        """
        Set the field of view.

        Args:
            fov_degrees: Field of view in degrees
        """
        self.state.fov = fov_degrees
        self._bridge.set_fov(fov_degrees)

    # =========================================================================
    # Public API - Layer Visibility
    # =========================================================================

    def set_constellation_lines(self, visible: bool):
        """Show or hide constellation lines."""
        self._bridge.set_constellation_lines(visible)

    def set_atmosphere(self, visible: bool):
        """Show or hide the atmosphere."""
        self._bridge.set_atmosphere(visible)

    def set_landscape(self, visible: bool):
        """Show or hide the landscape/horizon."""
        self._bridge.set_landscape(visible)

    def set_azimuthal_grid(self, visible: bool):
        """Show or hide the azimuthal (alt-az) grid."""
        self._bridge.set_azimuthal_grid(visible)

    def set_equatorial_grid(self, visible: bool):
        """Show or hide the equatorial grid."""
        self._bridge.set_equatorial_grid(visible)

    # =========================================================================
    # Public API - Query Functions (async)
    # =========================================================================

    async def get_object_altitude(self, object_name: str) -> Optional[float]:
        """
        Get the altitude of a celestial object above the horizon.

        Args:
            object_name: Name of the object (e.g., "NAME Polaris", "NAME Sun")

        Returns:
            Altitude in degrees, or None if object not found
        """
        return await self._bridge.get_object_altitude(object_name)


# =============================================================================
# Convenience Functions
# =============================================================================

def create_stellarium_view(
    latitude: float = 40.03784,
    longitude: float = -75.34238,
    height: str = "500px",
    show_controls: bool = True,
    show_status_bar: bool = True,
    config: Optional[StellariumConfig] = None,
) -> StellariumWidget:
    """
    Convenience function to create and render a Stellarium widget.

    Usage:
        stellarium = create_stellarium_view()
        # Widget is automatically rendered

        # Later:
        stellarium.set_location(45.0, -93.0)

    Returns:
        The StellariumWidget instance for later control
    """
    widget = StellariumWidget(
        height=height,
        show_controls=show_controls,
        show_status_bar=show_status_bar,
        config=config,
    )

    widget.set_location(latitude, longitude)
    widget.render()

    return widget
