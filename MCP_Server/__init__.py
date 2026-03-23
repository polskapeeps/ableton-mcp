"""Ableton Live integration through the Model Context Protocol."""

__version__ = "1.1.0"

from .connection import AbletonConnection, get_ableton_connection

__all__ = ["AbletonConnection", "get_ableton_connection", "__version__"]
