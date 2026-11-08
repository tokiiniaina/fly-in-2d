"""Main menu: choose a map and a drone, then play."""

from ursina import Entity

from flyin.src.engine import FlyInError
from flyin.src.viewer import theme
from flyin.src.viewer.animation import hover
from flyin.src.viewer.adapters.simulation_adapter import SimulationAdapter
from flyin.src.viewer.catalog import MapEntry
from flyin.src.viewer.entities.drone import DroneView
from flyin.src.viewer.entities.network import NetworkView
from flyin.src.viewer.layout import Rect, fit_size
from flyin.src.viewer.screens.base import Screen, ScreenHost
from flyin.src.viewer.shapes import clean, label, rounded_block, tint
from flyin.src.viewer.ui.controls import Selector, TextButton

CARD_WIDTH = 0.58
CARD_HEIGHT = 0.90
MAX_ERROR_CHARS = 50
SPRITE_Y = -0.175


class MenuScreen(Screen):
    """Browse the real map files and the drone sprites."""

    def __init__(self, host: ScreenHost, message: str = "") -> None:
        """Remember an optional message to show under the buttons."""
        super().__init__(host)
        self._message = message
        self._preview: NetworkView | None = None
        self._play: TextButton | None = None
        self._sprite: DroneView | None = None
        self._intro = True
        self._clock = 0.0

    def build(self, aspect: float) -> None:
        """Draw the card, the selectors and the map preview."""
        session = self.host.session
        self._preview = None
        cx = -aspect / 2 + 0.04 + CARD_WIDTH / 2
        card = Entity(parent=self.root, position=(cx, 0, 0))
        rounded_block(card, 0, 0, CARD_WIDTH, CARD_HEIGHT, 0.05,
                      theme.PANEL, 1.0)
        label(card, "FLY-IN", 0, 0.34, 3.4, theme.TEXT)
        label(card, "MAP", 0, 0.21, 0.9, theme.MUTED)
        self._maps = Selector(card, 0, 0.15, 0.46,
                              lambda: self._browse_map(-1),
                              lambda: self._browse_map(1))
        self._info = label(card, "", 0, 0.095, 0.75, theme.MUTED)
        label(card, "DRONE", 0, -0.02, 0.9, theme.MUTED)
        self._skins = Selector(card, 0, -0.075, 0.46,
                               lambda: self._browse_skin(-1),
                               lambda: self._browse_skin(1))
        self._sprite = DroneView(
            card, 0, session.texture(session.skin), session.skin.aspect,
            0.12)
        self._sprite.place(0, SPRITE_Y)
        self._play = TextButton(card, "PLAY", 0, -0.275, 0.2, 0.06,
                                self._start, 1.7)
        TextButton(card, "QUIT", 0, -0.34, 0.2, 0.06, self.host.quit, 1.2)
        self._notice = label(card, self._message, 0, -0.405, 0.7,
                             theme.WARN)
        left = cx + CARD_WIDTH / 2 + 0.04
        right = aspect / 2 - 0.04
        self._area = Rect((left + right) / 2, 0, max(right - left, 0.2),
                          0.88)
        self._refresh(self._intro)
        self._intro = False

    def update(self, dt: float) -> None:
        """Make the sample drone float, and advance the preview."""
        self._clock += dt
        if self._sprite is not None:
            lift = hover(self._clock, 0.0, 0.006) + 0.006
            self._sprite.apply(0, SPRITE_Y, True, lift=lift)
        if self._preview is not None:
            self._preview.update(dt)
        super().update(dt)

    def on_key(self, key: str) -> None:
        """Arrow keys browse, enter plays."""
        actions = {
            "left arrow": lambda: self._browse_map(-1),
            "right arrow": lambda: self._browse_map(1),
            "up arrow": lambda: self._browse_skin(-1),
            "down arrow": lambda: self._browse_skin(1),
            "enter": self._start,
        }
        action = actions.get(key)
        if action is not None:
            action()

    def _browse_map(self, delta: int) -> None:
        """Select another map."""
        self.host.session.move_map(delta)
        self._message = ""
        self._refresh(True)

    def _browse_skin(self, delta: int) -> None:
        """Select another drone sprite."""
        self.host.session.move_skin(delta)
        self._refresh(False)

    def _refresh(self, animate: bool) -> None:
        """Update the texts, the sprite and the preview."""
        session = self.host.session
        entry = session.entry
        skin = session.skin
        name = "NO MAP FOUND" if entry is None else entry.name
        self._maps.value.scale = fit_size(name, 1.2, 0.36)
        self._maps.set_value(name)
        self._skins.set_value(skin.name)
        if self._sprite is not None:
            self._sprite.set_texture(session.texture(skin))
        valid = entry is not None and entry.valid
        if entry is None:
            text = "ADD MAP FILES TO THE maps FOLDER"
        else:
            text = entry.summary()[:MAX_ERROR_CHARS]
        self._info.text = clean(text)
        self._info.scale = fit_size(text, 0.75, 0.52)
        self._info.color = tint(theme.MUTED if valid else theme.WARN)
        self._show_notice()
        if self._play is not None:
            self._play.set_enabled(valid)
        self._draw_preview(entry, animate)

    def _show_notice(self) -> None:
        """Show the error or message line under the buttons."""
        self._notice.text = clean(self._message)
        self._notice.scale = fit_size(self._message, 0.7, 0.52)

    def _draw_preview(self, entry: MapEntry | None,
                      animate: bool) -> None:
        """Draw the selected map WITHOUT drones (zones pop in)."""
        if self._preview is not None:
            self._preview.destroy()
            self._preview = None
        if entry is not None and entry.valid:
            assert entry.data is not None
            self._preview = NetworkView(self.root, entry.data, self._area,
                                        intro=animate)

    def _start(self) -> None:
        """Run the backend on the selected map and open the simulation."""
        entry = self.host.session.entry
        if entry is None or not entry.valid:
            return
        try:
            result = SimulationAdapter().run(str(entry.path))
        except (OSError, ValueError, FlyInError) as error:
            self._message = f"ERROR: {error}"[:MAX_ERROR_CHARS + 20]
            self._show_notice()
            return
        self.host.open_simulation(result)
