"""
gui/panels.py
=============
Sidebar panel components — design.md warm-minimalist system.

Typography rules (design.md §3):
  Section eyebrow  → DM Mono, 11px, 500, 0.1em spacing, uppercase, --ink4
  Values / numbers → DM Mono, 12px, --ink2
  Labels           → DM Sans, 12px, --ink3
  Primary text     → DM Sans, 13px, --ink

Radius rules (design.md §4):
  Cards / panels  → --r-lg = 18px outer, --r = 10px inner
  Buttons / tags  → --r-sm = 6px
"""
from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QListWidget, QListWidgetItem, QSizePolicy,
    QGridLayout,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QLinearGradient

from engine.pieces import Color, Piece, PieceType
from engine.moves import Move
from ai.search import SearchStats
from ai.evaluator import EvalBreakdown
from gui.theme import Theme, FONT_MONO, FONT_UI


# ─── Low-level helpers ────────────────────────────────────────────────────────

def _eyebrow(text: str, parent=None) -> QLabel:
    """Section eyebrow label — DM Mono 11px uppercase ink4."""
    lbl = QLabel(text.upper(), parent)
    t = Theme.current()
    lbl.setStyleSheet(
        f"color:{t.ink4}; font-family:{FONT_MONO}; font-size:10px;"
        f"font-weight:500; letter-spacing:0.1em; background:transparent;"
    )
    return lbl

def _ink_label(text: str = "", size: int = 13, mono: bool = False,
               muted: bool = False, bold: bool = False, parent=None) -> QLabel:
    lbl = QLabel(text, parent)
    t   = Theme.current()
    col = t.ink3 if muted else t.ink2
    ff  = FONT_MONO if mono else FONT_UI
    wt  = "600" if bold else ("500" if mono else "400")
    lbl.setStyleSheet(
        f"color:{col}; font-size:{size}px; font-weight:{wt};"
        f"font-family:{ff}; background:transparent;"
    )
    return lbl

def _divider() -> QFrame:
    sep = QFrame()
    sep.setFixedHeight(1)
    t = Theme.current()
    sep.setStyleSheet(f"background:{t.border}; border:none;")
    return sep


# ─── Panel base ───────────────────────────────────────────────────────────────

def _panel(parent=None) -> tuple[QFrame, QVBoxLayout]:
    """Standard surface panel with border and radius."""
    frame = QFrame(parent)
    frame.setObjectName("panel")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    return frame, layout


# ─── Evaluation Bar ───────────────────────────────────────────────────────────

class EvalBar(QWidget):
    """
    Slim vertical evaluation bar.
    White advantage = top segment in ink (warm white in dark).
    Black advantage = bottom segment in surface.
    """
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(20)
        self.setMinimumHeight(200)
        self._score: float = 0.0

    def set_score(self, score_cp: int) -> None:
        self._score = max(-1500, min(1500, score_cp))
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = Theme.current()
        w, h = self.width(), self.height()

        # Track background
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(t.surface))
        p.drawRoundedRect(4, 0, w - 8, h, 3, 3)

        # White fraction
        frac  = max(0.04, min(0.96, 0.5 + self._score / 3000))
        wh    = int(h * frac)      # white portion height (grows from bottom)
        bh    = h - wh             # black portion height (top)

        # Black portion (top)
        p.setBrush(QColor(t.ink).darker(160 if not Theme.is_dark() else 100))
        p.drawRoundedRect(4, 0, w - 8, bh, 3, 3)

        # White portion (bottom)
        p.setBrush(QColor(t.sq_light).lighter(110))
        p.drawRoundedRect(4, bh, w - 8, wh, 3, 3)

        # Score text
        if abs(self._score) > 15:
            score_str = f"{abs(self._score / 100):.0f}"
            p.setPen(QColor(t.ink4))
            font = QFont("DM Mono, Consolas", 7)
            p.setFont(font)
            ty = bh + 10 if self._score >= 0 else bh - 4
            ty = max(10, min(h - 4, ty))
            p.drawText(0, ty, w, 10, Qt.AlignCenter, score_str)
        p.end()


# ─── Captured Pieces ──────────────────────────────────────────────────────────

