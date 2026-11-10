"""Addition, subtraction and simple word-problem templates."""
from __future__ import annotations

import random

from .. import limits
from ..spec import (
    CountItem, CrossOut, Facts, LessonSpec, MergeGroups, ShowBlocks,
    ShowEquation, ShowObjects, ShowText, Step, TitleCard,
)
from ..validate import difficulty_limit
from .looks import noun
from .common import count_phrase, finish, need_numbers, number_word, split_tens_ones

OBJECT_LIMIT = limits.MAX_OBJECTS_ON_SCREEN
CHEERS = ("Great job!", "Awesome!", "You did it!", "Hooray!")


def _cheer(rng: random.Random) -> str:
    return rng.choice(CHEERS)


def _counting_steps(group: str, upto: int) -> list[Step]:
    return [
        Step(narration=number_word(i), actions=[CountItem(group=group, index=i)])
        for i in range(1, upto + 1)
    ]


# ---- addition ------------------------------------------------------------

def addition(grade: int, difficulty: str, numbers: list[int] | None,
             rng: random.Random, solid: bool = False, **_) -> LessonSpec:
    cap = difficulty_limit("addition", grade, difficulty)

    def make(r):
        total = r.randint(3, max(3, cap))
        a = r.randint(1, total - 2)
        return [a, total - a]

    a, b = need_numbers(numbers, 2, rng, make)
    c = a + b
    facts = Facts(kind="addition", operands=[a, b], result=c)
    title = f"{a} + {b} = ?"
    if c <= OBJECT_LIMIT:
        what = noun("circle", solid)
        steps = _objects_addition(a, b, c, rng, "red", "yellow", "circle", what, what + "s")
    else:
        steps = _blocks_addition(a, b, c, rng)
    steps.insert(0, Step(narration=f"Let's add! What is {a} plus {b}?", actions=[TitleCard(text=title)]))
    return finish(LessonSpec(topic="addition", grade=grade, difficulty=difficulty,
                             title=f"Adding {a} and {b}", facts=facts, steps=steps))


def _objects_addition(a, b, c, rng, color_a, color_b, shape, singular, plural,
                      first_line=None, second_line=None, ask=None, answer=None):
    steps = [
        Step(narration=first_line or f"Here are {count_phrase(a, color_a + ' ' + singular, color_a + ' ' + plural)}.",
             actions=[ShowObjects(group="a", count=a, shape=shape, color=color_a, position="left")]),
        Step(narration=second_line or f"And here are {count_phrase(b, color_b + ' ' + singular, color_b + ' ' + plural)}.",
             actions=[ShowObjects(group="b", count=b, shape=shape, color=color_b, position="right")]),
    ]
    if ask:
        steps.append(Step(narration=ask, actions=[]))
    steps.append(Step(narration="Let's put them all together.",
                      actions=[MergeGroups(source="b", target="a")]))
    steps.append(Step(narration="Now let's count them all.", actions=[]))
    steps += _counting_steps_merged(a, b)
    steps.append(Step(narration=f"{a} plus {b} equals {c}!", actions=[ShowEquation(text=f"{a} + {b} = {c}")]))
    steps.append(Step(narration=answer or f"{_cheer(rng)} {a} plus {b} makes {c}.",
                      actions=[ShowText(text=f"{c} in all!", region="top", color="green")]))
    return steps


def _counting_steps_merged(a: int, b: int) -> list[Step]:
    """Count the merged row: first the 'a' objects, then the 'b' objects."""
    steps = [Step(narration=number_word(i), actions=[CountItem(group="a", index=i)])
             for i in range(1, a + 1)]
    steps += [Step(narration=number_word(a + j), actions=[CountItem(group="b", index=j, number=a + j)])
              for j in range(1, b + 1)]
    return steps


