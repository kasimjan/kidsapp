"""Mathematical-correctness and age-appropriateness validation of lesson specs.

Nothing here uses eval/exec: equations are parsed with a strict regex and
recomputed with plain integer arithmetic.
"""
from __future__ import annotations

import re

from . import limits
from .spec import (
    CountItem, CrossOut, LessonSpec, MergeGroups, ShowBlocks, ShowEquation,
    ShowObjects, ShowShape, ShowSign,
)

_EQUATION = re.compile(r"^(\d{1,3}) ([+-]) (\d{1,3}) = (\d{1,3})$")
_NUMBER = re.compile(r"\d+")
_SENTENCE_SPLIT = re.compile(r"[.!?]+")
_WORD = re.compile(r"[A-Za-z']+")


class SpecValidationError(ValueError):
    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__("; ".join(issues))


def parse_equation(text: str) -> tuple[int, str, int, int] | None:
    m = _EQUATION.match(text)
    if not m:
        return None
    a, op, b, c = int(m[1]), m[2], int(m[3]), int(m[4])
    return a, op, b, c


def equation_is_correct(text: str) -> bool:
    parsed = parse_equation(text)
    if parsed is None:
        return False
    a, op, b, c = parsed
    return (a + b if op == "+" else a - b) == c


def number_limit(topic: str, grade: int) -> int:
    """Largest number a lesson of this topic may mention at this grade."""
    if topic == "place_value":
        return limits.MAX_PLACE_VALUE[grade]
    if topic == "comparison":
        return limits.MAX_COMPARE[grade]
    if topic in ("counting", "shapes"):
        return limits.MAX_COUNT[grade]
    return limits.MAX_ADD_SUB[grade]


def difficulty_limit(topic: str, grade: int, difficulty: str) -> int:
    """Cap for generated operands: grade limit scaled by difficulty."""
    cap = number_limit(topic, grade)
    return max(2, int(cap * limits.DIFFICULTY_FRACTION[difficulty]))


def validate_spec(spec: LessonSpec) -> LessonSpec:
    """Raise SpecValidationError listing every problem; return spec if clean."""
    issues: list[str] = []
    cap = number_limit(spec.topic, spec.grade)
    facts = spec.facts

    if facts.kind != spec.topic:
        issues.append(f"facts.kind '{facts.kind}' does not match topic '{spec.topic}'")

    _check_facts(spec, cap, issues)
    _check_steps(spec, cap, issues)
    _check_narration(spec, cap, issues)

    if issues:
        raise SpecValidationError(issues)
    return spec


def _check_facts(spec: LessonSpec, cap: int, issues: list[str]) -> None:
    f = spec.facts
    ops = f.operands
    if any(n < 0 for n in ops) or (f.result is not None and f.result < 0):
        issues.append("negative numbers are not allowed in K-2 lessons")
    for n in [*ops, *([f.result] if f.result is not None else [])]:
        if n > cap:
            issues.append(f"number {n} exceeds the grade {spec.grade} limit of {cap} for {spec.topic}")

    kind = f.kind
    if kind == "addition" or (kind == "word_problem" and f.operation == "add"):
        if len(ops) != 2 or f.result is None:
            issues.append("addition facts need two operands and a result")
        elif ops[0] + ops[1] != f.result:
            issues.append(f"{ops[0]} + {ops[1]} is {ops[0] + ops[1]}, not {f.result}")
    elif kind == "subtraction" or (kind == "word_problem" and f.operation == "subtract"):
        if len(ops) != 2 or f.result is None:
            issues.append("subtraction facts need two operands and a result")
        elif ops[0] - ops[1] != f.result:
            issues.append(f"{ops[0]} - {ops[1]} is {ops[0] - ops[1]}, not {f.result}")
        elif ops[1] > ops[0]:
            issues.append("subtrahend may not exceed minuend")
    elif kind == "word_problem":
        issues.append("word_problem facts need operation 'add' or 'subtract'")
    elif kind == "counting":
        if len(ops) != 1 or ops[0] < 1:
            issues.append("counting facts need one operand (how far to count)")
    elif kind == "comparison":
        if len(ops) != 2:
            issues.append("comparison facts need two operands")
    elif kind == "place_value":
        if len(ops) != 1 or f.result is None:
            issues.append("place_value facts need one operand (the number)")
    elif kind == "shapes":
        if f.shape not in limits.SHAPES_BY_GRADE[spec.grade]:
            issues.append(f"shape '{f.shape}' is not taught at grade {spec.grade}")


