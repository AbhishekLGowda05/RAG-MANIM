# modules/manim/templates/diagram_scene.py

from manim import *
import numpy as np
from ..style_config import *


class DiagramScene(Scene):

    def _normalize_nodes(self, nodes: list) -> list[str]:
        labels: list[str] = []
        for node in nodes:
            if isinstance(node, dict):
                labels.append(str(node.get("label", node.get("name", "?"))))
            else:
                labels.append(str(node))
        return labels[:8] if labels else ["A", "B", "C"]

    def build_scene(
        self,
        title_text: str,
        nodes: list,
        audio_duration: float = 0.0,
    ):
        self.camera.background_color = SLATE_BG
        labels = self._normalize_nodes(nodes)

        title = Text(
            str(title_text)[:60],
            font=TITLE_FONT,
            font_size=36,
            color=CHALK_WHITE,
            weight=BOLD,
        ).to_edge(UP, buff=0.4)
        self.play(Write(title), run_time=0.8)

        n = len(labels)
        if n <= 4:
            positions = [
                np.array([x, -0.3, 0])
                for x in np.linspace(-4.5, 4.5, n)
            ]
        else:
            cols = min(4, n)
            rows = (n + cols - 1) // cols
            positions = []
            for i in range(n):
                row, col = divmod(i, cols)
                positions.append(
                    np.array([
                        -4.5 + col * (9.0 / max(cols - 1, 1)),
                        1.0 - row * 1.8,
                        0,
                    ])
                )

        objects = []
        for label, pos in zip(labels, positions):
            circle = Circle(radius=0.55, color=CHALK_BLUE, stroke_width=2)
            circle.set_fill(CHALK_BLUE, opacity=0.15)
            label_mob = Text(
                str(label)[:24],
                font=BODY_FONT,
                font_size=18,
                color=CHALK_WHITE,
            )
            group = VGroup(circle, label_mob)
            group.move_to(pos)
            objects.append(group)

        graph = VGroup(*objects)
        self.play(
            LaggedStart(*[FadeIn(o, scale=0.8) for o in graph], lag_ratio=0.25),
            run_time=min(2.5, 0.4 * n + 0.5),
        )

        if len(objects) >= 2:
            arrows = VGroup(*[
                Arrow(
                    objects[i].get_right(),
                    objects[i + 1].get_left(),
                    color=CHALK_YELLOW,
                    stroke_width=2,
                    buff=0.15,
                    max_tip_length_to_length_ratio=0.2,
                )
                for i in range(len(objects) - 1)
            ])
            self.play(
                LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.2),
                run_time=0.8,
            )

        tail = max(0.5, audio_duration - 3.0) if audio_duration > 0 else 1.5
        self.wait(tail)
