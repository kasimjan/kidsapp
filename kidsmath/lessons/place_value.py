"""Place value template (tens and ones; hundreds from Grade 2)."""
from __future__ import annotations

import random

from ..spec import Facts, LessonSpec, ShowBlocks, ShowEquation, ShowText, Step, TitleCard
from ..validate import difficulty_limit
from .common import finish, need_numbers, split_tens_ones

_LOW = {0: 11, 1: 11, 2: 101}


def place_value(grade: int, difficulty: str, numbers: list[int] | None,
                rng: random.Random, **_) -> LessonSpec:
    low = _LOW[grade]
    cap = max(difficulty_limit("place_value", grade, difficulty), low + 5)

    n, = need_numbers(numbers, 1, rng, lambda r: [r.randint(low, cap)])
    if n < 10:
        raise ValueError("place value lessons start at 10")
    h, t, o = split_tens_ones(n)
    steps = [
        Step(narration=f"Let's take apart the number {n}!", actions=[TitleCard(text=f"{n}")]),
        Step(narration=f"Here is {n} made with blocks.",
             actions=[ShowBlocks(group="a", hundreds=h, tens=t, ones=o)]),
    ]
    if h:
        steps.append(Step(narration=f"The flats are hundreds. There are {h} hundreds.",
                          actions=[ShowText(text=f"{h} hundreds = {h * 100}", color="orange")]))
    steps.append(Step(narration=f"The long rods are tens. There {'is' if t == 1 else 'are'} {t} {'ten' if t == 1 else 'tens'}.",
                      actions=[ShowText(text=f"{t} tens = {t * 10}", color="purple")]))
    steps.append(Step(narration=f"The little cubes are ones. There {'is' if o == 1 else 'are'} {o} {'one' if o == 1 else 'ones'}.",
                     actions=[ShowText(text=f"{o} ones = {o}", color="green")]))
    if h:
        steps.append(Step(narration=f"{h * 100} plus {t * 10} is {h * 100 + t * 10}.",
                          actions=[ShowEquation(text=f"{h * 100} + {t * 10} = {h * 100 + t * 10}")]))
        steps.append(Step(narration=f"{h * 100 + t * 10} plus {o} is {n}.",
                          actions=[ShowEquation(text=f"{h * 100 + t * 10} + {o} = {n}")]))
    else:
        steps.append(Step(narration=f"{t * 10} plus {o} equals {n}!",
                          actions=[ShowEquation(text=f"{t * 10} + {o} = {n}")]))
    steps.append(Step(narration=f"Great job! {n} is {t} tens and {o} ones." if not h
                      else f"Great job! {n} is {h} hundreds, {t} tens and {o} ones.",
                      actions=[ShowText(text=f"{n}", region="top", color="green")]))
    return finish(LessonSpec(topic="place_value", grade=grade, difficulty=difficulty,
                             title=f"Place value of {n}",
                             facts=Facts(kind="place_value", operands=[n], result=n), steps=steps))
