"""Tests of the drone: model, procedural animation, placement (pure)."""

import math
import unittest
from pathlib import Path

from flyin.src.viewer.adapters.simulation_adapter import SimulationAdapter
from flyin.src.viewer3d import drone_model
from flyin.src.viewer3d.drone_layout import (
    drone_scale,
    ring_offsets,
    targets_for_state,
)
from flyin.src.viewer3d.drone_rig import (
    CELEBRATE_TIME,
    MAX_SPARKS,
    DroneRig,
    DronePose,
    angle_difference,
)
from flyin.src.viewer3d.terrain import TerrainPlanner

ROOT = Path(__file__).resolve().parents[1]
FRAME = 1 / 60


def run(rig: DroneRig, seconds: float, x: float = 0.0, z: float = 0.0,
        vx: float = 0.0, vz: float = 0.0, ground: float = 0.22
        ) -> tuple[DronePose, float, float]:
    """Advance a rig; the floor point moves at (vx, vz)."""
    pose = rig.update(FRAME, x, z, ground, None)
    for _ in range(round(seconds / FRAME) - 1):
        x += vx * FRAME
        z += vz * FRAME
        pose = rig.update(FRAME, x, z, ground, None)
    return pose, x, z


class ModelTests(unittest.TestCase):
    """The drone has every feature of the reference image."""

    def test_parts_are_valid_single_meshes(self) -> None:
        """Each animated part is one valid mesh."""
        parts = {"body": drone_model.build_body(),
                 "eye": drone_model.build_eye(),
                 "arm": drone_model.build_arm(1.0),
                 "flame": drone_model.build_flame(),
                 "spark": drone_model.build_particle()}
        for name, builder in parts.items():
            meshes = builder.meshes()
            self.assertEqual(len(meshes), 1, name)
            vertices, triangles, colors = meshes[0]
            self.assertEqual(len(vertices), len(colors))
            self.assertLess(max(i for t in triangles for i in t),
                            len(vertices))

    def test_features_of_the_reference(self) -> None:
        """White body, black eye, glowing ring, antenna, arms, thruster."""
        body = drone_model.build_static_drone()
        colors = [c for _, _, cols in body.meshes() for c in cols]
        whites = [c for c in colors
                  if min(c) > 0.55 and max(c) - min(c) < 0.1]
        blacks = [c for c in colors if max(c) < 0.08]
        glows = [c for c in colors if c[2] > 0.9 and c[1] > 0.8
                 and c[0] < 0.6]
        self.assertGreater(len(whites), 150)
        self.assertGreater(len(blacks), 20)
        self.assertGreater(len(glows), 30)
        ys = [v[1] for vs, _, _ in body.meshes() for v in vs]
        self.assertGreater(max(ys), 0.55)
        self.assertLess(min(ys), -0.6)

    def test_arms_are_mirrored(self) -> None:
        """Left and right arms reach out on opposite sides."""
        left = drone_model.build_arm(-1.0).meshes()[0][0]
        right = drone_model.build_arm(1.0).meshes()[0][0]
        self.assertLess(sum(v[0] for v in left), 0)
        self.assertGreater(sum(v[0] for v in right), 0)

    def test_drone_is_a_small_object(self) -> None:
        """The whole drone fits in about one unit before scaling."""
        xs = [v for vs, _, _ in drone_model.build_static_drone().meshes()
              for v in vs]
        width = max(v[0] for v in xs) - min(v[0] for v in xs)
        self.assertLess(width, 1.1)
        self.assertGreater(width, 0.6)


