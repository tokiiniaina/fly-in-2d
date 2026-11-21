"""Tests of the space decor: stars, smoke, backdrop image."""

import math
import unittest
from pathlib import Path

from PIL import Image

from flyin.src.parser_function import MapParser
from flyin.src.viewer3d import builders, environment
from flyin.src.viewer3d.terrain import CELL, TerrainPlan, TerrainPlanner

ROOT = Path(__file__).resolve().parents[1]


def plans() -> list[tuple[str, TerrainPlan]]:
    """Plan every valid map."""
    result = []
    for path in sorted((ROOT / "maps").glob("*.txt")):
        try:
            data = MapParser().parse(str(path))
        except ValueError:
            continue
        result.append((path.name, TerrainPlanner(data, path.name).plan()))
    return result


class SpaceDecorTests(unittest.TestCase):
    """Stars and smoke surround the islands without touching them."""

    def test_stars_stay_outside_the_play_volume(self) -> None:
        """No star inside the ellipsoid around the islands."""
        for name, plan in plans():
            cx, cz, rx, rz = environment.extent(plan)
            stars = environment.star_points(plan, name)
            self.assertEqual(len(stars), environment.STAR_COUNT)
            for star in stars:
                inside = (((star.x - cx) / (rx + 8)) ** 2
                          + ((star.z - cz) / (rz + 8)) ** 2
                          + (star.y / environment.STAR_CLEAR_Y) ** 2)
                self.assertGreaterEqual(inside, 1.0, name)
                self.assertGreater(star.size, 0.0)

    def test_smoke_never_touches_the_terrain(self) -> None:
        """Every puff stays below the ground it is under."""
        for name, plan in plans():
            for puff in environment.smoke_puffs(plan, name):
                top = puff.y + puff.radius * puff.flat
                for cell, island in plan.island.items():
                    near = math.hypot(puff.x - cell[0] * CELL,
                                      puff.z - cell[1] * CELL)
                    if near > puff.radius + 0.6:
                        continue
                    bottom = (plan.base_level[island]
                              - plan.depth[island] - 1.3)
                    self.assertLess(top, bottom, f"{name} {cell}")

    def test_decor_is_deterministic_and_map_specific(self) -> None:
        """Same seed, same sky; another seed, another sky."""
        name, plan = plans()[0]
        first = environment.star_points(plan, name)
        again = environment.star_points(plan, name)
        other = environment.star_points(plan, "zz")
        self.assertEqual(first, again)
        self.assertNotEqual(first, other)
        puffs = environment.smoke_puffs(plan, name)
        self.assertEqual(puffs, environment.smoke_puffs(plan, name))
        self.assertGreater(len(puffs), 10)

    def test_stars_glow_and_smoke_is_translucent(self) -> None:
        """Stars are bright and unshaded; smoke is a translucent mesh."""
        name, plan = plans()[0]
        data = MapParser().parse(str(ROOT / "maps" / name))
        parts = builders.build_all(plan, data, name)
        alphas = [p.alpha for p in parts]
        self.assertEqual(alphas.count(environment.SMOKE_ALPHA), 1)
        self.assertLess(environment.SMOKE_ALPHA, 1.0)
        stars = environment.build_stars(plan, name)
        for _, _, colors in stars.meshes():
            self.assertTrue(all(max(c) > 0.55 for c in colors))
        self.assertEqual(parts[-1].alpha, environment.SMOKE_ALPHA)

    def test_ground_is_galactic_with_a_glowing_rim(self) -> None:
        """Dark tiles, with bright unshaded rim faces."""
        name, plan = plans()[0]
        data = MapParser().parse(str(ROOT / "maps" / name))
        ground = builders.build_ground(plan, builders.map_colors(data))
        colors = [c for _, _, cols in ground.meshes() for c in cols]
        dark = [c for c in colors if sum(c) / 3 < 0.35]
        glow = [c for c in colors if c[2] > 0.8 and c[1] > 0.75]
        self.assertGreater(len(dark), len(colors) // 4)
        self.assertGreater(len(glow), 20)


class BackdropImageTests(unittest.TestCase):
    """The generated galaxy image is a usable static backdrop."""

    def test_image_exists_and_is_large_enough(self) -> None:
        """16:9, at least full HD, dark with some bright stars."""
        path = ROOT / "assets/background/space.jpg"
        self.assertTrue(path.is_file())
        with Image.open(path) as image:
            self.assertGreaterEqual(image.width, 1920)
            self.assertAlmostEqual(image.width / image.height, 16 / 9,
                                   places=1)
            gray = image.convert("L")
            brightest = gray.getextrema()[1]
            mean = sum(gray.resize((64, 36)).tobytes()) / (64 * 36)
        self.assertLess(mean, 70)
        self.assertGreater(brightest, 200)


if __name__ == "__main__":
    unittest.main()
