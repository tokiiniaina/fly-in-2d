"""A tiny stand-in for the `ursina` module, used by the smoke tests.

It records what the viewer creates (entities, texts, meshes) so the tests
can check the screens without opening a window. It is NOT a replacement
for running the real Ursina application.
"""

import sys
import types
from typing import Any


class Entity:
    """Records its attributes and its place in the scene tree."""

    def __init__(self, **kwargs: Any) -> None:
        """Store every keyword as an attribute and attach to the parent."""
        self.children: list[Entity] = []
        self.parent: Entity | None = None
        self.enabled = True
        self.destroyed = False
        self.position = (0, 0, 0)
        self.scale = (1, 1)
        for key, value in kwargs.items():
            setattr(self, key, value)
        if "z" in kwargs:
            x, y = self.position[0], self.position[1]
            self.position = (x, y, kwargs["z"])
        if self.parent is not None:
            self.parent.children.append(self)


class Text(Entity):
    """An entity with a text."""

    def __init__(self, **kwargs: Any) -> None:
        """Default to an empty text."""
        self.text = ""
        super().__init__(**kwargs)


class Mesh:
    """Stores its geometry."""

    def __init__(self, vertices: list[Any], triangles: list[Any],
                 colors: list[Any] | None = None) -> None:
        """Keep the vertices, triangles and optional vertex colors."""
        self.vertices = vertices
        self.triangles = triangles
        self.colors = colors


class Texture:
    """Stores the path of the image."""

    def __init__(self, path: Any) -> None:
        """Keep the path."""
        self.path = path


class Ursina:
    """Does nothing: the tests drive the frames themselves."""

    def __init__(self, **kwargs: Any) -> None:
        """Ignore the window options."""
        self.options = kwargs

    def run(self) -> None:
        """Return immediately."""


def destroy(entity: Entity) -> None:
    """Remove an entity and its children from the tree."""
    for child in list(entity.children):
        destroy(child)
    entity.destroyed = True
    if entity.parent is not None and entity in entity.parent.children:
        entity.parent.children.remove(entity)


class _Color:
    """Colors are kept as plain strings."""

    clear = "clear"

    @staticmethod
    def hex(value: str) -> str:
        """Return the hex string unchanged."""
        return value


class _Window:
    """Window state used by the viewer."""

    aspect_ratio = 16 / 9
    color = None
    exit_button = types.SimpleNamespace(visible=True)
    fps_counter = types.SimpleNamespace(enabled=True)


class _Camera:
    """Camera state used by the viewer."""

    orthographic = False
    fov = 40
    ui = Entity()
    children: list[Entity] = []


class _Application:
    """Records the quit request."""

    quit_requested = False

    @staticmethod
    def quit() -> None:
        """Remember that the application was asked to quit."""
        _Application.quit_requested = True


def install() -> types.ModuleType:
    """Make `import ursina` return this stub, with fresh viewer modules."""
    _Camera.children = []
    module = types.ModuleType("ursina")
    for name, value in {
        "Entity": Entity, "Text": Text, "Mesh": Mesh, "Texture": Texture,
        "Ursina": Ursina, "destroy": destroy, "color": _Color(),
        "window": _Window, "camera": _Camera, "application": _Application,
    }.items():
        setattr(module, name, value)
    sys.modules["ursina"] = module
    for name in [n for n in sys.modules
                 if n.startswith(("flyin.src.viewer.",
                                  "flyin.src.viewer3d."))]:
        del sys.modules[name]
    return module
