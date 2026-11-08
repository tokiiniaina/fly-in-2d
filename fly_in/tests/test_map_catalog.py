"""Tests for automatic valid-map discovery."""

from pathlib import Path

from flyin.src.map_catalog import MapCatalog


def _write_valid_map(directory: Path, name: str) -> None:
    """Write a minimal valid map with the given file name."""
    content = "\n".join(
        (
            "nb_drones: 1",
            "start_hub: start 0 0",
            "end_hub: end 1 0",
            "connection: start-end",
        )
    )
    (directory / name).write_text(content, encoding="utf-8")


def test_valid_map_uses_name_without_extension(tmp_path: Path) -> None:
    """A valid text map is returned with its stem as name."""
    _write_valid_map(tmp_path, "new_maps.txt")

    entries = MapCatalog(tmp_path).entries()

    assert [(entry.name, entry.path.name) for entry in entries] == [
        ("new_maps", "new_maps.txt")
    ]


def test_invalid_map_is_ignored(tmp_path: Path) -> None:
    """An invalid text map is not returned."""
    (tmp_path / "invalid.txt").write_text("not a map", encoding="utf-8")

    assert MapCatalog(tmp_path).entries() == []


def test_non_text_maps_are_ignored(tmp_path: Path) -> None:
    """Markdown and JSON files are not scanned."""
    (tmp_path / "notes.md").write_text("notes", encoding="utf-8")
    (tmp_path / "metadata.json").write_text("{}", encoding="utf-8")

    assert MapCatalog(tmp_path).entries() == []


def test_absent_directory_is_empty(tmp_path: Path) -> None:
    """A missing map directory returns no entries."""
    assert MapCatalog(tmp_path / "missing").entries() == []


def test_entries_are_sorted_by_name(tmp_path: Path) -> None:
    """Valid map entries are sorted alphabetically by their names."""
    _write_valid_map(tmp_path, "zulu.txt")
    _write_valid_map(tmp_path, "alpha.txt")

    assert [entry.name for entry in MapCatalog(tmp_path).entries()] == [
        "alpha",
        "zulu",
    ]
