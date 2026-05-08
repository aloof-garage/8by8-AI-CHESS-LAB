"""
gui/panels.py
=============
Sidebar panel widgets for the 8by8 AI CHESS LAB GUI.

Panels:
  - EvalBar: vertical evaluation bar (White/Black advantage)
  - MoveHistoryPanel: scrollable SAN move list
  - CapturedPiecesPanel: shows taken pieces
  - AIThinkingPanel: live search stats display
  - EvalBreakdownPanel: component-by-component evaluation
  - TopMovesPanel: ranked AI candidate moves
  - AIExplanationPanel: natural-language move explanation
  - GameInfoPanel: game mode, result, clocks
"""

from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QListWidget, QListWidgetItem, QProgressBar,
    QSizePolicy, QGridLayout,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QLinearGradient

from engine.pieces import Color, Piece, PieceType
from engine.moves import Move
from ai.search import SearchStats
from ai.evaluator import EvalBreakdown
from gui.theme import Theme, FONT_MONO


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _panel(title: str = "", parent=None) -> tuple[QFrame, QVBoxLayout]:
    """Create a styled panel frame with optional title."""
    frame = QFrame(parent)
    frame.setObjectName("panel")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(6)
    if title:
        lbl = QLabel(title)
        lbl.setObjectName("panelTitle")
        c = Theme.current()
        lbl.setStyleSheet(f"color: {c.text_muted}; font-size: 10px; "
                          f"font-weight: 700; letter-spacing: 1px; "
                          f"text-transform: uppercase; background: transparent;")
        layout.addWidget(lbl)
    return frame, layout

def _sep() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.HLine)
    c = Theme.current()
    sep.setStyleSheet(f"background: {c.separator}; max-height: 1px; border: none;")
    return sep

def _label(text: str, bold: bool = False, size: int = 13,
           color: str = "", muted: bool = False) -> QLabel:
    lbl = QLabel(text)
    c = Theme.current()
    fg = color if color else (c.text_secondary if muted else c.text_primary)
    weight = "700" if bold else "400"
    lbl.setStyleSheet(f"color: {fg}; font-size: {size}px; "
                      f"font-weight: {weight}; background: transparent;")
    return lbl


# ─── Evaluation Bar ───────────────────────────────────────────────────────────

class EvalBar(QWidget):
    """
    Vertical evaluation bar.
    Shows White advantage at top (light color) / Black advantage at bottom (dark).
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(28)
        self.setMinimumHeight(200)
        self._score: float = 0.0    # centipawns, from White's perspective

    def set_score(self, score_cp: int) -> None:
        self._score = max(-1500, min(1500, score_cp))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        c = Theme.current()
        w, h = self.width(), self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor(c.bg_medium))

        # White fraction (clamp to 0-1)
        white_frac = max(0.05, min(0.95, 0.5 + self._score / 3000))
        white_h = int(h * (1 - white_frac))   # top portion = Black

        # Black portion
        painter.fillRect(2, 2, w-4, white_h - 2, QColor(c.eval_black))
        # White portion
        painter.fillRect(2, white_h, w-4, h - white_h - 2, QColor(c.eval_white))

        # Score text
        score_pawns = abs(self._score / 100)
        text = f"{score_pawns:.1f}" if score_pawns < 10 else f"{int(score_pawns)}"
        painter.setPen(QColor(c.text_secondary))
        font = QFont("Segoe UI", 7, QFont.Bold)
        painter.setFont(font)
        y = white_h + 10 if self._score >= 0 else white_h - 4
        painter.drawText(0, y, w, 12, Qt.AlignCenter, text)
        painter.end()


# ─── Captured Pieces ──────────────────────────────────────────────────────────

class CapturedPiecesPanel(QFrame):
    """Shows pieces captured by each side."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        self._white_label = QLabel("White captured: —")
        self._black_label = QLabel("Black captured: —")
        for lbl in (self._white_label, self._black_label):
            c = Theme.current()
            lbl.setStyleSheet(f"color: {c.text_secondary}; font-size: 12px; "
                              f"background: transparent;")
            layout.addWidget(lbl)

    def update_captured(self, white_captured: list[Piece],
                        black_captured: list[Piece]) -> None:
        order = [PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP,
                 PieceType.KNIGHT, PieceType.PAWN]
        def fmt(pieces: list[Piece]) -> str:
            if not pieces:
                return "—"
            sorted_p = sorted(pieces, key=lambda p: order.index(p.piece_type)
                              if p.piece_type in order else 99)
            return " ".join(p.symbol for p in sorted_p)

        self._white_label.setText(f"⚪ {fmt(white_captured)}")
        self._black_label.setText(f"⚫ {fmt(black_captured)}")


# ─── Move History ─────────────────────────────────────────────────────────────

