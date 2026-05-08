"""
gui/theme.py
============
Design system for 8by8 AI CHESS LAB.

Tokens derived directly from design.md:
  Colors  — warm monochromatic palette (light parchment / near-black)
  Type    — DM Sans (UI) + DM Mono (technical/data)
  Radius  — --r-sm 6px / --r 10px / --r-lg 18px
  Shadow  — two-level system
  Motion  — .2s / .4s cubic-bezier(.4,0,.2,1)
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Tokens:
    bg: str; bg2: str; surface: str; surface2: str
    border: str; border2: str
    ink: str; ink2: str; ink3: str; ink4: str
    accent: str; accent_fg: str
    sq_light: str; sq_dark: str
    hl_select: str; hl_move: str; hl_last: str; hl_check: str
    success: str; warning: str; danger: str


DARK = Tokens(
    bg="#0f0e0c", bg2="#171613", surface="#1a1916", surface2="#221f1b",
    border="#2a2822", border2="#3a3830",
    ink="#f0ede6", ink2="#c6c0b4", ink3="#7a7468", ink4="#4a4840",
    accent="#f0ede6", accent_fg="#0f0e0c",
    sq_light="#c9b99a", sq_dark="#6b5040",
    hl_select="rgba(210,165,70,0.52)", hl_move="rgba(210,165,70,0.36)",
    hl_last="rgba(210,165,70,0.28)", hl_check="rgba(185,55,55,0.55)",
    success="#4a8c6a", warning="#b07a30", danger="#a04040",
)

LIGHT = Tokens(
    bg="#f4f3ef", bg2="#eceae4", surface="#ffffff", surface2="#f0ede8",
    border="#e0dbd2", border2="#c8c2b6",
    ink="#0e0d0b", ink2="#2e2c25", ink3="#6b6760", ink4="#9e9990",
    accent="#0e0d0b", accent_fg="#f4f3ef",
    sq_light="#f0e4cc", sq_dark="#9a7a5c",
    hl_select="rgba(140,95,10,0.42)", hl_move="rgba(140,95,10,0.30)",
    hl_last="rgba(140,95,10,0.22)", hl_check="rgba(180,40,40,0.38)",
    success="#166534", warning="#92400e", danger="#991b1b",
)


class Theme:
    _tokens: Tokens = DARK
    _dark: bool = True

    @classmethod
    def current(cls) -> Tokens:
        return cls._tokens

    @classmethod
    def is_dark(cls) -> bool:
        return cls._dark

    @classmethod
    def set_dark(cls) -> None:
        cls._tokens = DARK; cls._dark = True

    @classmethod
    def set_light(cls) -> None:
        cls._tokens = LIGHT; cls._dark = False

    @classmethod
    def toggle(cls) -> None:
        cls.set_light() if cls._dark else cls.set_dark()

    @classmethod
    def stylesheet(cls) -> str:
        t = cls._tokens
        return f"""
* {{ outline: none; }}
QMainWindow, QWidget {{
    background-color: {t.bg};
    color: {t.ink};
    font-family: "DM Sans","Segoe UI","Inter",system-ui,sans-serif;
    font-size: 13px;
}}
QFrame {{ background-color: transparent; border: none; }}
QFrame#panel {{
    background-color: {t.surface};
    border: 1px solid {t.border};
    border-radius: 10px;
}}
QFrame#toolbar {{
    background-color: {t.bg};
    border-bottom: 1px solid {t.border};
    border-radius: 0px;
}}
QLabel {{ background: transparent; border: none; color: {t.ink}; }}
QPushButton {{
    background-color: {t.surface};
    color: {t.ink2};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 6px 14px;
    font-family: "DM Sans","Segoe UI",system-ui,sans-serif;
    font-size: 12px;
    font-weight: 500;
    min-height: 30px;
}}
QPushButton:hover {{
    background-color: {t.surface2};
    border-color: {t.border2};
    color: {t.ink};
}}
QPushButton:pressed {{ background-color: {t.border}; }}
QPushButton#accent {{
    background-color: {t.accent};
    color: {t.accent_fg};
    border: none;
    font-weight: 600;
    padding: 6px 18px;
}}
QPushButton#accent:hover {{ background-color: {t.ink2}; }}
QPushButton#accent:pressed {{ background-color: {t.ink}; }}
QComboBox {{
    background-color: {t.surface};
    color: {t.ink2};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
    font-weight: 500;
    min-height: 30px;
    min-width: 110px;
}}
QComboBox:hover {{ border-color: {t.border2}; color: {t.ink}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background-color: {t.surface};
    border: 1px solid {t.border2};
    border-radius: 6px;
    color: {t.ink};
    selection-background-color: {t.surface2};
    selection-color: {t.ink};
    padding: 4px;
    outline: none;
}}
QListWidget {{
    background-color: transparent;
    border: none;
    color: {t.ink};
    outline: none;
    font-family: "DM Mono","JetBrains Mono","Consolas",monospace;
    font-size: 12px;
}}
QListWidget::item {{
    padding: 5px 12px;
    color: {t.ink2};
    border-bottom: 1px solid {t.border};
}}
QListWidget::item:selected {{ background-color: {t.surface2}; color: {t.ink}; }}
QListWidget::item:hover {{ background-color: {t.surface2}; }}
QScrollBar:vertical {{
    background: transparent; width: 4px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {t.border2}; border-radius: 2px; min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0; background: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QSplitter::handle {{ background-color: {t.border}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}
QToolTip {{
    background-color: {t.surface};
    color: {t.ink2};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
}}
QDialog {{
    background-color: {t.bg};
    border: 1px solid {t.border};
    border-radius: 18px;
}}
QTabWidget::pane {{ border: none; border-top: 1px solid {t.border}; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background: transparent;
    color: {t.ink4};
    padding: 8px 16px;
    font-size: 11px;
    font-weight: 500;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 2px;
    font-family: "DM Mono","Consolas",monospace;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
QTabBar::tab:selected {{ color: {t.ink}; border-bottom: 2px solid {t.ink}; }}
QTabBar::tab:hover:!selected {{ color: {t.ink2}; }}
QCheckBox {{
    color: {t.ink2}; background: transparent; spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    background-color: {t.surface};
    border: 1px solid {t.border2};
    border-radius: 4px;
}}
QCheckBox::indicator:checked {{ background-color: {t.accent}; border-color: {t.accent}; }}
"""


# Typography constants  (design.md §3)
FONT_UI   = '"DM Sans","Segoe UI","Inter",system-ui,sans-serif'
FONT_MONO = '"DM Mono","JetBrains Mono","Consolas",monospace'

# Border radii  (design.md §4)
R_SM = 6
R    = 10
R_LG = 18
