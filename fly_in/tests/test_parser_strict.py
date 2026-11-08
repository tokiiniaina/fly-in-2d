"""Tests of the strict parsing rules."""

from pathlib import Path

import pytest

from flyin.src.parser_function import MapParser


def write_map(tmp_path: Path, text: str) -> str:
    """Write a map file and return its path."""
    path = tmp_path / "map.txt"
    path.write_text(text, encoding="utf-8")
    return str(path)


@pytest.mark.parametrize("value", ["1_0", "+5", "5.0", "abc", "٥"])
def test_nb_drones_must_be_plain_digits(tmp_path: Path, value: str) -> None:
    """Python-only integer forms are refused for nb_drones."""
    text = f"nb_drones: {value}\nstart_hub: s 0 0\nend_hub: e 1 0\n"
    with pytest.raises(ValueError, match="must be an integer"):
        MapParser().parse(write_map(tmp_path, text))


@pytest.mark.parametrize("value", ["0", "-5"])
def test_nb_drones_must_be_positive(tmp_path: Path, value: str) -> None:
    """Zero and negative drone counts are refused."""
    text = f"nb_drones: {value}\nstart_hub: s 0 0\nend_hub: e 1 0\n"
    with pytest.raises(ValueError, match="must be positive"):
        MapParser().parse(write_map(tmp_path, text))


def test_space_before_colon_is_refused(tmp_path: Path) -> None:
    """'nb_drones : 5' is refused with the right message."""
    text = "nb_drones : 5\nstart_hub: s 0 0\nend_hub: e 1 0\n"
    with pytest.raises(ValueError, match="expected 'nb_drones"):
        MapParser().parse(write_map(tmp_path, text))


@pytest.mark.parametrize("coord", ["1_0", "+5", "1.5", "x"])
def test_coordinates_must_be_integers(tmp_path: Path, coord: str) -> None:
    """Only optional minus and ASCII digits are valid coordinates."""
    text = f"nb_drones: 1\nstart_hub: s {coord} 0\nend_hub: e 1 0\n"
    with pytest.raises(ValueError, match="coordinates must be integers"):
        MapParser().parse(write_map(tmp_path, text))


def test_negative_coordinates_are_accepted(tmp_path: Path) -> None:
    """Negative integers stay valid."""
    text = "nb_drones: 1\nstart_hub: s -1 -2\nend_hub: e 1 0\n"
    data = MapParser().parse(write_map(tmp_path, text))
    assert (data.zones["s"].x, data.zones["s"].y) == (-1, -2)


def test_brackets_are_allowed_in_zone_names(tmp_path: Path) -> None:
    """A zone name with brackets can be connected."""
    text = (
        "nb_drones: 1\nstart_hub: s 0 0\nhub: a[1] 1 0\n"
        "end_hub: e 2 0\n"
        "connection: s-a[1]\n"
        "connection: a[1]-e [max_link_capacity=2]\n"
    )
    data = MapParser().parse(write_map(tmp_path, text))
    assert "a[1]" in data.zones
    assert data.connections[0].zone2 == "a[1]"
    assert data.connections[1].max_link_capacity == 2
