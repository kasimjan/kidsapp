import pytest

from kidsmath.lessons import generate_lesson
from kidsmath.spec import LessonSpec, ShowEquation
from kidsmath.validate import (
    SpecValidationError, equation_is_correct, parse_equation, validate_spec,
)


def spec_dict(**changes):
    d = generate_lesson("addition", 0, numbers=[3, 2]).model_dump()
    d.update(changes)
    return d


def test_equation_parser_is_strict_and_correct():
    assert parse_equation("3 + 2 = 5") == (3, "+", 2, 5)
    assert equation_is_correct("3 + 2 = 5")
    assert not equation_is_correct("3 + 2 = 6")
    assert equation_is_correct("5 - 2 = 3")
    for bad in ("3+2=5", "__import__('os')", "3 * 2 = 6", "3 + 2 = 5; x", "-3 + 5 = 2", ""):
        assert parse_equation(bad) is None


def test_valid_lesson_passes():
    validate_spec(generate_lesson("addition", 0, numbers=[3, 2]))


def test_wrong_fact_result_is_rejected():
    d = spec_dict()
    d["facts"]["result"] = 6
    with pytest.raises(SpecValidationError, match="not 6"):
        validate_spec(LessonSpec.model_validate(d))


def test_wrong_equation_text_is_rejected():
    spec = generate_lesson("addition", 0, numbers=[3, 2])
    for step in spec.steps:
        for a in step.actions:
            if isinstance(a, ShowEquation):
                a.text = "3 + 2 = 6"
    with pytest.raises(SpecValidationError, match="mathematically wrong"):
        validate_spec(spec)


def test_numbers_above_grade_limit_rejected():
    with pytest.raises(SpecValidationError, match="exceeds the grade 0 limit"):
        generate_lesson("addition", 0, numbers=[8, 7])  # 15 > 10 for kindergarten


def test_negative_subtraction_rejected():
    with pytest.raises(SpecValidationError):
        generate_lesson("subtraction", 0, numbers=[2, 5])


def test_long_sentences_and_banned_words_rejected():
    d = spec_dict()
    d["steps"][0]["narration"] = " ".join(["word"] * 20) + "."
    with pytest.raises(SpecValidationError, match="too long"):
        validate_spec(LessonSpec.model_validate(d))
    d = spec_dict()
    d["steps"][0]["narration"] = "That was stupid."
    with pytest.raises(SpecValidationError, match="inappropriate"):
        validate_spec(LessonSpec.model_validate(d))


def test_narration_number_above_limit_rejected():
    d = spec_dict()
    d["steps"][0]["narration"] = "Count to 500."
    with pytest.raises(SpecValidationError, match="narration mentions 500"):
        validate_spec(LessonSpec.model_validate(d))


def test_unknown_group_reference_rejected():
    d = spec_dict()
    d["steps"][3]["actions"] = [{"type": "merge", "source": "zzz", "target": "a"}]
    with pytest.raises(SpecValidationError, match="unknown group"):
        validate_spec(LessonSpec.model_validate(d))


def test_spec_schema_rejects_unknown_actions_and_fields():
    d = spec_dict()
    d["steps"][0]["actions"] = [{"type": "python", "code": "print(1)"}]
    with pytest.raises(ValueError):
        LessonSpec.model_validate(d)
    d = spec_dict()
    d["steps"][0]["evil"] = True
    with pytest.raises(ValueError):
        LessonSpec.model_validate(d)


def test_comparison_sign_must_be_true():
    spec = generate_lesson("comparison", 0, numbers=[7, 4])
    for step in spec.steps:
        for a in step.actions:
            if a.type == "sign":
                a.sign = "<"
    with pytest.raises(SpecValidationError, match="wrong for 7 and 4"):
        validate_spec(spec)


def test_shape_facts_checked():
    spec = generate_lesson("shapes", 0, shape="triangle")
    spec.facts.operands = [4, 4]
    with pytest.raises(SpecValidationError, match="sides=3"):
        validate_spec(spec)