class CapturedPiecesPanel(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(3)
        t = Theme.current()
        self._w = QLabel("—")
        self._b = QLabel("—")
        for lbl in (self._w, self._b):
            lbl.setStyleSheet(
                f"color:{t.ink3}; font-size:13px; background:transparent; letter-spacing:1px;"
            )
            layout.addWidget(lbl)

    def update_captured(self, wc: list[Piece], bc: list[Piece]) -> None:
        order = [PieceType.QUEEN, PieceType.ROOK,
                 PieceType.BISHOP, PieceType.KNIGHT, PieceType.PAWN]
        def fmt(pieces):
            if not pieces: return "—"
            s = sorted(pieces, key=lambda p: order.index(p.piece_type)
                       if p.piece_type in order else 9)
            return " ".join(p.symbol for p in s)
        self._w.setText(fmt(wc))
        self._b.setText(fmt(bc))


# ─── Move History ─────────────────────────────────────────────────────────────

class MoveHistoryPanel(QFrame):
    """Monospace move list with alternating row tints."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(36)
        t = Theme.current()
        header.setStyleSheet(f"background:{t.surface}; border-radius:0px;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 16, 0)
        hl.addWidget(_eyebrow("Moves"))
        hl.addStretch()
        layout.addWidget(header)
        layout.addWidget(_divider())

        self._list = QListWidget()
        self._list.setSpacing(0)
        self._list.setSelectionMode(QListWidget.NoSelection)
        layout.addWidget(self._list, 1)

    def update_moves(self, sans: list[str]) -> None:
        self._list.clear()
        t  = Theme.current()
        for i in range(0, len(sans), 2):
            w = sans[i]
            b = sans[i + 1] if i + 1 < len(sans) else ""
            num = f"{i//2 + 1}."
            text = f"{num:<5}{w:<9}{b}"
            item = QListWidgetItem(text)
            bg = t.surface if i % 4 == 0 else t.bg
            item.setBackground(QColor(bg))
            item.setForeground(QColor(t.ink2))
            self._list.addItem(item)
        self._list.scrollToBottom()

    def clear(self) -> None:
        self._list.clear()


# ─── AI Thinking Panel ────────────────────────────────────────────────────────

class AIThinkingPanel(QFrame):
    """Live search statistics — monospace values, sans labels."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header row
        hdr = QWidget()
        hdr.setFixedHeight(36)
        t = Theme.current()
        hdr.setStyleSheet(f"background:{t.surface};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 0, 16, 0)
        hl.addWidget(_eyebrow("Engine"))
        hl.addStretch()
        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet(
            f"color:{t.ink4}; font-size:8px; background:transparent;"
        )
        hl.addWidget(self._status_dot)
        layout.addWidget(hdr)
        layout.addWidget(_divider())

        # Grid of stats
        body = QWidget()
        body.setStyleSheet(f"background:{t.surface};")
        grid = QGridLayout(body)
        grid.setContentsMargins(16, 12, 16, 12)
        grid.setVerticalSpacing(8)
        grid.setHorizontalSpacing(12)
        grid.setColumnStretch(1, 1)

        rows = [
            ("Best move",  "_v_best"),
            ("Evaluation", "_v_eval"),
            ("Depth",      "_v_depth"),
            ("Nodes",      "_v_nodes"),
            ("Nodes / s",  "_v_nps"),
            ("Time",       "_v_time"),
            ("TT hits",    "_v_tt"),
        ]
        self._vals: dict[str, QLabel] = {}
        for row_i, (label, attr) in enumerate(rows):
            lbl = _ink_label(label, size=11, muted=True)
            val = _ink_label("—", size=12, mono=True)
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(lbl, row_i, 0)
            grid.addWidget(val, row_i, 1)
            self._vals[attr] = val

        layout.addWidget(body)

        self._dot_timer = QTimer(self)
        self._dot_timer.timeout.connect(self._tick)
        self._dots = 0

    def set_thinking(self, thinking: bool) -> None:
        t = Theme.current()
        if thinking:
            self._dot_timer.start(450)
            self._status_dot.setStyleSheet(
                f"color:{t.warning}; font-size:8px; background:transparent;"
            )
        else:
            self._dot_timer.stop()
            self._status_dot.setStyleSheet(
                f"color:{t.success}; font-size:8px; background:transparent;"
            )
            self._status_dot.setText("●")

    def _tick(self) -> None:
        self._dots = (self._dots + 1) % 4
        self._status_dot.setText("●" + "·" * self._dots)

    def update_stats(self, stats: SearchStats) -> None:
        t  = Theme.current()
        bm = stats.best_move.uci() if stats.best_move else "—"
        sc = stats.best_score / 100
        sg = "+" if sc >= 0 else ""
        self._vals["_v_best"].setText(bm)
        self._vals["_v_eval"].setText(f"{sg}{sc:.2f}")
        self._vals["_v_depth"].setText(str(stats.depth_reached))
        self._vals["_v_nodes"].setText(f"{stats.total_nodes:,}")
        self._vals["_v_nps"].setText(f"{stats.nodes_per_sec:,.0f}")
        self._vals["_v_time"].setText(f"{stats.elapsed:.2f}s")
        self._vals["_v_tt"].setText(f"{stats.tt_hits:,}")

        # Color-code eval
        col = t.success if sc > 0.3 else (t.danger if sc < -0.3 else t.ink2)
        self._vals["_v_eval"].setStyleSheet(
            f"color:{col}; font-size:12px; font-weight:500;"
            f"font-family:{FONT_MONO}; background:transparent;"
        )

    def reset(self) -> None:
        for v in self._vals.values():
            v.setText("—")
        t = Theme.current()
        self._status_dot.setStyleSheet(
            f"color:{t.ink4}; font-size:8px; background:transparent;"
        )


# ─── Top Moves Panel ──────────────────────────────────────────────────────────

class TopMovesPanel(QFrame):
    """Ranked candidate moves — monospace, ink scale."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hdr = QWidget()
        hdr.setFixedHeight(36)
        t = Theme.current()
        hdr.setStyleSheet(f"background:{t.surface};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 0, 16, 0)
        hl.addWidget(_eyebrow("Candidates"))
        hl.addStretch()
        layout.addWidget(hdr)
        layout.addWidget(_divider())

        body = QWidget()
        body.setStyleSheet(f"background:{t.surface};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(16, 10, 16, 10)
        bl.setSpacing(5)
        self._rows: list[QLabel] = []
        for i in range(5):
            row = QLabel("—")
            alpha = 1.0 if i == 0 else max(0.35, 1.0 - i * 0.18)
            col = self._alpha_color(t.ink if i == 0 else t.ink2, alpha)
            row.setStyleSheet(
                f"color:{col}; font-size:12px; font-weight:{'600' if i==0 else '400'};"
                f"font-family:{FONT_MONO}; background:transparent;"
            )
            bl.addWidget(row)
            self._rows.append(row)
        layout.addWidget(body)

    @staticmethod
    def _alpha_color(hex_col: str, alpha: float) -> str:
        return hex_col  # Qt labels use full color; opacity via stylesheet not supported

    def update_moves(self, top_moves: list[tuple[Move, int]]) -> None:
        t = Theme.current()
        for i, row in enumerate(self._rows):
            if i < len(top_moves):
                move, score = top_moves[i]
                s = score / 100
                sign = "+" if s >= 0 else ""
                medal = ["1.", "2.", "3.", "4.", "5."][i]
                row.setText(f"{medal}  {move.uci():<8}  {sign}{s:.2f}")
                col = t.ink if i == 0 else t.ink3
                wt  = "600" if i == 0 else "400"
                row.setStyleSheet(
                    f"color:{col}; font-size:12px; font-weight:{wt};"
                    f"font-family:{FONT_MONO}; background:transparent;"
                )
            else:
                row.setText("—")

    def clear(self) -> None:
        for r in self._rows:
            r.setText("—")


# ─── Eval Breakdown Panel ─────────────────────────────────────────────────────

class EvalBreakdownPanel(QFrame):
    """Component-by-component evaluation grid."""

    _COMPONENTS = [
        ("Material",       "_material"),
        ("Position",       "_position"),
        ("Mobility",       "_mobility"),
        ("King Safety",    "_king_safety"),
        ("Center",         "_center"),
        ("Pawn Structure", "_pawn_struct"),
        ("Piece Activity", "_piece_activity"),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hdr = QWidget()
        hdr.setFixedHeight(36)
        t = Theme.current()
        hdr.setStyleSheet(f"background:{t.surface};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 0, 16, 0)
        hl.addWidget(_eyebrow("Evaluation"))
        hl.addStretch()
        layout.addWidget(hdr)
        layout.addWidget(_divider())

        body = QWidget()
        body.setStyleSheet(f"background:{t.surface};")
        grid = QGridLayout(body)
        grid.setContentsMargins(16, 10, 16, 10)
        grid.setVerticalSpacing(7)
        grid.setHorizontalSpacing(12)
        grid.setColumnStretch(1, 1)

        self._labels: dict[str, QLabel] = {}
        for row_i, (name, key) in enumerate(self._COMPONENTS):
            name_lbl = _ink_label(name, size=11, muted=True)
            val_lbl  = _ink_label("—", size=11, mono=True)
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(name_lbl, row_i, 0)
            grid.addWidget(val_lbl,  row_i, 1)
            self._labels[key] = val_lbl
        layout.addWidget(body)

    def update_breakdown(self, bd: EvalBreakdown) -> None:
        t = Theme.current()
        mapping = {
            "_material":      bd.material,
            "_position":      bd.position,
            "_mobility":      bd.mobility,
            "_king_safety":   bd.king_safety,
            "_center":        bd.center,
            "_pawn_struct":   bd.pawn_struct,
            "_piece_activity":bd.piece_activity,
        }
        for key, raw in mapping.items():
            score = raw / 100
            sign  = "+" if score >= 0 else ""
            text  = f"{sign}{score:.2f}"
            col   = (t.success if score > 0.05
                     else t.danger if score < -0.05
                     else t.ink3)
            self._labels[key].setText(text)
            self._labels[key].setStyleSheet(
                f"color:{col}; font-size:11px; font-weight:500;"
                f"font-family:{FONT_MONO}; background:transparent;"
            )

    def clear(self) -> None:
        for v in self._labels.values():
            v.setText("—")


# ─── AI Explanation Panel ─────────────────────────────────────────────────────

class AIExplanationPanel(QFrame):
    """Natural-language move explanation."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hdr = QWidget()
        hdr.setFixedHeight(36)
        t = Theme.current()
        hdr.setStyleSheet(f"background:{t.surface};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 0, 16, 0)
        hl.addWidget(_eyebrow("Reasoning"))
        hl.addStretch()
        layout.addWidget(hdr)
        layout.addWidget(_divider())

        body = QWidget()
        body.setStyleSheet(f"background:{t.surface};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(16, 12, 16, 14)

        self._text = QLabel("Waiting for move…")
        self._text.setWordWrap(True)
        self._text.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._text.setStyleSheet(
            f"color:{t.ink3}; font-size:12px; line-height:1.6;"
            f"background:transparent; font-family:{FONT_UI};"
        )
        bl.addWidget(self._text)
        layout.addWidget(body)

    def set_explanation(self, text: str) -> None:
        self._text.setText(text)

    def clear(self) -> None:
        self._text.setText("Waiting for move…")


# ─── Game Status Panel ────────────────────────────────────────────────────────

class GameStatusPanel(QFrame):
    """Turn indicator, check warning, result."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statusbar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(10)

        t = Theme.current()
        self._turn = QLabel("White to move")
        self._turn.setStyleSheet(
            f"color:{t.ink}; font-size:13px; font-weight:600; background:transparent;"
        )
        self._check = QLabel("")
        self._check.setStyleSheet(
            f"color:{t.danger}; font-size:12px; font-weight:600; background:transparent;"
        )
        self._result = QLabel("")
        self._result.setStyleSheet(
            f"color:{t.ink3}; font-size:12px; background:transparent;"
        )

        layout.addWidget(self._turn)
        layout.addWidget(self._check)
        layout.addStretch()
        layout.addWidget(self._result)

    def update_status(self, color: Color, in_check: bool, result_text: str = "") -> None:
        t = Theme.current()
        side = "White" if color == Color.WHITE else "Black"

        if result_text:
            self._turn.setText(result_text)
            self._turn.setStyleSheet(
                f"color:{t.ink2}; font-size:13px; font-weight:600; background:transparent;"
            )
            self._check.setText("")
            self._result.setText("")
        else:
            self._turn.setText(f"{side} to move")
            self._turn.setStyleSheet(
                f"color:{t.ink}; font-size:13px; font-weight:600; background:transparent;"
            )
            self._check.setText("Check  !" if in_check else "")
            self._result.setText("")
