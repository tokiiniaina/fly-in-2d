"""Smoke test of the screens, driven through a stub of the ursina module.

It runs the real menu, HUD, buttons and network code against a recording
stand-in for Ursina. It does not prove the look in a real window.
"""

import math
import unittest
from pathlib import Path
from typing import Any

from tests import fake_ursina

ROOT = Path(__file__).resolve().parents[1]
FRAME = 1.0 / 60


def texts(root: Any) -> list[str]:
    """Return every non-empty text below an entity."""
    found: list[str] = []
    for child in root.children:
        value = getattr(child, "text", None)
        if isinstance(value, str) and value.strip():
            found.append(value)
        found.extend(texts(child))
    return found


def clickable(root: Any) -> list[Any]:
    """Return every entity that reacts to a click."""
    found: list[Any] = []
    for child in root.children:
        if hasattr(child, "on_click"):
            found.append(child)
        found.extend(clickable(child))
    return found


class ViewerSmokeTests(unittest.TestCase):
    """Drive the viewer frame by frame."""

    def setUp(self) -> None:
        """Install the stub and start the application."""
        self.ursina = fake_ursina.install()
        self.ursina.window.aspect_ratio = 16 / 9
        from flyin.src.viewer.app import ViewerApp
        self.app = ViewerApp()
        self.assertEqual(self.app.run(), 0)

    def frames(self, seconds: float) -> None:
        """Advance the application clock."""
        for _ in range(int(seconds / FRAME)):
            self.app.tick(FRAME)

    def select_map(self, name: str) -> None:
        """Select a map by file name in the menu."""
        session = self.app.session
        for index, entry in enumerate(session.maps):
            if entry.path.name == name:
                session.map_index = index
                self.app.on_key("left arrow")
                self.app.on_key("right arrow")
                return
        self.fail(f"map {name} not found")

    def open_sim(self, name: str) -> Any:
        """Open the simulation of a map through the menu PLAY."""
        self.select_map(name)
        self.app.on_key("enter")
        self.app.tick(FRAME)
        screen = self.app._screen
        self.assertEqual(type(screen).__name__, "SimulationScreen")
        return screen

    def test_menu_content(self) -> None:
        """The menu lists real maps and shows a drone-free preview."""
        screen = self.app._screen
        self.assertEqual(type(screen).__name__, "MenuScreen")
        shown = texts(screen.root)
        for word in ("FLY-IN", "MAP", "DRONE", "PLAY", "QUIT"):
            self.assertIn(word, shown)
        self.assertNotIn("<", shown)
        self.assertIn("SPHERE", shown)
        names = {e.path.name for e in self.app.session.maps}
        valid_names = {p.name for p in (ROOT / "maps").glob("*.txt")}
        self.assertEqual(
            names, valid_names)
        self.assertIsNotNone(screen._preview)
        self.assertEqual(screen._preview.drones, {})

    def test_all_discovered_maps_are_playable(self) -> None:
        """Every map offered by the menu has a preview."""
        names = {entry.path.name for entry in self.app.session.maps}
        expected = {p.name for p in (ROOT / "maps").glob("*.txt")}
        self.assertEqual(names, expected)
        self.assertIsNotNone(self.app._screen._preview)

    def test_hud_matches_backend(self) -> None:
        """Counters come from the real timeline, turn after turn."""
        screen = self.open_sim("02_simple_fork.txt")
        result = screen._result
        total = result.timeline.total_turns
        self.assertEqual(total, 4)
        self.frames(1.05)
        self.assertEqual(screen.controller.turn, 1)
        hud = texts(screen.root)
        self.assertIn("TURN: 01 / 04", hud)
        self.assertIn("DRONES LEFT: 04", hud)
        self.assertIn("DELIVERED: 00", hud)
        self.frames(10)
        self.assertEqual(screen.controller.turn, total)
        hud = texts(screen.root)
        self.assertIn("DELIVERED: 04", hud)
        self.assertIn("DRONES LEFT: 00", hud)
        self.assertIn("STATUS: FINISHED", hud)
        self.assertIn("OUTPUT: VALID", hud)

    def test_buttons(self) -> None:
        """PLAY, PAUSE, RESTART, SPEED -/+ and MAP all work."""
        screen = self.open_sim("03_basic_capacity.txt")
        buttons = screen._hud.buttons
        buttons["pause"].click()
        turn = screen.controller.turn
        self.frames(3)
        self.assertEqual(screen.controller.turn, turn)
        self.assertIn("STATUS: PAUSED", texts(screen.root))
        buttons["play"].click()
        self.frames(1.1)
        self.assertGreater(screen.controller.turn, turn)
        buttons["faster"].click()
        self.assertIn("2x", texts(screen.root))
        buttons["slower"].click()
        buttons["slower"].click()
        self.assertIn("0.5x", texts(screen.root))
        total = screen.controller.total_turns
        buttons["restart"].click()
        self.app.tick(FRAME)
        self.assertEqual(screen.controller.turn, 0)
        self.assertEqual(screen.controller.total_turns, total)
        self.assertIn("TURN: 00 / 04", texts(screen.root))
        self.assertIn("0.5x", texts(screen.root))
        buttons = screen._hud.buttons
        buttons["map"].click()
        self.app.tick(FRAME)
        self.assertEqual(type(self.app._screen).__name__, "MenuScreen")
        screen = self.open_sim("03_basic_capacity.txt")
        screen._hud.buttons["quit"].click()
        self.assertTrue(self.ursina.application.quit_requested)

    def test_speed_does_not_change_result(self) -> None:
        """All speeds replay the same backend lines."""
        screen = self.open_sim("02_circular_loop.txt")
        reference = list(screen._result.lines)
        for _ in range(3):
            screen._hud.buttons["faster"].click()
        self.frames(30)
        self.assertEqual(screen.controller.turn, len(reference))
        self.assertEqual(screen._result.lines, reference)

    def test_every_valid_map_every_skin(self) -> None:
        """Every map plays to the end with each of the four sprites."""
        session = self.app.session
        for skin_index in range(len(session.skins)):
            session.skin_index = skin_index
            for entry in session.maps:
                if not entry.valid:
                    continue
                screen = self.open_sim(entry.path.name)
                sprites = screen._network.drones
                self.assertEqual(len(sprites), entry.data.nb_drones)
                for _ in range(screen.controller.total_turns + 1):
                    self.frames(1.0)
                    visible = [d for d in sprites.values()
                               if d.entity.enabled]
                    self.assertLessEqual(len(visible), len(sprites))
                self.assertEqual(
                    screen._result.timeline.state(
                        screen.controller.turn).delivered,
                    entry.data.nb_drones, entry.path.name)
                self.app.open_menu()
                self.app.tick(FRAME)

    def test_drones_sit_on_real_positions(self) -> None:
        """A flying drone is drawn at the middle of its connection."""
        screen = self.open_sim("00_restricted_zone_check.txt")
        screen.controller.pause()
        self.frames(1.5)
        screen.controller.turn = 1
        screen._refresh()
        network = screen._network
        pos = network.layout.positions
        mid_x = (pos["start"][0] + pos["r1"][0]) / 2
        mid_y = (pos["start"][1] + pos["r1"][1]) / 2
        state = screen._result.timeline.state(1)
        flyer = next(d for d in state.drones if d.flight)
        x, y, _ = network.drones[flyer.drone_id].entity.position
        self.assertAlmostEqual(x, mid_x, delta=0.2)
        self.assertAlmostEqual(y, mid_y, delta=0.2)
        self.assertTrue(network.drones[flyer.drone_id].entity.enabled)

    def test_resize_rebuilds_layout(self) -> None:
        """A new window shape rebuilds, keeping turn and speed."""
        screen = self.open_sim("01_maze_nightmare.txt")
        screen.controller.pause()
        screen.controller.turn = 4
        screen._refresh()
        before = dict(screen._network.layout.positions)
        self.ursina.window.aspect_ratio = 1.0
        self.frames(0.4)
        after = screen._network.layout.positions
        self.assertNotEqual(before, after)
        self.assertEqual(screen.controller.turn, 4)
        self.assertIn("TURN: 04 / 13", texts(screen.root))
        self.ursina.window.aspect_ratio = 16 / 9

    def test_all_text_buttons_are_clickable_in_menu(self) -> None:
        """Arrows change map and drone; the sprite texture follows."""
        screen = self.app._screen
        session = self.app.session
        start_map, start_skin = session.map_index, session.skin_index
        arrows = [c for c in clickable(screen.root)]
        self.assertGreaterEqual(len(arrows), 6)
        screen._maps.following.click()
        self.assertEqual(session.map_index,
                         (start_map + 1) % len(session.maps))
        screen._skins.following.click()
        self.assertEqual(session.skin_index,
                         (start_skin + 1) % len(session.skins))
        self.assertEqual(screen._sprite.entity.texture.path,
                         session.skin.path)
        screen._skins.previous.click()
        screen._maps.previous.click()
        self.assertEqual(session.map_index, start_map)

    def test_no_teleport_during_playback(self) -> None:
        """At 1x, a visible drone never jumps between two frames."""
        screen = self.open_sim("01_maze_nightmare.txt")
        sprites = screen._network.drones
        layout = screen._network.layout
        last: dict[int, tuple[float, float]] = {}
        worst = 0.0
        for _ in range(int(screen.controller.total_turns * 62)):
            self.app.tick(FRAME)
            for drone_id, view in sprites.items():
                if not view.entity.enabled:
                    last.pop(drone_id, None)
                    continue
                x, y, _ = view.entity.position
                if drone_id in last:
                    gap = math.hypot(x - last[drone_id][0],
                                     y - last[drone_id][1])
                    worst = max(worst, gap)
                last[drone_id] = (x, y)
        self.assertEqual(screen.controller.turn,
                         screen.controller.total_turns)
        self.assertLess(worst, layout.unit * 0.25)

    def test_intro_wave_then_drones(self) -> None:
        """Zones start hidden, pop in from the center, drones come last."""
        screen = self.open_sim("02_simple_fork.txt")
        screen.controller.pause()
        network = screen._network
        scales = {n: z.root.scale[0] for n, z in network.zones.items()}
        self.assertTrue(all(v < 0.5 for v in scales.values()))
        self.assertFalse(any(d.entity.enabled
                             for d in network.drones.values()))
        self.frames(0.25)
        mid = {n: z.root.scale[0] for n, z in network.zones.items()}
        self.assertTrue(any(v > 0.5 for v in mid.values()))
        self.frames(1.5)
        for zone in network.zones.values():
            self.assertAlmostEqual(zone.root.scale[0], 1.0, places=2)
        self.assertTrue(any(d.entity.enabled
                            for d in network.drones.values()))

    def test_zone_pulses_when_a_drone_lands(self) -> None:
        """A zone bumps after a drone moves into it."""
        screen = self.open_sim("03_basic_capacity.txt")
        screen.controller.pause()
        self.frames(2.0)
        screen.controller.step(1)
        screen._refresh(animate=True)
        zone = screen._network.zones["bottleneck"]
        seen = []
        for _ in range(60):
            self.app.tick(FRAME)
            seen.append(zone.root.scale[0])
        self.assertGreater(max(seen), 1.03)
        self.assertAlmostEqual(seen[-1], 1.0, places=2)

    def test_flight_time_follows_speed(self) -> None:
        """Faster speed means a shorter flight, same destination."""
        durations = []
        for presses in (0, 2):
            screen = self.open_sim("03_basic_capacity.txt")
            screen.controller.pause()
            self.frames(2.0)
            for _ in range(presses):
                screen.controller.faster()
            screen.controller.step(1)
            screen._refresh(animate=True)
            frames = 0
            while screen._network.animator.moving and frames < 300:
                self.app.tick(FRAME)
                frames += 1
            durations.append(frames)
            self.app.open_menu()
            self.app.tick(FRAME)
        self.assertGreater(durations[0], durations[1] * 2)

    def test_intro_replays_on_restart_not_on_resize(self) -> None:
        """RESTART replays the wave; a resize rebuilds without it."""
        screen = self.open_sim("02_simple_fork.txt")
        self.frames(2.0)
        self.ursina.window.aspect_ratio = 1.3
        self.frames(0.4)
        zones = screen._network.zones.values()
        self.assertTrue(all(z.root.scale[0] > 0.9 for z in zones))
        self.ursina.window.aspect_ratio = 16 / 9
        self.frames(0.4)
        screen._hud.buttons["restart"].click()
        self.app.tick(FRAME)
        zones = screen._network.zones.values()
        self.assertTrue(all(z.root.scale[0] < 0.5 for z in zones))

    def test_menu_preview_pops_in_and_sprite_floats(self) -> None:
        """Browsing maps replays the wave; the sample drone bobs."""
        screen = self.app._screen
        screen._maps.following.click()
        preview = screen._preview
        self.assertTrue(all(z.root.scale[0] < 0.5
                            for z in preview.zones.values()))
        heights = set()
        for _ in range(90):
            self.app.tick(FRAME)
            heights.add(round(screen._sprite.entity.position[1], 5))
        self.assertGreater(len(heights), 10)
        self.assertTrue(all(abs(z.root.scale[0] - 1.0) < 0.02
                            for z in preview.zones.values()))

    def all_texts(self, root: Any) -> list[str]:
        """Every raw text below an entity, empty ones included."""
        found: list[str] = []
        for child in root.children:
            value = getattr(child, "text", None)
            if isinstance(value, str):
                found.append(value)
            found.extend(self.all_texts(child))
        return found

    def test_texts_are_safe_for_ursina(self) -> None:
        """No text has angle brackets (tags) or is empty, on any screen."""
        def check() -> None:
            """Assert the current screen has only safe texts."""
            for text in self.all_texts(self.app._screen.root):
                self.assertNotIn("<", text)
                self.assertNotIn(">", text)
                self.assertNotEqual(text, "", "empty Ursina text")
        check()
        for entry in self.app.session.maps:
            self.select_map(entry.path.name)
            check()
        screen = self.open_sim("02_simple_fork.txt")
        self.frames(8)
        self.assertEqual(type(self.app._screen).__name__,
                         "SimulationScreen")
        check()
        self.assertIsNotNone(screen)

    def test_start_on_given_map(self) -> None:
        """--gui MAP opens the simulation of that map directly."""
        from flyin.src.viewer.app import ViewerApp
        app = ViewerApp(str(ROOT / "maps/03_basic_capacity.txt"))
        app.run()
        self.assertEqual(type(app._screen).__name__, "SimulationScreen")
        self.assertEqual(app._screen._entry.path.name,
                         "03_basic_capacity.txt")


if __name__ == "__main__":
    unittest.main()
