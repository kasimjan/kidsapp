"""Kid-friendly 3D addition lesson for original 3Blue1Brown ManimGL.

Render: manimgl addition_3d.py Addition3D -w
Designed for ManimGL 1.7.x (not Manim Community Edition).
"""
from manimlib import *


class Addition3D(ThreeDScene):
    def construct(self):
        # Keep captions in screen coordinates while the 3D camera moves.
        self.frame.reorient(-18, 68)
        title = Text("Let's Add!", font_size=58, color=YELLOW)
        title.to_edge(UP, buff=0.4)
        title.fix_in_frame()
        self.add(title)

        instruction = Text("First, we have 3 red balls", font_size=35)
        instruction.next_to(title, DOWN, buff=0.45)
        instruction.fix_in_frame()
        self.play(FadeIn(instruction), run_time=0.8)

        # Sphere is genuine 3D geometry; specular shading adds depth.
        red_positions = [-3.8, -2.3, -0.8]
        yellow_positions = [1.5, 3.0]
        reds = Group(*[
            Sphere(radius=0.53, color=RED).move_to([x, -0.3, 0])
            for x in red_positions
        ])
        yellows = Group(*[
            Sphere(radius=0.53, color=YELLOW).move_to([x, -0.3, 0])
            for x in yellow_positions
        ])

        for ball in reds:
            ball.shift(1.4 * OUT)
            self.play(FadeIn(ball, shift=1.4 * IN), run_time=0.7)
        self.wait(0.5)

        second = Text("Now add 2 yellow balls!", font_size=35)
        second.move_to(instruction)
        second.fix_in_frame()
        self.play(FadeTransform(instruction, second), run_time=0.7)
        for ball in yellows:
            ball.shift(1.4 * OUT)
            self.play(FadeIn(ball, shift=1.4 * IN), run_time=0.8)
        self.wait(0.5)

        counting = Text("Let's count them all!", font_size=35)
        counting.move_to(second)
        counting.fix_in_frame()
        self.play(FadeTransform(second, counting), run_time=0.7)

        # Camera movement emphasizes the 3D nature of the objects.
        self.play(self.frame.animate.increment_theta(12 * DEG), run_time=1.6)
        for index, ball in enumerate([*reds, *yellows], start=1):
            number = Text(str(index), font_size=46, color=WHITE)
            number.fix_in_frame()
            number.move_to([0, -2.35, 0])
            self.play(ball.animate.scale(1.18), FadeIn(number), run_time=0.32)
            self.play(ball.animate.scale(1 / 1.18), FadeOut(number), run_time=0.32)

        self.play(FadeOut(counting), run_time=0.5)
        equation = Text("3 + 2 = 5", font_size=82, color=YELLOW)
        equation.move_to([0, -2.5, 0])
        equation.fix_in_frame()
        self.play(Write(equation), run_time=2)
        self.wait(1.5)

        celebration = Text("Great job!", font_size=46, color=GREEN)
        celebration.next_to(title, DOWN, buff=0.45)
        celebration.fix_in_frame()
        self.play(FadeIn(celebration, scale=1.3), run_time=1)
        self.wait(2)
