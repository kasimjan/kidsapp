"""Structured JSON lesson specification.

A lesson is pure data: a list of steps, each with a narration sentence and a
list of actions drawn from a small closed vocabulary. The renderer interprets
these actions; no code from a spec is ever executed. This is the contract a
future natural-language front end (e.g. an LLM) must target.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from .limits import MAX_OBJECTS_ON_SCREEN, MAX_STEPS

Topic = Literal[
    "addition", "subtraction", "counting", "comparison",
    "shapes", "place_value", "word_problem",
]
Color = Literal["red", "orange", "yellow", "green", "blue", "purple", "pink", "teal"]
ObjectShape = Literal["circle", "square", "triangle", "star", "heart"]
Position = Literal["left", "center", "right"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---- actions -------------------------------------------------------------

class TitleCard(_Strict):
    type: Literal["title"] = "title"
    text: str = Field(max_length=60)


class ShowText(_Strict):
    """A caption in a fixed region of the screen."""
    type: Literal["text"] = "text"
    text: str = Field(max_length=80)
    region: Literal["top", "bottom"] = "top"
    color: Color = "blue"
    replace: bool = True  # replace the previous caption in this region


class ShowObjects(_Strict):
    """Pop in `count` identical objects as a named group."""
    type: Literal["objects"] = "objects"
    group: str = Field(pattern=r"^[a-z][a-z0-9_]{0,15}$")
    count: int = Field(ge=1, le=MAX_OBJECTS_ON_SCREEN)
    shape: ObjectShape = "circle"
    color: Color = "red"
    position: Position = "center"


class CountItem(_Strict):
    """Highlight object `index` (1-based) of a group and show its number."""
    type: Literal["count_item"] = "count_item"
    group: str
    index: int = Field(ge=1, le=MAX_OBJECTS_ON_SCREEN)
    # Number shown on the badge when counting continues across groups (4, 5, ...).
    number: int | None = Field(default=None, ge=1, le=MAX_OBJECTS_ON_SCREEN * 2)


class MergeGroups(_Strict):
    """Slide group `source` next to group `target` so they read as one."""
    type: Literal["merge"] = "merge"
    source: str
    target: str


class CrossOut(_Strict):
    """Cross out the last `count` objects of a group (take away)."""
    type: Literal["cross_out"] = "cross_out"
    group: str
    count: int = Field(ge=1, le=MAX_OBJECTS_ON_SCREEN)


class ShowEquation(_Strict):
    """Reveal an equation such as '3 + 2 = 5'. Checked by the validator."""
    type: Literal["equation"] = "equation"
    text: str = Field(max_length=24)
    color: Color = "purple"


class ShowSign(_Strict):
    """Comparison sign between the left and right groups."""
    type: Literal["sign"] = "sign"
    sign: Literal["<", ">", "="]


class ShowShape(_Strict):
    """Draw a named geometric shape with its name underneath."""
    type: Literal["shape"] = "shape"
    name: Literal["circle", "square", "triangle", "rectangle", "pentagon", "hexagon"]
    color: Color = "blue"
    highlight: Literal["none", "sides", "corners"] = "none"


class ShowBlocks(_Strict):
    """Base-ten blocks: hundreds flats, tens rods and ones cubes."""
    type: Literal["blocks"] = "blocks"
    group: str = Field(pattern=r"^[a-z][a-z0-9_]{0,15}$")
    hundreds: int = Field(default=0, ge=0, le=9)
    tens: int = Field(ge=0, le=9)
    ones: int = Field(ge=0, le=9)
    position: Position = "center"


class Clear(_Strict):
    """Fade everything off the screen."""
    type: Literal["clear"] = "clear"


Action = Annotated[
    Union[
        TitleCard, ShowText, ShowObjects, CountItem, MergeGroups, CrossOut,
        ShowEquation, ShowSign, ShowShape, ShowBlocks, Clear,
    ],
    Field(discriminator="type"),
]


# ---- facts ---------------------------------------------------------------

class Facts(_Strict):
    """Machine-checkable claims the lesson makes. The validator recomputes them."""
    kind: Literal[
        "addition", "subtraction", "counting", "comparison",
        "shapes", "place_value", "word_problem",
    ]
    operands: list[int] = Field(default_factory=list, max_length=3)
    result: int | None = None
    shape: str | None = None
    operation: Literal["add", "subtract"] | None = None  # for word problems


# ---- lesson --------------------------------------------------------------

class Step(_Strict):
    narration: str = Field(min_length=1, max_length=280)
    actions: list[Action] = Field(default_factory=list, max_length=8)
    # Filled in by the pipeline once narration audio length is known.
    duration: float | None = Field(default=None, gt=0, le=60)


class LessonSpec(_Strict):
    version: Literal[1] = 1
    topic: Topic
    grade: Literal[0, 1, 2]
    difficulty: Literal["easy", "medium", "hard"] = "easy"
    title: str = Field(max_length=60)
    mascot: Literal["milo", "none"] = "milo"  # the character who explains the lesson
    facts: Facts
    steps: list[Step] = Field(min_length=1, max_length=MAX_STEPS)
