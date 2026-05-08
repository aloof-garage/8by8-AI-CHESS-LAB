"""
gui/dialogs.py
==============
Modal dialogs for piece promotion selection and game settings.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QFrame, QGridLayout, QDialogButtonBox, QCheckBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from engine.pieces import PieceType, Color, Piece, PIECE_UNICODE
from gui.theme import Theme


# ─── Promotion Dialog ─────────────────────────────────────────────────────────

class PromotionDialog(QDialog):
    """
    Lets the player choose a promotion piece.
    Shown when a pawn reaches the back rank.
    """

    piece_chosen = Signal(PieceType)

    def __init__(self, color: Color, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pawn Promotion")
        self.setModal(True)
        self.setFixedSize(320, 130)
        self._chosen = PieceType.QUEEN

        c = Theme.current()
        self.setStyleSheet(f"""
            QDialog {{
                background: {c.bg_dark};
                border: 1px solid {c.bg_light};
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        lbl = QLabel("Choose promotion piece:")
        lbl.setStyleSheet(f"color: {c.text_primary}; font-size: 13px; "
                          f"font-weight: 600; background: transparent;")
        layout.addWidget(lbl, alignment=Qt.AlignCenter)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        options = [
            (PieceType.QUEEN,  "Queen"),
            (PieceType.ROOK,   "Rook"),
            (PieceType.BISHOP, "Bishop"),
            (PieceType.KNIGHT, "Knight"),
        ]
        for pt, name in options:
            symbol = PIECE_UNICODE[(color, pt)]
            btn = QPushButton(f"{symbol}\n{name}")
            btn.setFixedSize(62, 62)
            btn.setFont(QFont("Segoe UI Symbol", 20))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {c.bg_medium};
                    color: {c.text_primary};
                    border: 1px solid {c.bg_light};
                    border-radius: 8px;
                    font-size: 18px;
                    padding: 4px;
                }}
                QPushButton:hover {{
                    background: {c.accent_dim};
                    border-color: {c.accent};
                }}
            """)
            btn.clicked.connect(lambda _, p=pt: self._select(p))
            btn_row.addWidget(btn)

        layout.addLayout(btn_row)

    def _select(self, pt: PieceType) -> None:
        self._chosen = pt
        self.piece_chosen.emit(pt)
        self.accept()

    def chosen_piece(self) -> PieceType:
        return self._chosen


# ─── New Game Dialog ──────────────────────────────────────────────────────────

class NewGameDialog(QDialog):
    """Dialog for configuring a new game."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Game")
        self.setModal(True)
        self.setFixedSize(360, 280)

        c = Theme.current()
        self.setStyleSheet(f"""
            QDialog {{
                background: {c.bg_dark};
                border: 1px solid {c.bg_light};
                border-radius: 10px;
            }}
            QLabel {{ background: transparent; color: {c.text_primary}; }}
            QComboBox {{
                background: {c.bg_medium};
                color: {c.text_primary};
                border: 1px solid {c.bg_light};
                border-radius: 5px;
                padding: 5px 10px;
                min-width: 160px;
            }}
            QComboBox QAbstractItemView {{
                background: {c.bg_medium};
                color: {c.text_primary};
                selection-background-color: {c.accent_dim};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("New Game Settings")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {c.text_primary};")
        layout.addWidget(title)

        # Game mode
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Game Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Human vs AI", "Human vs Human", "AI vs AI"])
        mode_row.addWidget(self.mode_combo)
        layout.addLayout(mode_row)

        # Player color
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Play as:"))
        self.color_combo = QComboBox()
        self.color_combo.addItems(["White", "Black", "Random"])
        color_row.addWidget(self.color_combo)
        layout.addLayout(color_row)

        # AI difficulty
        diff_row = QHBoxLayout()
        diff_row.addWidget(QLabel("AI Difficulty:"))
        self.diff_combo = QComboBox()
        self.diff_combo.addItems(["Easy", "Medium", "Hard", "Expert"])
        self.diff_combo.setCurrentText("Hard")
        diff_row.addWidget(self.diff_combo)
        layout.addLayout(diff_row)

        # AI vs AI: second AI difficulty
        diff2_row = QHBoxLayout()
        diff2_row.addWidget(QLabel("AI 2 Difficulty:"))
        self.diff2_combo = QComboBox()
        self.diff2_combo.addItems(["Easy", "Medium", "Hard", "Expert"])
        self.diff2_combo.setCurrentText("Medium")
        diff2_row.addWidget(self.diff2_combo)
        layout.addLayout(diff2_row)

        # Show AI as White option
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        self._diff2_row_widget = diff2_row
        self._on_mode_changed(self.mode_combo.currentText())

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedWidth(80)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {c.bg_medium}; color: {c.text_primary};
                border: 1px solid {c.bg_light}; border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{ background: {c.bg_light}; }}
        """)
        cancel_btn.clicked.connect(self.reject)

        ok_btn = QPushButton("Start Game")
        ok_btn.setFixedWidth(100)
        ok_btn.setObjectName("accent")
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background: {c.accent}; color: white;
                border: none; border-radius: 6px;
                padding: 6px 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {c.accent_hover}; }}
        """)
        ok_btn.clicked.connect(self.accept)

        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(ok_btn)
        layout.addStretch()
        layout.addLayout(btn_box)

    def _on_mode_changed(self, mode: str) -> None:
        show = (mode == "AI vs AI")
        # Hide/show rows based on mode
        for i in range(self._diff2_row_widget.count()):
            item = self._diff2_row_widget.itemAt(i)
            if item and item.widget():
                item.widget().setVisible(show)

    def get_config(self) -> dict:
        import random
        color_choice = self.color_combo.currentText()
        if color_choice == "Random":
            color_choice = random.choice(["White", "Black"])
        return {
            "mode":         self.mode_combo.currentText(),
            "player_color": color_choice,
            "difficulty":   self.diff_combo.currentText(),
            "difficulty2":  self.diff2_combo.currentText(),
        }


# ─── Settings Dialog ──────────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    """Application settings dialog."""

    def __init__(self, current_settings: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setFixedSize(360, 260)

        c = Theme.current()
        self.setStyleSheet(f"""
            QDialog {{ background: {c.bg_dark}; border: 1px solid {c.bg_light}; border-radius: 10px; }}
            QLabel {{ background: transparent; color: {c.text_primary}; }}
            QComboBox {{
                background: {c.bg_medium}; color: {c.text_primary};
                border: 1px solid {c.bg_light}; border-radius: 5px; padding: 5px 10px;
            }}
            QCheckBox {{ color: {c.text_primary}; background: transparent; spacing: 6px; }}
            QCheckBox::indicator {{
                width: 16px; height: 16px;
                background: {c.bg_medium}; border: 1px solid {c.bg_light};
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{ background: {c.accent}; border-color: {c.accent}; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Settings")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {c.text_primary};")
        layout.addWidget(title)

        # Theme
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setCurrentText(
            "Dark" if current_settings.get("dark_mode", True) else "Light")
        theme_row.addWidget(self.theme_combo)
        layout.addLayout(theme_row)

        # Coordinates
        self.coords_check = QCheckBox("Show board coordinates")
        self.coords_check.setChecked(current_settings.get("show_coords", True))
        layout.addWidget(self.coords_check)

        # Animations
        self.anim_check = QCheckBox("Enable piece animations")
        self.anim_check.setChecked(current_settings.get("animations", True))
        layout.addWidget(self.anim_check)

        # Sounds
        self.sound_check = QCheckBox("Enable move sounds")
        self.sound_check.setChecked(current_settings.get("sounds", False))
        layout.addWidget(self.sound_check)

        # Confirm button
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        ok_btn = QPushButton("Apply")
        ok_btn.setFixedWidth(80)
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background: {c.accent}; color: white; border: none;
                border-radius: 6px; padding: 6px 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {c.accent_hover}; }}
        """)
        ok_btn.clicked.connect(self.accept)
        btn_box.addWidget(ok_btn)
        layout.addStretch()
        layout.addLayout(btn_box)

    def get_settings(self) -> dict:
        return {
            "dark_mode":   self.theme_combo.currentText() == "Dark",
            "show_coords": self.coords_check.isChecked(),
            "animations":  self.anim_check.isChecked(),
            "sounds":      self.sound_check.isChecked(),
        }