def _blocks_addition(a, b, c, rng):
    _, ta, oa = split_tens_ones(a)
    _, tb, ob = split_tens_ones(b)
    if a > 99 or b > 99:
        raise ValueError("block-based addition supports numbers up to 99")
    tens_sum, ones_sum = (ta + tb) * 10, oa + ob
    return [
        Step(narration=f"Here is {a}. It is {ta} tens and {oa} ones.",
             actions=[ShowBlocks(group="a", tens=ta, ones=oa, position="left")]),
        Step(narration=f"Here is {b}. It is {tb} tens and {ob} ones.",
             actions=[ShowBlocks(group="b", tens=tb, ones=ob, position="right")]),
        Step(narration=f"First, add the tens. {ta * 10} plus {tb * 10} is {tens_sum}.",
             actions=[ShowEquation(text=f"{ta * 10} + {tb * 10} = {tens_sum}", color="orange")]),
        Step(narration=f"Next, add the ones. {oa} plus {ob} is {ones_sum}.",
             actions=[ShowEquation(text=f"{oa} + {ob} = {ones_sum}", color="orange")]),
        Step(narration=f"Now put them together. {tens_sum} plus {ones_sum} is {c}.",
             actions=[ShowEquation(text=f"{tens_sum} + {ones_sum} = {c}", color="orange")]),
        Step(narration=f"So {a} plus {b} equals {c}!",
             actions=[ShowEquation(text=f"{a} + {b} = {c}")]),
        Step(narration=f"{_cheer(rng)} The answer is {c}.",
             actions=[ShowText(text=f"{c} in all!", region="top", color="green")]),
    ]


# ---- subtraction ---------------------------------------------------------

def subtraction(grade: int, difficulty: str, numbers: list[int] | None,
                rng: random.Random, solid: bool = False, **_) -> LessonSpec:
    cap = difficulty_limit("subtraction", grade, difficulty)

    def make(r):
        a = r.randint(3, max(3, cap))
        hi = a if difficulty != "easy" else a - 1
        return [a, r.randint(1, hi)]

    a, b = need_numbers(numbers, 2, rng, make)
    c = a - b
    facts = Facts(kind="subtraction", operands=[a, b], result=c)
    if a <= OBJECT_LIMIT:
        what = noun("star", solid)
        steps = _objects_subtraction(a, b, c, rng, noun_s=f"blue {what}", noun_p=f"blue {what}s")
    else:
        steps = _blocks_subtraction(a, b, c, rng)
    steps.insert(0, Step(narration=f"Let's subtract! What is {a} minus {b}?",
                         actions=[TitleCard(text=f"{a} - {b} = ?")]))
    return finish(LessonSpec(topic="subtraction", grade=grade, difficulty=difficulty,
                             title=f"Taking {b} away from {a}", facts=facts, steps=steps))


def _objects_subtraction(a, b, c, rng, noun_s="blue star", noun_p="blue stars",
                         shape="star", color="blue", start_line=None, take_line=None,
                         ask=None, answer=None):
    steps = [
        Step(narration=start_line or f"We start with {count_phrase(a, noun_s, noun_p)}.",
             actions=[ShowObjects(group="a", count=a, shape=shape, color=color)]),
        Step(narration=take_line or f"Let's take away {b}.",
             actions=[CrossOut(group="a", count=b)]),
    ]
    if ask:
        steps.append(Step(narration=ask, actions=[]))
    steps.append(Step(narration="Now count the ones that are left.", actions=[]))
    steps += _counting_steps("a", c)
    steps.append(Step(narration=f"{a} minus {b} equals {c}!",
                      actions=[ShowEquation(text=f"{a} - {b} = {c}")]))
    steps.append(Step(narration=answer or f"{_cheer(rng)} {a} minus {b} leaves {c}.",
                      actions=[ShowText(text=f"{c} left!", region="top", color="green")]))
    return steps


