"""
Stellarium Bridge

A thin wrapper that translates Python method calls to JavaScript for controlling
the Stellarium Web Engine. This keeps all JS generation logic in one place and
provides a clean Pythonic API.
"""

import json
import logging
from typing import Optional
from nicegui import ui

logger = logging.getLogger(__name__)


class StellariumBridge:
    """
    Bridge between Python and the Stellarium Web Engine JavaScript API.

    This class encapsulates all JavaScript communication, providing type-safe
    Python methods that translate to the appropriate JS calls.

    Usage:
        bridge = StellariumBridge("stel_1")
        bridge.set_location(40.0, -75.0)
        bridge.set_constellation_lines(True)

        # For queries (async):
        altitude = await bridge.get_object_altitude("NAME Polaris")
    """

    def __init__(self, widget_id: str):
        """
        Initialize the bridge.

        Args:
            widget_id: The unique identifier for the widget instance.
                       Used to reference window.{widget_id}_stel in JS.
        """
        self.widget_id = widget_id
        self._stel_ref = f"window.{widget_id}_stel"

    def _run(self, js: str) -> None:
        """
        Execute JavaScript if the engine is ready.

        Args:
            js: JavaScript code to execute. Can reference 'stel' variable.
        """
        ui.run_javascript(f'''
            (function() {{
                var stel = {self._stel_ref};
                if (!stel) return;
                {js}
            }})();
        ''')

    async def _query(self, js: str):
        """
        Execute JavaScript and return the result.

        Args:
            js: JavaScript expression to evaluate. Can reference 'stel' variable.
                Should return a value.

        Returns:
            The result of the JavaScript expression, or None if engine not ready.
        """
        try:
            return await ui.run_javascript(f'''
                (function() {{
                    var stel = {self._stel_ref};
                    if (!stel) return null;
                    {js}
                }})()
            ''')
        except Exception as e:
            logger.warning(f"[{self.widget_id}] JS query failed: {e}")
            return None

    async def is_ready(self) -> bool:
        """Check if the Stellarium engine is initialized and ready."""
        result = await ui.run_javascript(f'window.{self.widget_id}_ready === true')
        return result is True

    # =========================================================================
    # Location and Time
    # =========================================================================

    def set_location(self, latitude: float, longitude: float) -> None:
        """
        Set the observer's location.

        Args:
            latitude: Latitude in degrees (-90 to 90)
            longitude: Longitude in degrees (-180 to 180)
        """
        self._run(f'''
            stel.observer.latitude = {latitude} * stel.D2R;
            stel.observer.longitude = {longitude} * stel.D2R;
        ''')

    def set_datetime(self, timestamp_ms: float) -> None:
        """
        Set the observation date/time.

        Args:
            timestamp_ms: Unix timestamp in milliseconds
        """
        self._run(f'''
            var mjd = stel.date2MJD({timestamp_ms});
            stel.observer.utc = mjd;
        ''')

    # =========================================================================
    # View Control
    # =========================================================================

    def look_at_object(self, object_name: str) -> None:
        """
        Center the view on a named celestial object.

        Args:
            object_name: Name of the object (e.g., "NAME Polaris", "NAME Jupiter")
        """
        # Escape the object name for JS string
        safe_name = json.dumps(object_name)
        self._run(f'''
            var obj = stel.getObj({safe_name});
            if (obj) {{
                stel.core.selection = obj;
                stel.pointAndLock(obj);
            }}
        ''')

    def set_fov(self, fov_degrees: float) -> None:
        """
        Set the field of view.

        Args:
            fov_degrees: Field of view in degrees
        """
        self._run(f'stel.core.fov = {fov_degrees} * stel.D2R;')

    # =========================================================================
    # Layer Visibility
    # =========================================================================

    def set_constellation_lines(self, visible: bool) -> None:
        """Show or hide constellation lines."""
        self._run(f'stel.core.constellations.lines_visible = {str(visible).lower()};')

    def set_constellation_labels(self, visible: bool) -> None:
        """Show or hide constellation labels."""
        self._run(f'stel.core.constellations.labels_visible = {str(visible).lower()};')

    def set_atmosphere(self, visible: bool) -> None:
        """Show or hide the atmosphere."""
        self._run(f'stel.core.atmosphere.visible = {str(visible).lower()};')

    def set_landscape(self, visible: bool) -> None:
        """Show or hide the landscape/horizon."""
        self._run(f'stel.core.landscapes.visible = {str(visible).lower()};')

    def set_azimuthal_grid(self, visible: bool) -> None:
        """Show or hide the azimuthal (alt-az) grid."""
        self._run(f'stel.core.lines.azimuthal.visible = {str(visible).lower()};')

    def set_equatorial_grid(self, visible: bool) -> None:
        """Show or hide the equatorial grid."""
        self._run(f'stel.core.lines.equatorial.visible = {str(visible).lower()};')

    def set_milkyway(self, visible: bool) -> None:
        """Show or hide the Milky Way."""
        self._run(f'stel.core.milkyway.visible = {str(visible).lower()};')

    # =========================================================================
    # Queries (async)
    # =========================================================================

    async def get_object_altitude(self, object_name: str) -> Optional[float]:
        """
        Get the altitude of a celestial object above the horizon.

        Args:
            object_name: Name of the object (e.g., "NAME Polaris", "NAME Sun")

        Returns:
            Altitude in degrees, or None if object not found
        """
        safe_name = json.dumps(object_name)
        return await self._query(f'''
            var obj = stel.getObj({safe_name});
            if (!obj) return null;

            var pvo = obj.getInfo('pvo', stel.observer);
            if (!pvo) return null;

            var observed = stel.convertFrame(stel.observer, 'ICRF', 'OBSERVED', pvo[0]);
            var azalt = stel.c2s(observed);
            var alt = stel.anp(azalt[1]) / stel.D2R;

            // Normalize to -180 to 180 range
            if (alt > 180) alt -= 360;

            return alt;
        ''')

    async def get_object_azimuth(self, object_name: str) -> Optional[float]:
        """
        Get the azimuth of a celestial object.

        Args:
            object_name: Name of the object (e.g., "NAME Polaris", "NAME Sun")

        Returns:
            Azimuth in degrees (0-360, North=0, East=90), or None if not found
        """
        safe_name = json.dumps(object_name)
        return await self._query(f'''
            var obj = stel.getObj({safe_name});
            if (!obj) return null;

            var pvo = obj.getInfo('pvo', stel.observer);
            if (!pvo) return null;

            var observed = stel.convertFrame(stel.observer, 'ICRF', 'OBSERVED', pvo[0]);
            var azalt = stel.c2s(observed);
            var az = stel.anp(azalt[0]) / stel.D2R;

            return az;
        ''')
