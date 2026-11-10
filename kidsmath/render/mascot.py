"""Milo the Mouse: an original cartoon mascot drawn from ManimGL primitives.

Everything about Milo's motion is a pure function of the scene clock, so he is
frame-accurate: lip-sync follows the narration loudness, he blinks every few
seconds, bobs while idle, and hops to celebrate.
"""
import math

from manimlib import *  # noqa: F401,F403

FUR = "#9AA5B8"
FUR_DARK = "#7C879B"
INNER = "#FFB3C7"
VEST = "#FF9F1C"
INK = "#2B2D42"
MOUTH = "#8E2C48"

BASE = (-6.05, -2.65, 0.0)
SCALE = 1.0
HOP_SECONDS = 0.7
HOP_HEIGHT = 0.55


def _blob(shape, color, stroke=True):
    # ManimGL draws every outline above every fill, so shapes that sit behind
    # others get no outline (otherwise it would show through the head).
    shape.set_fill(color, opacity=1)
    shape.set_stroke(INK, width=3 if stroke else 0)
    return shape


class Milo(VGroup):
    def __init__(self):
        super().__init__()
        ear_l = _blob(Circle(radius=0.36), FUR_DARK, False).move_to([-0.55, 0.95, 0])
        ear_r = _blob(Circle(radius=0.36), FUR_DARK, False).move_to([0.55, 0.95, 0])
        inner_l = _blob(Circle(radius=0.2), INNER, False).move_to(ear_l)
        inner_r = _blob(Circle(radius=0.2), INNER, False).move_to(ear_r)
        body = _blob(Circle(radius=0.55).stretch_to_fit_height(0.95), VEST, False).move_to([0, -0.7, 0])
        belly = _blob(Circle(radius=0.3).stretch_to_fit_height(0.5), "#FFE3B0", False).move_to([0, -0.72, 0])
        arm_l = _blob(Circle(radius=0.15).stretch_to_fit_height(0.5), FUR, False).move_to([-0.62, -0.62, 0])
        arm_r = _blob(Circle(radius=0.15).stretch_to_fit_height(0.5), FUR, False).move_to([0.62, -0.62, 0])
        foot_l = _blob(Circle(radius=0.2).stretch_to_fit_width(0.5).stretch_to_fit_height(0.24), INK).move_to([-0.25, -1.22, 0])
        foot_r = _blob(Circle(radius=0.2).stretch_to_fit_width(0.5).stretch_to_fit_height(0.24), INK).move_to([0.25, -1.22, 0])
        head = _blob(Circle(radius=0.78), FUR).move_to([0, 0.35, 0])
        muzzle = _blob(Circle(radius=0.36).stretch_to_fit_height(0.5), "#E4E9F2", False).move_to([0, 0.12, 0])
        nose = _blob(Circle(radius=0.1), INNER).move_to([0, 0.3, 0])
        self.smile = Arc(start_angle=-math.pi * 0.85, angle=math.pi * 0.7, radius=0.3)
        self.smile.set_stroke(INK, width=4).move_to([0, 0.07, 0])
        self.mouth = _blob(Circle(radius=0.16), MOUTH)
        self.mouth.move_to([0, 0.0, 0])
        self.eyes = VGroup(*[
            VGroup(_blob(Circle(radius=0.15), WHITE), _blob(Circle(radius=0.075), INK, False).shift(0.03 * DOWN))
            .move_to([x, 0.58, 0])
            for x in (-0.28, 0.28)
        ])
        self.add(ear_l, ear_r, inner_l, inner_r, foot_l, foot_r, body, belly, arm_l, arm_r,
                 head, muzzle, nose, self.smile, self.mouth, self.eyes)
        self.scale(SCALE)
        self.move_to(BASE)
        self._mouth_h = 0.0
        self.mouth.stretch_to_fit_height(0.001)
        self.mouth.set_opacity(0)
        self._offset = 0.0
        self._eyes_closed = False

    # ---- pure functions of time ----
    def set_openness(self, openness: float):
        openness = max(0.0, min(1.0, openness))
        if openness < 0.08:
            self.mouth.set_opacity(0)
            self.smile.set_opacity(1)
            self._mouth_h = 0.0
            return
        h = 0.05 + 0.42 * openness * SCALE
        if abs(h - self._mouth_h) > 1e-4:
            center = self.mouth.get_center()
            self.mouth.stretch_to_fit_height(h)
            self.mouth.move_to(center)
            self._mouth_h = h
        self.mouth.set_opacity(1)
        self.smile.set_opacity(0)

    def set_blink(self, t: float):
        closed = (t % 3.4) < 0.14
        if closed != self._eyes_closed:
            self._eyes_closed = closed
            self.eyes.stretch_to_fit_height(0.04 if closed else 0.30 * SCALE,
                                            about_point=self.eyes.get_center())

    def y_offset(self, t: float, hops: list[float]) -> float:
        y = 0.04 * math.sin(t * 2.2)
        for h in hops:
            dt = t - h
            if 0 <= dt < HOP_SECONDS:
                u = dt / HOP_SECONDS
                y += HOP_HEIGHT * 4 * u * (1 - u)
        return y


def attach_milo(scene, spec, envelopes, fixed_in_frame=False):
    """Create Milo, add him to `scene`, and drive him from the scene clock.

    Lip-sync follows `envelopes[step][frame]`; he hops when an equation appears
    and at the very end.  Returns the mascot (or None when disabled).
    """
    if spec.mascot != "milo":
        return None
    from kidsmath.render import timing

    starts, t = [], 0.0
    for step in spec.steps:
        starts.append(t)
        t += step.duration
    hops = [st for st, step in zip(starts, spec.steps)
            if any(a.type == "equation" for a in step.actions)]
    hops.append(starts[-1])
    milo = Milo()
    if fixed_in_frame:
        milo.fix_in_frame()
        milo.set_z_index(100)
    state = {"y": 0.0}

    def update(m, dt=0):
        now = scene.time
        openness = 0.0
        for i in range(len(starts) - 1, -1, -1):
            if now >= starts[i]:
                frame = int((now - starts[i]) * timing.FPS)
                if i < len(envelopes) and frame < len(envelopes[i]):
                    openness = envelopes[i][frame]
                break
        m.set_openness(openness)
        m.set_blink(now)
        y = m.y_offset(now, hops)
        m.shift((y - state["y"]) * UP)
        state["y"] = y

    milo.add_updater(update)
    scene.add(milo)
    return milo