def _blocks_subtraction(a, b, c, rng):
    if a > 99:
        raise ValueError("block-based subtraction supports numbers up to 99")
    _, ta, oa = split_tens_ones(a)
    _, tb, ob = split_tens_ones(b)
    after_tens = a - tb * 10
    _, tc, oc = split_tens_ones(c)
    return [
        Step(narration=f"Start with {a}. It is {ta} tens and {oa} ones.",
             actions=[ShowBlocks(group="a", tens=ta, ones=oa)]),
        Step(narration=f"First, take away the tens. {a} minus {tb * 10} is {after_tens}.",
             actions=[ShowEquation(text=f"{a} - {tb * 10} = {after_tens}", color="orange")]),
        Step(narration=f"Next, take away the ones. {after_tens} minus {ob} is {c}.",
             actions=[ShowEquation(text=f"{after_tens} - {ob} = {c}", color="orange")]),
        Step(narration=f"Here is what is left. {c} is {tc} tens and {oc} ones.",
             actions=[ShowBlocks(group="a", tens=tc, ones=oc)]),
        Step(narration=f"So {a} minus {b} equals {c}!",
             actions=[ShowEquation(text=f"{a} - {b} = {c}")]),
        Step(narration=f"{_cheer(rng)} The answer is {c}.",
             actions=[ShowText(text=f"{c} left!", region="top", color="green")]),
    ]


# ---- word problems -------------------------------------------------------

NAMES = ("Mia", "Leo", "Ava", "Sam", "Zoe", "Max", "Ivy", "Ben")
# singular, plural, shape, color
THINGS = (
    ("apple", "apples", "circle", "red"),
    ("cookie", "cookies", "circle", "orange"),
    ("balloon", "balloons", "circle", "blue"),
    ("block", "blocks", "square", "green"),
    ("sticker", "stickers", "star", "yellow"),
    ("flower", "flowers", "heart", "pink"),
)


def word_problem(grade: int, difficulty: str, numbers: list[int] | None,
                 rng: random.Random, operation: str | None = None, solid: bool = False, **_) -> LessonSpec:
    op = operation or rng.choice(("add", "subtract"))
    if op not in ("add", "subtract"):
        raise ValueError("operation must be 'add' or 'subtract'")
    # Stories are drawn with objects, so cap at what fits on screen.
    cap = min(difficulty_limit("word_problem", grade, difficulty), 10 if grade == 0 else OBJECT_LIMIT)

    if op == "add":
        def make(r):
            total = r.randint(3, max(3, cap))
            a = r.randint(1, total - 2)
            return [a, total - a]
    else:
        def make(r):
            a = r.randint(3, max(3, cap))
            return [a, r.randint(1, a - 1)]
    a, b = need_numbers(numbers, 2, rng, make)
    c = a + b if op == "add" else a - b
    if max(a, b, c) > OBJECT_LIMIT:
        raise ValueError(f"word problems support numbers up to {OBJECT_LIMIT}")
    name = rng.choice(NAMES)
    sing, plur, shape, color = rng.choice(THINGS)
    facts = Facts(kind="word_problem", operands=[a, b], result=c, operation=op)

    if op == "add":
        steps = _objects_addition(
            a, b, c, rng, color, "teal" if color != "teal" else "blue", shape, sing, plur,
            first_line=f"{name} has {count_phrase(a, sing, plur)}.",
            second_line=f"Then {name} gets {b} more.",
            ask=f"How many {plur} does {name} have now?",
            answer=f"{_cheer(rng)} {name} has {c} {plur} now.",
        )
    else:
        steps = _objects_subtraction(
            a, b, c, rng, noun_s=sing, noun_p=plur, shape=shape, color=color,
            start_line=f"{name} has {count_phrase(a, sing, plur)}.",
            take_line=f"{name} gives away {b}.",
            ask=f"How many {plur} are left?",
            answer=f"{_cheer(rng)} {name} has {c} {plur} left.",
        )
    steps.insert(0, Step(narration=f"Let's solve a story problem about {name}!",
                         actions=[TitleCard(text=f"{name}'s {plur.title()}")]))
    return finish(LessonSpec(topic="word_problem", grade=grade, difficulty=difficulty,
                             title=f"{name} and the {plur}", facts=facts, steps=steps))
