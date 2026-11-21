"""Colors of the 3D scene, taken from the map files (pure Python)."""

import colorsys
import zlib

from flyin.src.viewer.theme import NAMED_COLORS, lighten

RAINBOW: tuple[str, ...] = ("#ff5b5b", "#ff9f43", "#ffd93d", "#5fd068",
                            "#4dabf7", "#9775fa")

EXTRA_COLORS: dict[str, str] = {
    "darkgreen": "#2e7d32",
    "lightblue": "#81d4fa",
    "turquoise": "#26c6da",
    "beige": "#e8d9b5",
    "indigo": "#5c6bc0",
    "coral": "#ff7f6e",
    "salmon": "#fa8072",
    "olive": "#9e9d24",
}

DEFAULT_PAD: dict[str, str] = {
    "start": "#6fd36b",
    "end": "#ef6f7e",
    "normal": "#8fc7f0",
    "priority": "#ffc54a",
    "restricted": "#b79be8",
    "blocked": "#8a8794",
}

GROUND_A = "#40457a"
GROUND_B = "#383c6e"
RIM_GLOW = "#5fd6e6"
SHADOW_PLATE = "#262a4d"
STONE = "#5b5478"
STONE_DARK = "#403b58"
PLATE = "#cdd6f0"
PLATE_CLOSED = "#80829a"
ROCK = "#7d7896"
CRYSTALS = ("#5ee6f2", "#b58cff", "#ff8fd0")
SPECKS = ("#8fe9ff", "#ffffff", "#d9b8ff")

NAMED: dict[str, str] = {**NAMED_COLORS, **EXTRA_COLORS}


def hue_color(word: str) -> str:
    """Deterministic pastel color for a color word we do not know."""
    hue = (zlib.crc32(word.encode()) % 360) / 360.0
    red, green, blue = colorsys.hsv_to_rgb(hue, 0.55, 0.92)
    return "#{:02x}{:02x}{:02x}".format(
        round(red * 255), round(green * 255), round(blue * 255))


def color_stops(word: str | None) -> list[str] | None:
    """Colors written in the map: None if unset, several for rainbow.

    A known word gives its color; an unknown word (a custom color) gets
    its own stable color, so it is never replaced by a default.
    """
    if word is None:
        return None
    key = word.strip().lower()
    if key in ("", "none"):
        return None
    if key == "rainbow":
        return list(RAINBOW)
    return [NAMED.get(key) or hue_color(key)]


def hex_to_rgb(value: str) -> tuple[float, float, float]:
    """Convert '#rrggbb' to floats in [0, 1]."""
    return (int(value[1:3], 16) / 255, int(value[3:5], 16) / 255,
            int(value[5:7], 16) / 255)


def rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    """Convert floats in [0, 1] to '#rrggbb'."""
    parts = [max(0, min(255, round(c * 255))) for c in rgb]
    return "#{:02x}{:02x}{:02x}".format(*parts)


def mix(first: str, second: str, amount: float) -> str:
    """Blend two colors (amount 0 gives the first, 1 the second)."""
    a, b = hex_to_rgb(first), hex_to_rgb(second)
    return rgb_to_hex((a[0] + (b[0] - a[0]) * amount,
                       a[1] + (b[1] - a[1]) * amount,
                       a[2] + (b[2] - a[2]) * amount))


def darken(value: str, amount: float) -> str:
    """Mix a color with black (amount 0 to 1)."""
    return mix(value, "#000000", amount)


def brighten(value: str, amount: float) -> str:
    """Mix a color with white (amount 0 to 1)."""
    return lighten(value, amount)


def harmonize(base: str, map_colors: list[str], amount: float = 0.1
              ) -> str:
    """Tint a terrain color slightly toward the colors of the map.

    The map colors themselves are never changed: only the grass is.
    """
    if not map_colors:
        return base
    count = len(map_colors)
    avg = tuple(sum(hex_to_rgb(c)[i] for c in map_colors) / count
                for i in range(3))
    mean = rgb_to_hex((avg[0], avg[1], avg[2]))
    return mix(base, mean, amount)
