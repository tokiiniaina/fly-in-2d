"""Tests of the pure 3D logic: terrain plan, meshes, colors, camera."""

import math
import unittest
from pathlib import Path

from flyin.src.parser_function import MapParser
from flyin.src.viewer3d import builders, palette
from flyin.src.viewer3d.camera import (
    PITCH,
    box_corners,
    dot,
    fit_view,
    iso_axes,
    project,
)
from flyin.src.viewer3d.meshbuilder import MAX_VERTICES, MeshBuilder
from flyin.src.viewer3d.terrain import (
    CELL,
    SPACING,
    TerrainPlanner,
    pad_radius,
    prop_radius,
    segment_distance,
)

ROOT = Path(__file__).resolve().parents[1]


def valid_maps() -> list[Path]:
    """Every map file the parser accepts."""
    found = []
    for path in sorted((ROOT / "maps").glob("*.txt")):
        try:
            MapParser().parse(str(path))
        except ValueError:
            continue
        found.append(path)
    return found


class TerrainFidelityTests(unittest.TestCase):
    """The 3D world is exactly the graph of the map file."""

    def test_pads_have_exact_coordinates(self) -> None:
        """One pad per zone, at the zone coordinates times SPACING."""
        for path in valid_maps():
            data = MapParser().parse(str(path))
            plan = TerrainPlanner(data, path.name).plan()
            self.assertEqual(len(plan.pads), len(data.zones), path.name)
            for pad in plan.pads:
                zone = data.zones[pad.name]
                self.assertEqual((pad.x, pad.z),
                                 (zone.x * SPACING, zone.y * SPACING))
                self.assertEqual(pad.color_word, zone.color)
                self.assertEqual(pad.capacity, zone.max_drones)

    def test_zone_kinds(self) -> None:
        """Start and end are marked; other kinds follow the zone type."""
        path = ROOT / "maps/03_ultimate_challenge.txt"
        plan = TerrainPlanner(MapParser().parse(str(path)), "x").plan()
        kinds = {p.name: p.kind for p in plan.pads}
        self.assertEqual(kinds["start"], "start")
        self.assertEqual(kinds["goal"], "end")
        self.assertEqual(kinds["overflow1"], "restricted")
        self.assertEqual(kinds["priority_hub"], "priority")
        self.assertEqual(kinds["bottleneck1"], "normal")

    def test_paths_are_exactly_the_connections(self) -> None:
        """No missing, no extra, no duplicate path (no fake link)."""
        for path in valid_maps():
            data = MapParser().parse(str(path))
            plan = TerrainPlanner(data, path.name).plan()
            wanted = [frozenset((c.zone1, c.zone2))
                      for c in data.connections]
            drawn = [frozenset((p.first, p.second)) for p in plan.paths]
            self.assertEqual(sorted(map(sorted, drawn)),
                             sorted(map(sorted, wanted)), path.name)
            for p in plan.paths:
                a, b = plan.pad(p.first), plan.pad(p.second)
                self.assertEqual((p.x0, p.z0, p.x1, p.z1),
                                 (a.x, a.z, b.x, b.z))

    def test_capacity_widens_paths_and_blocked_are_closed(self) -> None:
        """A wide connection draws a wider path; blocked links close."""
        path = ROOT / "maps/03_ultimate_challenge.txt"
        plan = TerrainPlanner(MapParser().parse(str(path)), "x").plan()
        widths = {(p.first, p.second): p.width for p in plan.paths}
        self.assertGreater(widths[("start", "dist_gate2")],
                           widths[("start", "dist_gate1")])
        path = ROOT / "maps/01_the_impossible_dream.txt"
        data = MapParser().parse(str(path))
        self.assertFalse(any(
            p.closed for p in TerrainPlanner(data, "x").plan().paths))

    def test_ground_under_every_pad_and_path(self) -> None:
        """Every pad and every point of a path stands on flat ground."""
        for path in valid_maps():
            data = MapParser().parse(str(path))
            plan = TerrainPlanner(data, path.name).plan()
            for pad in plan.pads:
                cell = (round(pad.x / CELL), round(pad.z / CELL))
                self.assertEqual(plan.cells.get(cell), 0.0, path.name)
            for p in plan.paths:
                for k in range(11):
                    t = k / 10
                    x = p.x0 + (p.x1 - p.x0) * t
                    z = p.z0 + (p.z1 - p.z0) * t
                    cell = (round(x / CELL), round(z / CELL))
                    self.assertEqual(plan.cells.get(cell), 0.0,
                                     f"{path.name} {p.first}-{p.second}")

    def test_islets_are_decor_only(self) -> None:
        """Islets are far from the graph, with no pad and no path."""
        for path in valid_maps():
            data = MapParser().parse(str(path))
            plan = TerrainPlanner(data, path.name).plan()
            main = [c for c, k in plan.island.items() if k == 0]
            self.assertGreaterEqual(len(plan.base_level), 2, path.name)
            for cell, island in plan.island.items():
                if island == 0:
                    continue
                for other in main:
                    self.assertGreaterEqual(
                        max(abs(cell[0] - other[0]),
                            abs(cell[1] - other[1])), 4, path.name)
                for pad in plan.pads:
                    self.assertGreater(
                        math.hypot(cell[0] - pad.x, cell[1] - pad.z), 3)

    def test_props_never_on_pads_or_paths(self) -> None:
        """Trees and rocks keep clear of pads and paths."""
        for path in valid_maps():
            data = MapParser().parse(str(path))
            plan = TerrainPlanner(data, path.name).plan()
            self.assertGreater(len(plan.props), 5, path.name)
            for prop in plan.props:
                radius = prop_radius(prop.kind, prop.scale)
                for pad in plan.pads:
                    self.assertGreater(
                        math.hypot(prop.x - pad.x, prop.z - pad.z),
                        pad_radius(pad) + radius * 0.5, path.name)
                for p in plan.paths:
                    self.assertGreater(
                        segment_distance(prop.x, prop.z, p),
                        p.width / 2 + radius * 0.5, path.name)
                cell = (round(prop.x / CELL), round(prop.z / CELL))
                self.assertEqual(plan.cells[cell], prop.y)

    def test_prop_clearance_rule(self) -> None:
        """A prop is refused on a pad, on a path, or on another prop."""
        path = ROOT / "maps/02_simple_fork.txt"
        data = MapParser().parse(str(path))
        plan = TerrainPlanner(data, "x").plan()
        fits = TerrainPlanner._prop_fits
        pad = plan.pad("junction")
        self.assertFalse(fits(plan, "crystal", pad.x, pad.z, 1.0))
        self.assertFalse(fits(plan, "rock", pad.x + 0.6, pad.z, 1.0))
        road = plan.paths[0]
        mid = ((road.x0 + road.x1) / 2, (road.z0 + road.z1) / 2)
        self.assertFalse(fits(plan, "rock", mid[0], mid[1], 1.0))
        self.assertTrue(fits(plan, "rock", pad.x + 5.0, pad.z + 5.0, 1.0))
        plan.props.append(builders.PropPlan("rock", pad.x + 5.0, 0.0,
                                            pad.z + 5.0, 1.0, 0))
        self.assertFalse(fits(plan, "rock", pad.x + 5.1, pad.z + 5.0, 1.0))

    def test_no_vegetation(self) -> None:
        """Only rocks and crystals: no tree, pine or bush anywhere."""
        for path in valid_maps():
            data = MapParser().parse(str(path))
            plan = TerrainPlanner(data, path.name).plan()
            kinds = {p.kind for p in plan.props}
            self.assertLessEqual(kinds, {"rock", "crystal"}, path.name)
        self.assertFalse(hasattr(palette, "LEAVES"))
        self.assertFalse(hasattr(palette, "WOOD"))

    def test_decor_is_deterministic_per_map(self) -> None:
        """Same map name gives the same world; another name differs."""
        data = MapParser().parse(str(ROOT / "maps/01_maze_nightmare.txt"))
        first = TerrainPlanner(data, "maze").plan()
        again = TerrainPlanner(data, "maze").plan()
        other = TerrainPlanner(data, "other").plan()
        self.assertEqual(first.props, again.props)
        self.assertEqual(first.cells, again.cells)
        self.assertNotEqual(first.props, other.props)
        self.assertEqual(first.pads, other.pads)
        self.assertEqual(first.paths, other.paths)


