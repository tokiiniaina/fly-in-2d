"""Common behavior of the screens: build, rebuild on resize, close."""

from abc import ABC, abstractmethod
from typing import Protocol

from ursina import Entity, camera, destroy, window

from flyin.src.viewer.adapters.simulation_adapter import SimulationResult
from flyin.src.viewer.session import ViewerSession

RESIZE_DELAY = 0.15


class ScreenHost(Protocol):
    """What a screen may ask the application to do."""

    session: ViewerSession

    def open_menu(self, message: str = "") -> None:
        """Go back to the menu, optionally with a message."""

    def open_simulation(self, result: SimulationResult) -> None:
        """Show the simulation of a backend result."""

    def quit(self) -> None:
        """Close the application."""


class Screen(ABC):
    """A full-window screen drawn under camera.ui."""

    def __init__(self, host: ScreenHost) -> None:
        """Create the root entity; call `show` to draw."""
        self.host = host
        self.root = Entity(parent=camera.ui)
        self._built_aspect = 0.0
        self._waited = 0.0
        self._rebuild_requested = False

    @abstractmethod
    def build(self, aspect: float) -> None:
        """Create every entity for a window of this aspect ratio."""

    def show(self) -> None:
        """Draw the screen for the current window size."""
        self._rebuild(window.aspect_ratio)

    def request_rebuild(self) -> None:
        """Rebuild on the next frame (never inside an Ursina callback)."""
        self._rebuild_requested = True

    def update(self, dt: float) -> None:
        """Rebuild when asked, or once the window size stopped changing."""
        aspect = window.aspect_ratio
        if self._rebuild_requested:
            self._rebuild(aspect)
            return
        if abs(aspect - self._built_aspect) < 1e-3:
            self._waited = 0.0
            return
        self._waited += dt
        if self._waited >= RESIZE_DELAY:
            self._rebuild(aspect)

    def on_key(self, key: str) -> None:
        """Handle a key press (nothing by default)."""

    def close(self) -> None:
        """Remove the screen."""
        destroy(self.root)

    def _rebuild(self, aspect: float) -> None:
        """Clear the screen and build it again."""
        for child in list(self.root.children):
            destroy(child)
        self._built_aspect = aspect
        self._waited = 0.0
        self._rebuild_requested = False
        self.build(aspect)
