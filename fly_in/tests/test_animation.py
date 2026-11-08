"""Tests of the pure animation engine and of the mesh geometry."""

import math
import unittest

from flyin.src.viewer.animation import (
    APPEAR_TIME,
    LAND_TIME,
    DroneAnimator,
    DroneTarget,
    bump,
    ease_in_out_cubic,
    ease_out_back,
    ease_out_cubic,
    hover,
)
from flyin.src.viewer.geometry import (
    circle_outline,
    fan,
    polygon_area,
    rounded_rect_outline,
)
from flyin.src.viewer.theme import lighten

FRAME = 1 / 60


def run(animator: DroneAnimator, seconds: float) -> None:
    """Advance an animator by whole frames."""
    for _ in range(round(seconds / FRAME)):
        animator.tick(FRAME)


class EasingTests(unittest.TestCase):
    """Curves start and end where expected."""

    def test_endpoints(self) -> None:
        """Every curve maps 0 to 0 and 1 to 1."""
        for curve in (ease_out_cubic, ease_in_out_cubic, ease_out_back):
            self.assertAlmostEqual(curve(0.0), 0.0)
            self.assertAlmostEqual(curve(1.0), 1.0)
            self.assertAlmostEqual(curve(-3.0), 0.0)
            self.assertAlmostEqual(curve(7.0), 1.0)

    def test_monotonic(self) -> None:
        """Cubic curves never go backwards."""
        for curve in (ease_out_cubic, ease_in_out_cubic):
            values = [curve(i / 100) for i in range(101)]
            self.assertEqual(values, sorted(values))

    def test_soft_start_and_stop(self) -> None:
        """The flight curve is slow at both ends, fast in the middle."""
        self.assertLess(ease_in_out_cubic(0.1), 0.01)
        self.assertGreater(ease_in_out_cubic(0.9), 0.99)
        self.assertAlmostEqual(ease_in_out_cubic(0.5), 0.5)

    def test_back_overshoots(self) -> None:
        """The pop curve goes past 1 before settling."""
        self.assertGreater(max(ease_out_back(i / 50) for i in range(51)),
                           1.05)

    def test_bump_and_hover(self) -> None:
        """A bump is 1 outside its window; hover stays bounded."""
        self.assertEqual(bump(-1, 0.2, 0.1), 1.0)
        self.assertEqual(bump(0.3, 0.2, 0.1), 1.0)
        self.assertAlmostEqual(bump(0.1, 0.2, 0.1), 1.1)
        for i in range(100):
            self.assertLessEqual(abs(hover(i * 0.1, 1.0, 0.02)), 0.02)