class AllTypesTests(unittest.TestCase):
    """The dedicated test map covers blocked, rainbow and custom colors."""

    def setUp(self) -> None:
        """Plan the test map."""
        path = ROOT / "tests/data/all_types.txt"
        self.data = MapParser().parse(str(path))
        self.plan = TerrainPlanner(self.data, path.name).plan()

    def test_blocked_zone_and_closed_paths(self) -> None:
        """Blocked is a barrier; its real links are drawn closed."""
        self.assertEqual(self.plan.pad("wall").kind, "blocked")
        closed = {frozenset((p.first, p.second))
                  for p in self.plan.paths if p.closed}
        self.assertEqual(closed, {frozenset(("b", "wall")),
                                  frozenset(("c", "wall"))})
        self.assertEqual(len(self.plan.paths), len(self.data.connections))

    def test_every_pad_kind_builds(self) -> None:
        """Each kind gives a non-empty pad mesh."""
        kinds = set()
        for pad in self.plan.pads:
            kinds.add(pad.kind)
            self.assertGreater(builders.build_pad(pad).vertex_count, 100)
        self.assertEqual(kinds, {"start", "end", "normal", "priority",
                                 "restricted", "blocked"})

    def test_custom_and_rainbow_colors_are_kept(self) -> None:
        """A custom word keeps its own color, rainbow its wedges."""
        custom = palette.color_stops("nebulous")
        self.assertEqual(custom, [palette.hue_color("nebulous")])
        self.assertEqual(self.plan.pad("a").color_word, "nebulous")
        self.assertEqual(self.plan.pad("d").color_word, "rainbow")


