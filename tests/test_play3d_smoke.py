"""The 3D drones follow the real backend simulation (stub ursina)."""

import math
import unittest
from pathlib import Path
from typing import Any

from tests import fake_ursina

ROOT = Path(__file__).resolve().parents[1]
FRAME = 1 / 60


def texts(root: Any) -> list[str]:
    """Every text below an entity."""
    found: list[str] = []
    for child in root.children:
        value = getattr(child, "text", None)
        if isinstance(value, str):
            found.append(value)
        found.extend(texts(child))
    return found


class Play3DTests(unittest.TestCase):
    """Drive the 3D viewer in play mode."""

    def setUp(self) -> None:
        """Start the viewer on the fork map and press PLAY."""
        self.ursina = fake_ursina.install()
        self.ursina.window.aspect_ratio = 16 / 9
        from flyin.src.viewer3d.launcher import Viewer3D
        self.Viewer3D = Viewer3D
        self.viewer = self.open("02_simple_fork.txt")

    def open(self, name: str) -> Any:
        """A viewer in play mode on a map."""
        viewer = self.Viewer3D(ROOT / "maps" / name)
        viewer.run()
        viewer.start_play()
        self.assertEqual(viewer.mode, "play")
        return viewer

    def frames(self, seconds: float, viewer: Any = None) -> None:
        """Advance the viewer clock."""
        for _ in range(round(seconds / FRAME)):
            (viewer or self.viewer).tick(FRAME)

    def settle(self, turn: int) -> None:
        """Pause on a turn and wait for the flights to end."""
        sim = self.viewer.sim
        sim.controller.pause()
        sim.controller.turn = turn
        sim.refresh(animate=True)
        self.frames(2.0)
        self.viewer._refresh_hud()

    def test_one_drone_per_backend_drone(self) -> None:
        """The scene has exactly the drones of the map, and a HUD."""
        sim = self.viewer.sim
        self.assertEqual(len(sim.actors), 4)
        shown = texts(self.ursina.camera.ui)
        self.assertIn("TURN: 00 / 05", shown)
        self.assertIn("DRONES LEFT: 04", shown)
        self.assertIn("DELIVERED: 00", shown)
        self.assertIn("OUTPUT: VALID", shown)

    def test_hud_follows_the_playback_by_itself(self) -> None:
        """The HUD turn counter moves with the simulation, no clicks."""
        for _ in range(4):
            self.frames(1.05)
            turn = self.viewer.sim.controller.turn
            self.assertIn(f"TURN: {turn:02d} / 05",
                          texts(self.ursina.camera.ui))
        self.assertGreaterEqual(self.viewer.sim.controller.turn, 3)

    def test_drones_follow_the_backend_turn_by_turn(self) -> None:
        """After each turn, each drone hovers where the backend says."""
        from flyin.src.viewer3d.drone_layout import targets_for_state
        sim = self.viewer.sim
        plan = sim.scene.plan
        self.frames(1.0)
        for turn in range(1, sim.controller.total_turns + 1):
            self.settle(turn)
            state = sim.result.timeline.state(turn)
            targets = targets_for_state(plan, state, sim.scale)
            for drone_id, actor in sim.actors.items():
                x, y, z = actor.root.position
                self.assertAlmostEqual(x, targets[drone_id].x, places=6)
                self.assertAlmostEqual(z, targets[drone_id].y, places=6)
                self.assertGreater(y, 0.12 + 0.3)
                self.assertLess(y, 0.34 + 1.6)
                self.assertTrue(actor.root.enabled)

    def test_flight_to_a_restricted_zone_is_on_the_link(self) -> None:
        """At turn 2 a drone hovers at the middle of junction-path_b."""
        sim = self.viewer.sim
        self.frames(1.0)
        self.settle(2)
        state = sim.result.timeline.state(2)
        flyer = next(d for d in state.drones if d.flight)
        a, b = sim.scene.plan.pad("junction"), sim.scene.plan.pad("path_b")
        x, _, z = sim.actors[flyer.drone_id].root.position
        self.assertAlmostEqual(x, (a.x + b.x) / 2, delta=0.1)
        self.assertAlmostEqual(z, (a.z + b.z) / 2, delta=0.1)

    def test_delivery_matches_the_backend(self) -> None:
        """At the end all drones are at the goal and counted."""
        sim = self.viewer.sim
        self.frames(1.0)
        self.settle(sim.controller.total_turns)
        shown = texts(self.ursina.camera.ui)
        self.assertIn("DELIVERED: 04", shown)
        self.assertIn("DRONES LEFT: 00", shown)
        end = sim.scene.plan.pad("goal")
        for actor in sim.actors.values():
            x, _, z = actor.root.position
            self.assertLess(math.hypot(x - end.x, z - end.z), 3.0)

    def finish(self) -> None:
        """Play until the last turn."""
        for _ in range(8):
            self.viewer.on_key("up arrow")
        sim = self.viewer.sim
        for _ in range(60 * 60):
            self.viewer.tick(FRAME)
            if sim.controller.turn >= sim.controller.total_turns:
                break
        self.frames(0.3)

    def test_summary_panel_at_the_end(self) -> None:
        """The panel shows the real result and the subject target."""
        self.assertIsNone(self.viewer._summary)
        self.finish()
        self.assertIsNotNone(self.viewer._summary)
        shown = texts(self.viewer._summary)
        self.assertIn("ALL DRONES DELIVERED", shown)
        self.assertTrue(any(t.startswith("TURNS: 5") and "TARGET: 8" in t
                            and t.endswith("OK") for t in shown))
        self.assertIn("OUTPUT: VALID", shown)

    def test_summary_hides_on_restart_and_leave(self) -> None:
        """The panel goes away when replaying or leaving."""
        self.finish()
        self.viewer.on_key("r")
        self.frames(0.2)
        self.assertIsNone(self.viewer._summary)
        self.finish()
        self.assertIsNotNone(self.viewer._summary)
        self.viewer.stop()
        self.assertIsNone(self.viewer._summary)

    def test_summary_for_the_impossible_dream(self) -> None:
        """The biggest map is reported against its record."""
        viewer = self.open("01_the_impossible_dream.txt")
        for _ in range(8):
            viewer.on_key("up arrow")
        sim = viewer.sim
        for _ in range(60 * 120):
            viewer.tick(FRAME)
            if sim.controller.turn >= sim.controller.total_turns:
                break
        shown = texts(viewer._summary)
        self.assertTrue(any("TURNS: 43" in t and "TARGET: 45" in t
                            and t.endswith("OK") for t in shown))

    def test_browse_shows_the_target(self) -> None:
        """The map view tells the target number of turns."""
        self.viewer.stop()
        self.assertIn("TARGET 8 TURNS", self.viewer._info.text)

    def test_pads_are_centered_entities(self) -> None:
        """Each pad entity sits on its pad, with local vertices."""
        scene = self.viewer.scene
        for pad in scene.plan.pads:
            entity = scene.pad_entities[pad.name]
            self.assertEqual(entity.position, (pad.x, 0.0, pad.z))
            xs = [v[0] for v in entity.model.vertices]
            self.assertLess(abs(max(xs) + min(xs)), 0.5)
            self.assertLess(max(xs), 2.0)

    def test_pad_pulses_when_a_drone_lands(self) -> None:
        """A landing makes the pad bump; the goal bumps more."""
        sim = self.viewer.sim
        self.frames(1.0)
        peaks: dict[str, float] = {}
        last: dict[str, tuple[float, float, float]] = {}
        for _ in range(60 * 14):
            self.viewer.tick(FRAME)
            for name, entity in sim.scene.pad_entities.items():
                peaks[name] = max(peaks.get(name, 1.0), entity.scale[0])
                last[name] = entity.scale
        self.assertGreater(peaks["junction"], 1.02)
        self.assertGreater(peaks["goal"], peaks["junction"])
        self.assertEqual(peaks.get("start", 1.0), 1.0)
        for scale in last.values():
            self.assertAlmostEqual(scale[0], 1.0, places=3)
            self.assertAlmostEqual(scale[1], 1.0, places=3)

    def test_every_drone_celebrates_at_the_goal(self) -> None:
        """The arrival animation plays once per drone."""
        sim = self.viewer.sim
        celebrated: set[int] = set()
        for _ in range(60 * 14):
            self.viewer.tick(FRAME)
            celebrated |= {i for i, r in sim.rigs.items() if r.celebrating}
        self.assertEqual(celebrated, {1, 2, 3, 4})
        self.assertEqual(sim.controller.turn,
                         sim.controller.total_turns)

    def test_drones_face_where_they_fly(self) -> None:
        """Mid-flight, the heading points to the movement."""
        sim = self.viewer.sim
        self.frames(1.0)
        self.settle(1)
        sim.controller.turn = 2
        sim.refresh(animate=True)
        self.frames(0.4)
        moving = [i for i in sim.actors
                  if sim.animator.flight_progress(i) is not None]
        self.assertTrue(moving)
        for drone_id in moving:
            track = sim.animator.sample(drone_id)
            rig = sim.rigs[drone_id]
            speed = math.hypot(rig.vx, rig.vz)
            if speed > 0.5:
                want = math.degrees(math.atan2(rig.vx, rig.vz))
                diff = (want - rig.heading + 180) % 360 - 180
                self.assertLess(abs(diff), 30.0)
            self.assertIsNotNone(track)

    def test_speed_changes_pace_not_the_result(self) -> None:
        """Faster speed: shorter flights, same lines, same last turn."""
        durations = []
        for presses in (0, 3):
            viewer = self.open("03_basic_capacity.txt")
            sim = viewer.sim
            lines = list(sim.result.lines)
            self.frames(2.0, viewer)
            sim.controller.pause()
            for _ in range(presses):
                viewer.on_key("up arrow")
            sim.controller.turn = 1
            sim.refresh(animate=True)
            count = 0
            while sim.animator.moving and count < 400:
                viewer.tick(FRAME)
                count += 1
            durations.append(count)
            self.assertEqual(sim.result.lines, lines)
            viewer.stop()
        self.assertGreater(durations[0], durations[1] * 2)

    def test_buttons_and_keys(self) -> None:
        """PLAY, PAUSE, RESTART, SPEED, MAP and the keyboard work."""
        viewer = self.viewer
        sim = viewer.sim
        buttons = viewer.hud.buttons
        buttons["pause"].click()
        turn = sim.controller.turn
        self.frames(3.0)
        self.assertEqual(sim.controller.turn, turn)
        self.assertIn("STATUS: PAUSED", texts(self.ursina.camera.ui))
        buttons["play"].click()
        self.frames(1.2)
        self.assertGreater(sim.controller.turn, turn)
        buttons["faster"].click()
        self.assertIn("2x", texts(self.ursina.camera.ui))
        viewer.on_key("space")
        self.assertIn("STATUS: PAUSED", texts(self.ursina.camera.ui))
        viewer.on_key("space")
        viewer.on_key("r")
        self.assertEqual(viewer.sim.controller.turn, 0)
        self.assertEqual(viewer.mode, "play")
        self.assertIn("TURN: 00 / 05", texts(self.ursina.camera.ui))
        viewer.hud.buttons["map"].click()
        self.assertEqual(viewer.mode, "browse")
        self.assertIsNone(viewer.sim)
        self.assertIsNone(viewer.hud)
        self.assertTrue(viewer._browse.enabled)

    def test_escape_goes_back_then_quits(self) -> None:
        """ESC leaves the simulation, then the application."""
        self.viewer.on_key("escape")
        self.assertEqual(self.viewer.mode, "browse")
        self.assertFalse(self.ursina.application.quit_requested)
        self.viewer.on_key("escape")
        self.assertTrue(self.ursina.application.quit_requested)

    def test_browse_play_button_and_enter(self) -> None:
        """The PLAY text button and ENTER start the simulation."""
        self.viewer.stop()
        buttons = [c for c in self.viewer._browse.children
                   if hasattr(c, "on_click")]
        self.assertGreaterEqual(len(buttons), 3)
        self.viewer.on_key("enter")
        self.assertEqual(self.viewer.mode, "play")

    def test_old_drones_are_removed_when_changing_map(self) -> None:
        """Leaving play removes the drone entities of the scene."""
        scene = self.viewer.scene
        from flyin.src.viewer3d.drone_actor import SPARK_POOL
        before = len(scene.root.children)
        base = 3 + len(scene.plan.pads) + 2
        self.assertEqual(before, base + 4 * (1 + SPARK_POOL))
        self.viewer.stop()
        self.assertEqual(len(scene.root.children), base)
        self.viewer.on_key("right arrow")
        self.assertTrue(scene.root.destroyed)

    def test_camera_leaves_room_for_the_hud(self) -> None:
        """In play mode the scene shifts right of the HUD panel."""
        rig = self.viewer._rig
        playing = rig.position
        self.viewer.stop()
        self.assertNotEqual(playing, rig.position)

    def test_play_texts_are_safe(self) -> None:
        """No angle brackets or empty texts in play mode."""
        self.frames(2.0)
        for text in texts(self.ursina.camera.ui):
            self.assertNotIn("<", text)
            self.assertNotIn(">", text)
            self.assertNotEqual(text, "")

    def test_every_map_plays_to_the_end(self) -> None:
        """Every valid map: all drones delivered, nothing crashes."""
        for path in sorted((ROOT / "maps").glob("*.txt")):
            try:
                viewer = self.open(path.name)
            except Exception:
                continue
            sim = viewer.sim
            for _ in range(8):
                viewer.on_key("up arrow")
            for _ in range(60 * 90):
                viewer.tick(FRAME)
                if sim.controller.turn >= sim.controller.total_turns \
                        and not sim.animator.moving:
                    break
            self.frames(0.5, viewer)
            last = sim.result.timeline.state(sim.controller.total_turns)
            self.assertEqual(last.delivered, sim.result.data.nb_drones,
                             path.name)
            self.assertEqual(sim.controller.turn,
                             sim.controller.total_turns, path.name)
            visible = [a for a in sim.actors.values() if a.root.enabled]
            self.assertEqual(len(visible), sim.result.data.nb_drones,
                             path.name)


if __name__ == "__main__":
    unittest.main()
