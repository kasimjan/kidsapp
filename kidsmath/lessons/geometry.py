"""Shapes template."""
from __future__ import annotations

import random

from .. import limits
from ..spec import Facts, LessonSpec, ShowShape, ShowText, Step, TitleCard
from .common import finish, number_word

_COLORS = ("blue", "orange", "green", "purple", "pink", "teal")


def shapes(grade: int, difficulty: str, numbers: list[int] | None,
           rng: random.Random, shape: str | None = None, **_) -> LessonSpec:
    allowed = limits.SHAPES_BY_GRADE[grade]
    if shape is not None and shape not in allowed:
        raise ValueError(f"shape '{shape}' is not taught at grade {grade}; choose from {list(allowed)}")
    shape = shape or rng.choice(allowed)
    sides, corners = limits.SHAPE_FACTS[shape]
    color = rng.choice(_COLORS)
    article = "an" if shape[0] in "aeiou" else "a"
    steps = [
        Step(narration=f"Let's learn about shapes! Today we meet {article} {shape}.",
             actions=[TitleCard(text=shape.title())]),
        Step(narration=f"This is {article} {shape}.",
             actions=[ShowShape(name=shape, color=color)]),
    ]
    if shape == "circle":
        steps += [
            Step(narration="A circle is round like a ball. It has no sides and no corners.",
                 actions=[ShowText(text="No sides. No corners.", region="top", color="orange")]),
        ]
    else:
        steps += [
            Step(narration=f"Look at the sides. A {shape} has {number_word(sides)} sides.",
                 actions=[ShowShape(name=shape, color=color, highlight="sides"),
                          ShowText(text=f"{sides} sides", region="top", color="orange")]),
            Step(narration=f"Now look at the corners. A {shape} has {number_word(corners)} corners.",
                 actions=[ShowShape(name=shape, color=color, highlight="corners"),
                          ShowText(text=f"{corners} corners", region="top", color="purple")]),
        ]
        if shape == "rectangle":
            steps.append(Step(narration="A rectangle has two long sides and two short sides.", actions=[]))
        if shape == "square":
            steps.append(Step(narration="All four sides of a square are the same length.", actions=[]))
    steps.append(Step(narration=f"Great job! Now you know the {shape}!",
                      actions=[ShowText(text=f"I know the {shape}!", region="top", color="green")]))
    return finish(LessonSpec(
        topic="shapes", grade=grade, difficulty=difficulty, title=f"The {shape.title()}",
        facts=Facts(kind="shapes", shape=shape, operands=[sides, corners]), steps=steps))
