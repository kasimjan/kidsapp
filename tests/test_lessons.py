import pytest

from kidsmath import limits
from kidsmath.lessons import TEMPLATES, generate_lesson
from kidsmath.spec import LessonSpec
from kidsmath.validate import validate_spec


def test_3_plus_2_lesson_contents():
    spec = generate_lesson("addition", 0, "easy", numbers=[3, 2])
    assert spec.facts.operands == [3, 2] and spec.facts.result == 5
    eqs = [a.text for s in spec.steps for a in s.actions if a.type == "equation"]
    assert "3 + 2 = 5" in eqs
    counts = [a.count for s in spec.steps for a in s.actions if a.type == "objects"]
    assert counts == [3, 2]


@pytest.mark.parametrize("topic", sorted(TEMPLATES))
@pytest.mark.parametrize("grade", [0, 1, 2])
@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_every_generated_lesson_validates(topic, grade, difficulty):
    for seed in range(15):
        spec = generate_lesson(topic, grade, difficulty, seed=seed)
        validate_spec(spec)
        # round-trips through JSON unchanged
        assert LessonSpec.model_validate_json(spec.model_dump_json()) == spec


def test_seed_is_deterministic():
    a = generate_lesson("subtraction", 1, "medium", seed=7)
    b = generate_lesson("subtraction", 1, "medium", seed=7)
    assert a == b


def test_difficulty_scales_numbers():
    easy = max(generate_lesson("addition", 1, "easy", seed=s).facts.result for s in range(40))
    hard = max(generate_lesson("addition", 1, "hard", seed=s).facts.result for s in range(40))
    assert easy <= limits.MAX_ADD_SUB[1] * 0.5 and hard > easy


def test_grade2_two_digit_addition_uses_place_value_steps():
    spec = generate_lesson("addition", 2, numbers=[34, 28])
    eqs = [a.text for s in spec.steps for a in s.actions if a.type == "equation"]
    assert eqs == ["30 + 20 = 50", "4 + 8 = 12", "50 + 12 = 62", "34 + 28 = 62"]


def test_subtraction_to_zero_allowed_for_medium():
    spec = generate_lesson("subtraction", 0, "medium", numbers=[4, 4])
    assert spec.facts.result == 0


def test_word_problem_story():
    spec = generate_lesson("word_problem", 0, numbers=[4, 3], operation="add", seed=1)
    text = " ".join(s.narration for s in spec.steps)
    assert "4" in text and "3" in text and "7" in text


def test_shape_by_grade():
    generate_lesson("shapes", 1, shape="hexagon")
    with pytest.raises(ValueError, match="not taught"):
        generate_lesson("shapes", 0, shape="hexagon")


@pytest.mark.parametrize("args", [
    ("fractions", 0), ("addition", 5), ("addition", 0, "impossible"),
])
def test_bad_requests_rejected(args):
    with pytest.raises(ValueError):
        generate_lesson(*args)


def test_wrong_number_count_rejected():
    with pytest.raises(ValueError, match="exactly 2"):
        generate_lesson("addition", 0, numbers=[3])


def test_milo_introduces_the_lesson_and_can_be_disabled():
    with_milo = generate_lesson("addition", 0, numbers=[3, 2])
    assert with_milo.mascot == "milo"
    assert with_milo.steps[0].narration.startswith("Hi, I'm Milo the Mouse!")
    without = generate_lesson("addition", 0, numbers=[3, 2], mascot="none")
    assert without.mascot == "none" and "Milo" not in without.steps[0].narration
    with pytest.raises(ValueError):
        generate_lesson("addition", 0, numbers=[3, 2], mascot="mickey")
