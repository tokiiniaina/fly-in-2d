"""Locations of the project resources used by the viewer."""

from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[3]
ASSETS_DIR: Path = REPO_ROOT / "assets"
MAPS_DIR: Path = REPO_ROOT / "maps"
BACKGROUND_PATH: Path = ASSETS_DIR / "background" / "background.png"
DRONES_DIR: Path = ASSETS_DIR / "drones"
