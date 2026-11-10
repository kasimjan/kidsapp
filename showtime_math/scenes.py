"""Word problem: Mia has 7 apples, gives away 3. How many are left? (7 - 3 = 4)

Beat sheet
  1. question: show the problem, apples pop in
  2. count:    number each apple 1..7
  3. give:     slide 3 apples to the friend, fade them
  4. stay:     count the 4 that remain
  5. answer:   write 7 - 3 = 4
"""
from st_manim import *

N, GIVE = 7, 3


def apple(color):
    body = Circle(radius=0.5, fill_color=color, fill_opacity=1, stroke_color=WHITE, stroke_width=3)
    leaf = Ellipse(width=0.3, height=0.16, fill_color=GREEN, fill_opacity=1, stroke_width=0)
    leaf.move_to(body.get_top() + UP * 0.08 + RIGHT * 0.12).rotate(0.5)
    return VGroup(body, leaf)


class Apples(ShowScene):
    def construct(self):
        self.beat("question")
        head = title("Mia's apples")
        place(head, "top")
        self.add(head)
        apples = VGroup(*[apple(RED) for _ in range(N)]).arrange(RIGHT, buff=0.35)
        place(apples, "center")
        ask = callout("7 apples. Give away 3.")
        place(ask, "bottom")
        self.play(LaggedStart(*[GrowFromCenter(a) for a in apples], lag_ratio=0.3), run_time=2.4)
        self.play(FadeIn(ask, shift=UP * 0.3), run_time=0.8)
        self.play(ask.animate.scale(1.15), apples.animate.scale(1.06), run_time=3.0)

        self.beat("counting")
        self.play(apples.animate.scale(1 / 1.06), run_time=1.2)
        nums = VGroup(*[label(str(i + 1)).scale(1.8).next_to(a, DOWN, buff=0.25) for i, a in enumerate(apples)])
        for i, w in enumerate(["one", "two", "three", "four", "five", "six", "seven"]):
            self.at(w)
            self.play(Indicate(apples[i], scale_factor=1.3), FadeIn(nums[i]), run_time=0.25)

        self.beat("give")
        given, kept = apples[N - GIVE:], apples[:N - GIVE]
        friend = callout("Her friend")
        friend.next_to(given.copy().shift(UP * 1.2 + RIGHT * 0.5), DOWN, buff=0.3)
        self.play(FadeOut(nums), *[a[0].animate.set_fill(T.hue(2)) for a in given], FadeIn(friend), run_time=0.7)
        self.play(given.animate.shift(UP * 1.2 + RIGHT * 0.5), run_time=1.3)
        for w, a in zip(["one", "two", "three#2"], given):
            self.at(w)
            self.play(Indicate(a, scale_factor=1.3), run_time=0.25)
        self.play(given.animate.set_opacity(0.3), run_time=0.5)

        self.beat("keep")
        self.play(kept.animate.move_to(ORIGIN + DOWN * 0.3), run_time=1.2)
        k = VGroup(*[label(str(i + 1)).scale(1.8).next_to(a, DOWN, buff=0.25) for i, a in enumerate(kept)])
        for i, w in enumerate(["one", "two", "three", "four"]):
            self.at(w)
            self.play(Indicate(kept[i], scale_factor=1.3), FadeIn(k[i]), run_time=0.25)
        self.play(kept.animate.scale(1.1), FadeOut(ask), FadeOut(friend), run_time=0.8)

        self.beat("answer")
        a7, minus, a3, eq_, a4 = (title(t) for t in ["7", "-", "3", "=", "4"])
        sum_ = VGroup(a7, minus, a3, eq_, a4).arrange(RIGHT, buff=0.4)
        place(sum_, "bottom")
        a4.set_color(T.emph)
        self.at("seven")
        self.play(FadeIn(VGroup(a7, minus, a3), shift=UP * 0.3), run_time=0.6)
        self.at("four")
        self.play(FadeIn(VGroup(eq_, a4), shift=UP * 0.3), run_time=0.4)
        self.at("four#2")
        self.play(*[Indicate(a, scale_factor=1.25) for a in kept], run_time=1.5)
        self.play(sum_.animate.scale(1.2), run_time=2.5)
        self.hold(0.5)
