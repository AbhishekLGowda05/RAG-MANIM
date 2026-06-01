# modules/manim/templates/equation_scene.py

from manim import *
from ..style_config import *


class EquationScene(Scene):

    def build_scene(
        self,
        title_text: str,
        equation_text: str,
        explanation: str = "",
        audio_duration: float = 0.0,
    ):
        self.camera.background_color = SLATE_BG

        title = Text(
            str(title_text)[:60],
            font=TITLE_FONT,
            font_size=38,
            color=CHALK_WHITE,
            weight=BOLD,
        ).to_edge(UP, buff=0.4)

        eq_str = str(equation_text).strip() or r"E = mc^2"
        try:
            equation = MathTex(eq_str, color=CHALK_YELLOW).scale(1.4)
        except Exception:
            equation = Text(eq_str, font=MONO_FONT, font_size=36, color=CHALK_YELLOW)

        explanation_text = Text(
            str(explanation)[:180] if explanation else "",
            font=BODY_FONT,
            font_size=22,
            color=CHALK_WHITE,
            line_spacing=1.3,
        ).next_to(equation, DOWN, buff=0.6)

        self.play(Write(title), run_time=0.8)
        self.play(Write(equation), run_time=1.0)
        if explanation:
            self.play(FadeIn(explanation_text), run_time=0.7)

        tail = max(0.5, audio_duration - 3.0) if audio_duration > 0 else 1.5
        self.wait(tail)
