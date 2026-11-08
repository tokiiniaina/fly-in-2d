"""The textual head-up display of the simulation screen."""

from collections.abc import Callable
from typing import Any

from ursina import Entity, destroy

from flyin.src.map_data import MapData
from flyin.src.viewer import theme
from flyin.src.viewer.adapters.simulation_adapter import (
    SimulationResult,
    TurnState,
)
from flyin.src.viewer.layout import fit_size
from flyin.src.viewer.playback import PlaybackController
from flyin.src.viewer.shapes import label, rounded_block
from flyin.src.viewer.ui.controls import TextButton

HUD_WIDTH = 0.40
HUD_HEIGHT = 0.94
LEGEND: tuple[tuple[str, str], ...] = (
    ("start", "START"), ("end", "END"), ("normal", "NORMAL"),
    ("priority", "PRIORITY"), ("restricted", "RESTRICTED"),
    ("blocked", "BLOCKED"),
)


class HudActions:
    """Callbacks triggered by the HUD buttons."""

    def __init__(self, play: Callable[[], None],
                 pause: Callable[[], None],
                 restart: Callable[[], None],
                 slower: Callable[[], None],
                 faster: Callable[[], None],
                 back: Callable[[], None],
                 quit_app: Callable[[], None]) -> None:
        """Store one callback per button."""
        self.play = play
        self.pause = pause
        self.restart = restart
        self.slower = slower
        self.faster = faster
        self.back = back
        self.quit_app = quit_app


class Hud:
    """Left panel: counters, playback controls, speed, map and quit."""

    def __init__(self, parent: Any, data: MapData, map_label: str,
                 actions: HudActions) -> None:
        """Build the panel; call `place` then `refresh` to use it."""
        self.root = Entity(parent=parent)
        self.buttons: dict[str, TextButton] = {}
        left = HUD_WIDTH / 2
        rounded_block(self.root, left, 0, HUD_WIDTH, HUD_HEIGHT, 0.04,
                      theme.PANEL, 1.0)
        x0 = 0.04
        label(self.root, "FLY-IN", x0, 0.40, 2.3, theme.TEXT,
              origin=(-0.5, 0))
        self._turn = label(self.root, "", x0, 0.30, 1.0, theme.TEXT,
                           origin=(-0.5, 0))
        self._left = label(self.root, "", x0, 0.25, 1.0, theme.TEXT,
                           origin=(-0.5, 0))
        self._done = label(self.root, "", x0, 0.20, 1.0, theme.TEXT,
                           origin=(-0.5, 0))
        self._status = label(self.root, "", x0, 0.15, 1.0, theme.ACCENT,
                             origin=(-0.5, 0))
        self._build_controls(actions, map_label)
        self._build_legend(data)

    def _build_controls(self, actions: HudActions, map_label: str) -> None:
        """Create the PLAY/PAUSE/RESTART row, speed, MAP and QUIT."""
        add = self._button
        add("play", "PLAY", 0.09, 0.06, 0.10, actions.play)
        add("pause", "PAUSE", 0.20, 0.06, 0.11, actions.pause)
        add("restart", "RESTART", 0.32, 0.06, 0.13, actions.restart)
        label(self.root, "SPEED:", 0.04, -0.02, 1.0, theme.MUTED,
              origin=(-0.5, 0))
        add("slower", "-", 0.18, -0.02, 0.05, actions.slower, 1.4)
        self._speed = label(self.root, "1x", 0.26, -0.02, 1.0, theme.TEXT)
        add("faster", "+", 0.34, -0.02, 0.05, actions.faster, 1.4)
        map_text = f"MAP: {map_label}"
        self.map_button = self._button(
            "map", map_text, 0.20, -0.10, 0.36, actions.back,
            fit_size(map_text, 1.0, 0.30))
        self._check = label(self.root, "", 0.04, -0.155, 0.8, theme.MUTED,
                            origin=(-0.5, 0))
        add("quit", "QUIT", 0.07, -0.22, 0.10, actions.quit_app)

    def _button(self, key: str, text: str, x: float, y: float,
                width: float, action: Callable[[], None],
                size: float = 1.0) -> TextButton:
        """Create a button and remember it under `key`."""
        button = TextButton(self.root, text, x, y, width, 0.05, action,
                            size)
        self.buttons[key] = button
        return button

    def _build_legend(self, data: MapData) -> None:
        """List only the zone kinds that exist on this map."""
        present = {z.zone_type for z in data.zones.values()}
        present |= {"start", "end"}
        kinds = [item for item in LEGEND if item[0] in present]
        for index, (kind, text) in enumerate(kinds):
            col, row = divmod(index, 3)
            x = 0.05 + col * 0.17
            y = -0.31 - row * 0.05
            rounded_block(self.root, x, y, 0.03, 0.03, 0.008,
                          theme.ZONE_FILL[kind], 0.0)
            label(self.root, text, x + 0.028, y, 0.68, theme.MUTED,
                  origin=(-0.5, 0))

    def place(self, aspect: float) -> None:
        """Anchor the panel to the left edge of the window."""
        self.root.position = (-aspect / 2 + 0.02, 0, 0)

    def refresh(self, controller: PlaybackController, state: TurnState,
                result: SimulationResult) -> None:
        """Show the real simulation numbers."""
        total = result.data.nb_drones
        self._turn.text = (f"TURN: {state.index:02d} / "
                           f"{controller.total_turns:02d}")
        self._left.text = f"DRONES LEFT: {total - state.delivered:02d}"
        self._done.text = f"DELIVERED: {state.delivered:02d}"
        self._status.text = f"STATUS: {controller.status.value}"
        self._speed.text = controller.speed_label
        self._check.text = ("OUTPUT: VALID" if result.valid
                            else "OUTPUT: INVALID")

    def destroy(self) -> None:
        """Remove the panel."""
        destroy(self.root)