class MoveHistoryPanel(QFrame):
    """Scrollable list of moves in standard algebraic notation."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = _label("MOVES", bold=True, size=10, muted=True)
        title.setContentsMargins(12, 8, 12, 4)
        layout.addWidget(title)

        self._list = QListWidget()
        self._list.setSpacing(0)
        self._list.setSelectionMode(QListWidget.NoSelection)
        layout.addWidget(self._list)

        self._moves: list[tuple[str, str]] = []   # [(white_san, black_san)]

    def update_moves(self, sans: list[str]) -> None:
        self._list.clear()
        c = Theme.current()
        pairs: list[tuple[str, str]] = []
        for i in range(0, len(sans), 2):
            w = sans[i]
            b = sans[i+1] if i+1 < len(sans) else ""
            pairs.append((w, b))

        for i, (w, b) in enumerate(pairs):
            # Build one row: "1. e4   e5"
            num_lbl = f"{i+1}."
            row_text = f"{num_lbl:<4} {w:<8} {b}"
            item = QListWidgetItem(row_text)
            item.setFont(QFont(FONT_MONO.split(",")[0].strip('"'), 11))
            item.setForeground(QColor(c.text_primary))
            if i % 2 == 0:
                item.setBackground(QColor(c.bg_medium))
            else:
                item.setBackground(QColor(c.bg_dark))
            self._list.addItem(item)

        # Scroll to bottom
        self._list.scrollToBottom()

    def clear(self) -> None:
        self._list.clear()


# ─── AI Thinking Panel ────────────────────────────────────────────────────────

class AIThinkingPanel(QFrame):
    """
    Live AI search statistics display.
    Updates during search via progress callbacks.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = _label("AI ENGINE", bold=True, size=10, muted=True)
        layout.addWidget(title)
        layout.addWidget(_sep())

        grid = QGridLayout()
        grid.setSpacing(4)
        grid.setColumnMinimumWidth(0, 110)

        def _row(label: str, row: int):
            lbl = _label(label, muted=True, size=11)
            val = _label("—", size=12)
            grid.addWidget(lbl, row, 0)
            grid.addWidget(val, row, 1)
            return val

        self._best_move_lbl  = _row("Best move",    0)
        self._score_lbl      = _row("Evaluation",   1)
        self._depth_lbl      = _row("Depth",        2)
        self._nodes_lbl      = _row("Nodes",        3)
        self._nps_lbl        = _row("Nodes/sec",    4)
        self._time_lbl       = _row("Time",         5)
        self._tt_hits_lbl    = _row("TT hits",      6)

        layout.addLayout(grid)

        # Status indicator
        self._status_lbl = _label("Idle", size=11, muted=True)
        layout.addWidget(self._status_lbl)

        # Thinking indicator animation
        self._dots = 0
        self._dot_timer = QTimer(self)
        self._dot_timer.timeout.connect(self._tick_dots)

    def set_thinking(self, thinking: bool) -> None:
        if thinking:
            self._dot_timer.start(400)
            c = Theme.current()
            self._status_lbl.setStyleSheet(
                f"color: {c.accent}; font-size: 11px; background: transparent;")
        else:
            self._dot_timer.stop()
            self._status_lbl.setText("Search complete")
            c = Theme.current()
            self._status_lbl.setStyleSheet(
                f"color: {c.success}; font-size: 11px; background: transparent;")

    def _tick_dots(self) -> None:
        self._dots = (self._dots + 1) % 4
        c = Theme.current()
        self._status_lbl.setText("Thinking" + "." * self._dots)

    def update_stats(self, stats: SearchStats) -> None:
        bm    = stats.best_move.uci() if stats.best_move else "—"
        score = stats.best_score / 100
        sign  = "+" if score >= 0 else ""

        self._best_move_lbl.setText(bm)
        self._score_lbl.setText(f"{sign}{score:.2f}")
        self._depth_lbl.setText(str(stats.depth_reached))
        self._nodes_lbl.setText(f"{stats.total_nodes:,}")
        self._nps_lbl.setText(f"{stats.nodes_per_sec:,.0f}")
        self._time_lbl.setText(f"{stats.elapsed:.2f}s")
        self._tt_hits_lbl.setText(f"{stats.tt_hits:,}")

    def reset(self) -> None:
        for lbl in (self._best_move_lbl, self._score_lbl, self._depth_lbl,
                    self._nodes_lbl, self._nps_lbl, self._time_lbl,
                    self._tt_hits_lbl):
            lbl.setText("—")
        self._status_lbl.setText("Idle")


# ─── Top Moves Panel ─────────────────────────────────────────────────────────

