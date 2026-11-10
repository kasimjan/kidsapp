"""Shared helpers for lesson templates."""
from __future__ import annotations

import random

from ..spec import LessonSpec
from ..validate import validate_spec

_WORDS = (
    "zero one two three four five six seven eight nine ten eleven twelve "
    "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty"
).split()


def number_word(n: int) -> str:
    """Spell small numbers; larger ones stay as digits for the voice to read."""
    return _WORDS[n] if 0 <= n <= 20 else str(n)


def count_phrase(n: int, singular: str, plural: str | None = None) -> str:
    return f"{n} {singular if n == 1 else (plural or singular + 's')}"


def finish(spec: LessonSpec) -> LessonSpec:
    """Every template output goes through the validator before it leaves."""
    return validate_spec(spec)


def split_tens_ones(n: int) -> tuple[int, int, int]:
    return n // 100, n // 10 % 10, n % 10


def need_numbers(numbers: list[int] | None, count: int, rng: random.Random, make) -> list[int]:
    """Use the caller's numbers if given, else ask `make(rng)` for a fresh set."""
    if numbers is None:
        return make(rng)
    if len(numbers) != count:
        raise ValueError(f"this topic needs exactly {count} number(s), got {len(numbers)}")
    return list(numbers)