class RigTests(unittest.TestCase):
    """Procedural animation: hover, tilt, heading, blink, goal spin."""

    def test_hover_moves_a_little_and_stays_above_ground(self) -> None:
        """A still drone bobs gently and never touches the ground."""
        rig = DroneRig(3, 0.8)
        heights = []
        for _ in range(300):
            pose = rig.update(FRAME, 0.0, 0.0, 0.22, None)
            heights.append(pose.y)
        self.assertGreater(max(heights) - min(heights), 0.05)
        self.assertLess(max(heights) - min(heights), 0.15)
        self.assertGreater(min(heights), 0.22 + 0.4)

    def test_still_drone_is_level(self) -> None:
        """No forward tilt when it does not move."""
        rig = DroneRig(1, 0.8)
        pose, _, _ = run(rig, 3.0)
        self.assertLess(abs(pose.pitch), 0.01)
        self.assertLess(abs(pose.roll), 3.0)
        self.assertAlmostEqual(rig.heading, 0.0)

    def test_tilts_forward_and_faces_the_motion(self) -> None:
        """Moving along +x: heading 90, nose down, tilt grows smoothly."""
        rig = DroneRig(1, 0.8)
        pitches = []
        x = 0.0
        for _ in range(120):
            x += 2.0 * FRAME
            pitches.append(rig.update(FRAME, x, 0.0, 0.22, 0.5).pitch)
        self.assertAlmostEqual(rig.heading, 90.0, delta=1.0)
        self.assertGreater(pitches[-1], 8.0)
        self.assertLessEqual(max(pitches), 18.0 + 1e-6)
        self.assertEqual(pitches, sorted(pitches))
        self.assertLess(pitches[1], 5.0)

    def test_heading_for_each_direction(self) -> None:
        """+z is 0 degrees, -x is -90, -z is 180."""
        cases = ((0, 1, 0.0), (-1, 0, -90.0), (0, -1, 180.0))
        for vx, vz, expected in cases:
            rig = DroneRig(1, 0.8)
            run(rig, 2.0, vx=vx * 2.0, vz=vz * 2.0)
            self.assertAlmostEqual(
                abs(angle_difference(rig.heading, expected)), 0.0,
                delta=1.5)

    def test_levels_out_after_stopping(self) -> None:
        """Deceleration: the tilt goes back to zero progressively."""
        rig = DroneRig(1, 0.8)
        _, x, z = run(rig, 2.0, vx=2.0)
        pose, _, _ = run(rig, 0.05, x, z)
        self.assertGreater(pose.pitch, 1.0)
        pose, _, _ = run(rig, 2.0, x, z)
        self.assertLess(pose.pitch, 0.2)

    def test_turns_the_short_way(self) -> None:
        """Going from 350 to 10 degrees does not spin through 180."""
        self.assertAlmostEqual(angle_difference(10.0, 350.0), 20.0)
        self.assertAlmostEqual(angle_difference(350.0, 10.0), -20.0)
        rig = DroneRig(1, 0.8, heading=170.0)
        seen = []
        x = z = 0.0
        for _ in range(90):
            x += 2.0 * FRAME * math.sin(math.radians(-170.0))
            z += 2.0 * FRAME * math.cos(math.radians(-170.0))
            rig.update(FRAME, x, z, 0.22, None)
            seen.append(rig.heading)
        self.assertTrue(all(abs(angle_difference(h, 170.0)) < 25
                            for h in seen))

    def test_blinks_now_and_then(self) -> None:
        """The eye closes briefly, and is open almost all the time."""
        rig = DroneRig(5, 0.8)
        opens = [rig.update(FRAME, 0.0, 0.0, 0.22, None).eye_open
                 for _ in range(60 * 30)]
        self.assertLess(min(opens), 0.3)
        self.assertGreater(sum(o > 0.99 for o in opens) / len(opens), 0.9)

    def test_sparks_are_bounded_and_expire(self) -> None:
        """Discreet exhaust: capped number, short life."""
        rig = DroneRig(2, 0.8)
        counts = []
        x = 0.0
        for _ in range(600):
            x += 1.5 * FRAME
            counts.append(len(rig.update(FRAME, x, 0.0, 0.22,
                                         0.5).sparks))
        self.assertGreater(max(counts), 2)
        self.assertLessEqual(max(counts), MAX_SPARKS)
        for spark in rig.sparks:
            self.assertLess(spark.age, spark.life)

    def test_goal_celebration(self) -> None:
        """A spin of 360 degrees, a jump, confetti, then back to normal."""
        rig = DroneRig(4, 0.8)
        calm, _, _ = run(rig, 1.0)
        rig.celebrate()
        self.assertTrue(rig.celebrating)
        yaws, ys, sparks = [], [], []
        for _ in range(round(CELEBRATE_TIME / FRAME) + 5):
            pose = rig.update(FRAME, 0.0, 0.0, 0.22, None)
            yaws.append(pose.yaw)
            ys.append(pose.y)
            sparks.append(len(pose.sparks))
        self.assertGreater(max(yaws) - min(yaws), 300.0)
        self.assertGreater(max(ys) - calm.y, 0.25)
        self.assertGreater(max(sparks), MAX_SPARKS)
        self.assertFalse(rig.celebrating)
        after, _, _ = run(rig, 2.0)
        self.assertLess(after.y, calm.y + 0.15)

    def test_drones_are_independent(self) -> None:
        """Two drones do not bob or blink in sync."""
        first, second = DroneRig(1, 0.8), DroneRig(2, 0.8)
        a = [first.update(FRAME, 0, 0, 0.22, None).y for _ in range(120)]
        b = [second.update(FRAME, 0, 0, 0.22, None).y for _ in range(120)]
        self.assertNotEqual(a, b)

    def test_deterministic(self) -> None:
        """The same drone id gives the same animation."""
        poses = []
        for _ in range(2):
            rig = DroneRig(7, 0.8)
            poses.append([rig.update(FRAME, i * 0.01, 0, 0.22, None)
                          for i in range(200)])
        self.assertEqual(poses[0], poses[1])


