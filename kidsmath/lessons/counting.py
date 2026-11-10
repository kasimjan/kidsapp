"""Counting and number-comparison templates."""
from __future__ import annotations

import random

from .. import limits
from ..spec import (
    CountItem, Facts, LessonSpec, ShowBlocks, ShowObjects, ShowSign, ShowText,
    Step, TitleCard,
)
from ..validate import difficulty_limit
from .looks import noun
from .common import count_phrase, finish, need_numbers, number_word, split_tens_ones

_LOOKS = (("star", "yellow"), ("heart", "pink"), ("circle", "blue"),
          ("square", "green"), ("triangle", "orange"))
_SOLID_LOOKS = (("circle", "red"), ("square", "blue"), ("triangle", "green"),
                ("circle", "orange"), ("square", "purple"))


def counting(grade: int, difficulty: str, numbers: list[int] | None,
             rng: random.Random, solid: bool = False, **_) -> LessonSpec:
    cap = difficulty_limit("counting", grade, difficulty)
    n, = need_numbers(numbers, 1, rng, lambda r: [r.randint(3, max(3, cap))])
    shape, color = rng.choice(_SOLID_LOOKS if solid else _LOOKS)
    what = noun(shape, solid)
    steps = [
        Step(narration=f"Let's count to {n}!", actions=[TitleCard(text=f"Count to {n}")]),
        Step(narration=f"Here are {count_phrase(n, color + ' ' + what)}.",
             actions=[ShowObjects(group="a", count=n, shape=shape, color=color)]),
        Step(narration="Let's count them together.", actions=[]),
    ]
    steps += [Step(narration=number_word(i), actions=[CountItem(group="a", index=i)])
              for i in range(1, n + 1)]
    steps.append(Step(narration=f"There are {n}! Great counting!",
                      actions=[ShowText(text=f"{n}", region="top", color="green")]))
    return finish(LessonSpec(topic="counting", grade=grade, difficulty=difficulty,
                             title=f"Counting to {n}", facts=Facts(kind="counting", operands=[n]),
                             steps=steps))


def _compare_phrase(a: int, b: int) -> tuple[str, str]:
    if a > b:
        return ">", f"{a} is greater than {b}."
    if a < b:
        return "<", f"{a} is less than {b}."
    return "=", f"{a} is equal to {b}."


def comparison(grade: int, difficulty: str, numbers: list[int] | None,
               rng: random.Random, solid: bool = False, **_) -> LessonSpec:
    cap = difficulty_limit("comparison", grade, difficulty)

    def make(r):
        a = r.randint(1, cap)
        b = r.randint(1, cap)
        while b == a:
            b = r.randint(1, cap)
        return [a, b]

    a, b = need_numbers(numbers, 2, rng, make)
    sign, sentence = _compare_phrase(a, b)
    if max(a, b) <= limits.MAX_OBJECTS_ON_SCREEN:
        steps = [
            Step(narration=f"Which number is bigger, {a} or {b}?",
                 actions=[TitleCard(text=f"{a} or {b}?")]),
            Step(narration=f"Here are {count_phrase(a, 'red ' + noun('circle', solid))}.",
                 actions=[ShowObjects(group="a", count=a, shape="circle", color="red", position="left")]),
            Step(narration=f"And here are {count_phrase(b, 'yellow ' + noun('circle', solid))}.",
                 actions=[ShowObjects(group="b", count=b, shape="circle", color="yellow", position="right")]),
            Step(narration=("Let's look at both groups." if a != b else "Both groups look the same."), actions=[]),
        ]
    else:
        ha, ta, oa = split_tens_ones(a)
        hb, tb, ob = split_tens_ones(b)
        steps = [
            Step(narration=f"Which number is bigger, {a} or {b}?",
                 actions=[TitleCard(text=f"{a} or {b}?")]),
            Step(narration=f"Here is {a}.",
                 actions=[ShowBlocks(group="a", hundreds=ha, tens=ta, ones=oa, position="left")]),
            Step(narration=f"And here is {b}.",
                 actions=[ShowBlocks(group="b", hundreds=hb, tens=tb, ones=ob, position="right")]),
        ]
        if ha != hb:
            steps.append(Step(narration="Look at the hundreds first.", actions=[]))
        elif ta != tb:
            steps.append(Step(narration="The hundreds match, so look at the tens.", actions=[]))
        else:
            steps.append(Step(narration="Look at the ones.", actions=[]))
    steps.append(Step(narration=sentence, actions=[ShowSign(sign=sign)]))
    steps.append(Step(narration=f"Great job! {sentence}",
                      actions=[ShowText(text=f"{a} {sign} {b}", region="top", color="green")]))
    return finish(LessonSpec(topic="comparison", grade=grade, difficulty=difficulty,
                             title=f"Comparing {a} and {b}",
                             facts=Facts(kind="comparison", operands=[a, b]), steps=steps))
