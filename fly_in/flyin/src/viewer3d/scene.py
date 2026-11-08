"""Ursina scene of one map: the pure meshes become entities."""

from typing import Any

from ursina import Entity, Mesh, color, destroy

from flyin.src.map_data import MapData
from flyin.src.viewer3d import builders
from flyin.src.viewer3d.camera import Vec, box_corners
from flyin.src.viewer3d.meshbuilder import MeshBuilder, RGB
from flyin.src.viewer3d.palette import rgb_to_hex
from flyin.src.viewer3d.terrain import TerrainPlan, TerrainPlanner


class ColorCache:
    """Convert RGB floats to Ursina colors, once per distinct color."""

    def __init__(self) -> None:
        """Start empty."""
        self._colors: dict[str, Any] = {}

    def get(self, rgb: RGB) -> Any:
        """Return the Ursina color of an RGB tuple."""
        key = rgb_to_hex(rgb)
        if key not in self._colors:
            self._colors[key] = color.hex(key)
        return self._colors[key]


class MapScene:
    """The 3D world of a map, without drones (milestone M1)."""

    def __init__(self, data: MapData, name: str) -> None:
        """Plan the terrain and create one entity per mesh."""
        self.plan: TerrainPlan = TerrainPlanner(data, name).plan()
        self.root = Entity()
        self._colors = ColorCache()
        for part in builders.build_all(self.plan, data, name):
            self._add(part.builder, part.alpha)

    def _add(self, builder: MeshBuilder, alpha: float = 1.0) -> None:
        """Create the entities of a builder (several if it is large)."""
        for vertices, triangles, colors in builder.meshes():
            entity = Entity(
                parent=self.root,
                model=Mesh(vertices=vertices, triangles=triangles,
                           colors=[self._colors.get(c) for c in colors]),
                double_sided=True)
            if alpha < 1.0:
                entity.alpha = alpha

    def frame_points(self) -> list[Vec]:
        """Points the camera must keep in view (the main island)."""
        return box_corners(self.plan.bounds(main_only=True))

    def destroy(self) -> None:
        """Remove the whole scene."""
        destroy(self.root)
