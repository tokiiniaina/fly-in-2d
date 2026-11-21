"""Window, camera, modes and keys of the 3D viewer.

Two modes: BROWSE shows a map alone (arrows or keys change the map,
PLAY starts) and PLAY shows the drones flying the real simulation with
the HUD (turn, drones left, delivered, play/pause/restart, speed).
"""

from pathlib import Path
from typing import Any

from ursina import (
    Entity,
    Texture,
    Ursina,
    application,
    camera,
    destroy,
    window,
)

from flyin.src.map_data import MapData
from flyin.src.viewer.adapters.simulation_adapter import (
    SimulationAdapter,
    SimulationResult,
)
from flyin.src.viewer.catalog import MapCatalog, MapEntry
from flyin.src.viewer.layout import cover_scale, fit_size
from flyin.src.viewer.paths import ASSETS_DIR
from flyin.src.viewer.playback import PlaybackStatus
from flyin.src.viewer.shapes import clean, label, rounded_block, tint
from flyin.src.viewer.ui.controls import Selector, TextButton
from flyin.src.viewer.ui.hud import Hud, HudActions
from flyin.src.viewer3d.camera import (
    PITCH,
    YAW_START,
    approach_angle,
    fit_view,
    iso_axes,
)
from flyin.src.viewer3d.benchmarks import summary_lines, target_for
from flyin.src.viewer3d.scene import MapScene
from flyin.src.viewer3d.simulation3d import Simulation3D

BACKGROUND = "#070a1a"
BACKDROP_PATH = ASSETS_DIR / "background" / "space.jpg"
BACKDROP_ASPECT = 2048 / 1152
BACKDROP_DISTANCE = 700.0
CAMERA_DISTANCE = 80.0
ZOOM_STEP = 1.12
ZOOM_RANGE = (0.35, 2.5)
HUD_SHIFT = 0.12
HINT_BROWSE = "ENTER: PLAY     Q / E: ROTATE     SCROLL: ZOOM     ESC: QUIT"
HINT_PLAY = "SPACE: PLAY / PAUSE     R: RESTART     ESC: MAP"


class _Driver(Entity):
    """Receives Ursina's frame and key events."""

    def __init__(self, viewer: "Viewer3D") -> None:
        """Keep the viewer and the time of the previous frame."""
        super().__init__()
        self._viewer = viewer

    def update(self) -> None:
        """Called by Ursina every frame."""
        from time import perf_counter
        now = perf_counter()
        last = getattr(self, "_last", now)
        self._last = now
        self._viewer.tick(min(now - last, 0.1))

    def input(self, key: str) -> None:
        """Called by Ursina for every key and mouse event."""
        self._viewer.on_key(key)