class LayoutTests(unittest.TestCase):
    """Drone size and placement follow the pads and the backend."""

    def test_size_adapts_to_pads(self) -> None:
        """Bigger pads give bigger drones, within limits."""
        self.assertLess(drone_scale(0.4), drone_scale(0.62))
        self.assertGreaterEqual(drone_scale(0.01), 0.5)
        self.assertLessEqual(drone_scale(5.0), 1.15)

    def test_rings_do_not_overlap(self) -> None:
        """Any group of drones keeps a minimum spacing."""
        for count in (1, 2, 3, 6, 7, 12, 19, 25, 40):
            offsets = ring_offsets(count, 0.8)
            self.assertEqual(len(offsets), count)
            for i, a in enumerate(offsets):
                for b in offsets[i + 1:]:
                    self.assertGreater(math.dist(a, b), 0.8 * 0.95,
                                       count)

    def test_every_drone_has_a_target_on_every_map(self) -> None:
        """All drones are placed, at the zone or on its connection."""
        for path in sorted((ROOT / "maps").glob("*.txt")):
            try:
                result = SimulationAdapter().run(str(path))
            except ValueError:
                continue
            plan = TerrainPlanner(result.data, path.name).plan()
            scale = drone_scale(plan.pads[0].half)
            pads = {p.name: p for p in plan.pads}
            for turn in range(result.timeline.total_turns + 1):
                state = result.timeline.state(turn)
                targets = targets_for_state(plan, state, scale)
                self.assertEqual(len(targets), result.data.nb_drones)
                for drone in state.drones:
                    target = targets[drone.drone_id]
                    if drone.zone is not None:
                        pad = pads[drone.zone]
                        near = math.hypot(target.x - pad.x,
                                          target.y - pad.z)
                        self.assertLessEqual(near, 4.0 * scale * 2.2,
                                             path.name)

    def test_flying_drone_is_between_the_two_pads(self) -> None:
        """A drone on a restricted link hovers at the link middle."""
        result = SimulationAdapter().run(str(ROOT / "maps/02_simple_fork.txt"))
        plan = TerrainPlanner(result.data, "x").plan()
        state = result.timeline.state(2)
        flyer = next(d for d in state.drones if d.flight)
        targets = targets_for_state(plan, state, 0.8)
        a, b = plan.pad("junction"), plan.pad("path_b")
        target = targets[flyer.drone_id]
        self.assertAlmostEqual(target.x, (a.x + b.x) / 2, delta=0.1)
        self.assertAlmostEqual(target.y, (a.z + b.z) / 2, delta=0.1)


if __name__ == "__main__":
    unittest.main()
