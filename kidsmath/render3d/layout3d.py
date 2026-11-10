"""Ground-plane layout for 3D toys (pure math, unit tested).

Groups stand on the ground in rows; a 'left' or 'right' group is centred on
an anchor that depends on its own size so small groups stay close together
and big ones never collide with the middle.
"""
from __future__ import annotations

SPACING = 1.12
ROW_GAP = 1.7
PER_ROW = 5
MERGED_PER_ROW = 10
GAP_TO_CENTER = 0.7


def _rows(n: int, per_row: int, cx: float) -> list[tuple[float, float]]:
    rows = -(-n // per_row)
    pts = []
    for k in range(n):
        r, c = divmod(k, per_row)
        in_row = min(per_row, n - r * per_row)
        pts.append((cx + (c - (in_row - 1) / 2) * SPACING,
                    ((rows - 1) / 2 - r) * ROW_GAP))
    return pts


def group_positions(n: int, position: str) -> list[tuple[float, float]]:
    if position == "center":
        return _rows(n, MERGED_PER_ROW if n > MERGED_PER_ROW else n, 0.0)
    half_width = min(n, PER_ROW) * SPACING / 2
    cx = (half_width + GAP_TO_CENTER) * (-1 if position == "left" else 1)
    return _rows(n, PER_ROW, cx)


def merged_positions(n_total: int) -> list[tuple[float, float]]:
    return _rows(n_total, MERGED_PER_ROW if n_total > MERGED_PER_ROW else n_total, 0.0)


def half_extent(points: list[tuple[float, float]]) -> float:
    return max((abs(x) for x, _ in points), default=0.0) + 0.6
