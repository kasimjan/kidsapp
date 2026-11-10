"""Animation timing, shared by the pipeline (for audio sync) and the scene.

All durations are whole numbers of frames so the video length matches the
narration track exactly.
"""
from __future__ import annotations

import math

from ..spec import (
    Clear, CountItem, CrossOut, LessonSpec, MergeGroups, ShowBlocks, ShowEquation,
    ShowObjects, ShowShape, ShowSign, ShowText, Step, TitleCard,
)

FPS = 30
STEP_PAD = 0.35      # silence after each narration line
FINAL_HOLD = 1.0     # extra time on the last step


def to_frames(seconds: float) -> int:
    return max(1, math.ceil(seconds * FPS - 1e-9))


def quantize(seconds: float) -> float:
    return to_frames(seconds) / FPS


def action_time(a) -> float:
    if isinstance(a, TitleCard):
        raw = 1.2
    elif isinstance(a, ShowText):
        raw = 0.6
    elif isinstance(a, ShowObjects):
        raw = min(2.0, 0.5 + 0.12 * a.count)
    elif isinstance(a, CountItem):
        raw = 0.4
    elif isinstance(a, MergeGroups):
        raw = 1.0
    elif isinstance(a, CrossOut):
        raw = min(1.6, 0.4 + 0.2 * a.count)
    elif isinstance(a, ShowEquation):
        raw = 1.0
    elif isinstance(a, ShowSign):
        raw = 0.6
    elif isinstance(a, ShowShape):
        raw = 1.2 if a.highlight == "none" else 0.9
    elif isinstance(a, ShowBlocks):
        raw = 1.0
    elif isinstance(a, Clear):
        raw = 0.6
    else:  # pragma: no cover - the spec union is closed
        raw = 0.5
    return quantize(raw)


def animation_time(step: Step) -> float:
    return sum(action_time(a) for a in step.actions)


def step_duration(step: Step, audio_seconds: float) -> float:
    return quantize(max(audio_seconds + STEP_PAD, animation_time(step) + 0.1))


def total_duration(spec: LessonSpec) -> float:
    total = sum(s.duration or 0 for s in spec.steps)
    return total


def estimate_audio_seconds(text: str, words_per_second: float = 2.3) -> float:
    """Rough speech length, for previews rendered without a TTS backend."""
    return max(0.4, len(text.split()) / words_per_second)


def with_estimated_durations(spec: LessonSpec) -> LessonSpec:
    steps = [s.model_copy(update={"duration": step_duration(s, estimate_audio_seconds(s.narration))})
             for s in spec.steps]
    return spec.model_copy(update={"steps": steps})
