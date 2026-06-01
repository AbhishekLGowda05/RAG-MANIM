# modules/manim/templates/chalkboard_scene.py
from manim import *
from ..style_config import *

class ChalkboardScene(Scene):
    """
    Template: Chalk-on-blackboard sketch style
    For anatomical breakdowns, structural diagrams, labeled illustrations
    """
    
    def chalk_stroke(self, mobject, color=CHALK_WHITE):
        """Make any shape look like chalk — slightly rough, high contrast"""
        mobject.set_stroke(color=color, width=2.5, opacity=0.9)
        mobject.set_fill(opacity=0)
        return mobject
    
    def draw_label_arrow(self, label_text, target_point, 
                          label_position, color=CHALK_WHITE):
        label = Text(label_text, font=MONO_FONT, 
                     font_size=20, color=color)
        label.move_to(label_position)
        
        arrow = Line(
            label.get_edge_center(DOWN),
            target_point,
            color=color,
            stroke_width=1.5
        )
        tip = ArrowTip(color=color).scale(0.5)
        tip.move_to(target_point)
        tip.rotate(arrow.get_angle() + PI)
        
        return VGroup(label, arrow, tip)
    
    def build_anatomy_scene(self, shapes: list, labels: list):
        """
        shapes = [{"type": "rectangle", "pos": [...], 
                   "size": [...], "color": "white", "label": "RECT-A"}]
        """
        # Dark slate background — NOT pure black
        self.camera.background_color = "#1C1C1E"
        
        # Draw outer reference frame first
        frame = self.chalk_stroke(
            Rectangle(width=11, height=6.5),
            color="#4A6080"  # muted blue grid lines
        )
        self.play(Create(frame), run_time=0.8)
        
        # Draw structural shapes
        for shape_data in shapes:
            shape = self.chalk_stroke(
                self.create_shape(shape_data),
                color=shape_data.get("color", CHALK_WHITE)
            )
            label = self.draw_label_arrow(
                shape_data["label"],
                shape.get_center(),
                shape.get_top() + UP * 0.4
            )
            self.play(
                Create(shape),
                run_time=shape_data.get("draw_time", 0.8)
            )
            self.play(FadeIn(label), run_time=0.4)
