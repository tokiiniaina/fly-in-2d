"""Ursina application: window, background, screen switching."""

from collections.abc import Callable
from pathlib import Path
from time import perf_counter

from PIL import Image
from ursina import (
    Entity,
    Texture,
    Ursina,
    application,
    camera,
    window,
)

from flyin.src.engine import FlyInError
from flyin.src.viewer import theme
from flyin.src.viewer.adapters.simulation_adapter import (
    SimulationAdapter,
    SimulationResult,
)
from flyin.src.viewer.catalog import DroneCatalog, MapCatalog
from flyin.src.viewer.layout import cover_scale
from flyin.src.viewer.paths import BACKGROUND_PATH
from flyin.src.viewer.screens.base import Screen
from flyin.src.viewer.screens.menu import MenuScreen
from flyin.src.viewer.screens.simulation import SimulationScreen
from flyin.src.viewer.session import ViewerSession
from flyin.src.viewer.shapes import tint

MAX_FRAME = 0.1


class _Driver(Entity):
    """Receives the Ursina frame and key events for the active screen."""

    def __init__(self, app: "ViewerApp") -> None:
        """Keep the application and start the frame clock."""
        super().__init__()
        self._app = app
        self._last = perf_counter()

    def update(self) -> None:
        """Called by Ursina every frame."""
        now = perf_counter()
        elapsed = min(now - self._last, MAX_FRAME)
        self._last = now
        self._app.tick(elapsed)

    def input(self, key: str) -> None:
        """Called by Ursina for every key and mouse event."""
        self._app.on_key(key)


class ViewerApp:
    """The graphical front end of Fly-in."""

    def __init__(self, start_map: str | None = None) -> None:
        """Optionally open a map directly instead of the menu."""
        self._start_map = start_map
        self._screen: Screen | None = None
        self._pending: Callable[[], Screen] | None = None
        self._background: Entity | None = None
        self._background_aspect = 1.0
        self._applied_aspect = 0.0
        self.session = ViewerSession(maps=[], skins=[])

    def run(self) -> int:
        """Open the window and run until it is closed.

        Raises:
            FileNotFoundError: If a sprite or the background is missing.
            ValueError: If the map given at start cannot be simulated.
            OSError: If the map given at start cannot be read.
        """
        skins = DroneCatalog().discover()
        if not BACKGROUND_PATH.is_file():
            raise FileNotFoundError(f"missing '{BACKGROUND_PATH}'")
        first = None
        startup_error = ""
        if self._start_map is not None:
            try:
                first = SimulationAdapter().run(self._start_map)
            except (OSError, ValueError, FlyInError) as error:
                startup_error = f"ERROR: {error}"
        engine = Ursina(title="Fly-in", borderless=False,
                        development_mode=False)
        self._configure_window()
        self.session = ViewerSession(MapCatalog().discover(), skins)
        self._make_background()
        self._driver = _Driver(self)
        if first is None:
            self.open_menu(startup_error)
        else:
            self._select(self._start_map)
            self.open_simulation(first)
        self._apply_pending()
        engine.run()
        return 0

    @staticmethod
    def _configure_window() -> None:
        """Set the window and the 2D orthographic camera."""
        window.exit_button.visible = False
        window.fps_counter.enabled = False
        window.color = tint(theme.SAND)
        camera.orthographic = True
        camera.fov = 10

    def _make_background(self) -> None:
        """Create the desert background, scaled to cover the window."""
        with Image.open(BACKGROUND_PATH) as image:
            self._background_aspect = image.width / image.height
        self._background = Entity(
            parent=camera.ui, model="quad",
            texture=Texture(BACKGROUND_PATH), z=theme.Z_BACKGROUND)
        self._fit_background()

    def _fit_background(self) -> None:
        """Rescale the background for the current window shape."""
        aspect = window.aspect_ratio
        if self._background is None or aspect == self._applied_aspect:
            return
        width, height = cover_scale(aspect, self._background_aspect)
        self._background.scale = (width, height)
        self._applied_aspect = aspect

    def _select(self, map_path: str | None) -> None:
        """Select the catalog entry matching a map path."""
        if map_path is None:
            return
        wanted = Path(map_path).resolve()
        for index, entry in enumerate(self.session.maps):
            if entry.path.resolve() == wanted:
                self.session.map_index = index
                return
        self.session.maps.append(MapCatalog().load(wanted))
        self.session.map_index = len(self.session.maps) - 1

    def _apply_pending(self) -> None:
        """Replace the active screen by the queued one, if any."""
        factory, self._pending = self._pending, None
        if factory is None:
            return
        if self._screen is not None:
            self._screen.close()
        self._screen = factory()
        self._screen.show()

    def open_menu(self, message: str = "") -> None:
        """Show the main menu (on the next frame)."""
        current = self.session.entry
        maps = MapCatalog().discover()
        self.session.maps = maps
        if current is not None:
            for index, entry in enumerate(maps):
                if entry.path.resolve() == current.path.resolve():
                    self.session.map_index = index
                    break
            else:
                self.session.map_index = 0
        else:
            self.session.map_index = 0
        self._pending = lambda: MenuScreen(self, message)

    def open_simulation(self, result: SimulationResult) -> None:
        """Show the simulation of a backend result (next frame)."""
        entry = self.session.entry
        if entry is None:
            self.open_menu("ERROR: map not in the catalog")
            return
        skin = self.session.skin
        self._pending = lambda: SimulationScreen(self, entry, skin, result)

    def quit(self) -> None:
        """Close the application."""
        application.quit()

    def tick(self, dt: float) -> None:
        """Forward a frame to the active screen."""
        self._fit_background()
        self._apply_pending()
        if self._screen is not None:
            self._screen.update(dt)

    def on_key(self, key: str) -> None:
        """Forward a key press to the active screen."""
        if self._screen is not None:
            self._screen.on_key(key)
