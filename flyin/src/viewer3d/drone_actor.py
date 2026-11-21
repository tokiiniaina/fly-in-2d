"""Ursina entities of one drone, driven by a DronePose."""

from typing import Any

from ursina import Entity, Mesh, destroy

from flyin.src.viewer3d import drone_model
from flyin.src.viewer3d.drone_rig import DronePose
from flyin.src.viewer3d.meshbuilder import MeshBuilder
from flyin.src.viewer3d.scene import ColorCache

SPARK_POOL = 14
FLAME_ALPHA = 0.6
SPARK_ALPHA = 0.85


class DroneParts:
    """Mesh data of every drone part, built once and shared."""

    def __init__(self, colors: ColorCache) -> None:
        """Build the parts and convert their colors."""
        builders = {
            "body": drone_model.build_body(),
            "eye": drone_model.build_eye(),
            "arm_left": drone_model.build_arm(-1.0),
            "arm_right": drone_model.build_arm(1.0),
            "flame": drone_model.build_flame(),
            "spark": drone_model.build_particle(),
        }
        self._data: dict[str, tuple[list[Any], list[Any], list[Any]]] = {}
        for name, builder in builders.items():
            vertices, triangles, rgb = self._single(builder)
            self._data[name] = (vertices, triangles,
                                [colors.get(c) for c in rgb])

    @staticmethod
    def _single(builder: MeshBuilder) -> tuple[list[Any], list[Any],
                                               list[Any]]:
        """The only mesh of a small builder."""
        meshes = builder.meshes()
        if len(meshes) != 1:
            raise ValueError("a drone part must be a single mesh")
        return meshes[0]

    def mesh(self, name: str) -> Any:
        """Create a new Mesh of a part (a Mesh cannot be shared)."""
        vertices, triangles, colors = self._data[name]
        return Mesh(vertices=vertices, triangles=triangles, colors=colors)


class DroneActor:
    """A drone made of a body, an eye, two arms, a flame and sparks."""

    def __init__(self, world: Any, parts: DroneParts,
                 scale: float) -> None:
        """Create every entity (hidden until the first pose)."""
        self.scale = scale
        self.root = Entity(parent=world, scale=(scale, scale, scale),
                           enabled=False)
        self.tilt = Entity(parent=self.root)
        self.body = Entity(parent=self.tilt, model=parts.mesh("body"),
                           double_sided=True)
        self.eye = Entity(parent=self.tilt, model=parts.mesh("eye"),
                          position=(0, drone_model.EYE_Y, 0),
                          double_sided=True)
        shoulder_y, shoulder_z = (drone_model.SHOULDER_Y,
                                  drone_model.SHOULDER_Z)
        self.arm_left = Entity(
            parent=self.tilt, model=parts.mesh("arm_left"),
            position=(-drone_model.SHOULDER_X, shoulder_y, shoulder_z),
            double_sided=True)
        self.arm_right = Entity(
            parent=self.tilt, model=parts.mesh("arm_right"),
            position=(drone_model.SHOULDER_X, shoulder_y, shoulder_z),
            double_sided=True)
        self.flame = Entity(parent=self.tilt, model=parts.mesh("flame"),
                            position=(0, drone_model.THRUSTER_Y, 0),
                            double_sided=True)
        self.flame.alpha = FLAME_ALPHA
        self.sparks = []
        for _ in range(SPARK_POOL):
            spark = Entity(parent=world, model=parts.mesh("spark"),
                           enabled=False, double_sided=True)
            spark.alpha = SPARK_ALPHA
            self.sparks.append(spark)

    def apply(self, pose: DronePose, visible: bool, pop: float) -> None:
        """Move and pose every part for one frame."""
        self.root.enabled = visible
        size = self.scale * max(pop, 1e-3)
        self.root.scale = (size, size, size)
        self.root.position = (pose.x, pose.y, pose.z)
        self.root.rotation = (0, pose.yaw, 0)
        self.tilt.rotation = (pose.pitch, 0, pose.roll)
        self.eye.scale_y = max(pose.eye_open, 0.05)
        self.arm_left.rotation = (pose.arm_left, 0, 0)
        self.arm_right.rotation = (pose.arm_right, 0, 0)
        self.flame.scale = (1, max(pose.flame, 0.05), 1)
        for index, spark in enumerate(self.sparks):
            if visible and index < len(pose.sparks):
                view = pose.sparks[index]
                spark.position = (view.x, view.y, view.z)
                scale = max(view.size * 2.0, 1e-3)
                spark.scale = (scale, scale, scale)
                spark.enabled = True
            else:
                spark.enabled = False

    def destroy(self) -> None:
        """Remove all entities of the drone."""
        destroy(self.root)
        for spark in self.sparks:
            destroy(spark)
