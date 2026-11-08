"""Tests of the pure viewer logic: catalog, layout, timeline, playback."""

import unittest
from pathlib import Path

from flyin.src.engine.solver import Solver
from flyin.src.parser_function import MapParser
from flyin.src.viewer.adapters.simulation_adapter import (
    SimulationAdapter,
    TimelineBuilder,
)
from flyin.src.viewer.catalog import DroneCatalog, MapCatalog
from flyin.src.viewer.layout import (
    NetworkLayout,
    Rect,
    cluster_offsets,
    cover_scale,
    fit_size,
)
from flyin.src.viewer.playback import (
    PlaybackController,
    PlaybackStatus,
)

ROOT = Path(__file__).resolve().parents[1]
MAPS = sorted((ROOT / "maps").glob("*.txt"))


class CatalogTests(unittest.TestCase):
    """Maps and sprites are discovered from the real files."""

    def test_every_map_file_is_listed(self) -> None:
        """Only valid maps in the maps folder are listed."""
        entries = MapCatalog().discover()
        valid = {p.name for p in MAPS}
        self.assertEqual({e.path.name for e in entries},
                         valid)

    def test_discovered_maps_are_valid(self) -> None:
        """The viewer catalog contains only parser-valid maps."""
        entries = {e.path.name: e for e in MapCatalog().discover()}
        self.assertTrue(all(entry.valid for entry in entries.values()))

    def test_difficulty_and_label(self) -> None:
        """The difficulty comes from the map header."""
        entries = {e.path.name: e for e in MapCatalog().discover()}
        fork = entries["02_simple_fork.txt"]
        self.assertEqual(fork.difficulty, "EASY")
        self.assertEqual(fork.name, "02_simple_fork")

    def test_four_drone_sprites(self) -> None:
        """The four supplied sprites are found, in order."""
        skins = DroneCatalog().discover()
        self.assertEqual([s.name for s in skins],
                         ["SPHERE", "SPIDER", "ROVER", "CUBE"])
        self.assertTrue(all(s.aspect > 1.0 for s in skins))

    def test_empty_folder(self) -> None:
        """A missing maps folder gives an empty catalog."""
        self.assertEqual(MapCatalog(ROOT / "nope").discover(), [])


class LayoutTests(unittest.TestCase):
    """The map is centered, fitted and keeps its topology."""

    def test_fit_inside_area_for_all_maps(self) -> None:
        """Every zone lands inside the area, for several areas."""
        areas = [Rect(0.3, 0, 1.2, 0.9), Rect(0, 0, 0.5, 0.5),
                 Rect(0, 0, 2.0, 0.3)]
        for path in MAPS:
            try:
                data = MapParser().parse(str(path))
            except ValueError:
                continue
            for area in areas:
                layout = NetworkLayout(data, area)
                for x, y in layout.positions.values():
                    self.assertLessEqual(abs(x - area.cx),
                                         area.width / 2 + 1e-9, path.name)
                    self.assertLessEqual(abs(y - area.cy),
                                         area.height / 2 + 1e-9, path.name)

    def test_relative_positions_preserved(self) -> None:
        """Uniform scale: ratios between distances are unchanged."""
        data = MapParser().parse(str(ROOT / "maps/03_priority_puzzle.txt"))
        layout = NetworkLayout(data, Rect(0, 0, 1.5, 0.9))
        zones = data.zones
        a, b, c = "start", "fast_junction", "merge_point"
        dx = zones[c].x - zones[a].x
        dy = zones[b].x - zones[a].x
        pa, pb, pc = (layout.positions[n] for n in (a, b, c))
        self.assertAlmostEqual((pc[0] - pa[0]) / (pb[0] - pa[0]), dx / dy)

    def test_centered(self) -> None:
        """The bounding box is centered on the area."""
        data = MapParser().parse(str(ROOT / "maps/02_simple_fork.txt"))
        area = Rect(0.2, -0.1, 1.0, 0.8)
        xs = [p[0] for p in NetworkLayout(data, area).positions.values()]
        ys = [p[1] for p in NetworkLayout(data, area).positions.values()]
        self.assertAlmostEqual((min(xs) + max(xs)) / 2, 0.2)
        self.assertAlmostEqual((min(ys) + max(ys)) / 2, -0.1)

    def test_names_shown_only_when_they_fit(self) -> None:
        """Long names are hidden on dense maps, short ones kept."""
        data = MapParser().parse(str(ROOT / "maps/02_capacity_hell.txt"))
        layout = NetworkLayout(data, Rect(0.3, 0, 1.3, 0.92))
        self.assertFalse(layout.name_fits("restricted_tunnel1"))
        self.assertTrue(layout.name_fits("gate1"))
        fork = MapParser().parse(str(ROOT / "maps/02_simple_fork.txt"))
        spacious = NetworkLayout(fork, Rect(0.3, 0, 1.3, 0.92))
        self.assertTrue(spacious.name_fits("junction"))

    def test_cluster_offsets(self) -> None:
        """Clustered drones never share the same spot."""
        for count in range(0, 7):
            spots = {(round(x, 6), round(y, 6))
                     for x, y in cluster_offsets(count, 0.05)}
            self.assertEqual(len(spots), 1 if count == 1 else count)

    def test_cover_scale(self) -> None:
        """The background always covers the whole window."""
        for aspect in (0.8, 1.0, 1.78, 2.4):
            width, height = cover_scale(aspect, 1.78)
            self.assertGreaterEqual(width, aspect - 1e-9)
            self.assertGreaterEqual(height, 1.0 - 1e-9)
            self.assertAlmostEqual(width / height, 1.78, places=6)


