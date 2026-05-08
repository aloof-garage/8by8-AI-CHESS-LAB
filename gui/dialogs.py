"""
gui/dialogs.py
==============
Modal dialogs — design.md warm-minimalist system.
Radius: --r-lg (18px) outer, --r (10px) inner, --r-sm (6px) buttons.
"""
from __future__ import annotations
import random
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QFrame, QCheckBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from engine.pieces import PieceType, Color, PIECE_UNICODE
from gui.theme import Theme, FONT_UI, FONT_MONO, R_SM, R, R_LG
from ai.player import DIFFICULTY_CONFIGS


def _dlg_style(t) -> str:
    return f"""
QDialog {{
    background-color: {t.bg};
    border: 1px solid {t.border};
    border-radius: {R_LG}px;
}}
QLabel {{
    background: transparent;
    color: {t.ink};
    font-family: {FONT_UI};
}}
QComboBox {{
    background: {t.surface};
    color: {t.ink2};
    border: 1px solid {t.border};
    border-radius: {R_SM}px;
    padding: 6px 12px;
    font-size: 12px;
    min-height: 30px;
    min-width: 150px;
}}
QComboBox:hover {{ border-color: {t.border2}; color: {t.ink}; }}
QComboBox QAbstractItemView {{
    background: {t.surface};
    border: 1px solid {t.border2};
    color: {t.ink};
    selection-background-color: {t.surface2};
    outline: none;
    border-radius: {R_SM}px;
}}
QCheckBox {{
    color: {t.ink2};
    background: transparent;
    spacing: 8px;
    font-size: 13px;
    font-family: {FONT_UI};
}}
QCheckBox::indicator {{
    width: 15px; height: 15px;
    background: {t.surface};
    border: 1px solid {t.border2};
    border-radius: 4px;
}}
QCheckBox::indicator:checked {{
    background: {t.accent};
    border-color: {t.accent};
}}
"""


def _btn_primary(text: str, t) -> QPushButton:
    btn = QPushButton(text)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {t.accent}; color: {t.accent_fg};
            border: none; border-radius: {R_SM}px;
            padding: 7px 20px; font-weight: 600; font-size: 13px;
            font-family: {FONT_UI}; min-height: 32px;
        }}
        QPushButton:hover {{ background: {t.ink2}; }}
        QPushButton:pressed {{ background: {t.ink}; }}
    """)
    return btn


def _btn_ghost(text: str, t) -> QPushButton:
    btn = QPushButton(text)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent; color: {t.ink3};
            border: 1px solid {t.border}; border-radius: {R_SM}px;
            padding: 7px 16px; font-size: 13px;
            font-family: {FONT_UI}; min-height: 32px;
        }}
        QPushButton:hover {{
            background: {t.surface2};
            color: {t.ink};
            border-color: {t.border2};
        }}
    """)
    return btn


def _eyebrow(text: str, t) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        f"color:{t.ink4}; font-family:{FONT_MONO}; font-size:10px;"
        f"font-weight:500; letter-spacing:0.1em; background:transparent;"
    )
    return lbl


# ─── Promotion Dialog ─────────────────────────────────────────────────────────

