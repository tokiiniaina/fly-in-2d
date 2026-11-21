"""Where drones hover for a turn, and how big they are (pure)."""

import math

from flyin.src.viewer.adapters.simulation_adapter import (
    DroneSnapshot,
    TurnState,
)
from flyin.src.viewer.animation import DroneTarget
from flyin.src.viewer3d.terrain import PadPlan, TerrainPlan

RING_SIZE = 6
PAD_TOP = 0.22


def drone_scale(pad_half: float) -> float:
    """Size of a drone, adapted to the size of the pads."""
    return max(0.5, min(1.15, pad_half / 0.62 * 1.05))


def ring_offsets(count: int, radius: float) -> list[tuple[float, float]]:
    """Positions of `count` drones around a point, in rings of 6, 12, 18..."""
    if count <= 1:
        return [(0.0, 0.0)] * max(count, 0)
    offsets: list[tuple[float, float]] = []
    ring = 0
    while len(offsets) < count:
        ring += 1
        capacity = RING_SIZE * ring
        amount = min(capacity, count - len(offsets))
        if ring == 1 and count <= RING_SIZE:
            amount = count
        for k in range(amount):
            angle = math.pi / 2 + 2 * math.pi * k / amount + ring * 0.4
            offsets.append((radius * ring * math.cos(angle),
                            radius * ring * math.sin(angle)))
    return offsets


def targets_for_state(plan: TerrainPlan, state: TurnState,
                      scale: float) -> dict[int, DroneTarget]:
    """Floor position (x, z) of every drone for a state.

    A drone in flight toward a restricted zone hovers at the middle of
    its connection. Several drones in one place spread in rings.
    """
    pads = {pad.name: pad for pad in plan.pads}
    zone_groups: dict[str, list[DroneSnapshot]] = {}
    link_groups: dict[frozenset[str], list[DroneSnapshot]] = {}
    for drone in state.drones:
        if drone.zone is not None:
            zone_groups.setdefault(drone.zone, []).append(drone)
        elif drone.flight is not None:
            link_groups.setdefault(frozenset(drone.flight), []).append(
                drone)
    targets: dict[int, DroneTarget] = {}
    for name, group in zone_groups.items():
        pad = pads[name]
        _spread(targets, group, pad.x, pad.z, scale)
    for key, group in link_groups.items():
        first, second = sorted(key)
        a, b = pads[first], pads[second]
        _spread(targets, group, (a.x + b.x) / 2, (a.z + b.z) / 2, scale)
    return targets


def _spread(targets: dict[int, DroneTarget], group: list[DroneSnapshot],
            x: float, z: float, scale: float) -> None:
    """Fan a group of drones around a point."""
    for drone, (dx, dz) in zip(group,
                               ring_offsets(len(group), 0.95 * scale)):
        targets[drone.drone_id] = DroneTarget(x + dx, z + dz, True)


def ground_height(pad: PadPlan) -> float:
    """Height of the floor under a pad (where drones hover above)."""
    return {"priority": 0.34, "restricted": 0.12}.get(pad.kind, PAD_TOP)