class TextFitTests(unittest.TestCase):
    """Long labels shrink instead of overflowing their panel."""

    def test_fit_size(self) -> None:
        """Short text keeps its size, long text is reduced."""
        self.assertEqual(fit_size("OK", 1.2, 0.4), 1.2)
        self.assertEqual(fit_size("", 1.0, 0.4), 1.0)
        long = "CHALLENGER_THE_IMPOSSIBLE_DREAM"
        size = fit_size(long, 1.2, 0.36)
        self.assertLess(size, 1.2)
        self.assertLessEqual(len(long) * 0.0145 * size, 0.36 + 1e-9)


class TimelineTests(unittest.TestCase):
    """The timeline replays exactly the backend output."""

    def test_matches_backend_on_every_valid_map(self) -> None:
        """Delivered counts and moved drones match the output lines."""
        for path in MAPS:
            try:
                data = MapParser().parse(str(path))
            except ValueError:
                continue
            lines = Solver().solve(data)
            timeline = TimelineBuilder(data).build(lines)
            self.assertEqual(timeline.total_turns, len(lines), path.name)
            for turn, line in enumerate(lines, start=1):
                ids = {int(t[1:].split("-", 1)[0]) for t in line.split()}
                self.assertEqual(set(timeline.state(turn).moved), ids)
            last = timeline.state(timeline.total_turns)
            self.assertEqual(last.delivered, data.nb_drones, path.name)
            self.assertFalse(any(d.flight for d in last.drones))

    def test_restricted_flight_takes_two_turns(self) -> None:
        """A drone on a restricted link is in flight for one state."""
        path = ROOT / "maps/00_restricted_zone_check.txt"
        result = SimulationAdapter().run(str(path))
        state1 = result.timeline.state(1)
        flying = [d for d in state1.drones if d.flight is not None]
        self.assertEqual(len(flying), 1)
        self.assertEqual(flying[0].flight, ("start", "r1"))
        self.assertIsNone(flying[0].zone)
        landed = result.timeline.state(2).drones[flying[0].drone_id - 1]
        self.assertEqual(landed.zone, "r1")

    def test_initial_state_and_clamping(self) -> None:
        """Turn 0 has every drone at the start; turns are clamped."""
        path = ROOT / "maps/03_basic_capacity.txt"
        result = SimulationAdapter().run(str(path))
        first = result.timeline.state(0)
        self.assertTrue(all(d.zone == "start" for d in first.drones))
        self.assertEqual(result.timeline.state(-5).index, 0)
        total = result.timeline.total_turns
        self.assertEqual(result.timeline.state(999).index, total)

    def test_backend_output_is_validated(self) -> None:
        """The independent OutputChecker accepts the real runs."""
        for path in MAPS:
            try:
                result = SimulationAdapter().run(str(path))
            except ValueError:
                continue
            self.assertTrue(result.valid, path.name)

    def test_bad_output_is_rejected(self) -> None:
        """A line that cannot be replayed raises ValueError."""
        data = MapParser().parse(str(ROOT / "maps/02_simple_fork.txt"))
        builder = TimelineBuilder(data)
        for bad in (["D9-junction"], ["D1-nowhere"], ["garbage"],
                    ["D1-junction D1-path_a"]):
            with self.assertRaises(ValueError):
                builder.build(bad)

    def test_bad_landing_is_rejected(self) -> None:
        """A drone in flight must land on the zone it flies to."""
        data = MapParser().parse(str(ROOT / "maps/02_simple_fork.txt"))
        builder = TimelineBuilder(data)
        flight = ["D1-junction", "D1-junction-path_b"]
        with self.assertRaises(ValueError):
            builder.build(flight + ["D1-path_a"])
        with self.assertRaises(ValueError):
            builder.build(flight + [""])
        self.assertEqual(
            builder.build(flight + ["D1-path_b"]).total_turns, 3)

    def test_dead_end_map_is_solved(self) -> None:
        """The space-time solver handles the former dead-end fixture."""
        result = SimulationAdapter().run(
            str(ROOT / "maps/01_dead_end_trap.txt"))
        self.assertTrue(result.valid)
        with self.assertRaises(OSError):
            SimulationAdapter().run(str(ROOT / "maps/missing.txt"))