class ColorTests(unittest.TestCase):
    """Colors come from the map file, rainbow and custom words included."""

    def test_every_color_word_of_every_map_resolves(self) -> None:
        """A written color never falls back to a default."""
        for path in valid_maps():
            data = MapParser().parse(str(path))
            for zone in data.zones.values():
                stops = palette.color_stops(zone.color)
                if zone.color == "none":
                    self.assertIsNone(stops)
                else:
                    self.assertIsNotNone(stops, zone.color)

    def test_rainbow_and_custom_colors(self) -> None:
        """Rainbow gives several stops; unknown words keep one stable."""
        self.assertGreaterEqual(len(palette.color_stops("rainbow") or []), 6)
        self.assertEqual(palette.color_stops("maroon"), ["#800000"])
        first = palette.color_stops("nebulous")
        self.assertEqual(first, palette.color_stops("nebulous"))
        self.assertNotEqual(first, palette.color_stops("glimmering"))

    def test_pad_uses_the_map_color(self) -> None:
        """The pad mesh is colored from the map, not from the type."""
        data = MapParser().parse(str(ROOT / "maps/02_simple_fork.txt"))
        plan = TerrainPlanner(data, "x").plan()
        reds = {c for v, t, cols in builders.build_pad(
            plan.pad("goal")).meshes() for c in cols}
        blue = {c for v, t, cols in builders.build_pad(
            plan.pad("path_a")).meshes() for c in cols}
        self.assertTrue(any(r > b and r > g for r, g, b in reds))
        self.assertTrue(any(b > r and b > g for r, g, b in blue))

    def test_rainbow_pad_has_all_the_stops(self) -> None:
        """A rainbow pad shows every rainbow color on its top."""
        path = ROOT / "maps/01_the_impossible_dream.txt"
        plan = TerrainPlanner(MapParser().parse(str(path)), "x").plan()
        pad = plan.pad("impossible_goal")
        self.assertEqual(pad.color_word, "rainbow")
        found = {c for v, t, cols in builders.build_pad(pad).meshes()
                 for c in cols}
        for stop in palette.RAINBOW:
            r, g, b = palette.hex_to_rgb(stop)
            self.assertTrue(
                any(abs(c[0] - r * 0.91) + abs(c[1] - g * 0.91)
                    + abs(c[2] - b * 0.91) < 0.06 for c in found), stop)

    def test_harmonize_never_replaces(self) -> None:
        """Grass is only tinted a little toward the map colors."""
        tinted = palette.harmonize(palette.GROUND_A, ["#ff0000"])
        r, g, b = palette.hex_to_rgb(tinted)
        gr, gg, gb = palette.hex_to_rgb(palette.GROUND_A)
        self.assertLess(abs(r - gr), 0.1)
        self.assertLess(abs(g - gg), 0.1)
        self.assertLess(abs(b - gb), 0.1)
        self.assertEqual(palette.harmonize(palette.GROUND_A, []),
                         palette.GROUND_A)


