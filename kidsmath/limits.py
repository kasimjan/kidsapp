"""Age-appropriateness limits per grade (US Common Core style, K-2)."""

GRADES = (0, 1, 2)  # 0 = Kindergarten
DIFFICULTIES = ("easy", "medium", "hard")

GRADE_NAMES = {0: "Kindergarten", 1: "Grade 1", 2: "Grade 2"}

# Largest allowed sum / minuend for addition and subtraction.
MAX_ADD_SUB = {0: 10, 1: 20, 2: 100}
# Largest number that may be counted or compared.
MAX_COUNT = {0: 20, 1: 20, 2: 20}
MAX_COMPARE = {0: 20, 1: 100, 2: 1000}
# Largest number that may be taken apart into hundreds/tens/ones.
MAX_PLACE_VALUE = {0: 19, 1: 99, 2: 999}
# Largest number of objects drawn on screen at once.
MAX_OBJECTS_ON_SCREEN = 20

# Per-difficulty cap on operands as a fraction of the grade limit.
DIFFICULTY_FRACTION = {"easy": 0.5, "medium": 0.8, "hard": 1.0}

# Shapes by the earliest grade that meets them.
SHAPES_BY_GRADE = {
    0: ("circle", "square", "triangle", "rectangle"),
    1: ("circle", "square", "triangle", "rectangle", "hexagon"),
    2: ("circle", "square", "triangle", "rectangle", "hexagon", "pentagon"),
}
# (sides, corners)
SHAPE_FACTS = {
    "circle": (0, 0),
    "triangle": (3, 3),
    "square": (4, 4),
    "rectangle": (4, 4),
    "pentagon": (5, 5),
    "hexagon": (6, 6),
}

MAX_WORDS_PER_SENTENCE = 16
MAX_NARRATION_CHARS = 280
MAX_STEPS = 40
BANNED_WORDS = frozenset(
    "stupid dumb idiot hate kill die dead hurt wrong fail failure bad".split()
)
