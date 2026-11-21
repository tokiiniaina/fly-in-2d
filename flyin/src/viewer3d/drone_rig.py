"""Procedural animation of one drone (pure math, no Ursina).

A DroneRig turns where the drone is (and how it moves) into a pose:
hover bob, forward tilt while flying, banking in turns, arm swing,
blinking, exhaust flame and sparks, and a spin at the goal. Everything
is smoothed, so speeding up and slowing down look natural. The rig only
decorates a position decided elsewhere (the simulation).
"""

import math
import random
from dataclasses import dataclass, field

from flyin.src.viewer.animation import clamp01, ease_out_cubic

MAX_SPARKS = 8
CELEBRATE_TIME = 1.5
SPIN_TIME = 1.0
HOVER_HEIGHT = 0.78
CONFETTI = ("#ffd23f", "#ff6b9d", "#6fe3ff", "#9d7bff", "#7dff9a")
EXHAUST = "#8ae9ff"
THRUSTER_DROP = 0.5


@dataclass
class Spark:
    """One exhaust or confetti speck."""

    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    life: float
    size: float
    color: str
    age: float = 0.0


@dataclass(frozen=True)
class SparkView:
    """What to draw for a spark."""

    x: float
    y: float
    z: float
    size: float
    color: str


@dataclass(frozen=True)
class DronePose:
    """Everything the 3D actor needs to draw one frame."""

    x: float
    y: float
    z: float
    yaw: float
    pitch: float
    roll: float
    eye_open: float
    arm_left: float
    arm_right: float
    flame: float
    sparks: tuple[SparkView, ...]


def angle_difference(target: float, current: float) -> float:
    """Shortest signed difference between two angles, in degrees."""
    return (target - current + 180.0) % 360.0 - 180.0


