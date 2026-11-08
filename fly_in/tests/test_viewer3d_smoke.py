"""Smoke test of the 3D viewer through a stub of the ursina module."""

import unittest
from pathlib import Path
from typing import Any

from tests import fake_ursina

ROOT = Path(__file__).resolve().parents[1]


def texts(root: Any) -> list[str]:
    """Every text below an entity."""
    found: list[str] = []
    for child in root.children:
        value = getattr(child, "text", None)
        if isinstance(value, str):
            found.append(value)
        found.extend(texts(child))
    return found


class Viewer3DSmokeTests(unittest.TestCase):
    """Drive the viewer by keys."""

    def setUp(self) -> None:
        """Install the stub and start the viewer on the fork map."""
        self.ursina = fake_ursina.install()
        self.ursina.window.aspect_ratio = 16 / 9
        from flyin.src.viewer3d.launcher import Viewer3D
        self.viewer = Viewer3D(ROOT / "maps/02_simple_fork.txt")
        self.assertEqual(self.viewer.run(), 0)

    def test_scene_matches_the_map(self) -> None:
        """The scene is built from the selected map, with meshes."""
        scene = self.viewer.scene
        self.assertEqual(len(scene.plan.pads), 5)
        self.assertEqual(len(scene.plan.paths), 5)
        meshes = [c for c in scene.root.children
                  if hasattr(c.model, "vertices")]
        self.assertGreaterEqual(len(meshes), 5 + 3)
        for entity in meshes:
            self.assertEqual(len(entity.model.vertices),
                             len(entity.model.colors))
            self.assertTrue(entity.double_sided)

    def test_isometric_camera(self) -> None:
        """Orthographic camera, tilted 35 degrees, yaw 45."""
        camera = self.ursina.camera
        self.assertTrue(camera.orthographic)
        rig = self.viewer._rig
        self.assertEqual(rig.rotation, (35.0, 45.0, 0))
        self.assertIs(camera.parent, rig)
        self.assertGreater(camera.fov, 1.0)

    def test_browse_maps_rebuilds_the_scene(self) -> None:
        """Arrow keys switch map; the old scene is destroyed."""
        old = self.viewer.scene
        first = self.viewer.index
        self.viewer.on_key("right arrow")
        self.assertTrue(old.root.destroyed)
        self.assertNotEqual(self.viewer.index, first)
        self.assertIsNot(self.viewer.scene, old)
        self.viewer.on_key("left arrow")
        self.assertEqual(self.viewer.index, first)
        names = {e.path.name for e in self.viewer.entries}
        self.assertIn("00_restricted_zone_check.txt", names)

    def test_every_map_loads(self) -> None:
        """Cycling through all maps never fails."""
        for _ in range(len(self.viewer.entries) + 1):
            self.viewer.on_key("right arrow")
            scene = self.viewer.scene
            self.assertGreaterEqual(len(scene.root.children),
                                    3 + len(scene.plan.pads))

    def test_rotate_and_zoom(self) -> None:
        """Q/E rotate by 90 degrees, scroll zooms within limits."""
        rig = self.viewer._rig
        self.viewer.on_key("e")
        self.assertEqual(rig.rotation[1], 135.0)
        self.viewer.on_key("q")
        self.viewer.on_key("q")
        self.assertEqual(rig.rotation[1], -45.0)
        base = self.ursina.camera.fov
        self.viewer.on_key("scroll up")
        self.assertLess(self.ursina.camera.fov, base)
        for _ in range(60):
            self.viewer.on_key("scroll down")
        self.assertLessEqual(self.viewer.zoom, 2.5)
        self.viewer.on_key("r")
        self.assertEqual(rig.rotation[1], 45.0)
        self.assertAlmostEqual(self.ursina.camera.fov, base)

    def test_resize_reframes(self) -> None:
        """A new window shape changes the view size."""
        before = self.ursina.camera.fov
        self.ursina.window.aspect_ratio = 1.0
        self.viewer.tick()
        self.assertNotEqual(self.ursina.camera.fov, before)

    def test_hud_text_is_safe_for_ursina(self) -> None:
        """No angle brackets and no empty text in the HUD."""
        for text in texts(self.ursina.camera.ui):
            self.assertNotIn("<", text)
            self.assertNotIn(">", text)
            self.assertNotEqual(text, "")
        joined = " ".join(texts(self.ursina.camera.ui))
        self.assertIn("02_simple_fork", joined)

    def test_backdrop_covers_the_view_at_any_zoom_and_shape(self) -> None:
        """The galaxy image is camera-fixed and always covers the view."""
        camera = self.ursina.camera
        backdrop = self.viewer._backdrop
        self.assertIs(backdrop.parent, camera)
        self.assertTrue(str(backdrop.texture.path).endswith("space.jpg"))
        for aspect in (1.0, 16 / 9, 2.4):
            self.ursina.window.aspect_ratio = aspect
            self.viewer.tick()
            for key in ("scroll up", "scroll down", "scroll down"):
                self.viewer.on_key(key)
                width, height = backdrop.scale
                self.assertGreaterEqual(width, camera.fov * aspect - 1e-6)
                self.assertGreaterEqual(height, camera.fov - 1e-6)
        self.assertGreater(backdrop.position[2], 400)
        self.assertGreater(camera.clip_plane_far, backdrop.position[2]
                           + 80)

    def test_space_look(self) -> None:
        """Dark window color and light HUD text."""
        self.assertEqual(self.ursina.window.color, "#070a1a")
        self.assertEqual(self.viewer._title.color, "#e9e6ff")

    def test_scene_has_stars_and_translucent_smoke(self) -> None:
        """Smoke entities are translucent; stars and ground are not."""
        translucent = [c for c in self.viewer.scene.root.children
                       if getattr(c, "alpha", 1.0) < 1.0]
        self.assertGreaterEqual(len(translucent), 1)
        self.assertEqual(translucent[0].alpha, 0.45)
        solid = [c for c in self.viewer.scene.root.children
                 if getattr(c, "alpha", 1.0) == 1.0]
        self.assertGreaterEqual(len(solid), 3 + 5 + 1)

    def test_escape_quits(self) -> None:
        """ESC asks the application to quit."""
        self.viewer.on_key("escape")
        self.assertTrue(self.ursina.application.quit_requested)

    def test_start_on_a_map_outside_the_folder(self) -> None:
        """A map outside maps/ is added and shown."""
        from flyin.src.viewer3d.launcher import Viewer3D
        viewer = Viewer3D(ROOT / "tests/data/all_types.txt")
        viewer.run()
        self.assertEqual(viewer.entries[viewer.index].path.name,
                         "all_types.txt")
        self.assertEqual(len(viewer.scene.plan.pads), 8)


if __name__ == "__main__":
    unittest.main()
