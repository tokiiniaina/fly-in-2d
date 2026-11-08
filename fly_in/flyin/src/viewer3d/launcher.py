"""Window, camera, keys and map switching of the 3D viewer."""

from pathlib import Path
from typing import Any

from ursina import (
    Entity,
    Texture,
    Ursina,
    application,
    camera,
    window,
)

from flyin.src.map_data import MapData
from flyin.src.viewer.catalog import MapCatalog, MapEntry
from flyin.src.viewer.layout import cover_scale
from flyin.src.viewer.paths import ASSETS_DIR
from flyin.src.viewer.shapes import clean, label, tint
from flyin.src.viewer3d.camera import PITCH, YAW_START, fit_view
from flyin.src.viewer3d.scene import MapScene

BACKGROUND = "#070a1a"
BACKDROP_PATH = ASSETS_DIR / "background" / "space.jpg"
BACKDROP_ASPECT = 2048 / 1152
BACKDROP_DISTANCE = 700.0
CAMERA_DISTANCE = 80.0
ZOOM_STEP = 1.12
ZOOM_RANGE = (0.35, 2.5)
HINT = "LEFT / RIGHT: MAP     Q / E: ROTATE     SCROLL: ZOOM     ESC: QUIT"


class _Driver(Entity):
    """Receives Ursina's frame and key events."""

    def __init__(self, viewer: "Viewer3D") -> None:
        """Keep the viewer."""
        super().__init__()
        self._viewer = viewer

    def update(self) -> None:
        """Called by Ursina every frame."""
        self._viewer.tick()

    def input(self, key: str) -> None:
        """Called by Ursina for every key and mouse event."""
        self._viewer.on_key(key)


class Viewer3D:
    """Browse the maps of the project in isometric 3D."""

    def __init__(self, start_path: Path | None = None) -> None:
        """Optionally start on a given map file."""
        self._start_path = start_path
        self.entries: list[MapEntry] = []
        self.index = 0
        self.yaw = YAW_START
        self.zoom = 1.0
        self.scene: MapScene | None = None
        self._rig: Any = None
        self._title: Any = None
        self._backdrop: Any = None
        self._hint: Any = None
        self._aspect = 0.0

    def run(self) -> int:
        """Open the window and run until it is closed.

        Raises:
            ValueError: If there is no valid map to show.
            FileNotFoundError: If the backdrop image is missing.
        """
        if not BACKDROP_PATH.is_file():
            raise FileNotFoundError(f"missing '{BACKDROP_PATH}'")
        self.entries = MapCatalog().discover()
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
        self._title = label(camera.ui, "", 0, 0, 1.3, "#e9e6ff",
                            origin=(-0.5, 0))
        self._hint = label(camera.ui, HINT, 0, 0, 0.8, "#9aa0c8",
                           origin=(-0.5, 0))
        self._driver = _Driver(self)
        self._load()
        engine.run()
        return 0

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

    def _load(self) -> None:
        """Build the scene of the selected map and frame it."""
        if self.scene is not None:
            self.scene.destroy()
        entry = self.entries[self.index]
        data: MapData | None = entry.data
        if data is None:
            raise ValueError(f"map '{entry.path.name}' is not valid")
        self.scene = MapScene(data, entry.path.name)
        self.zoom = 1.0
        self._title.text = clean(
            f"{entry.name}   {self.index + 1}/{len(self.entries)}")
        self._place_hud(force=True)
        self._frame()

    def _frame(self) -> None:
        """Aim the isometric camera at the scene and size the view."""
        if self.scene is None:
            return
        fit = fit_view(self.scene.frame_points(), PITCH, self.yaw,
                       window.aspect_ratio, 1.12)
        self._rig.position = fit.target
        self._rig.rotation = (PITCH, self.yaw, 0)
        camera.fov = fit.fov * self.zoom
        self._fit_backdrop()

    def _fit_backdrop(self) -> None:
        """Scale the backdrop to cover the whole view, whatever the zoom."""
        if self._backdrop is None:
            return
        width, height = cover_scale(window.aspect_ratio, BACKDROP_ASPECT)
        view = camera.fov * 1.03
        self._backdrop.scale = (width * view, height * view)

    def _place_hud(self, force: bool = False) -> None:
        """Keep the texts at the top left of the window."""
        aspect = window.aspect_ratio
        if not force and abs(aspect - self._aspect) < 1e-3:
            return
        self._aspect = aspect
        left = -aspect / 2 + 0.03
        self._title.position = (left, 0.46, -0.2)
        self._hint.position = (left, 0.42, -0.2)

    def tick(self) -> None:
        """Follow window resizing."""
        if abs(window.aspect_ratio - self._aspect) >= 1e-3:
            self._place_hud()
            self._frame()

    def on_key(self, key: str) -> None:
        """Keyboard and mouse wheel controls."""
        if key == "escape":
            application.quit()
        elif key in ("right arrow", "left arrow"):
            step = 1 if key == "right arrow" else -1
            self.index = (self.index + step) % len(self.entries)
            self._load()
        elif key in ("q", "e"):
            self.yaw += -90.0 if key == "q" else 90.0
            self._frame()
        elif key == "scroll up":
            self._zoom(1 / ZOOM_STEP)
        elif key == "scroll down":
            self._zoom(ZOOM_STEP)
        elif key == "r":
            self.zoom, self.yaw = 1.0, YAW_START
            self._frame()

    def _zoom(self, factor: float) -> None:
        """Zoom in (factor < 1) or out (factor > 1)."""
        low, high = ZOOM_RANGE
        self.zoom = max(low, min(high, self.zoom * factor))
        self._frame()


def show3d(data: MapData, lines: list[str], name: str,
           map_path: str) -> None:
    """Open the 3D viewer on a map (entry point used by the CLI).

    Milestone M1 only shows the terrain: `data`, `lines` and `name` are
    accepted for the CLI hook and will drive the drones from M4 on.
    """
    del data, lines, name
    Viewer3D(Path(map_path)).run()
