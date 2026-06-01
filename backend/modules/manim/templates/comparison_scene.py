# modules/manim/templates/comparison_scene.py

from manim import *
from ..style_config import *

class ComparisonScene(Scene):

    def build_scene(
        self,
        left_title,
        left_content,
        right_title,
        right_content
    ):

        self.camera.background_color = "#1C1C1E"

        left_box = RoundedRectangle(
            width=5,
            height=4,
            color=BLUE
        ).shift(LEFT*3)

        right_box = RoundedRectangle(
            width=5,
            height=4,
            color=GREEN
        ).shift(RIGHT*3)

        left_header = Text(
            left_title,
            font_size=28
        ).move_to(left_box.get_top()+DOWN*0.5)

        right_header = Text(
            right_title,
            font_size=28
        ).move_to(right_box.get_top()+DOWN*0.5)

        left_text = Text(
            left_content,
            font_size=20
        ).move_to(left_box.get_center())

        right_text = Text(
            right_content,
            font_size=20
        ).move_to(right_box.get_center())

        self.play(Create(left_box))
        self.play(Create(right_box))

        self.play(
            FadeIn(left_header),
            FadeIn(right_header)
        )

        self.play(
            FadeIn(left_text),
            FadeIn(right_text)
        )

        self.wait(2)