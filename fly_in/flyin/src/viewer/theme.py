"""Colors and sizes shared by every widget of the viewer."""

INK = "#2b2f3b"
INK_SOFT = "#3d4353"
PANEL = "#262a35"
TEXT = "#fff4df"
MUTED = "#b9a98d"
ACCENT = "#35d0e6"
WARN = "#ff6b5e"
SAND = "#fdbf66"
NEUTRAL_RIM = "#f6e7c8"

ZONE_FILL: dict[str, str] = {
    "normal": "#52b8f2",
    "priority": "#ffb02e",
    "restricted": "#9aa0b4",
    "blocked": "#ef5350",
    "start": "#31c48d",
    "end": "#6c5ce7",
}

SHADOW = "#d49445"
FLAG_POLE = "#f1ece1"
ROAD = "#3a4050"
ROAD_DEAD = "#b79a72"
ROAD_OUTLINE = "#252936"

NAMED_COLORS: dict[str, str] = {
    "red": "#e53935",
    "green": "#43a047",
    "blue": "#1e88e5",
    "yellow": "#fdd835",
    "orange": "#fb8c00",
    "purple": "#8e24aa",
    "black": "#212121",
    "brown": "#6d4c41",
    "gray": "#9e9e9e",
    "grey": "#9e9e9e",
    "cyan": "#00bcd4",
    "gold": "#ffc107",
    "maroon": "#800000",
    "darkred": "#8b0000",
    "crimson": "#dc143c",
    "violet": "#9c27b0",
    "magenta": "#e91e8c",
    "lime": "#aeea00",
    "pink": "#f48fb1",
    "white": "#fafafa",
    "teal": "#009688",
    "navy": "#1a237e",
    "silver": "#c0c0c0",
}

# Z layers of camera.ui: larger z is further from the viewer.
Z_BACKGROUND = 5.0
Z_ROAD = 1.0
Z_ZONE = 0.5
Z_DRONE = 0.0
Z_LABEL = -0.2


def map_color(word: str) -> str | None:
    """Return the hex color of a map color word, None if unknown."""
    return NAMED_COLORS.get(word.strip().lower())


def lighten(value: str, amount: float) -> str:
    """Mix a '#rrggbb' color with white (amount 0 to 1)."""
    channels = [int(value[i:i + 2], 16) for i in (1, 3, 5)]
    mixed = [round(c + (255 - c) * amount) for c in channels]
    return "#{:02x}{:02x}{:02x}".format(*mixed)
