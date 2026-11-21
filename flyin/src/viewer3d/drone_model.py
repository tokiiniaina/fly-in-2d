"""The 3D drone, built from primitives (pure, no Ursina).

It follows the reference image: a compact white egg-shaped body, a big
black eye with a glowing blue ring, a small antenna, two jointed arms
with claws, and a glowing blue thruster underneath. The drone faces +Z.
Each moving part is its own builder so it can be animated separately.
"""

from flyin.src.viewer3d.meshbuilder import MeshBuilder, Vec

WHITE = "#f2efe9"
SHELL = "#d9d5ce"
GRAY = "#8e93a1"
DARK = "#23262f"
BLACK = "#0b0d14"
GLOW = "#45d9ff"
GLOW_SOFT = "#8ae9ff"

BODY_RADIUS = 0.34
EYE_Y = 0.07
SHOULDER_X = 0.30
SHOULDER_Y = -0.2
SHOULDER_Z = 0.04
THRUSTER_Y = -0.46


def build_body() -> MeshBuilder:
    """Egg body, side pods, antenna, belly band and thruster."""
    b = MeshBuilder()
    b.blob(0.0, 0.0, 0.0, BODY_RADIUS, WHITE, (1.0, 0.95, 1.0), 5, 12)
    b.blob(0.0, 0.2, -0.1, 0.2, SHELL, (1.0, 0.5, 1.0), 3, 8)
    for side in (-1.0, 1.0):
        b.tube((side * 0.3, 0.0, 0.02), (side * 0.43, 0.0, 0.02), 0.1,
               GRAY, WHITE, 10)
        b.tube((side * 0.425, 0.0, 0.02), (side * 0.445, 0.0, 0.02),
               0.065, GLOW, GLOW, 10, lit=False)
    b.tube((0.0, 0.3, -0.05), (0.0, 0.6, -0.05), 0.016, GRAY, GRAY, 6)
    b.blob(0.0, 0.63, -0.05, 0.045, GLOW_SOFT, (1.0, 1.0, 1.0), 2, 6,
           soft=True)
    b.tube((0.0, -0.3, 0.0), (0.0, -0.38, 0.0), 0.22, DARK, DARK, 12)
    for k in (-1, 0, 1):
        b.tube((k * 0.06 + 0.08, -0.28, 0.2), (k * 0.06 + 0.08, -0.34,
                                               0.2), 0.012, GLOW, GLOW,
               4, lit=False)
    b.tube((0.0, -0.38, 0.0), (0.0, THRUSTER_Y, 0.0), 0.13, DARK, GRAY,
           10)
    b.disc_facing((0.0, THRUSTER_Y - 0.004, 0.0), (0.0, -1.0, 0.0), 0.1,
                  GLOW, sides=12)
    return b


def build_eye() -> MeshBuilder:
    """The big black eye with a glowing ring and a highlight."""
    b = MeshBuilder()
    b.tube((0.0, 0.0, 0.30), (0.0, 0.0, 0.335), 0.215, GLOW, GLOW, 16,
           lit=False)
    b.tube((0.0, 0.0, 0.31), (0.0, 0.0, 0.355), 0.175, BLACK, BLACK, 16,
           lit=False)
    b.disc_facing((0.065, 0.065, 0.357), (0.0, 0.0, 1.0), 0.042,
                  "#ffffff", sides=10)
    return b


def build_arm(side: float) -> MeshBuilder:
    """One articulated arm with a claw, relative to its shoulder.

    `side` is -1 for the left arm and +1 for the right arm.
    """
    b = MeshBuilder()
    elbow: Vec = (side * 0.12, -0.2, 0.06)
    wrist: Vec = (side * 0.08, -0.4, 0.17)
    b.tube((0.0, 0.0, 0.0), elbow, 0.05, WHITE, WHITE, 7)
    b.blob(elbow[0], elbow[1], elbow[2], 0.065, DARK, (1, 1, 1), 2, 6)
    b.tube(elbow, wrist, 0.058, WHITE, SHELL, 7)
    b.blob(wrist[0], wrist[1], wrist[2], 0.06, GRAY, (1, 1, 1), 2, 6)
    for spread in (-1.0, 1.0):
        tip: Vec = (wrist[0] + spread * 0.055, wrist[1] - 0.15,
                    wrist[2] + 0.07)
        b.tube(wrist, tip, 0.024, BLACK, DARK, 5)
    return b


def build_flame() -> MeshBuilder:
    """The glowing exhaust cone (scaled by the animation)."""
    b = MeshBuilder()
    b.pyramid_down(0.0, 0.0, 0.085, 0.085, 0.0, -0.55, GLOW_SOFT,
                   lit=False)
    return b


def build_particle() -> MeshBuilder:
    """One small glowing speck (the exhaust particles)."""
    b = MeshBuilder()
    b.diamond(0.0, 0.0, 0.0, 0.5, GLOW_SOFT)
    return b


def build_static_drone() -> MeshBuilder:
    """All the parts in one builder (previews and tests)."""
    result = MeshBuilder()
    parts: list[tuple[MeshBuilder, Vec]] = [
        (build_body(), (0.0, 0.0, 0.0)), (build_eye(), (0.0, EYE_Y, 0.0)),
        (build_arm(-1.0), (-SHOULDER_X, SHOULDER_Y, SHOULDER_Z)),
        (build_arm(1.0), (SHOULDER_X, SHOULDER_Y, SHOULDER_Z)),
        (build_flame(), (0.0, THRUSTER_Y, 0.0)),
    ]
    for builder, (dx, dy, dz) in parts:
        for vertices, triangles, colors in builder.meshes():
            moved = [(x + dx, y + dy, z + dz) for x, y, z in vertices]
            result.add_mesh(moved, triangles, colors)
    return result
