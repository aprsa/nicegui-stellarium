"""nicegui-stellarium: Interactive planetarium widget for NiceGUI."""

from .stellarium_widget import (
    StellariumWidget,
    StellariumConfig,
    StellariumState,
    create_stellarium_view,
)
from .stellarium_bridge import StellariumBridge

__version__ = "0.1.0"

__all__ = [
    "StellariumWidget",
    "StellariumConfig",
    "StellariumState",
    "StellariumBridge",
    "create_stellarium_view",
]