class TopMovesPanel(QFrame):
    """Shows ranked candidate moves from the AI search."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title = _label("TOP CANDIDATES", bold=True, size=10, muted=True)
        layout.addWidget(title)
        layout.addWidget(_sep())

        self._rows: list[QLabel] = []
        for _ in range(5):
            lbl = QLabel("—")
            c = Theme.current()
            lbl.setStyleSheet(f"color: {c.text_primary}; font-size: 12px; "
                              f"font-family: {FONT_MONO}; background: transparent;")
            layout.addWidget(lbl)
            self._rows.append(lbl)

        layout.addStretch()

    def update_moves(self, top_moves: list[tuple[Move, int]]) -> None:
        c = Theme.current()
        for i, lbl in enumerate(self._rows):
            if i < len(top_moves):
                move, score = top_moves[i]
                score_pawns = score / 100
                sign = "+" if score_pawns >= 0 else ""
                medal = ["①", "②", "③", "④", "⑤"][i]
                text = f"{medal} {move.uci():<8} {sign}{score_pawns:.2f}"
                color = c.accent if i == 0 else c.text_primary
                lbl.setStyleSheet(
                    f"color: {color}; font-size: 12px; "
                    f"font-family: {FONT_MONO}; background: transparent;")
                lbl.setText(text)
            else:
                lbl.setText("—")

    def clear(self) -> None:
        for lbl in self._rows:
            lbl.setText("—")


# ─── Evaluation Breakdown Panel ───────────────────────────────────────────────

class EvalBreakdownPanel(QFrame):
    """Shows component-by-component evaluation breakdown."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title = _label("EVALUATION", bold=True, size=10, muted=True)
        layout.addWidget(title)
        layout.addWidget(_sep())

        self._grid = QGridLayout()
        self._grid.setSpacing(3)
        self._grid.setColumnMinimumWidth(0, 100)
        layout.addLayout(self._grid)

        self._bars:   dict[str, QProgressBar] = {}
        self._labels: dict[str, QLabel]       = {}

        components = [
            "Material", "Position", "Mobility",
            "King Safety", "Center Control",
            "Pawn Structure", "Piece Activity",
        ]
        for row, name in enumerate(components):
            name_lbl = _label(name, muted=True, size=11)
            val_lbl  = _label("+0.00", size=11)
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._grid.addWidget(name_lbl, row, 0)
            self._grid.addWidget(val_lbl,  row, 1)
            self._labels[name] = val_lbl

        layout.addStretch()

    def update_breakdown(self, bd: EvalBreakdown) -> None:
        d = bd.to_dict()
        c = Theme.current()
        for name, lbl in self._labels.items():
            score = d.get(name, 0.0)
            sign  = "+" if score >= 0 else ""
            text  = f"{sign}{score:.2f}"
            color = c.success if score > 0.1 else (
                    c.danger if score < -0.1 else c.text_secondary)
            lbl.setStyleSheet(
                f"color: {color}; font-size: 11px; background: transparent;")
            lbl.setText(text)

    def clear(self) -> None:
        for lbl in self._labels.values():
            c = Theme.current()
            lbl.setStyleSheet(
                f"color: {c.text_muted}; font-size: 11px; background: transparent;")
            lbl.setText("—")


# ─── AI Explanation Panel ─────────────────────────────────────────────────────

class AIExplanationPanel(QFrame):
    """Displays natural-language AI move explanation."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = _label("AI REASONING", bold=True, size=10, muted=True)
        layout.addWidget(title)
        layout.addWidget(_sep())

        self._text = QLabel("Make a move to see AI reasoning...")
        c = Theme.current()
        self._text.setStyleSheet(
            f"color: {c.text_secondary}; font-size: 12px; "
            f"background: transparent; line-height: 1.5;")
        self._text.setWordWrap(True)
        self._text.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self._text)
        layout.addStretch()

    def set_explanation(self, text: str) -> None:
        self._text.setText(text)

    def clear(self) -> None:
        self._text.setText("Make a move to see AI reasoning...")


# ─── Game Status Panel ────────────────────────────────────────────────────────

class GameStatusPanel(QFrame):
    """Displays current game state: whose turn, check, result."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        self._turn_lbl  = _label("White to move", bold=True, size=13)
        self._check_lbl = _label("", size=12)
        self._result_lbl= _label("", bold=True, size=12)

        layout.addWidget(self._turn_lbl)
        layout.addWidget(self._check_lbl)
        layout.addStretch()
        layout.addWidget(self._result_lbl)

    def update_status(self, color: Color, in_check: bool,
                      result_text: str = "") -> None:
        c = Theme.current()
        side = "White" if color == Color.WHITE else "Black"
        self._turn_lbl.setText(f"{side} to move")

        if result_text:
            self._turn_lbl.setStyleSheet(
                f"color: {c.text_muted}; font-size: 13px; "
                f"font-weight: 700; background: transparent;")
            self._result_lbl.setText(result_text)
            self._result_lbl.setStyleSheet(
                f"color: {c.accent}; font-size: 12px; "
                f"font-weight: 700; background: transparent;")
        else:
            self._turn_lbl.setStyleSheet(
                f"color: {c.text_primary}; font-size: 13px; "
                f"font-weight: 700; background: transparent;")
            self._result_lbl.setText("")

        if in_check and not result_text:
            self._check_lbl.setText("⚠ Check!")
            self._check_lbl.setStyleSheet(
                f"color: {c.danger}; font-size: 12px; "
                f"font-weight: 700; background: transparent;")
        else:
            self._check_lbl.setText("")