class PlaybackTests(unittest.TestCase):
    """Speed changes pacing only, never the turn count."""

    def test_status_cycle(self) -> None:
        """READY, PLAYING, PAUSED, FINISHED."""
        pc = PlaybackController(3)
        self.assertIs(pc.status, PlaybackStatus.READY)
        pc.play()
        self.assertIs(pc.status, PlaybackStatus.PLAYING)
        pc.pause()
        self.assertIs(pc.status, PlaybackStatus.PAUSED)
        pc.play()
        pc.tick(10)
        self.assertIs(pc.status, PlaybackStatus.FINISHED)
        self.assertEqual(pc.turn, 3)

    def test_speed_only_changes_pacing(self) -> None:
        """Any speed reaches the same last turn."""
        for index in range(6):
            pc = PlaybackController(7, index)
            pc.play()
            for _ in range(10000):
                pc.tick(0.05)
            self.assertEqual(pc.turn, 7)
            self.assertEqual(pc.total_turns, 7)

    def test_speed_scales_rate(self) -> None:
        """Double speed advances twice as fast."""
        slow, fast = PlaybackController(50, 2), PlaybackController(50, 3)
        slow.play()
        fast.play()
        slow.tick(4.0)
        fast.tick(4.0)
        self.assertEqual(slow.turn, 4)
        self.assertEqual(fast.turn, 8)

    def test_bounds_and_labels(self) -> None:
        """Speed is clamped; labels are readable."""
        pc = PlaybackController(3)
        for _ in range(20):
            pc.faster()
        self.assertEqual(pc.speed_label, "8x")
        for _ in range(20):
            pc.slower()
        self.assertEqual(pc.speed_label, "0.25x")

    def test_restart_and_replay(self) -> None:
        """Restart goes to turn 0 and plays; PLAY after the end replays."""
        pc = PlaybackController(2)
        pc.play()
        pc.tick(5)
        pc.play()
        self.assertEqual(pc.turn, 0)
        self.assertIs(pc.status, PlaybackStatus.PLAYING)
        pc.tick(1)
        pc.restart()
        self.assertEqual(pc.turn, 0)
        self.assertIs(pc.status, PlaybackStatus.PLAYING)

    def test_pause_freezes_and_step(self) -> None:
        """No tick effect while paused; stepping is bounded."""
        pc = PlaybackController(4)
        pc.play()
        pc.pause()
        self.assertFalse(pc.tick(10))
        self.assertTrue(pc.step(1))
        self.assertTrue(pc.step(-5))
        self.assertFalse(pc.step(-1))
        self.assertEqual(pc.turn, 0)

    def test_zero_turn_simulation(self) -> None:
        """A run with no turn finishes immediately."""
        pc = PlaybackController(0)
        pc.play()
        self.assertIs(pc.status, PlaybackStatus.FINISHED)


if __name__ == "__main__":
    unittest.main()
