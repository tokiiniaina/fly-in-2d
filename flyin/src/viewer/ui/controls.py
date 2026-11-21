"""Textual controls: buttons and '< value >' selectors."""

from collections.abc import Callable
from typing import Any

from ursina import Entity, Mesh, color

from flyin.src.viewer import theme
from flyin.src.viewer.geometry import chevron
from flyin.src.viewer.shapes import clean, label, tint


class _Clickable:
    """Invisible click area with hover, active and disabled looks."""

    def __init__(self, parent: Any, x: float, y: float, width: float,
                 height: float, on_click: Callable[[], None],
                 fill: str) -> None:
        """Create the click area; subclasses draw the visible part."""
        self._on_click = on_click
        self._base = fill
        self._active = False
        self._enabled = True
        self._hover = False
        self._hit = Entity(parent=parent, model="quad", collider="box",
                           color=color.clear, position=(x, y, -0.1),
                           scale=(width, height))
        self._hit.on_click = self._clicked
        self._hit.on_mouse_enter = self._enter
        self._hit.on_mouse_exit = self._exit

    def set_active(self, active: bool) -> None:
        """Highlight the control (for example the selected speed)."""
        self._active = active
        self._paint()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the control (a disabled one is dimmed)."""
        self._enabled = enabled
        self._paint()

    def click(self) -> None:
        """Trigger the action, as a mouse click would."""
        if self._enabled:
            self._on_click()

    def _clicked(self) -> None:
        """Mouse click handler."""
        self.click()

    def _enter(self) -> None:
        """Mouse enters the click area."""
        self._hover = True
        self._paint()

    def _exit(self) -> None:
        """Mouse leaves the click area."""
        self._hover = False
        self._paint()

    def _paint(self) -> None:
        """Apply the color matching the current state."""
        if not self._enabled:
            self._set_color(theme.MUTED)
        elif self._hover or self._active:
            self._set_color(theme.ACCENT)
        else:
            self._set_color(self._base)

    def _set_color(self, value: str) -> None:
        """Color the visible part."""
        raise NotImplementedError


class TextButton(_Clickable):
    """A clickable text. It only changes color, it has no background."""

    def __init__(self, parent: Any, text: str, x: float, y: float,
                 width: float, height: float, on_click: Callable[[], None],
                 size: float = 1.0, fill: str = theme.TEXT) -> None:
        """Create the text and its invisible click area."""
        super().__init__(parent, x, y, width, height, on_click, fill)
        self.text = label(parent, text, x, y, size, fill)

    def set_text(self, text: str) -> None:
        """Change the displayed text."""
        self.text.text = clean(text)

    def _set_color(self, value: str) -> None:
        """Color the text."""
        self.text.color = tint(value)


class ArrowButton(_Clickable):
    """A drawn '<' or '>' (Ursina reads a text '<' as a tag)."""

    def __init__(self, parent: Any, x: float, y: float, direction: int,
                 on_click: Callable[[], None], size: float = 0.022,
                 fill: str = theme.TEXT) -> None:
        """Draw the chevron and its click area."""
        super().__init__(parent, x, y, 0.07, 0.07, on_click, fill)
        vertices, triangles = chevron(direction, size, size * 0.38)
        self._shape = Entity(
            parent=parent, model=Mesh(vertices=vertices,
                                      triangles=triangles),
            color=tint(fill), double_sided=True,
            position=(x, y, theme.Z_LABEL))

    def _set_color(self, value: str) -> None:
        """Color the chevron."""
        self._shape.color = tint(value)


class Selector:
    """A '< VALUE >' row used to browse a list of choices."""

    def __init__(self, parent: Any, x: float, y: float, width: float,
                 on_previous: Callable[[], None],
                 on_next: Callable[[], None], size: float = 1.2) -> None:
        """Create the two arrows and the value text."""
        half = width / 2
        self.previous = ArrowButton(parent, x - half, y, -1, on_previous)
        self.following = ArrowButton(parent, x + half, y, 1, on_next)
        self.value = label(parent, "", x, y, size, theme.TEXT)

    def set_value(self, text: str) -> None:
        """Change the displayed value."""
        self.value.text = clean(text)