def _check_steps(spec: LessonSpec, cap: int, issues: list[str]) -> None:
    sizes: dict[str, int] = {}  # group -> objects still visible
    original: dict[str, int] = {}
    order: list[str] = []
    equations: list[tuple[int, str, int, int]] = []
    shapes_shown: list[str] = []
    saw_sign = False

    for i, step in enumerate(spec.steps, 1):
        for a in step.actions:
            where = f"step {i}"
            if isinstance(a, ShowObjects):
                if a.group in sizes:
                    issues.append(f"{where}: group '{a.group}' defined twice")
                sizes[a.group] = original[a.group] = a.count
                order.append(a.group)
                if sum(sizes.values()) > limits.MAX_OBJECTS_ON_SCREEN * 2:
                    issues.append(f"{where}: too many objects on screen")
            elif isinstance(a, ShowBlocks):
                sizes.setdefault(a.group, 0)
                value = a.hundreds * 100 + a.tens * 10 + a.ones
                if value > max(cap, limits.MAX_PLACE_VALUE[spec.grade]):
                    issues.append(f"{where}: blocks show {value}, above the grade limit")
            elif isinstance(a, CountItem):
                if a.group not in original:
                    issues.append(f"{where}: count_item on unknown group '{a.group}'")
                elif a.index > original[a.group]:
                    issues.append(f"{where}: index {a.index} beyond group size {original[a.group]}")
            elif isinstance(a, MergeGroups):
                for g in (a.source, a.target):
                    if g not in sizes:
                        issues.append(f"{where}: merge uses unknown group '{g}'")
            elif isinstance(a, CrossOut):
                if a.group not in sizes:
                    issues.append(f"{where}: cross_out on unknown group '{a.group}'")
                elif a.count > sizes[a.group]:
                    issues.append(f"{where}: cross_out {a.count} but only {sizes[a.group]} left")
                else:
                    sizes[a.group] -= a.count
            elif isinstance(a, ShowEquation):
                parsed = parse_equation(a.text)
                if parsed is None:
                    issues.append(f"{where}: equation '{a.text}' must look like '3 + 2 = 5'")
                elif not equation_is_correct(a.text):
                    issues.append(f"{where}: equation '{a.text}' is mathematically wrong")
                else:
                    equations.append(parsed)
                    if max(parsed[0], parsed[2], parsed[3]) > cap:
                        issues.append(f"{where}: equation '{a.text}' exceeds limit {cap}")
            elif isinstance(a, ShowShape):
                shapes_shown.append(a.name)
                if a.name not in limits.SHAPES_BY_GRADE[spec.grade]:
                    issues.append(f"{where}: shape '{a.name}' not taught at grade {spec.grade}")
            elif isinstance(a, ShowSign):
                saw_sign = True
                if len(sizes) < 2:
                    issues.append(f"{where}: sign needs two groups on screen")

    _check_consistency(spec, original, equations, shapes_shown, saw_sign, order, issues)


def _check_consistency(spec, original, equations, shapes_shown, saw_sign, order, issues):
    f = spec.facts
    ops = f.operands
    if f.kind in ("addition", "subtraction", "word_problem") and len(ops) == 2 and f.result is not None:
        op = "+" if (f.kind == "addition" or f.operation == "add") else "-"
        want = (ops[0], op, ops[1], f.result)
        if want not in equations:
            issues.append(f"lesson never states the equation {ops[0]} {op} {ops[1]} = {f.result}")
        # Object counts must agree with the operands when objects are used.
        if len(order) >= 2 and op == "+":
            if [original[g] for g in order[:2]] != ops:
                issues.append("object groups do not match the addends")
        if order and op == "-" and original[order[0]] != ops[0]:
            issues.append("starting object group does not match the minuend")
    elif f.kind == "comparison" and len(ops) == 2:
        if saw_sign and len(order) >= 2:
            if [original[g] for g in order[:2]] != ops:
                issues.append("object groups do not match the compared numbers")
        elif saw_sign:
            values = [b.hundreds * 100 + b.tens * 10 + b.ones for s in spec.steps
                      for b in s.actions if isinstance(b, ShowBlocks)]
            if values[:2] != ops:
                issues.append("blocks do not match the compared numbers")
        sign_actions = [a for s in spec.steps for a in s.actions if isinstance(a, ShowSign)]
        for a in sign_actions:
            truth = "<" if ops[0] < ops[1] else ">" if ops[0] > ops[1] else "="
            if a.sign != truth:
                issues.append(f"sign '{a.sign}' is wrong for {ops[0]} and {ops[1]}")
    elif f.kind == "shapes":
        if f.shape not in shapes_shown:
            issues.append(f"lesson about '{f.shape}' never draws it")
        sides, corners = limits.SHAPE_FACTS.get(f.shape or "", (None, None))
        if sides is None:
            issues.append(f"unknown shape '{f.shape}'")
        if f.operands and f.operands != [sides, corners]:
            issues.append(f"shape facts for {f.shape} should be sides={sides}, corners={corners}")
    elif f.kind == "place_value" and ops and f.result is not None:
        blocks = [a for s in spec.steps for a in s.actions if isinstance(a, ShowBlocks)]
        h, t, o = ops[0] // 100, ops[0] // 10 % 10, ops[0] % 10
        if not any((b.hundreds, b.tens, b.ones) == (h, t, o) for b in blocks):
            issues.append(f"no blocks show {ops[0]} as {h} hundreds, {t} tens, {o} ones")
    elif f.kind == "counting" and ops:
        if ops[0] != max((original.values()), default=ops[0]):
            issues.append("counted group size does not match facts")


def _check_narration(spec: LessonSpec, cap: int, issues: list[str]) -> None:
    for i, step in enumerate(spec.steps, 1):
        text = step.narration
        if len(text) > limits.MAX_NARRATION_CHARS:
            issues.append(f"step {i}: narration too long")
        for sentence in _SENTENCE_SPLIT.split(text):
            if len(_WORD.findall(sentence)) > limits.MAX_WORDS_PER_SENTENCE:
                issues.append(f"step {i}: sentence too long for young children: '{sentence.strip()}'")
        bad = {w.lower() for w in _WORD.findall(text)} & limits.BANNED_WORDS
        if bad:
            issues.append(f"step {i}: inappropriate words {sorted(bad)}")
        for n in _NUMBER.findall(text):
            if int(n) > cap:
                issues.append(f"step {i}: narration mentions {n}, above the limit {cap}")
