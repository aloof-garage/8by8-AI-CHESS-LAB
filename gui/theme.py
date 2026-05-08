"""
gui/theme.py
============
Color system and theme management for 8by8 AI CHESS LAB GUI.

Supports Dark Mode and Light Mode with a consistent design language:
  - Minimal, modern, premium aesthetic
  - Carefully tuned color palette
  - Typography scale
  - Spacing and sizing constants
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ColorPalette:
    # Window / background layers
    bg_darkest:     str    # deepest background
    bg_dark:        str    # panel backgrounds
    bg_medium:      str    # card / widget backgrounds
    bg_light:       str    # hover states / borders
    bg_highlight:   str    # selected / active states

    # Text
    text_primary:   str
    text_secondary: str
    text_muted:     str
    text_inverse:   str

    # Accent
    accent:         str    # primary accent (blue)
    accent_hover:   str
    accent_dim:     str

    # Status colors
    success:        str
    warning:        str
    danger:         str
    info:           str

    # Board squares
    board_light:    str
    board_dark:     str
    board_border:   str

    # Board highlights
    hl_selected:    str    # selected piece
    hl_legal:       str    # legal move dot
    hl_last_from:   str    # last move source
    hl_last_to:     str    # last move destination
    hl_check:       str    # king in check

    # Piece colors (for drawn pieces)
    piece_white:    str
    piece_black:    str
    piece_outline:  str

    # Evaluation bar
    eval_white:     str
    eval_black:     str

    # Panel separator
    separator:      str


DARK_THEME = ColorPalette(
    bg_darkest   = "#0f1117",
    bg_dark      = "#161b27",
    bg_medium    = "#1e2535",
    bg_light     = "#2a3348",
    bg_highlight = "#323d54",

    text_primary   = "#e8eaf0",
    text_secondary = "#9ba5b8",
    text_muted     = "#5c6882",
    text_inverse   = "#0f1117",

    accent       = "#4f8ef7",
    accent_hover = "#6fa3ff",
    accent_dim   = "#1e3a6a",

    success = "#4caf87",
    warning = "#f0a040",
    danger  = "#e05050",
    info    = "#6ab0e8",

    board_light  = "#d4b896",
    board_dark   = "#8b6347",
    board_border = "#2a3348",

    hl_selected  = "#4f8ef780",
    hl_legal     = "#4f8ef750",
    hl_last_from = "#ffe17740",
    hl_last_to   = "#ffe17760",
    hl_check     = "#e0505080",

    piece_white  = "#f0ece4",
    piece_black  = "#2c2c2c",
    piece_outline= "#1a1a1a",

    eval_white = "#e8eaf0",
    eval_black = "#2c2c2c",

    separator = "#2a3348",
)

LIGHT_THEME = ColorPalette(
    bg_darkest   = "#e8eaed",
    bg_dark      = "#f0f2f5",
    bg_medium    = "#ffffff",
    bg_light     = "#dce0e8",
    bg_highlight = "#c8d0de",

    text_primary   = "#1a1d24",
    text_secondary = "#4a5568",
    text_muted     = "#8896a8",
    text_inverse   = "#ffffff",

    accent       = "#2563eb",
    accent_hover = "#1d4ed8",
    accent_dim   = "#dbeafe",

    success = "#16a34a",
    warning = "#d97706",
    danger  = "#dc2626",
    info    = "#0284c7",

    board_light  = "#f0d9b5",
    board_dark   = "#b58863",
    board_border = "#c0c8d4",

    hl_selected  = "#2563eb80",
    hl_legal     = "#2563eb50",
    hl_last_from = "#f6f66940",
    hl_last_to   = "#f6f66970",
    hl_check     = "#dc262660",

    piece_white  = "#fafafa",
    piece_black  = "#1a1a1a",
    piece_outline= "#333333",

    eval_white = "#fafafa",
    eval_black = "#1a1a1a",

    separator = "#dce0e8",
)


class Theme:
    """Global theme manager."""

    _current: ColorPalette = DARK_THEME
    _is_dark:  bool        = True

    @classmethod
    def current(cls) -> ColorPalette:
        return cls._current

    @classmethod
    def is_dark(cls) -> bool:
        return cls._is_dark

    @classmethod
    def set_dark(cls) -> None:
        cls._current = DARK_THEME
        cls._is_dark = True

    @classmethod
    def set_light(cls) -> None:
        cls._current = LIGHT_THEME
        cls._is_dark = False

    @classmethod
    def toggle(cls) -> None:
        if cls._is_dark:
            cls.set_light()
        else:
            cls.set_dark()

    @classmethod
    def stylesheet(cls) -> str:
        """Generate a global QSS stylesheet."""
        c = cls._current
        return f"""
QMainWindow, QWidget {{
    background-color: {c.bg_darkest};
    color: {c.text_primary};
    font-family: "Segoe UI", "Inter", "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}

QFrame {{
    background-color: {c.bg_dark};
    border: none;
    border-radius: 8px;
}}

QLabel {{
    background: transparent;
    color: {c.text_primary};
}}

QLabel#subtitle, QLabel#muted {{
    color: {c.text_secondary};
    font-size: 11px;
}}

QPushButton {{
    background-color: {c.bg_medium};
    color: {c.text_primary};
    border: 1px solid {c.bg_light};
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
    font-size: 12px;
}}

QPushButton:hover {{
    background-color: {c.bg_light};
    border-color: {c.accent};
}}

QPushButton:pressed {{
    background-color: {c.accent_dim};
}}

QPushButton#accent {{
    background-color: {c.accent};
    color: {c.text_inverse};
    border: none;
    font-weight: 600;
}}

QPushButton#accent:hover {{
    background-color: {c.accent_hover};
}}

QPushButton#danger {{
    background-color: {c.danger};
    color: white;
    border: none;
}}

QComboBox {{
    background-color: {c.bg_medium};
    color: {c.text_primary};
    border: 1px solid {c.bg_light};
    border-radius: 6px;
    padding: 5px 10px;
    min-width: 100px;
}}

QComboBox:hover {{
    border-color: {c.accent};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {c.bg_medium};
    color: {c.text_primary};
    selection-background-color: {c.accent_dim};
    border: 1px solid {c.bg_light};
}}

QListWidget {{
    background-color: {c.bg_medium};
    border: 1px solid {c.bg_light};
    border-radius: 6px;
    color: {c.text_primary};
    padding: 4px;
}}

QListWidget::item {{
    padding: 4px 8px;
    border-radius: 4px;
}}

QListWidget::item:selected {{
    background-color: {c.accent_dim};
    color: {c.accent};
}}

QScrollBar:vertical {{
    background: {c.bg_dark};
    width: 6px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical {{
    background: {c.bg_highlight};
    border-radius: 3px;
    min-height: 30px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QProgressBar {{
    background-color: {c.bg_medium};
    border: none;
    border-radius: 4px;
    height: 6px;
}}

QProgressBar::chunk {{
    background-color: {c.accent};
    border-radius: 4px;
}}

QSplitter::handle {{
    background: {c.separator};
    width: 1px;
    height: 1px;
}}

QToolTip {{
    background-color: {c.bg_medium};
    color: {c.text_primary};
    border: 1px solid {c.bg_light};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}}
"""


# ── Typography helpers ─────────────────────────────────────────────────────────

FONT_SIZES = {
    "xs":    10,
    "sm":    11,
    "base":  13,
    "md":    14,
    "lg":    16,
    "xl":    20,
    "2xl":   24,
    "3xl":   30,
}

FONT_MONO = '"JetBrains Mono", "Cascadia Code", "Fira Code", "Consolas", monospace'
