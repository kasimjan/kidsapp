"""Camera director: turns a lesson into a smooth camera track.

The camera is a pure function of time (keyframes eased with smoothstep), so it
never fights with `play()` calls and always moves continuously.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from ..render import timing
from . import layout3d
from ..spec import (
    Clear, CountItem, CrossOut, LessonSpec, MergeGroups, ShowEquation, ShowObjects,
    ShowSign, ShowText, TitleCard,
)


@dataclass(frozen=True)
class View:
    theta: float          # degrees, rotation around the vertical axis
    phi: float            # degrees, 0 = looking straight down, 90 = side-on
    cx: float = 0.0
    cy: float = 0.0
    cz: float = 0.4
    height: float = 9.0   # visible world height


INTRO = View(-36, 66, 0, 0, 0.3, 11.0)
HERO = View(-24, 58, 0, -0.2, 0.4, 9.4)
MERGED = View(-12, 54, 0, 0.0, 0.4, 9.4)
EQUATION = View(-8, 60, 0, -0.5, 0.3, 9.8)
CELEBRATE = View(-30, 62, 0, 0.0, 0.5, 10.4)

SWAY_DEGREES = 1.2


def _lerp(a: float, b: float, u: float) -> float:
    return a + (b - a) * u


def smoothstep(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def blend(a: View, b: View, u: float) -> View:
    u = smoothstep(u)
    return View(*(_lerp(getattr(a, f), getattr(b, f), u)
                  for f in ("theta", "phi", "cx", "cy", "cz", "height")))


def _count_runs(spec: LessonSpec) -> dict[int, tuple[int, int]]:
    """Map the n-th count_item (in lesson order) to (position in run, run length)."""
    seq: list[bool] = []  # True for count_item, False for any other visual action
    for step in spec.steps:
        for a in step.actions:
            seq.append(isinstance(a, CountItem))
    runs, cur = [], []
    n = 0
    for is_count in seq:
        if is_count:
            cur.append(n)
            n += 1
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return {i: (k, len(r)) for r in runs for k, i in enumerate(r)}


def step_starts(spec: LessonSpec) -> list[float]:
    out, t = [], 0.0
    for s in spec.steps:
        out.append(t)
        t += s.duration or 0.0
    return out


ASPECT = 16 / 9
BASE_HEIGHT = 9.4            # HERO height that the preset views were tuned for


def fit_zoom(spec: LessonSpec) -> float:
    """Scale factor that keeps the widest arrangement inside the frame, as large as possible."""
    half = 2.0
    sizes = {}
    for step in spec.steps:
        for a in step.actions:
            if isinstance(a, ShowObjects):
                sizes[a.group] = a.count
                half = max(half, layout3d.half_extent(layout3d.group_positions(a.count, a.position)))
            elif isinstance(a, MergeGroups):
                total = sizes.get(a.source, 0) + sizes.get(a.target, 0)
                half = max(half, layout3d.half_extent(layout3d.merged_positions(total)))
    needed = 2 * half / ASPECT * 1.25          # frame height that fits the width, with margin
    return max(6.0, min(BASE_HEIGHT, needed)) / BASE_HEIGHT


def is_dense(spec: LessonSpec) -> bool:
    """More than one row of toys on screen at once: look down more so rows do not overlap."""
    total = 0
    for step in spec.steps:
        for a in step.actions:
            if isinstance(a, ShowObjects):
                total += a.count
    return total > layout3d.MERGED_PER_ROW


DENSE_EXTRA_PHI = -12


def build_track(spec: LessonSpec, zoom: float | None = None) -> list[tuple[float, View]]:
    """Keyframes as (arrival time, view). Needs step durations to be set."""
    zoom = fit_zoom(spec) if zoom is None else zoom
    starts = step_starts(spec)
    runs = _count_runs(spec)
    track: list[tuple[float, View]] = [(0.0, INTRO)]
    count_i = 0
    for step, t0 in zip(spec.steps, starts):
        t = t0
        end = t0 + (step.duration or 0.0)
        for a in step.actions:
            dur = timing.action_time(a)
            view, arrive = None, t + 1.0
            if isinstance(a, TitleCard):
                view = INTRO
            elif isinstance(a, ShowObjects):
                view = replace(HERO, cx={"left": -1.0, "right": -0.4, "center": 0.0}[a.position])
            elif isinstance(a, CountItem):
                k, n = runs[count_i]
                count_i += 1
                frac = k / max(1, n - 1)
                view = View(_lerp(-20, 14, frac), 56, 0, -0.2, 0.4, 8.2)
                arrive = max(t + 0.3, end)  # keep drifting through the whole step
            elif isinstance(a, MergeGroups):
                view = MERGED
            elif isinstance(a, CrossOut):
                view = View(-18, 58, 0, 0.0, 0.4, 9.0)
            elif isinstance(a, ShowEquation):
                view = EQUATION
            elif isinstance(a, ShowSign):
                view = View(-4, 62, 0, 0.0, 0.4, 9.6)
            elif isinstance(a, ShowText) and a.color == "green":
                view = CELEBRATE
            elif isinstance(a, Clear):
                view = HERO
            if view is not None:
                last_t = track[-1][0]
                track.append((max(arrive, last_t + 0.05), view))
            t += dur
    dphi = DENSE_EXTRA_PHI if is_dense(spec) else 0
    track = [(t, replace(v, height=v.height * zoom, phi=v.phi + dphi)) for t, v in track]
    # Gentle pull-back at the very end.
    final_t = starts[-1] + (spec.steps[-1].duration or 0.0) + timing.FINAL_HOLD
    track.append((max(final_t, track[-1][0] + 0.05), replace(track[-1][1], height=track[-1][1].height * 1.05)))
    return track


def view_at(track: list[tuple[float, View]], t: float) -> View:
    if t <= track[0][0]:
        return track[0][1]
    for (t0, v0), (t1, v1) in zip(track, track[1:]):
        if t <= t1:
            return blend(v0, v1, (t - t0) / (t1 - t0))
    return track[-1][1]


def sway(t: float) -> float:
    """Tiny continuous orbit so the scene never feels frozen."""
    return SWAY_DEGREES * math.sin(0.7 * t)
