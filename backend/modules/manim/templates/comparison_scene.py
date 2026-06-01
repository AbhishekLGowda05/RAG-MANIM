# modules/manim/templates/comparison_scene.py

from manim import *
from ..style_config import *


class ComparisonScene(Scene):

    def build_scene(
        self,
        left_title: str,
        left_content: str,
        right_title: str,
        right_content: str,
        audio_duration: float = 0.0,
    ):
        self.camera.background_color = SLATE_BG

        left_box = RoundedRectangle(
            width=5.2,
            height=4.2,
            corner_radius=0.25,
            stroke_color=CHALK_BLUE,
            stroke_width=2,
            fill_color=CARD_BG,
            fill_opacity=0.9,
        ).shift(LEFT * 3.2)

        right_box = RoundedRectangle(
            width=5.2,
            height=4.2,
            corner_radius=0.25,
            stroke_color=CHALK_GREEN,
            stroke_width=2,
            fill_color=CARD_BG,
            fill_opacity=0.9,
        ).shift(RIGHT * 3.2)

        left_header = Text(
            str(left_title)[:40],
            font=TITLE_FONT,
            font_size=26,
            color=CHALK_BLUE,
            weight=BOLD,
        ).move_to(left_box.get_top() + DOWN * 0.55)

        right_header = Text(
            str(right_title)[:40],
            font=TITLE_FONT,
            font_size=26,
            color=CHALK_GREEN,
            weight=BOLD,
        ).move_to(right_box.get_top() + DOWN * 0.55)

        left_text = Text(
            str(left_content)[:200],
            font=BODY_FONT,
            font_size=18,
            color=CHALK_WHITE,
            line_spacing=1.3,
        ).move_to(left_box.get_center() + DOWN * 0.2)

        right_text = Text(
            str(right_content)[:200],
            font=BODY_FONT,
            font_size=18,
            color=CHALK_WHITE,
            line_spacing=1.3,
        ).move_to(right_box.get_center() + DOWN * 0.2)

        self.play(Create(left_box), Create(right_box), run_time=0.8)
        self.play(FadeIn(left_header), FadeIn(right_header), run_time=0.6)
        self.play(FadeIn(left_text), FadeIn(right_text), run_time=0.7)

        tail = max(0.5, audio_duration - 2.5) if audio_duration > 0 else 1.5
        self.wait(tail)