class AnimatorTests(unittest.TestCase):
    """Drones fly smoothly and end exactly on the backend target."""

    def make(self) -> DroneAnimator:
        """An animator with drone 1 at the origin."""
        animator = DroneAnimator()
        animator.go({1: DroneTarget(0, 0, True)}, 0.0)
        return animator

    def test_flight_is_smooth_and_exact(self) -> None:
        """No jump between frames, and the final position is exact."""
        animator = self.make()
        animator.go({1: DroneTarget(1.0, 0.5, True)}, 0.75)
        previous = animator.sample(1)
        biggest = 0.0
        for _ in range(60):
            animator.tick(FRAME)
            now = animator.sample(1)
            biggest = max(biggest, math.hypot(now.x - previous.x,
                                              now.y - previous.y))
            previous = now
        # the curve is at most 3x faster than the average speed
        limit = 3.0 * math.hypot(1.0, 0.5) / (0.75 / FRAME)
        self.assertLessEqual(biggest, limit * 1.02)
        self.assertGreater(biggest, limit * 0.8)
        self.assertEqual((previous.x, previous.y), (1.0, 0.5))
        self.assertFalse(animator.moving)

    def test_stays_on_the_straight_connection(self) -> None:
        """Every intermediate point lies on the segment."""
        animator = self.make()
        animator.go({1: DroneTarget(1.0, 0.5, True)}, 0.5)
        for _ in range(40):
            animator.tick(FRAME)
            sample = animator.sample(1)
            self.assertAlmostEqual(sample.y, sample.x * 0.5, places=9)

    def test_halfway_is_between(self) -> None:
        """At half time the drone is strictly between start and end."""
        animator = self.make()
        animator.go({1: DroneTarget(2.0, 0.0, True)}, 1.0)
        run(animator, 0.5)
        self.assertGreater(animator.sample(1).x, 0.5)
        self.assertLess(animator.sample(1).x, 1.5)

    def test_stretch_in_flight_and_landing_bounce(self) -> None:
        """The sprite stretches while flying, then bounces on landing."""
        animator = self.make()
        animator.go({1: DroneTarget(1.0, 0.0, True)}, 1.0)
        run(animator, 0.5)
        flying = animator.sample(1)
        self.assertGreater(flying.scale_x, 1.0)
        self.assertLess(flying.scale_y, 1.0)
        run(animator, 0.5 + LAND_TIME / 2)
        landed = animator.sample(1)
        self.assertGreater(landed.scale_x, 1.0)
        run(animator, 1.0)
        self.assertEqual(animator.sample(1).scale_x, 1.0)

    def test_retarget_starts_from_current_position(self) -> None:
        """A new target mid-flight does not teleport the drone."""
        animator = self.make()
        animator.go({1: DroneTarget(1.0, 0.0, True)}, 1.0)
        run(animator, 0.5)
        here = animator.sample(1).x
        animator.go({1: DroneTarget(0.0, 1.0, True)}, 1.0)
        self.assertAlmostEqual(animator.sample(1).x, here)
        run(animator, 1.2)
        self.assertEqual((animator.sample(1).x, animator.sample(1).y),
                         (0.0, 1.0))

    def test_same_target_is_a_noop(self) -> None:
        """Asking for the same place again does not restart a flight."""
        animator = self.make()
        animator.go({1: DroneTarget(0.0, 0.0, True)}, 1.0)
        self.assertFalse(animator.moving)

    def test_zero_duration_jumps(self) -> None:
        """Without duration the drone is there immediately."""
        animator = self.make()
        animator.go({1: DroneTarget(3.0, 4.0, True)}, 0.0)
        self.assertEqual((animator.sample(1).x, animator.sample(1).y),
                         (3.0, 4.0))

    def test_hide_at_the_end_of_the_flight(self) -> None:
        """A drone that becomes hidden stays visible until it arrives."""
        animator = self.make()
        animator.go({1: DroneTarget(1.0, 0.0, False)}, 0.5)
        self.assertTrue(animator.sample(1).visible)
        run(animator, 0.6)
        self.assertFalse(animator.sample(1).visible)

    def test_pop_in_after_delay(self) -> None:
        """Drones created with a delay appear later, growing from zero."""
        animator = DroneAnimator()
        animator.go({1: DroneTarget(0, 0, True)}, 0.0, appear_delay=0.5)
        self.assertFalse(animator.sample(1).visible)
        run(animator, 0.5 + APPEAR_TIME * 0.3)
        sample = animator.sample(1)
        self.assertTrue(sample.visible)
        self.assertLess(sample.scale_x, 1.0)
        run(animator, 1.0)
        self.assertEqual(animator.sample(1).scale_x, 1.0)

    def test_many_drones_end_on_target(self) -> None:
        """Staggered starts still end exactly on every target."""
        animator = DroneAnimator()
        animator.go({i: DroneTarget(0, 0, True) for i in range(1, 13)}, 0)
        goals = {i: DroneTarget(i * 0.1, -i * 0.05, True)
                 for i in range(1, 13)}
        animator.go(goals, 0.8)
        run(animator, 1.0)
        for drone_id, goal in goals.items():
            sample = animator.sample(drone_id)
            self.assertEqual((sample.x, sample.y), (goal.x, goal.y))


class GeometryTests(unittest.TestCase):
    """Meshes are built from correct outlines."""

    def test_rounded_rect_bounds_and_area(self) -> None:
        """The outline fits its box and is smaller than the box."""
        points = rounded_rect_outline(2.0, 1.0, 0.25)
        self.assertLessEqual(max(abs(x) for x, _ in points), 1.0 + 1e-9)
        self.assertLessEqual(max(abs(y) for _, y in points), 0.5 + 1e-9)
        area = polygon_area(points)
        self.assertLess(area, 2.0)
        self.assertGreater(area, 2.0 - (4 - math.pi) * 0.25 ** 2 - 0.01)

    def test_circle_area(self) -> None:
        """A 32-gon is close to the circle."""
        area = polygon_area(circle_outline(1.0, 32))
        self.assertAlmostEqual(area, math.pi, delta=0.07)

    def test_fan_indices(self) -> None:
        """A fan references only existing vertices, with an offset."""
        points = circle_outline(1.0, 8)
        vertices, triangles = fan(points, (5.0, 5.0), offset=10)
        self.assertEqual(len(vertices), 9)
        self.assertEqual(len(triangles), 8)
        flat = {i for tri in triangles for i in tri}
        self.assertEqual(flat, set(range(10, 19)))

    def test_lighten(self) -> None:
        """Lightening moves a color toward white."""
        self.assertEqual(lighten("#000000", 1.0), "#ffffff")
        self.assertEqual(lighten("#336699", 0.0), "#336699")


if __name__ == "__main__":
    unittest.main()
