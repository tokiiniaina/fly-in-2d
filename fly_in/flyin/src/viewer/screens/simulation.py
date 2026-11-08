"""Simulation screen: the network, the drones and the textual HUD."""

from flyin.src.viewer.adapters.simulation_adapter import (
    SimulationAdapter,
    SimulationResult,
)
from flyin.src.viewer.catalog import DroneSkin, MapEntry
from flyin.src.viewer.entities.network import NetworkView
from flyin.src.viewer.layout import Rect
from flyin.src.viewer.playback import PlaybackController, PlaybackStatus
from flyin.src.viewer.screens.base import Screen, ScreenHost
from flyin.src.viewer.ui.hud import HUD_WIDTH, Hud, HudActions


class SimulationScreen(Screen):
    """Replay a backend result turn by turn."""

    def __init__(self, host: ScreenHost, entry: MapEntry,
                 skin: DroneSkin, result: SimulationResult) -> None:
        """Start playing the result right away."""
        super().__init__(host)
        self._entry = entry
        self._skin = skin
        self._result = result
        self._controller = PlaybackController(result.timeline.total_turns)
        self._controller.play()
        self._network: NetworkView | None = None
        self._hud: Hud | None = None
        self._intro = True

    @property
    def controller(self) -> PlaybackController:
        """The playback state (turn, speed, status)."""
        return self._controller

    def build(self, aspect: float) -> None:
        """Draw the HUD on the left and the network on the right."""
        self._network = None
        left = -aspect / 2 + HUD_WIDTH + 0.06
        right = aspect / 2 - 0.03
        area = Rect((left + right) / 2, 0, max(right - left, 0.3), 0.92)
        session = self.host.session
        self._network = NetworkView(
            self.root, self._result.data, area, self._skin,
            session.texture(self._skin), intro=self._intro)
        self._intro = False
        actions = HudActions(
            play=self._play, pause=self._pause, restart=self._restart,
            slower=self._slower, faster=self._faster,
            back=self.host.open_menu, quit_app=self.host.quit)
        self._hud = Hud(self.root, self._result.data, self._entry.label,
                        actions)
        self._hud.place(aspect)
        self._refresh()

    def update(self, dt: float) -> None:
        """Advance the playback, then handle window resizing."""
        if self._controller.tick(dt):
            self._refresh(animate=True)
        if self._network is not None:
            self._network.update(dt)
        super().update(dt)

    def on_key(self, key: str) -> None:
        """Keyboard shortcuts mirroring the buttons."""
        if key == "space":
            self._controller.toggle()
        elif key == "r":
            self._restart()
            return
        elif key == "escape":
            self.host.open_menu()
            return
        elif key == "left arrow":
            self._controller.step(-1)
            self._refresh(animate=True)
            return
        elif key == "right arrow":
            self._controller.step(1)
            self._refresh(animate=True)
            return
        elif key == "up arrow":
            self._controller.faster()
        elif key == "down arrow":
            self._controller.slower()
        else:
            return
        self._refresh()

    def _play(self) -> None:
        """PLAY: start or resume."""
        self._controller.play()
        self._refresh()

    def _pause(self) -> None:
        """PAUSE: freeze on the current turn."""
        self._controller.pause()
        self._refresh()

    def _slower(self) -> None:
        """SPEED -: show each turn longer."""
        self._controller.slower()
        self._refresh()

    def _faster(self) -> None:
        """SPEED +: show each turn shorter."""
        self._controller.faster()
        self._refresh()

    def _restart(self) -> None:
        """RESTART: run the backend again, then replay from turn 0."""
        try:
            result = SimulationAdapter().run(str(self._entry.path))
        except (OSError, ValueError) as error:
            self.host.open_menu(f"ERROR: {error}")
            return
        self._result = result
        speed = self._controller.speed_index
        self._controller = PlaybackController(
            result.timeline.total_turns, speed)
        self._controller.restart()
        self._intro = True
        self.request_rebuild()

    def _refresh(self, animate: bool = False) -> None:
        """Show the current turn from the real timeline.

        With `animate`, drones fly to their new place within the time one
        turn stays on screen; otherwise they jump there.
        """
        if self._network is None or self._hud is None:
            return
        state = self._result.timeline.state(self._controller.turn)
        duration = 0.0
        if animate:
            duration = max(0.06, self._controller.turn_seconds * 0.75)
        self._network.show_state(state, duration)
        self._hud.refresh(self._controller, state, self._result)
        status = self._controller.status
        self._hud.buttons["play"].set_active(
            status is PlaybackStatus.PLAYING)
        self._hud.buttons["pause"].set_active(
            status is PlaybackStatus.PAUSED)
