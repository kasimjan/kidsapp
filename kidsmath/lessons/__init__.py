"""Lesson templates and the public `generate_lesson` entry point."""
from __future__ import annotations

import random

from .. import limits
from ..spec import LessonSpec
from ..validate import validate_spec
from .arithmetic import addition, subtraction, word_problem
from .counting import comparison, counting
from .geometry import shapes
from .place_value import place_value

TEMPLATES = {
    "addition": addition,
    "subtraction": subtraction,
    "counting": counting,
    "comparison": comparison,
    "shapes": shapes,
    "place_value": place_value,
    "word_problem": word_problem,
}


def generate_lesson(topic: str, grade: int = 0, difficulty: str = "easy",
                    numbers: list[int] | None = None, seed: int | None = None,
                    shape: str | None = None, operation: str | None = None,
                    mascot: str = "milo", style: str = "2d") -> LessonSpec:
    """Build a validated LessonSpec from a topic, grade, difficulty and numbers."""
    topic = topic.strip().lower().replace(" ", "_").replace("-", "_")
    if topic not in TEMPLATES:
        raise ValueError(f"unknown topic '{topic}'; choose from {sorted(TEMPLATES)}")
    if grade not in limits.GRADES:
        raise ValueError("grade must be 0 (Kindergarten), 1 or 2")
    if difficulty not in limits.DIFFICULTIES:
        raise ValueError(f"difficulty must be one of {list(limits.DIFFICULTIES)}")
    if style not in ("2d", "3d"):
        raise ValueError("style must be '2d' or '3d'")
    spec = TEMPLATES[topic](grade, difficulty, numbers, random.Random(seed),
                            shape=shape, operation=operation, solid=(style == "3d"))
    if mascot == "milo":
        spec.mascot = "milo"
        first = spec.steps[0]
        first.narration = f"Hi, I'm Milo the Mouse! {first.narration}"
    elif mascot == "none":
        spec.mascot = "none"
    else:
        raise ValueError("mascot must be 'milo' or 'none'")
    return validate_spec(spec)
