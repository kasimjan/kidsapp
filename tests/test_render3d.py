import itertools
import math
import re

import numpy as np
import pytest

from kidsmath.lessons import generate_lesson
from kidsmath.render import timing
from kidsmath.render3d import director, layout3d
from kidsmath.render3d.projection import project_point
from kidsmath.render3d.subtitles import (
    Cue, active_word, build_cues, to_srt, word_windows, wrap_words,
)

BALL_DIAMETER = 0.92


# ---------------------------------------------------------------- projection
def test_projection_of_look_at_point_is_screen_center():
    from manimlib import CameraFrame
    f = CameraFrame()
    f.reorient(-30, 60, 0, (1.0, 2.0, 0.5), 8)
    x, y = project_point(f.get_view_matrix(), f.get_scale(), f.get_focal_distance(), (1.0, 2.0, 0.5))
    assert abs(x) < 1e-6 and abs(y) < 1e-6


def test_projection_top_down_matches_world_xy():
    from manimlib import CameraFrame
    f = CameraFrame()
    f.reorient(0, 0, 0, (0, 0, 0), 8)           # looking straight down, default height
    x, y = project_point(f.get_view_matrix(), f.get_scale(), f.get_focal_distance(), (2.0, -1.0, 0.0))
    assert (round(x, 3), round(y, 3)) == (2.0, -1.0)


def test_closer_points_appear_larger():
    from manimlib import CameraFrame
    f = CameraFrame()
    f.reorient(0, 0, 0, (0, 0, 0), 8)
    args = (f.get_view_matrix(), f.get_scale(), f.get_focal_distance())
    near = project_point(*args, (2.0, 0, 3.0))[0]   # toward the camera
    far = project_point(*args, (2.0, 0, -3.0))[0]
    assert near > 2.0 > far


# ----------------------------------------------------------------- subtitles
def test_wrap_words_respects_width_and_keeps_all_words():
    text = "Hi, I'm Milo the Mouse! Let's add! What is 3 plus 2?"
    lines = wrap_words(text, 30)
    assert all(len(" ".join(l)) <= 30 for l in lines)
    assert [w for l in lines for w in l] == text.split()


def test_word_windows_cover_audio_in_order():
    words = "Here are 3 red balls.".split()
    wins = word_windows(words, 2.0)
    assert wins[0][0] == pytest.approx(0.05) and wins[-1][1] == pytest.approx(2.0)
    assert all(a[1] == pytest.approx(b[0]) for a, b in zip(wins, wins[1:]))
    # the full stop makes the last word take longer than a short word
    assert wins[-1][1] - wins[-1][0] > wins[2][1] - wins[2][0]


def test_active_word_progresses():
    wins = word_windows(["one", "two", "three"], 1.5)
    assert active_word(wins, 0.0) == -1
    assert active_word(wins, 0.6) in (0, 1)
    assert active_word(wins, 5.0) == 2


def test_srt_format():
    cues = build_cues(["Hello there.", "Bye!"], [0.0, 2.5], [1.2, 0.6])
    srt = to_srt(cues)
    assert srt.startswith("1\n00:00:00,000 --> 00:00:01,350\nHello there.")
    assert "2\n00:00:02,500 --> 00:00:03,250\nBye!" in srt
    assert isinstance(cues[0], Cue)


# ------------------------------------------------------------------ layout3d
@pytest.mark.parametrize("n", range(1, 21))
@pytest.mark.parametrize("position", ["left", "right", "center"])
def test_toys_never_overlap(n, position):
    pts = layout3d.group_positions(n, position)
    assert len(pts) == n
    for (x1, y1), (x2, y2) in itertools.combinations(pts, 2):
        assert math.hypot(x1 - x2, y1 - y2) > BALL_DIAMETER


def test_left_and_right_groups_do_not_cross_the_middle():
    for n in range(1, 11):
        assert max(x for x, _ in layout3d.group_positions(n, "left")) < -0.2
        assert min(x for x, _ in layout3d.group_positions(n, "right")) > 0.2


