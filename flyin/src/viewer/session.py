"""State shared by the screens: the catalogs and the current choices."""

from dataclasses import dataclass, field
from typing import Any

from ursina import Texture

from flyin.src.viewer.catalog import DroneSkin, MapEntry


@dataclass
class ViewerSession:
    """The discovered maps and drone skins, and what is selected."""

    maps: list[MapEntry]
    skins: list[DroneSkin]
    map_index: int = 0
    skin_index: int = 0
    _textures: dict[str, Any] = field(default_factory=dict)

    @property
    def entry(self) -> MapEntry | None:
        """The selected map, None when no map exists."""
        return self.maps[self.map_index] if self.maps else None

    @property
    def skin(self) -> DroneSkin:
        """The selected drone sprite."""
        return self.skins[self.skin_index]

    def texture(self, skin: DroneSkin) -> Any:
        """Return the (cached) texture of a sprite."""
        if skin.name not in self._textures:
            self._textures[skin.name] = Texture(skin.path)
        return self._textures[skin.name]

    def move_map(self, delta: int) -> None:
        """Select the next or previous map (wraps around)."""
        if self.maps:
            self.map_index = (self.map_index + delta) % len(self.maps)

    def move_skin(self, delta: int) -> None:
        """Select the next or previous drone sprite (wraps around)."""
        self.skin_index = (self.skin_index + delta) % len(self.skins)
