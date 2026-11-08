"""Discovery of the maps and of the drone sprites used by the viewer."""

import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from flyin.src.map_catalog import MapCatalog as FileMapCatalog
from flyin.src.map_data import MapData
from flyin.src.parser_function import MapParser
from flyin.src.viewer.paths import DRONES_DIR, MAPS_DIR

DIFFICULTIES: tuple[str, ...] = ("EASY", "MEDIUM", "HARD", "CHALLENGER")
SKIN_ORDER: tuple[str, ...] = ("SPHERE", "SPIDER", "ROVER", "CUBE")

_HEADER = re.compile(r"#\s*(easy|medium|hard|challenger)\b", re.IGNORECASE)


@dataclass(frozen=True)
class MapEntry:
    """A map file found on disk, with its parsing result."""

    name: str
    path: Path
    difficulty: str
    data: MapData | None = None
    error: str | None = None

    @property
    def label(self) -> str:
        """Return the map name used by the viewers."""
        return self.name

    @property
    def valid(self) -> bool:
        """Tell whether the map was parsed without error."""
        return self.data is not None

    def summary(self) -> str:
        """Return a one-line description, or the parsing error."""
        if self.data is None:
            return f"INVALID: {self.error}"
        parts: list[str] = []
        if self.difficulty is not None:
            parts.append(self.difficulty)
        parts.append(f"{self.data.nb_drones} DRONES")
        parts.append(f"{len(self.data.zones)} ZONES")
        return " / ".join(parts)


class MapCatalog:
    """Find every map file under a directory and parse it."""

    def __init__(self, root: Path | None = None) -> None:
        """Remember the directory to scan (the project maps by default)."""
        self._root = MAPS_DIR if root is None else root

    def discover(self) -> list[MapEntry]:
        """Return valid maps sorted by their names."""
        catalog = FileMapCatalog(self._root)
        return [self.load(entry.path) for entry in catalog.entries()]

    def load(self, path: Path) -> MapEntry:
        """Parse one map file; a parsing failure is stored, not raised."""
        difficulty = self._difficulty(path) or "Custom"
        try:
            data = MapParser().parse(str(path))
        except (OSError, ValueError) as error:
            return MapEntry(path.stem, path, difficulty, error=str(error))
        return MapEntry(path.stem, path, difficulty, data=data)

    def _difficulty(self, path: Path) -> str | None:
        """Read the difficulty from a parent folder or the header."""
        try:
            folders = path.relative_to(self._root).parts[:-1]
        except ValueError:
            folders = ()
        for folder in folders:
            if folder.upper() in DIFFICULTIES:
                return folder.upper()
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as file:
                head = [file.readline() for _ in range(6)]
        except OSError:
            return None
        for line in head:
            match = _HEADER.match(line.strip())
            if match is not None:
                return match.group(1).upper()
        return None


@dataclass(frozen=True)
class DroneSkin:
    """One selectable drone sprite."""

    name: str
    path: Path
    aspect: float


class DroneCatalog:
    """Find the drone sprites (assets/drones/drone_*.png)."""

    def __init__(self, root: Path | None = None) -> None:
        """Remember the sprite directory."""
        self._root = DRONES_DIR if root is None else root

    def discover(self) -> list[DroneSkin]:
        """Return the sprites in a stable order.

        Raises:
            FileNotFoundError: If no sprite exists.
        """
        skins: list[DroneSkin] = []
        for path in sorted(self._root.glob("drone_*.png")):
            with Image.open(path) as image:
                width, height = image.size
            name = path.stem[len("drone_"):].upper()
            skins.append(DroneSkin(name, path, width / height))
        if not skins:
            raise FileNotFoundError(
                f"no drone sprite found in '{self._root}'")
        skins.sort(key=self._sort_key)
        return skins

    @staticmethod
    def _sort_key(skin: DroneSkin) -> tuple[int, str]:
        """Known sprites first, in their canonical order."""
        rank = (SKIN_ORDER.index(skin.name)
                if skin.name in SKIN_ORDER else len(SKIN_ORDER))
        return rank, skin.name