class Viewer3D:
    """Browse the maps of the project and play them in isometric 3D."""

    def __init__(self, start_path: Path | None = None) -> None:
        """Optionally start on a given map file."""
        self._start_path = start_path
        self.entries: list[MapEntry] = []
        self.index = 0
        self.yaw = YAW_START
        self.shown_yaw = YAW_START
        self.zoom = 1.0
        self.mode = "browse"
        self.scene: MapScene | None = None
        self.sim: Simulation3D | None = None
        self.hud: Hud | None = None
        self.result: SimulationResult | None = None
        self._rig: Any = None
        self._backdrop: Any = None
        self._browse: Any = None
        self._title: Any = None
        self._hint: Any = None
        self._notice: Any = None
        self._info: Any = None
        self._summary: Any = None
        self._selector: Selector | None = None
        self._aspect = 0.0

    def run(self) -> int:
        """Open the window and run until it is closed.

        Raises:
            ValueError: If there is no valid map to show.
            FileNotFoundError: If the backdrop image is missing.
        """
        if not BACKDROP_PATH.is_file():
            raise FileNotFoundError(f"missing '{BACKDROP_PATH}'")
        self.entries = [e for e in MapCatalog().discover() if e.valid]
        self._select_start()
        if not self.entries:
            raise ValueError("no valid map to show in the maps folder")
        engine = Ursina(title="Fly-in 3D", borderless=False,
                        development_mode=False)
        window.color = tint(BACKGROUND)
        window.exit_button.visible = False
        window.fps_counter.enabled = False
        camera.orthographic = True
        camera.clip_plane_near = 0.5
        camera.clip_plane_far = 900
        self._rig = Entity()
        camera.parent = self._rig
        camera.position = (0, 0, -CAMERA_DISTANCE)
        camera.rotation = (0, 0, 0)
        self._backdrop = Entity(
            parent=camera, model="quad", texture=Texture(BACKDROP_PATH),
            position=(0, 0, BACKDROP_DISTANCE))
        self._build_browse_ui()
        self._driver = _Driver(self)
        self._load()
        engine.run()
        return 0

    def _build_browse_ui(self) -> None:
        """Title, hint, map selector and PLAY button (browse mode)."""
        self._browse = Entity(parent=camera.ui)
        self._title = label(self._browse, "", 0, 0, 1.3, "#e9e6ff",
                            origin=(-0.5, 0))
        self._hint = label(self._browse, HINT_BROWSE, 0, 0, 0.8,
                           "#9aa0c8", origin=(-0.5, 0))
        self._info = label(self._browse, "", 0, 0, 0.9, "#9aa0c8",
                           origin=(-0.5, 0))
        self._selector = Selector(self._browse, 0, -0.385, 0.62,
                                  lambda: self._change_map(-1),
                                  lambda: self._change_map(1), 1.1)
        TextButton(self._browse, "PLAY", 0, -0.45, 0.2, 0.07,
                   self.start_play, 1.8)
        self._notice = label(self._browse, "", 0, -0.335, 0.8, "#ff6b5e")

    def _select_start(self) -> None:
        """Find (or add) the map given at start."""
        if self._start_path is None:
            return
        wanted = self._start_path.resolve()
        for index, entry in enumerate(self.entries):
            if entry.path.resolve() == wanted:
                self.index = index
                return
        entry = MapCatalog().load(wanted)
        if entry.valid:
            self.entries.append(entry)
            self.index = len(self.entries) - 1

    def _change_map(self, step: int) -> None:
        """Select another map (browse mode only)."""
        if self.mode != "browse":
            return
        self.index = (self.index + step) % len(self.entries)
        self._load()

    def _load(self) -> None:
        """Build the scene of the selected map and frame it."""
        self._stop_play()
        if self.scene is not None:
            self.scene.destroy()
        entry = self.entries[self.index]
        data: MapData | None = entry.data
        if data is None:
            raise ValueError(f"map '{entry.path.name}' is not valid")
        self.scene = MapScene(data, entry.path.name)
        self.zoom = 1.0
        self._title.text = clean(
            f"{entry.label}   {self.index + 1}/{len(self.entries)}")
        if self._selector is not None:
            self._selector.value.scale = fit_size(entry.label, 1.1, 0.4)
            self._selector.set_value(entry.label)
        target = target_for(entry.path.name)
        extra = f" / TARGET {target} TURNS" if target is not None else ""
        self._info.text = clean(entry.summary() + extra)
        self._notice.text = clean("")
        self._place_hud(force=True)
        self._frame()

    def start_play(self) -> None:
        """Run the backend on the map, then show the drones flying."""
        if self.mode != "browse" or self.scene is None:
            return
        entry = self.entries[self.index]
        try:
            result = SimulationAdapter().run(str(entry.path))
        except (OSError, ValueError) as error:
            self._notice.text = clean(f"ERROR: {error}"[:70])
            return
        self._begin(result)

    def _begin(self, result: SimulationResult) -> None:
        """Switch to play mode with a backend result."""
        if self.scene is None:
            return
        self._stop_play()
        self.mode = "play"
        self.result = result
        self._browse.enabled = False
        self.sim = Simulation3D(self.scene, result)
        entry = self.entries[self.index]
        actions = HudActions(
            play=self._play, pause=self._pause, restart=self.restart,
            slower=self._slower, faster=self._faster, back=self.stop,
            quit_app=application.quit)
        self.hud = Hud(camera.ui, result.data, entry.label, actions)
        self._place_hud(force=True)
        self._refresh_hud()
        self._frame()

    def _show_summary(self, show: bool) -> None:
        """Show or hide the end-of-run panel."""
        if not show and self._summary is not None:
            destroy(self._summary)
            self._summary = None
        if not show or self._summary is not None or self.sim is None:
            return
        if self.result is None:
            return
        entry = self.entries[self.index]
        timeline = self.result.timeline
        last = timeline.state(timeline.total_turns)
        lines = summary_lines(last.delivered, self.result.data.nb_drones,
                              timeline.total_turns,
                              target_for(entry.path.name),
                              self.result.valid)
        card = Entity(parent=camera.ui, position=(0.22, 0.36, 0))
        rounded_block(card, 0, 0, 0.8, 0.26, 0.04, "#262a35", 1.0)
        for row, (text, size, color) in enumerate(zip(
                lines, (1.5, 1.1, 0.9, 0.8),
                ("#7dff9a" if last.delivered == self.result.data.nb_drones
                 else "#ff6b5e", "#e9e6ff", "#9aa0c8", "#9aa0c8"))):
            label(card, text, 0, 0.085 - row * 0.055, size, color)
        self._summary = card

    def _stop_play(self) -> None:
        """Remove the drones and the HUD."""
        self._show_summary(False)
        if self.sim is not None:
            self.sim.destroy()
            self.sim = None
        if self.hud is not None:
            self.hud.destroy()
            self.hud = None
        self.mode = "browse"
        if self._browse is not None:
            self._browse.enabled = True

    def stop(self) -> None:
        """Leave the simulation and go back to the map alone."""
        if self.mode == "play":
            self._stop_play()
            self._frame()

    def restart(self) -> None:
        """Run the backend again and replay from the first turn."""
        if self.mode != "play":
            return
        entry = self.entries[self.index]
        try:
            result = SimulationAdapter().run(str(entry.path))
        except (OSError, ValueError) as error:
            self._stop_play()
            self._notice.text = clean(f"ERROR: {error}"[:70])
            return
        self._begin(result)

    def _play(self) -> None:
        """HUD PLAY."""
        if self.sim is not None:
            self.sim.controller.play()
            self._refresh_hud()

    def _pause(self) -> None:
        """HUD PAUSE."""
        if self.sim is not None:
            self.sim.controller.pause()
            self._refresh_hud()

    def _slower(self) -> None:
        """HUD SPEED -."""
        if self.sim is not None:
            self.sim.controller.slower()
            self._refresh_hud()

    def _faster(self) -> None:
        """HUD SPEED +."""
        if self.sim is not None:
            self.sim.controller.faster()
            self._refresh_hud()

    def _refresh_hud(self) -> None:
        """Show the real simulation numbers."""
        if self.sim is None or self.hud is None or self.result is None:
            return
        controller = self.sim.controller
        self.hud.refresh(controller, self.sim.state(), self.result)
        status = controller.status
        self._show_summary(status is PlaybackStatus.FINISHED)
        self.hud.buttons["play"].set_active(
            status is PlaybackStatus.PLAYING)
        self.hud.buttons["pause"].set_active(
            status is PlaybackStatus.PAUSED)

    def _frame(self) -> None:
        """Aim the isometric camera at the scene and size the view."""
        if self.scene is None:
            return
        fit = fit_view(self.scene.frame_points(), PITCH, self.shown_yaw,
                       window.aspect_ratio, 1.12)
        fov = fit.fov * self.zoom
        target = fit.target
        if self.mode == "play":
            right = iso_axes(PITCH, self.shown_yaw)[0]
            shift = HUD_SHIFT * fov * window.aspect_ratio
            target = (target[0] - right[0] * shift,
                      target[1] - right[1] * shift,
                      target[2] - right[2] * shift)
        self._rig.position = target
        self._rig.rotation = (PITCH, self.shown_yaw, 0)
        camera.fov = fov
        self._fit_backdrop()

    def _fit_backdrop(self) -> None:
        """Scale the backdrop to cover the whole view, whatever the zoom."""
        if self._backdrop is None:
            return
        width, height = cover_scale(window.aspect_ratio, BACKDROP_ASPECT)
        view = camera.fov * 1.03
        self._backdrop.scale = (width * view, height * view)

    def _place_hud(self, force: bool = False) -> None:
        """Keep the texts and the HUD at the left of the window."""
        aspect = window.aspect_ratio
        if not force and abs(aspect - self._aspect) < 1e-3:
            return
        self._aspect = aspect
        left = -aspect / 2 + 0.03
        self._title.position = (left, 0.46, -0.2)
        self._hint.position = (left, 0.42, -0.2)
        self._info.position = (left, 0.38, -0.2)
        if self.hud is not None:
            self.hud.place(aspect)

    def tick(self, dt: float = 1 / 60) -> None:
        """Advance the drones; follow window resizing."""
        turning = self.shown_yaw != self.yaw
        if turning:
            self.shown_yaw = approach_angle(self.shown_yaw, self.yaw, dt)
        if turning or abs(window.aspect_ratio - self._aspect) >= 1e-3:
            self._place_hud()
            self._frame()
        if self.sim is not None and self.sim.tick(dt):
            self._refresh_hud()

    def on_key(self, key: str) -> None:
        """Keyboard and mouse wheel controls."""
        if key in ("q", "e"):
            self.yaw += -90.0 if key == "q" else 90.0
        elif key == "scroll up":
            self._zoom(1 / ZOOM_STEP)
        elif key == "scroll down":
            self._zoom(ZOOM_STEP)
        elif key == "v":
            self.zoom, self.yaw = 1.0, YAW_START
            self._frame()
        elif self.mode == "play":
            self._play_key(key)
        else:
            self._browse_key(key)

    def _browse_key(self, key: str) -> None:
        """Keys of the browse mode."""
        if key == "escape":
            application.quit()
        elif key == "right arrow":
            self._change_map(1)
        elif key == "left arrow":
            self._change_map(-1)
        elif key == "enter":
            self.start_play()

    def _play_key(self, key: str) -> None:
        """Keys of the play mode."""
        if self.sim is None:
            return
        controller = self.sim.controller
        if key == "escape":
            self.stop()
        elif key == "space":
            controller.toggle()
        elif key == "r":
            self.restart()
            return
        elif key in ("left arrow", "right arrow"):
            controller.step(-1 if key == "left arrow" else 1)
            self.sim.refresh(animate=True)
        elif key == "up arrow":
            controller.faster()
        elif key == "down arrow":
            controller.slower()
        else:
            return
        self._refresh_hud()

    def _zoom(self, factor: float) -> None:
        """Zoom in (factor < 1) or out (factor > 1)."""
        low, high = ZOOM_RANGE
        self.zoom = max(low, min(high, self.zoom * factor))
        self._frame()


def show3d(data: MapData, lines: list[str], name: str,
           map_path: str) -> None:
    """Open the 3D viewer on a map (entry point used by the CLI)."""
    del data, lines, name
    Viewer3D(Path(map_path)).run()