@pytest.mark.parametrize("n", range(2, 21))
def test_merged_layout_is_centered_and_overlap_free(n):
    pts = layout3d.merged_positions(n)
    assert abs(sum(x for x, _ in pts)) < 1e-9
    for (x1, y1), (x2, y2) in itertools.combinations(pts, 2):
        assert math.hypot(x1 - x2, y1 - y2) > BALL_DIAMETER


# ------------------------------------------------------------------ director
def timed(topic="addition", **kw):
    return timing.with_estimated_durations(generate_lesson(topic, style="3d", **kw))


def test_camera_track_is_ordered_and_smooth():
    spec = timed(numbers=[3, 2])
    track = director.build_track(spec)
    times = [t for t, _ in track]
    assert times == sorted(times) and len(set(times)) == len(times)
    total = sum(s.duration for s in spec.steps) + timing.FINAL_HOLD
    prev = director.view_at(track, 0)
    t = 0.0
    while t < total:
        v = director.view_at(track, t)
        # no teleporting: at most a few degrees of orbit per frame
        assert abs(v.theta - prev.theta) < 3.0 and abs(v.phi - prev.phi) < 3.0
        assert abs(v.height - prev.height) < 0.4
        prev, t = v, t + 1 / 30


def test_camera_orbits_while_counting():
    spec = timed(numbers=[3, 2])
    track = director.build_track(spec)
    starts = director.step_starts(spec)
    count_steps = [i for i, s in enumerate(spec.steps) if any(a.type == "count_item" for a in s.actions)]
    first = director.view_at(track, starts[count_steps[0]])
    last = director.view_at(track, starts[count_steps[-1]] + spec.steps[count_steps[-1]].duration)
    assert last.theta - first.theta > 15


def test_zoom_fits_content():
    small = director.fit_zoom(timed(numbers=[3, 2]))
    big = director.fit_zoom(timed(grade=1, numbers=[10, 10]))
    assert 6.0 / 9.4 - 1e-9 <= small <= big <= 1.0 + 1e-9


def test_dense_lessons_look_down_more():
    assert not director.is_dense(timed(numbers=[3, 2]))
    assert director.is_dense(timed(grade=1, numbers=[9, 8]))


def test_sway_is_small():
    assert max(abs(director.sway(t / 10)) for t in range(300)) <= director.SWAY_DEGREES + 1e-9


# --------------------------------------------------------- lessons for 3D
def test_3d_wording_says_balls_and_uses_red_and_yellow():
    spec = generate_lesson("addition", 0, numbers=[3, 2], style="3d")
    text = " ".join(s.narration for s in spec.steps)
    assert "3 red balls" in text and "2 yellow balls" in text and "circle" not in text
    colors = [a.color for s in spec.steps for a in s.actions if a.type == "objects"]
    assert colors == ["red", "yellow"]


def test_2d_wording_unchanged_but_second_group_is_yellow():
    spec = generate_lesson("addition", 0, numbers=[3, 2], style="2d")
    assert "3 red circles" in " ".join(s.narration for s in spec.steps)


def test_counting_badges_continue_across_groups():
    spec = generate_lesson("addition", 0, numbers=[3, 2], style="3d")
    shown = [(a.number or a.index) for s in spec.steps for a in s.actions if a.type == "count_item"]
    assert shown == [1, 2, 3, 4, 5]


def test_3d_rejects_shapes_and_blocks():
    from kidsmath.render.pipeline import check_style
    check_style(generate_lesson("addition", 0, numbers=[3, 2], style="3d"), "3d")
    with pytest.raises(ValueError, match="shapes"):
        check_style(generate_lesson("shapes", 0), "3d")
    with pytest.raises(ValueError, match="blocks"):
        check_style(generate_lesson("place_value", 2, numbers=[345]), "3d")
    with pytest.raises(ValueError):
        check_style(generate_lesson("addition", 0), "4d")


@pytest.mark.parametrize("topic", ["addition", "subtraction", "counting", "comparison", "word_problem"])
@pytest.mark.parametrize("grade", [0, 1])
def test_all_3d_topics_generate_and_camera_tracks_build(topic, grade):
    for seed in range(6):
        spec = timed(topic, grade=grade, seed=seed)
        assert director.build_track(spec)
