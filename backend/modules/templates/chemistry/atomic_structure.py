"""Atomic Structure template.

Visual sequence:
  1. Title appears; nucleus (protons + neutrons) drawn at center
  2. Electron shells draw outward one by one (concentric dashed circles)
  3. Electrons (dots) populate each shell, labeled with shell number
  4. Element symbol + atomic number badge appears near nucleus
  5. Electron configuration text (e.g. 1s² 2s² 2p⁶) fades in at bottom
  6. Optional: highlight valence shell with glow / label
"""
from __future__ import annotations

import math
from typing import Any

from modules.templates.chemistry._base import (
    _HEADER,
    _FOOTER,
    TITLE_COLOR,
    TEXT_COLOR,
    LABEL_COLOR,
    ACCENT1,
    ACCENT2,
    ACCENT3,
    NUCLEUS_COLOR,
    NEUTRON_COLOR,
    ELECTRON_COLOR,
    SHELL_COLOR,
    event_rt,
    event_rt_type,
    event_hold,
    asset_instance,
    _aid,
    _aparams,
    _indent,
    _esc,
)


class AtomicStructureTemplate:
    ALLOWED_EVENTS = {
        "place", "draw_nucleus", "draw_shells",
        "populate_electrons", "label_element",
        "show_config", "highlight_valence", "hold",
    }
    SLOTS = {
        "atom": ["hydrogen", "helium", "carbon", "nitrogen",
                 "oxygen", "sodium", "chlorine", "generic"],
    }
    CONTENT_SCHEMA = """{
  "title": "<scene title, e.g. 'Bohr Model of the Atom'>",
  "atom": "hydrogen|helium|carbon|nitrogen|oxygen|sodium|chlorine|generic",
  "symbol": "<element symbol, e.g. 'Na'>",
  "atomic_number": <integer>,
  "mass_number": <integer>,
  "shells": [<electrons per shell, e.g. 2, 8, 1>],
  "config": "<electron configuration string, e.g. '2, 8, 1'>",
  "highlight_valence": true
}
Use 'generic' atom if the element is not in the list. shells must be a list of integers.
"""

    # Built-in element data: (symbol, Z, mass, shell_counts, config_string)
    _ELEMENTS: dict[str, tuple[str, int, int, list[int], str]] = {
        "hydrogen":  ("H",  1,  1,  [1],           "1s\u00b9"),
        "helium":    ("He", 2,  4,  [2],           "1s\u00b2"),
        "carbon":    ("C",  6,  12, [2, 4],        "1s\u00b2 2s\u00b2 2p\u00b2"),
        "nitrogen":  ("N",  7,  14, [2, 5],        "1s\u00b2 2s\u00b2 2p\u00b3"),
        "oxygen":    ("O",  8,  16, [2, 6],        "1s\u00b2 2s\u00b2 2p\u2074"),
        "sodium":    ("Na", 11, 23, [2, 8, 1],     "1s\u00b2 2s\u00b2 2p\u2076 3s\u00b9"),
        "chlorine":  ("Cl", 17, 35, [2, 8, 7],     "1s\u00b2 2s\u00b2 2p\u2076 3s\u00b2 3p\u2075"),
        "generic":   ("X",  0,  0,  [2, 8],        "..."),
    }

    @staticmethod
    def compile(plan: dict[str, Any], timeline: dict[str, Any]) -> str:
        audio_dur = float(timeline.get("audio_duration", 12.0))
        title_text = plan.get("title", "Atomic Structure")

        # Support both legacy asset-based params and new content dict (from semantic plan)
        content = plan.get("content") or {}
        if not isinstance(content, dict):
            content = {}

        atom_asset = content.get("atom") or _aid(plan, "atom", "carbon")
        atom_params = _aparams(plan, "atom")

        # Allow overrides from content dict (preferred) or asset params
        elem_data = AtomicStructureTemplate._ELEMENTS.get(atom_asset,
                     AtomicStructureTemplate._ELEMENTS["generic"])
        symbol    = content.get("symbol")    or atom_params.get("symbol",  elem_data[0])
        atomic_z  = content.get("atomic_number") or atom_params.get("atomic_number", elem_data[1])
        mass_num  = content.get("mass_number")   or atom_params.get("mass_number",   elem_data[2])
        shells    = content.get("shells")         or atom_params.get("shells",        elem_data[3])
        config_str = content.get("config")        or atom_params.get("config",        elem_data[4])

        # Coerce types
        atomic_z = int(atomic_z) if atomic_z else elem_data[1]
        mass_num = int(mass_num) if mass_num else elem_data[2]
        if not isinstance(shells, list):
            shells = elem_data[3]

        n_protons  = atomic_z
        n_neutrons = max(0, mass_num - atomic_z)

        # Layout
        cx, cy     = 0.0, 0.1
        nucleus_r  = 0.38
        shell_gap  = 0.72   # radial gap between shells
        shell_radii = [nucleus_r + shell_gap * (i + 1) for i in range(len(shells))]

        _evs = plan.get("events", [])
        rt_place    = event_rt_type(timeline, _evs, "place",              "e0", 0.6)
        rt_nucleus  = event_rt_type(timeline, _evs, "draw_nucleus",       "e1", 0.8)
        hold_nuc    = event_hold(timeline, "e1", 0.3)
        rt_shells   = event_rt_type(timeline, _evs, "draw_shells",        "e2", 1.0)
        rt_electrons= event_rt_type(timeline, _evs, "populate_electrons", "e3", 0.9)
        hold_elec   = event_hold(timeline, "e3", 0.4)
        rt_label    = event_rt_type(timeline, _evs, "label_element",      "e4", 0.6)
        rt_config   = event_rt_type(timeline, _evs, "show_config",        "e5", 0.7)
        hold_cfg    = event_hold(timeline, "e5", 0.5)
        rt_valence  = event_rt_type(timeline, _evs, "highlight_valence",  "e6", 0.6)
        hold_val    = event_hold(timeline, "e6", 0.5)

        lines: list[str] = [_HEADER]

        # ── Title ──────────────────────────────────────────────────
        lines += [
            f'        title = Text("{_esc(title_text)}", font_size=38, weight=BOLD, color="{TITLE_COLOR}")',
            f'        title.to_edge(UP, buff=0.3)',
            "",
        ]

        # ── Nucleus ────────────────────────────────────────────────
        lines += [
            f'        # Nucleus: overlapping proton + neutron dots',
            f'        nucleus_bg = Circle(radius={nucleus_r:.2f}, color="{NUCLEUS_COLOR}",'
            f'            fill_opacity=0.18, stroke_width=2)',
            f'        nucleus_bg.move_to(np.array([{cx:.2f}, {cy:.2f}, 0]))',
            "",
        ]
        # Proton/neutron dots arranged in a tight cluster
        cluster_positions = AtomicStructureTemplate._nucleus_positions(n_protons, n_neutrons, nucleus_r * 0.7)
        for i, (px, py, is_proton) in enumerate(cluster_positions[:16]):  # cap at 16 for visual clarity
            col = NUCLEUS_COLOR if is_proton else NEUTRON_COLOR
            vname = f'p_{i}' if is_proton else f'n_{i}'
            lines += [
                f'        {vname} = Dot(radius=0.10, color="{col}", fill_opacity=0.92)',
                f'        {vname}.move_to(np.array([{cx+px:.3f}, {cy+py:.3f}, 0]))',
            ]

        proton_vars  = [f'p_{i}' for i, (_, _, isp) in enumerate(cluster_positions[:16]) if isp]
        neutron_vars = [f'n_{i}' for i, (_, _, isp) in enumerate(cluster_positions[:16]) if not isp]
        all_nuc = proton_vars + neutron_vars
        nuc_group = ", ".join(all_nuc) if all_nuc else "nucleus_bg"
        lines += [f'        nucleus_grp = VGroup(nucleus_bg, {nuc_group})', ""]

        # ── Electron Shells (dashed circles) ───────────────────────
        for i, r in enumerate(shell_radii):
            lines += [
                f'        shell_{i} = DashedVMobject(Circle(radius={r:.3f},'
                f' color="{ACCENT1}", stroke_width=1.5, stroke_opacity=0.55),'
                f' num_dashes=40)',
                f'        shell_{i}.move_to(np.array([{cx:.2f}, {cy:.2f}, 0]))',
                f'        shell_{i}.set_opacity(0)',
            ]
        lines.append("")

        # ── Electrons on shells ────────────────────────────────────
        electron_vars: list[list[str]] = []
        for si, (r, n_elec) in enumerate(zip(shell_radii, shells)):
            shell_evars: list[str] = []
            for ei in range(n_elec):
                angle = 2 * math.pi * ei / n_elec
                ex = cx + r * math.cos(angle)
                ey = cy + r * math.sin(angle)
                vname = f'e_{si}_{ei}'
                lines += [
                    f'        {vname} = Dot(radius=0.09, color="{ELECTRON_COLOR}", fill_opacity=0.95)',
                    f'        {vname}.move_to(np.array([{ex:.3f}, {ey:.3f}, 0]))',
                    f'        {vname}.set_opacity(0)',
                ]
                shell_evars.append(vname)
            electron_vars.append(shell_evars)
        lines.append("")

        # Shell number labels
        for si, r in enumerate(shell_radii):
            lx = cx + r + 0.15
            ly = cy
            lines += [
                f'        shell_lbl_{si} = Text("n={si+1}", font_size=16, color="{LABEL_COLOR}")',
                f'        shell_lbl_{si}.move_to(np.array([{lx:.3f}, {ly:.3f}, 0]))',
                f'        shell_lbl_{si}.set_opacity(0)',
            ]
        lines.append("")

        # ── Element badge ──────────────────────────────────────────
        lines += [
            f'        elem_sym = Text("{_esc(symbol)}", font_size=32, weight=BOLD, color="{ACCENT3}")',
            f'        elem_sym.move_to(np.array([{cx:.2f}, {cy:.2f}, 0]))',
            f'        elem_badge = VGroup(elem_sym)',
            f'        elem_badge.set_opacity(0)',
            "",
        ]

        # ── Electron config text ───────────────────────────────────
        lines += [
            f'        config_text = Text("{_esc(config_str)}", font_size=24, color="{ACCENT2}")',
            f'        config_text.to_edge(DOWN, buff=0.55)',
            f'        config_text.set_opacity(0)',
            "",
        ]

        # ── Valence shell highlight (outermost shell) ──────────────
        val_r = shell_radii[-1] if shell_radii else nucleus_r + shell_gap
        lines += [
            f'        valence_glow = Circle(radius={val_r:.3f}, color="{ACCENT3}",'
            f' stroke_width=3.5, stroke_opacity=0.0)',
            f'        valence_glow.move_to(np.array([{cx:.2f}, {cy:.2f}, 0]))',
            f'        valence_lbl = Text("valence shell", font_size=18, color="{ACCENT3}")',
            f'        valence_lbl.next_to(valence_glow, RIGHT, buff=0.1)',
            f'        valence_lbl.set_opacity(0)',
            "",
        ]

        # ── Animation sequence ─────────────────────────────────────
        elapsed = 0.0

        # e0: title
        lines += [
            f'        self.play(Write(title), run_time={rt_place:.3f})',
        ]
        elapsed += rt_place

        # e1: nucleus
        lines += [
            f'        self.play(FadeIn(nucleus_grp), run_time={rt_nucleus:.3f})',
        ]
        elapsed += rt_nucleus
        if hold_nuc > 0.05:
            lines += [f'        self.wait({hold_nuc:.3f})']
            elapsed += hold_nuc

        # e2: shells appear one by one
        shell_rt = rt_shells / max(len(shell_radii), 1)
        for si in range(len(shell_radii)):
            lines += [
                f'        shell_{si}.set_opacity(1)',
                f'        self.play(Create(shell_{si}), FadeIn(shell_lbl_{si}), run_time={shell_rt:.3f})',
            ]
        elapsed += rt_shells

        # e3: electrons populate
        for si, evars in enumerate(electron_vars):
            if not evars:
                continue
            ev_list = ", ".join(evars)
            lines += [
                f'        self.play({", ".join(f"FadeIn({v})" for v in evars)}, run_time={rt_electrons/max(len(electron_vars),1):.3f})',
            ]
        elapsed += rt_electrons
        if hold_elec > 0.05:
            lines += [f'        self.wait({hold_elec:.3f})']
            elapsed += hold_elec

        # e4: element badge
        lines += [
            f'        elem_badge.set_opacity(1)',
            f'        self.play(FadeIn(elem_badge, scale=0.6), run_time={rt_label:.3f})',
        ]
        elapsed += rt_label

        # e5: electron config
        lines += [
            f'        config_text.set_opacity(1)',
            f'        self.play(Write(config_text), run_time={rt_config:.3f})',
        ]
        elapsed += rt_config
        if hold_cfg > 0.05:
            lines += [f'        self.wait({hold_cfg:.3f})']
            elapsed += hold_cfg

        # e6: highlight valence shell
        lines += [
            f'        valence_glow.set_stroke(opacity=0.85)',
            f'        valence_lbl.set_opacity(1)',
            f'        self.play(',
            f'            valence_glow.animate.set_stroke(opacity=0.85),',
            f'            FadeIn(valence_lbl), run_time={rt_valence:.3f}',
            f'        )',
        ]
        elapsed += rt_valence
        if hold_val > 0.05:
            lines += [f'        self.wait({hold_val:.3f})']
            elapsed += hold_val

        tail = audio_dur - elapsed - 0.40
        if tail > 0.05:
            lines += [f'        self.wait({tail:.3f})']

        lines += ["", _FOOTER]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    @staticmethod
    def _nucleus_positions(
        n_protons: int,
        n_neutrons: int,
        max_r: float,
    ) -> list[tuple[float, float, bool]]:
        """Generate (x, y, is_proton) for nucleus particles in a spiral."""
        particles = ([True] * n_protons) + ([False] * n_neutrons)
        positions: list[tuple[float, float, bool]] = []
        if not particles:
            return positions
        step = 0.18
        angle = 0.0
        r = 0.0
        for isp in particles:
            x = r * math.cos(angle)
            y = r * math.sin(angle)
            positions.append((x, y, isp))
            r += step * 0.28
            angle += math.pi * 0.618 * 2  # golden angle
            if r > max_r:
                r = max_r * 0.35
        return positions