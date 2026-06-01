from modules.manim.templates.chalkboard_scene import ChalkboardScene
from modules.manim.templates.concept_card import ConceptCardScene


class ChalkboardTemplate:
    @staticmethod
    def compile(plan, timeline):
        return f"""
from manim import *
from modules.manim.templates.chalkboard_scene import ChalkboardScene

class GeneratedScene(ChalkboardScene):
    def construct(self):
        self.build_anatomy_scene([], [])
"""


class ConceptCardTemplate:
    @staticmethod
    def compile(plan, timeline):
        return f"""
from manim import *
from modules.manim.templates.concept_card import ConceptCardScene

class GeneratedScene(ConceptCardScene):
    def construct(self):
        self.build_scene(
            main_title={repr(plan.get("concept","Concept"))},
            cards=[]
        )
"""


TEMPLATES = {
    "chalkboard": ChalkboardTemplate,
    "concept_card": ConceptCardTemplate,
}