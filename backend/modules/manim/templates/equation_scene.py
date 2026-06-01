# modules/manim/templates/equation_scene.py

from manim import *
from ..style_config import *

class EquationScene(Scene):

    def build_scene(
        self,
        title_text: str,
        equation_text: str,
        explanation: str = ""
    ):

        self.camera.background_color = "#1C1C1E"

        title = Text(
            title_text,
            font_size=40,
            color=WHITE
        ).to_edge(UP)

        equation = MathTex(
            equation_text,
            color=YELLOW
        ).scale(1.5)

        explanation_text = Text(
            explanation,
            font_size=24,
            color=WHITE
        ).next_to(equation, DOWN, buff=0.5)

        self.play(Write(title))
        self.play(Write(equation))
        self.play(FadeIn(explanation_text))

        self.wait(2)