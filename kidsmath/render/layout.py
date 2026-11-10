"""Pure layout math (no manimlib import) so it can be unit tested."""
from __future__ import annotations

ANCHOR_X = {"left": -3.6, "center": 0.0, "right": 3.6}
OBJECT_Y = 0.7
CAPTION_Y = {"top": 3.1, "bottom": -3.2}
EQUATION_Y = -2.5
OBJECT_SPACING = {"left": 1.05, "right": 1.05, "center": 1.2}
PER_ROW = {"left": 5, "right": 5, "center": 10}
ROW_GAP = 1.25


def grid_positions(n: int, per_row: int, spacing: float, cx: float, cy: float,
                   row_gap: float = ROW_GAP) -> list[tuple[float, float]]:
    """Row-major positions, each row centred on cx, rows centred on cy."""
    rows = -(-n // per_row)
    pts = []
    for k in range(n):
        r, c = divmod(k, per_row)
        in_row = min(per_row, n - r * per_row)
        x = cx + (c - (in_row - 1) / 2) * spacing
        y = cy + ((rows - 1) / 2 - r) * row_gap
        pts.append((x, y))
    return pts


def group_positions(n: int, position: str) -> list[tuple[float, float]]:
    per_row = PER_ROW[position] if n > PER_ROW[position] or position != "center" else n
    per_row = min(PER_ROW[position], max(1, per_row))
    return grid_positions(n, per_row, OBJECT_SPACING[position], ANCHOR_X[position], OBJECT_Y)


def merged_positions(n_total: int) -> list[tuple[float, float]]:
    """Layout of two merged groups as one centred block (first group first)."""
    per_row = 10 if n_total > 10 else n_total
    return grid_positions(n_total, per_row, OBJECT_SPACING["center"], 0.0, OBJECT_Y)
