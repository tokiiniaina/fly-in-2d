"""Read useful lines from a map file."""

from pathlib import Path


class LineReader:
    """Read non-empty, comment-free lines from a map file."""

    def read(self, file_path: str) -> list[tuple[int, str]]:
        """Read lines with their original line numbers."""
        lines: list[tuple[int, str]] = []
        with Path(file_path).open("r", encoding="utf-8") as file:
            for line_number, raw in enumerate(file, start=1):
                line = raw.split("#", 1)[0].strip()
                if line:
                    lines.append((line_number, line))
        return lines
