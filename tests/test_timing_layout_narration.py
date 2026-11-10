import wave

from kidsmath.lessons import generate_lesson
from kidsmath.narration import SilentBackend, synthesize_lesson, wav_duration
from kidsmath.render import layout, timing
from kidsmath.render.pipeline import with_durations


def test_durations_are_whole_frames():
    for seconds in (0.1, 0.34, 1.0, 2.71):
        q = timing.quantize(seconds)
        assert q >= seconds - 1e-9
        assert abs(q * timing.FPS - round(q * timing.FPS)) < 1e-9


def test_step_duration_covers_audio_and_animation():
    spec = generate_lesson("addition", 0, numbers=[3, 2])
    for step in spec.steps:
        d = timing.step_duration(step, 2.0)
        assert d >= 2.0 + timing.STEP_PAD - 1e-9
        assert d >= timing.animation_time(step)


def test_grid_positions_centered_and_distinct():
    pts = layout.grid_positions(5, 5, 1.0, 0.0, 0.0)
    assert [round(x, 3) for x, _ in pts] == [-2.0, -1.0, 0.0, 1.0, 2.0]
    assert len(set(layout.merged_positions(15))) == 15
    xs = [x for x, _ in layout.merged_positions(20)]
    assert abs(sum(xs)) < 1e-9 and max(xs) < 7.0  # fits the 14.2-wide frame


def test_groups_stay_inside_their_side_of_screen():
    for pos in ("left", "right"):
        for n in range(1, 11):
            xs = [x for x, _ in layout.group_positions(n, pos)]
            assert (min(xs) > 0.4) if pos == "right" else (max(xs) < -0.4)


def test_silent_narration_and_sync(tmp_path):
    spec = generate_lesson("addition", 0, numbers=[3, 2])
    paths = synthesize_lesson(spec, SilentBackend(), tmp_path / "a", cache_dir=tmp_path / "c")
    assert len(paths) == len(spec.steps)
    timed = with_durations(spec, paths)
    for step, p in zip(timed.steps, paths):
        assert step.duration >= wav_duration(p)
    # second run is served from the cache
    again = synthesize_lesson(spec, SilentBackend(), tmp_path / "b", cache_dir=tmp_path / "c")
    with wave.open(str(again[0])) as w:
        assert w.getnframes() > 0


def test_mouth_envelope_one_value_per_frame(tmp_path):
    import struct
    import wave as wv
    from kidsmath.narration import SAMPLE_RATE, mouth_envelope

    # 1 s: half a second of loud tone, half a second of silence
    frames = []
    for i in range(SAMPLE_RATE):
        v = int(12000 * ((i // 40) % 2 * 2 - 1)) if i < SAMPLE_RATE // 2 else 0
        frames.append(struct.pack("<h", v))
    path = tmp_path / "a.wav"
    with wv.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SAMPLE_RATE)
        w.writeframes(b"".join(frames))
    env = mouth_envelope(path, 30)
    assert 28 <= len(env) <= 31
    assert max(env[:12]) > 0.8 and max(env[18:]) < 0.1
    assert all(0 <= v <= 1 for v in env)


def test_silent_audio_gets_synthetic_flap(tmp_path):
    from kidsmath.narration import SilentBackend, mouth_envelope

    p = tmp_path / "s.wav"
    SilentBackend().synthesize("hello there friend", p)
    env = mouth_envelope(p, 30)
    assert max(env) > 0.3 and min(env) < 0.2
