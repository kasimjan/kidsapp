"""3D ManimGL scene that interprets a LessonSpec (original code, ManimGL 1.7.x).

Run it through `kidsmath.render.pipeline.render_lesson(..., style="3d")`.
The spec is re-validated here; it can only trigger the fixed actions below.
Supported: title, text, objects, count_item, merge, cross_out, equation, sign,
clear.  (shape and blocks lessons are 2D only for now.)
"""
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
from manimlib import *  # noqa: F401,F403

from kidsmath import spec as S
from kidsmath.render import timing
from kidsmath.render.mascot import attach_milo
from kidsmath.render3d import director, layout3d
from kidsmath.render3d.kit import (
    BACKGROUND, COLORS, INK, Badge, Subtitle, Token, arc_move, drop_in, hop, hud, label,
    make_stage, sparkles, spotlight_ring,
)
from kidsmath.narration import synthetic_envelope
from kidsmath.validate import validate_spec

EPS = 1e-3

class Lesson3DScene(ThreeDScene):
    samples = 4

    def get_spec(self):
        """The lesson to play. Subclasses may return a spec built in code."""
        return validate_spec(S.LessonSpec.model_validate_json(Path(os.environ["KIDSMATH_SPEC"]).read_text()))

    def construct(self):
        spec = self.get_spec()
        self.load_sidecar(spec)
        self.build_world(spec)

        starts = director.step_starts(spec)
        for i, step in enumerate(spec.steps):
            self.set_subtitle(step, i, starts[i])
            used = 0.0
            first = True
            for action in step.actions:
                t = timing.action_time(action)
                self.run_action(action, t, extra=self._pending_subtitle_fade() if first else [])
                first = False
                used += t
            rest = step.duration - used
            if rest > EPS:
                self.wait(rest - EPS)
        self.wait(timing.FINAL_HOLD - EPS)

    # ---------------------------------------------------------------- setup
    def load_sidecar(self, spec):
        self.audio_seconds = [timing.estimate_audio_seconds(s.narration) for s in spec.steps]
        self.envelopes = [synthetic_envelope(a, timing.FPS) for a in self.audio_seconds]
        path = os.environ.get("KIDSMATH_SIDECAR")
        if path and Path(path).exists():
            data = json.loads(Path(path).read_text())
            self.envelopes, self.audio_seconds = data["envelope"], data["audio_seconds"]

    def build_world(self, spec):
        self.camera.background_rgba = list(color_to_rgba(BACKGROUND, 1.0))
        self.camera.light_source.move_to([-9, 7, 14])
        self.stage = make_stage()
        self.add(self.stage)
        self.groups = {}       # name -> list[Token]
        self.alive = {}        # name -> tokens not yet taken away
        self.live = []         # mobjects `clear` should remove
        self.badges = []
        self.ring = None
        self.confetti = None
        self.caption = {}
        self.title_mob = self.equation_mob = self.sign_mob = None
        self.subtitle = None
        self.pending_subtitle = None

        track = director.build_track(spec)
        frame = self.frame

        def move_camera(f, dt=0):
            v = director.view_at(track, self.time)
            f.reorient(v.theta + director.sway(self.time), v.phi, 0, (v.cx, v.cy, v.cz), v.height)

        frame.add_updater(move_camera)
        move_camera(frame)
        self.milo = attach_milo(self, spec, self.envelopes, fixed_in_frame=True)

    # ------------------------------------------------------------ subtitles
    def set_subtitle(self, step, index, start):
        if self.subtitle is not None:
            self.remove(self.subtitle)
        self.subtitle = Subtitle(step.narration, self.audio_seconds[index], start,
                                 lambda: self.time, duration=step.duration)
        self.add(self.subtitle)

    def _pending_subtitle_fade(self):
        return []

    # --------------------------------------------------------------- actions
    def run_action(self, a, t, extra=()):
        anims = getattr(self, "_do_" + a.type)(a, t)
        anims = [*extra, *anims]
        if anims:
            self.play(*anims, run_time=t - EPS)
        else:
            self.wait(t - EPS)

    def _lead_out(self):
        out = []
        if self.title_mob is not None:
            out.append(FadeOut(self.title_mob))
            self.title_mob = None
        return out

    def _track(self, mob):
        self.live.append(mob)
        return mob

    def _do_title(self, a, t):
        self.title_mob = hud(label(a.text, 96, COLORS["purple"]).move_to([0, 1.2, 0]))
        return [FadeIn(self.title_mob, scale=0.7)]

    def _do_text(self, a, t):
        anims = self._lead_out()
        old = self.caption.get(a.region)
        if old is not None and a.replace:
            anims.append(FadeOut(old))
        y = 3.1 if a.region == "top" else -2.2
        mob = hud(label(a.text, 72, COLORS[a.color]).move_to([0, y, 0]))
        self.caption[a.region] = mob
        self._track(mob)
        anims.append(FadeIn(mob, shift=0.2 * UP))
        return anims

    def _do_objects(self, a, t):
        anims = self._lead_out()
        pts = layout3d.group_positions(a.count, a.position)
        tokens = [Token(a.shape, a.color, p) for p in pts]
        for tok in tokens:
            tok.body.set_opacity(0)
            self.add(tok)
        self.groups[a.group] = tokens
        self.alive[a.group] = list(tokens)
        self.live.extend(tokens)
        anims.append(LaggedStart(*[drop_in(tok) for tok in tokens], lag_ratio=0.25))
        return anims

    def _do_count_item(self, a, t):
        tok = self.groups[a.group][a.index - 1]
        number = a.number or a.index
        badge = Badge(str(number), tok.color_name, tok.ground_position, self.frame)
        self.badges.append(badge)
        self._track(badge)
        anims = [hop(tok.body, 0.5), FadeIn(badge, shift=0.25 * DOWN, scale=0.6)]
        ring = spotlight_ring(tok)
        if self.ring is not None:
            anims.append(FadeOut(self.ring))
            self.live.remove(self.ring) if self.ring in self.live else None
        self.ring = self._track(ring)
        anims.append(FadeIn(ring, scale=0.5))
        return anims

    def _do_merge(self, a, t):
        target, source = self.groups[a.target], self.groups[a.source]
        pts = layout3d.merged_positions(len(target) + len(source))
        anims = []
        for tok, (x, y) in zip(target + source, pts):
            anims.append(arc_move(tok.body, [x, y, tok.rest_z], lift=0.7))
        return anims

    def _do_cross_out(self, a, t):
        victims = self.alive[a.group][-a.count:]
        self.alive[a.group] = self.alive[a.group][:-a.count]
        anims = []
        for tok in victims:
            tok.shadow.clear_updaters()
            anims += [FadeOut(tok.body, shift=2.2 * OUT, scale=0.4), FadeOut(tok.shadow)]
            self.live.remove(tok) if tok in self.live else None
        return [LaggedStart(*anims, lag_ratio=0.12)]

    def _do_equation(self, a, t):
        anims = self._lead_out()
        if self.equation_mob is not None:
            anims.append(FadeOut(self.equation_mob))
        self.equation_mob = self._track(hud(label(a.text, 88, COLORS[a.color]).move_to([0, -2.15, 0])))
        anims.append(Write(self.equation_mob))
        if self.ring is not None:
            anims.append(FadeOut(self.ring))
            self.ring = None
        if self.confetti is None:
            self.confetti = self._track(sparkles(np.array([0.0, 0.0, 0.0])))
            for d in self.confetti:
                d.set_opacity(0)
            self.add(self.confetti)
            anims.append(LaggedStart(*[
                AnimationGroup(d.animate.set_opacity(1).shift(0.9 * OUT)) for d in self.confetti], lag_ratio=0.03))
        return anims

    def _do_sign(self, a, t):
        self.sign_mob = self._track(hud(label(a.sign, 150, COLORS["purple"]).move_to([0, 1.9, 0])))
        return self._lead_out() + [FadeIn(self.sign_mob, scale=0.3)]

    def _do_clear(self, a, t):
        anims = [FadeOut(m) for m in self.live]
        self.live, self.groups, self.alive, self.caption = [], {}, {}, {}
        self.badges, self.ring, self.confetti = [], None, None
        self.title_mob = self.equation_mob = self.sign_mob = None
        return anims

    def _do_shape(self, a, t):  # pragma: no cover - rejected before rendering
        raise NotImplementedError("shape lessons are 2D only")

    _do_blocks = _do_shape
