# modules/manim/templates/diagram_scene.py

from manim import *
from ..style_config import *

class DiagramScene(Scene):

    def build_scene(
        self,
        title_text: str,
        nodes: list
    ):

        self.camera.background_color = "#1C1C1E"

        title = Text(
            title_text,
            font_size=38,
            color=WHITE
        ).to_edge(UP)

        self.play(Write(title))

        objects = []

        for node in nodes:

            circle = Circle(
                radius=0.6,
                color=BLUE
            )

            label = Text(
                node["label"],
                font_size=20
            )

            group = VGroup(circle, label)

            group.move_to(node["position"])

            objects.append(group)

        graph = VGroup(*objects)

        self.play(
            LaggedStart(
                *[Create(o) for o in graph],
                lag_ratio=0.2
            )
        )

        self.wait(2)