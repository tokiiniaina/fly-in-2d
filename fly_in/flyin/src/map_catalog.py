"""List the valid map files of a directory."""

from dataclasses import dataclass
from pathlib import Path

from flyin.src.parser_function import MapParser


@dataclass(frozen=True)
class MapEntry:
    """A valid map file: its display name and its path."""

    name: str
    path: Path


class MapCatalog:
    """Scan a directory and keep only the maps the parser accepts."""

    def __init__(self, directory: Path) -> None:
        """Remember the directory to scan."""
        self._directory = directory
        self._parser = MapParser()

    def entries(self) -> list[MapEntry]:
        """Return the valid maps, sorted by name (without '.txt')."""
        if not self._directory.is_dir():
            return []
        found: list[MapEntry] = []
        for path in sorted(self._directory.rglob("*.txt")):
            if self._is_valid(path):
                found.append(MapEntry(path.stem, path))
        return sorted(found, key=lambda entry: entry.name)

    def _is_valid(self, path: Path) -> bool:
        """Tell whether the parser accepts the file."""
        try:
            self._parser.parse(str(path))
        except (OSError, ValueError):
            return False
        return True