class PromotionDialog(QDialog):
    piece_chosen = Signal(PieceType)

    def __init__(self, color: Color, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Promote Pawn")
        self.setModal(True)
        self.setFixedSize(340, 140)
        t = Theme.current()
        self.setStyleSheet(_dlg_style(t))
        self._chosen = PieceType.QUEEN

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        lbl = QLabel("Choose promotion piece")
        lbl.setStyleSheet(
            f"color:{t.ink2}; font-size:12px; font-weight:500; background:transparent;"
            f"letter-spacing:0.02em;"
        )
        layout.addWidget(lbl, alignment=Qt.AlignCenter)

        row = QHBoxLayout()
        row.setSpacing(8)
        options = [
            (PieceType.QUEEN,  "Q"),
            (PieceType.ROOK,   "R"),
            (PieceType.BISHOP, "B"),
            (PieceType.KNIGHT, "N"),
        ]
        for pt, short in options:
            sym = PIECE_UNICODE[(color, pt)]
            btn = QPushButton(sym)
            btn.setFixedSize(60, 60)
            btn.setFont(QFont("Segoe UI Symbol", 22))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {t.surface};
                    color: {t.ink};
                    border: 1px solid {t.border};
                    border-radius: {R}px;
                    font-size: 26px;
                }}
                QPushButton:hover {{
                    background: {t.surface2};
                    border-color: {t.border2};
                }}
                QPushButton:pressed {{
                    background: {t.border};
                }}
            """)
            btn.clicked.connect(lambda _, p=pt: self._select(p))
            row.addWidget(btn)
        layout.addLayout(row)

    def _select(self, pt: PieceType) -> None:
        self._chosen = pt
        self.piece_chosen.emit(pt)
        self.accept()

    def chosen_piece(self) -> PieceType:
        return self._chosen


# ─── New Game Dialog ──────────────────────────────────────────────────────────

class NewGameDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Game")
        self.setModal(True)
        self.setFixedSize(380, 310)
        t = Theme.current()
        self.setStyleSheet(_dlg_style(t))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel("New Game")
        title.setStyleSheet(
            f"color:{t.ink}; font-size:18px; font-weight:700; background:transparent;"
            f"letter-spacing:-0.02em;"
        )
        layout.addWidget(title)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background:{t.border};")
        layout.addWidget(div)

        # Rows
        def _row(label: str, combo: QComboBox) -> QHBoxLayout:
            hl = QHBoxLayout()
            hl.setSpacing(12)
            lbl = QLabel(label)
            lbl.setFixedWidth(110)
            lbl.setStyleSheet(
                f"color:{t.ink3}; font-size:12px; background:transparent;"
            )
            hl.addWidget(lbl)
            hl.addWidget(combo, 1)
            return hl

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Human vs AI", "Human vs Human", "AI vs AI"])
        layout.addLayout(_row("Game mode", self.mode_combo))

        self.color_combo = QComboBox()
        self.color_combo.addItems(["White", "Black", "Random"])
        layout.addLayout(_row("Play as", self.color_combo))

        self.diff_combo = QComboBox()
        self.diff_combo.addItems(list(DIFFICULTY_CONFIGS.keys()))
        self.diff_combo.setCurrentText("Hard")
        layout.addLayout(_row("AI difficulty", self.diff_combo))

        self.diff2_combo = QComboBox()
        self.diff2_combo.addItems(list(DIFFICULTY_CONFIGS.keys()))
        self.diff2_combo.setCurrentText("Medium")
        self._diff2_row = _row("AI 2 difficulty", self.diff2_combo)
        layout.addLayout(self._diff2_row)

        self.mode_combo.currentTextChanged.connect(self._on_mode)
        self._on_mode(self.mode_combo.currentText())

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        cancel = _btn_ghost("Cancel", t)
        cancel.clicked.connect(self.reject)
        ok = _btn_primary("Start Game", t)
        ok.clicked.connect(self.accept)
        btn_row.addWidget(cancel)
        btn_row.addWidget(ok)
        layout.addLayout(btn_row)

    def _on_mode(self, mode: str) -> None:
        show = mode == "AI vs AI"
        for i in range(self._diff2_row.count()):
            item = self._diff2_row.itemAt(i)
            if item and item.widget():
                item.widget().setVisible(show)

    def get_config(self) -> dict:
        color = self.color_combo.currentText()
        if color == "Random":
            color = random.choice(["White", "Black"])
        return {
            "mode":        self.mode_combo.currentText(),
            "player_color":color,
            "difficulty":  self.diff_combo.currentText(),
            "difficulty2": self.diff2_combo.currentText(),
        }


# ─── Settings Dialog ──────────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    def __init__(self, current: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setFixedSize(360, 260)
        t = Theme.current()
        self.setStyleSheet(_dlg_style(t))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel("Settings")
        title.setStyleSheet(
            f"color:{t.ink}; font-size:18px; font-weight:700; background:transparent;"
            f"letter-spacing:-0.02em;"
        )
        layout.addWidget(title)
        div = QFrame(); div.setFixedHeight(1)
        div.setStyleSheet(f"background:{t.border};")
        layout.addWidget(div)

        def _row(label: str, combo: QComboBox) -> QHBoxLayout:
            hl = QHBoxLayout(); hl.setSpacing(12)
            lbl = QLabel(label); lbl.setFixedWidth(110)
            lbl.setStyleSheet(f"color:{t.ink3}; font-size:12px; background:transparent;")
            hl.addWidget(lbl); hl.addWidget(combo, 1)
            return hl

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setCurrentText("Dark" if current.get("dark_mode", True) else "Light")
        layout.addLayout(_row("Theme", self.theme_combo))

        self.coords_cb = QCheckBox("Show board coordinates")
        self.coords_cb.setChecked(current.get("show_coords", True))
        layout.addWidget(self.coords_cb)

        self.anim_cb = QCheckBox("Enable piece animations")
        self.anim_cb.setChecked(current.get("animations", True))
        layout.addWidget(self.anim_cb)

        layout.addStretch()
        btn_row = QHBoxLayout(); btn_row.setSpacing(8); btn_row.addStretch()
        cancel = _btn_ghost("Cancel", t); cancel.clicked.connect(self.reject)
        ok = _btn_primary("Apply", t);    ok.clicked.connect(self.accept)
        btn_row.addWidget(cancel); btn_row.addWidget(ok)
        layout.addLayout(btn_row)

    def get_settings(self) -> dict:
        return {
            "dark_mode":   self.theme_combo.currentText() == "Dark",
            "show_coords": self.coords_cb.isChecked(),
            "animations":  self.anim_cb.isChecked(),
            "sounds":      False,
        }