@dataclass
class DroneRig:
    """Animation state of one drone."""

    drone_id: int
    scale: float
    heading: float = 0.0
    clock: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    vx: float = 0.0
    vz: float = 0.0
    sparks: list[Spark] = field(default_factory=list)
    _last: tuple[float, float] | None = None
    _celebrate: float | None = None
    _blink_at: float = 0.0
    _emit: float = 0.0
    _rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        """Seed the randomness from the drone id (independent drones)."""
        self._rng = random.Random(self.drone_id * 7919)
        self._blink_at = 1.0 + self._rng.uniform(0.5, 4.0)

    @property
    def celebrating(self) -> bool:
        """Tell whether the goal animation is running."""
        return self._celebrate is not None

    def celebrate(self) -> None:
        """Start the arrival animation (spin, jump, confetti)."""
        self._celebrate = 0.0
        for _ in range(MAX_SPARKS + 4):
            angle = self._rng.uniform(0, 2 * math.pi)
            push = self._rng.uniform(0.6, 1.6) * self.scale
            self.sparks.append(Spark(
                self._x, self._y, self._z, math.cos(angle) * push,
                self._rng.uniform(1.2, 2.4) * self.scale,
                math.sin(angle) * push, self._rng.uniform(0.7, 1.1),
                0.07 * self.scale, self._rng.choice(CONFETTI)))

    _x: float = 0.0
    _y: float = 0.0
    _z: float = 0.0

    def update(self, dt: float, x: float, z: float, ground: float,
               flight: float | None) -> DronePose:
        """Advance by `dt` seconds with the drone at floor point (x, z)."""
        dt = max(dt, 1e-4)
        self.clock += dt
        phase = self.drone_id * 1.37
        self._track_motion(dt, x, z)
        speed = math.hypot(self.vx, self.vz)
        previous = self.heading
        if speed > 0.25:
            target = math.degrees(math.atan2(self.vx, self.vz))
            self.heading += angle_difference(target, self.heading) * min(
                1.0, dt * 8.0)
        turn_rate = angle_difference(self.heading, previous) / dt
        self.pitch += (min(speed * 7.0, 18.0) - self.pitch) * min(
            1.0, dt * 6.0)
        bank = max(-12.0, min(12.0, -turn_rate * 0.05))
        self.roll += (bank - self.roll) * min(1.0, dt * 5.0)
        lift = 0.0
        spin = 0.0
        boost = 0.0
        if self._celebrate is not None:
            self._celebrate += dt
            t = self._celebrate
            lift = 0.5 * self.scale * math.sin(
                math.pi * clamp01(t / SPIN_TIME))
            spin = 360.0 * ease_out_cubic(t / SPIN_TIME)
            boost = 0.5 * (1.0 - clamp01(t / CELEBRATE_TIME))
            if t >= CELEBRATE_TIME:
                self._celebrate = None
        arc = 0.0 if flight is None else 0.3 * math.sin(math.pi * flight)
        height = (ground + (HOVER_HEIGHT * self.scale)
                  + 0.05 * math.sin(self.clock * 2.4 + phase)
                  + arc * self.scale + lift)
        self._x, self._y, self._z = x, height, z
        self._update_sparks(dt, speed)
        yaw = (self.heading + spin
               + 3.0 * math.sin(self.clock * 1.3 + phase * 1.7))
        swing = 6.0 * math.sin(self.clock * 2.1 + phase)
        flame = (0.7 + 0.25 * math.sin(self.clock * 25.0 + phase)
                 + min(speed * 0.25, 0.6) + boost)
        return DronePose(
            x, height, z, yaw, self.pitch,
            self.roll + 2.0 * math.sin(self.clock * 1.9 + phase),
            self._eye(), swing - self.pitch * 0.8,
            -swing - self.pitch * 0.8, flame,
            tuple(SparkView(s.x, s.y, s.z,
                            s.size * (1.0 - s.age / s.life), s.color)
                  for s in self.sparks))

    def _track_motion(self, dt: float, x: float, z: float) -> None:
        """Smoothed velocity of the floor point."""
        if self._last is None:
            self._last = (x, z)
        raw_x = (x - self._last[0]) / dt
        raw_z = (z - self._last[1]) / dt
        blend = min(1.0, dt * 10.0)
        self.vx += (raw_x - self.vx) * blend
        self.vz += (raw_z - self.vz) * blend
        self._last = (x, z)

    def _eye(self) -> float:
        """Eye opening: 1 most of the time, a quick blink now and then."""
        since = self.clock - self._blink_at
        if since < 0:
            return 1.0
        if since > 0.14:
            self._blink_at = self.clock + self._rng.uniform(2.5, 5.5)
            return 1.0
        return 1.0 - 0.9 * math.sin(math.pi * since / 0.14)

    def _update_sparks(self, dt: float, speed: float) -> None:
        """Move the sparks and emit exhaust ones from the thruster."""
        for spark in self.sparks:
            spark.age += dt
            spark.x += spark.vx * dt
            spark.y += spark.vy * dt
            spark.z += spark.vz * dt
            if spark.color in CONFETTI:
                spark.vy -= 3.0 * dt
        self.sparks = [s for s in self.sparks if s.age < s.life]
        self._emit += dt * (4.0 + min(speed, 3.0) * 4.0)
        exhaust = [s for s in self.sparks if s.color == EXHAUST]
        while self._emit >= 1.0:
            self._emit -= 1.0
            if len(exhaust) >= MAX_SPARKS:
                continue
            jitter = self.scale * 0.05
            spark = Spark(
                self._x + self._rng.uniform(-jitter, jitter),
                self._y - THRUSTER_DROP * self.scale,
                self._z + self._rng.uniform(-jitter, jitter),
                -self.vx * 0.15, -self._rng.uniform(0.5, 1.0) * self.scale,
                -self.vz * 0.15, self._rng.uniform(0.45, 0.8),
                0.06 * self.scale, EXHAUST)
            self.sparks.append(spark)
            exhaust.append(spark)