class MeshTests(unittest.TestCase):
    """Meshes are valid and bounded."""

    def test_indices_and_colors(self) -> None:
        """Every triangle index exists and every vertex has a color."""
        builder = MeshBuilder()
        builder.box(0, 0, 0, (1, 0), 1, 0.2, 0.5, "#ffffff", "#cccccc",
                    0.04)
        builder.rounded_prism(2, 0, 0.5, 0.5, 0.2, 0, 0.2, "#8888ff",
                              "#4444aa", 0.05)
        builder.blob(0, 1, 0, 0.4, "#44aa44")
        builder.star(0, 0, 2, 0.4, 0.18, 0.1, "#ffcc00", "#aa8800")
        builder.cone(3, 3, 0.4, 0, 0.8, "#33aa33")
        builder.pyramid_down(0, 0, 1, 1, 0, -1, "#888888")
        for vertices, triangles, colors in builder.meshes():
            self.assertEqual(len(vertices), len(colors))
            self.assertLess(max(i for t in triangles for i in t),
                            len(vertices))
            self.assertTrue(all(0 <= c <= 1 for rgb in colors for c in rgb))

    def test_large_builders_are_split(self) -> None:
        """No mesh goes over the vertex limit."""
        builder = MeshBuilder()
        for k in range(MAX_VERTICES // 4 + 50):
            builder.face([(k, 0, 0), (k + 1, 0, 0), (k + 1, 0, 1),
                          (k, 0, 1)], "#ffffff", (0, 1, 0))
        meshes = builder.meshes()
        self.assertGreaterEqual(len(meshes), 2)
        self.assertTrue(all(len(m[0]) <= MAX_VERTICES for m in meshes))

    def test_light_makes_tops_brighter_than_sides(self) -> None:
        """Flat shading: the top is lighter than the faces below."""
        builder = MeshBuilder()
        builder.box(0, 0, 0, (1, 0), 1, 1, 1, "#808080", "#808080")
        shades = {round(c[0], 3) for _, _, cols in builder.meshes()
                  for c in cols}
        self.assertGreater(len(shades), 2)
        self.assertEqual(max(shades), round(
            palette.hex_to_rgb("#808080")[0] * (0.58 + 0.42 * 0.8 / math.sqrt(
                0.25 + 0.64 + 0.0196)), 3))

    def test_every_map_builds_within_budget(self) -> None:
        """All maps give valid, reasonably small scenes."""
        for path in valid_maps():
            data = MapParser().parse(str(path))
            plan = TerrainPlanner(data, path.name).plan()
            total = 0
            parts = [builders.build_ground(plan, builders.map_colors(data)),
                     builders.build_paths(plan), builders.build_props(plan)]
            parts += [builders.build_pad(p) for p in plan.pads]
            for part in parts:
                for vertices, triangles, colors in part.meshes():
                    self.assertEqual(len(vertices), len(colors))
                    self.assertLess(max(i for t in triangles for i in t),
                                    len(vertices))
                total += part.vertex_count
            self.assertLess(total, 300000, path.name)


class CameraTests(unittest.TestCase):
    """The isometric camera frames every map at any rotation."""

    def test_axes_are_orthonormal(self) -> None:
        """Right, up and forward form an orthonormal basis."""
        for yaw in (45.0, 135.0, 225.0, 315.0):
            right, up, forward = iso_axes(PITCH, yaw)
            for a, b in ((right, up), (right, forward), (up, forward)):
                self.assertAlmostEqual(dot(a, b), 0.0)
            for a in (right, up, forward):
                self.assertAlmostEqual(dot(a, a), 1.0)
            self.assertGreater(up[1], 0.0)
            self.assertLess(forward[1], 0.0)

    def test_pitch_is_between_30_and_35(self) -> None:
        """The brief asks for a tilt of about 30 to 35 degrees."""
        self.assertGreaterEqual(PITCH, 30.0)
        self.assertLessEqual(PITCH, 35.0)
        _, _, forward = iso_axes(PITCH, 45.0)
        self.assertAlmostEqual(math.degrees(math.asin(-forward[1])), PITCH)

    def test_fit_keeps_everything_in_view(self) -> None:
        """Every corner of the main island is on screen."""
        for path in valid_maps():
            data = MapParser().parse(str(path))
            plan = TerrainPlanner(data, path.name).plan()
            corners = box_corners(plan.bounds(main_only=True))
            for yaw in (45.0, 135.0, 225.0, 315.0):
                for aspect in (1.0, 16 / 9, 2.4):
                    fit = fit_view(corners, PITCH, yaw, aspect, 1.0)
                    cx, cy, _ = project(fit.target, PITCH, yaw)
                    for corner in corners:
                        x, y, _ = project(corner, PITCH, yaw)
                        self.assertLessEqual(
                            abs(x - cx), fit.fov * aspect / 2 + 1e-6)
                        self.assertLessEqual(
                            abs(y - cy), fit.fov / 2 + 1e-6)


if __name__ == "__main__":
    unittest.main()
