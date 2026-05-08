"""
gui/board_widget.py
===================
Chessboard widget — warm minimalist aesthetic from design.md.

Board squares use warm parchment / warm brown palette.
Highlights: amber tint for selection / moves, red tint for check.
Pieces: unicode symbols rendered with DM Sans fallback, shadowed.
Coordinates: DM Mono, ink4 tone, tight corners.
Animation: 60 fps linear interpolation via QTimer.
"""

from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, QRect, QPoint, QTimer, Signal
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush,
    QRadialGradient, QPainterPath,
)

from engine.board import Board
from engine.moves import Move, rank_of, file_of, sq
from engine.pieces import Color, PieceType, Piece
from gui.theme import Theme, FONT_MONO


class BoardWidget(QWidget):
    """Interactive chessboard with warm-minimalist visual style."""

    move_requested = Signal(object)   # Move

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(380, 380)

        self._board:        Optional[Board] = None
        self._legal_moves:  list[Move]      = []
        self._selected_sq:  Optional[int]   = None
        self._legal_dests:  set[int]        = set()
        self._last_move:    Optional[Move]  = None
        self._flipped:      bool            = False
        self._check_sq:     Optional[int]   = None
        self._interactive:  bool            = True
        self._show_coords:  bool            = True
        self._show_heatmap: bool            = False
        self._heatmap_color: Optional[Color]= None
        self._heatmap_data: dict[int, int]  = {}

        # Smooth move animation
        self._anim_from:  Optional[int]   = None
        self._anim_to:    Optional[int]   = None
        self._anim_piece: Optional[Piece] = None
        self._anim_t:     float           = 1.0

        # Drag state
        self._drag_sq:   Optional[int]    = None
        self._drag_pos:  Optional[QPoint] = None

        self.setMouseTracking(True)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_board(self, board: Board) -> None:
        self._board = board
        self.update()

    def set_legal_moves(self, moves: list[Move]) -> None:
        self._legal_moves = moves

    def set_last_move(self, move: Optional[Move]) -> None:
        self._last_move = move
        self.update()

    def set_flipped(self, flipped: bool) -> None:
        self._flipped = flipped
        self.update()

    def flip(self) -> None:
        self._flipped = not self._flipped
        self.update()

    def set_interactive(self, v: bool) -> None:
        self._interactive = v

    def clear_selection(self) -> None:
        self._selected_sq = None
        self._legal_dests = set()
        self.update()

    def set_check_square(self, s: Optional[int]) -> None:
        self._check_sq = s
        self.update()

    def set_heatmap(self, color: Optional[Color], data: dict[int, int]) -> None:
        self._show_heatmap  = color is not None
        self._heatmap_color = color
        self._heatmap_data  = data
        self.update()

    def clear_heatmap(self) -> None:
        self._show_heatmap = False
        self._heatmap_data = {}
        self.update()

    def animate_move(self, move: Move, piece: Piece) -> None:
        self._anim_from  = move.from_sq
        self._anim_to    = move.to_sq
        self._anim_piece = piece
        self._anim_t     = 0.0
        timer = QTimer(self)
        timer.setInterval(14)   # ~70 fps

        def _tick():
            self._anim_t = min(1.0, self._anim_t + 0.07)
            if self._anim_t >= 1.0:
                self._anim_from = None
                timer.stop()
            self.update()

        timer.timeout.connect(_tick)
        timer.start()

    # ── Geometry ──────────────────────────────────────────────────────────────

    @property
    def _cell(self) -> int:
        return min(self.width(), self.height()) // 8

    @property
    def _ox(self) -> int:
        return (self.width()  - self._cell * 8) // 2

    @property
    def _oy(self) -> int:
        return (self.height() - self._cell * 8) // 2

    def _sq_to_pt(self, square: int) -> QPoint:
        r, f = rank_of(square), file_of(square)
        dr = r if self._flipped else (7 - r)
        df = (7 - f) if self._flipped else f
        return QPoint(self._ox + df * self._cell,
                      self._oy + dr * self._cell)

    def _pt_to_sq(self, pos: QPoint) -> Optional[int]:
        x = pos.x() - self._ox
        y = pos.y() - self._oy
        c = self._cell
        if not (0 <= x < c * 8 and 0 <= y < c * 8):
            return None
        df, dr = x // c, y // c
        f = (7 - df) if self._flipped else df
        r = dr       if self._flipped else (7 - dr)
        return sq(r, f)

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        if self._board is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        self._paint_board(p)
        self._paint_highlights(p)
        if self._show_heatmap:
            self._paint_heatmap(p)
        self._paint_pieces(p)
        if self._show_coords:
            self._paint_coords(p)
        if self._drag_sq is not None and self._drag_pos:
            piece = self._board.piece_at(self._drag_sq)
            if piece:
                self._paint_piece_at(p, piece,
                                     self._drag_pos.x() - self._cell // 2,
                                     self._drag_pos.y() - self._cell // 2,
                                     self._cell)
        p.end()

    def _paint_board(self, p: QPainter) -> None:
        t = Theme.current()
        c = self._cell
        ox, oy = self._ox, self._oy

        # Outer shadow via semi-transparent rect
        shadow = QPainterPath()
        shadow.addRoundedRect(ox - 2, oy - 2, c*8 + 4, c*8 + 4, 4, 4)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 28 if Theme.is_dark() else 14))
        p.drawPath(shadow)

        # Squares
        for rank in range(8):
            for file in range(8):
                s = sq(rank, file)
                pt = self._sq_to_pt(s)
                is_light = (rank + file) % 2 == 0
                col = QColor(t.sq_light if is_light else t.sq_dark)
                p.fillRect(pt.x(), pt.y(), c, c, col)

    def _paint_highlights(self, p: QPainter) -> None:
        t = Theme.current()
        c = self._cell

        def fill(s: int, hex_color: str) -> None:
            pt = self._sq_to_pt(s)
            p.fillRect(pt.x(), pt.y(), c, c, QColor(hex_color))

        # Last move tint
        if self._last_move:
            fill(self._last_move.from_sq, t.hl_last)
            fill(self._last_move.to_sq,   t.hl_last)

        # Check glow (radial)
        if self._check_sq is not None:
            pt = self._sq_to_pt(self._check_sq)
            cx, cy = pt.x() + c / 2, pt.y() + c / 2
            g = QRadialGradient(cx, cy, c * 0.72)
            base = t.hl_check
            g.setColorAt(0.0, QColor(base))
            g.setColorAt(1.0, QColor(base[:-4] + "0.0)"))
            p.setBrush(g)
            p.setPen(Qt.NoPen)
            p.drawRect(pt.x(), pt.y(), c, c)

        # Selected square
        if self._selected_sq is not None:
            fill(self._selected_sq, t.hl_select)

        # Legal move dots / capture rings
        p.setPen(Qt.NoPen)
        for dest in self._legal_dests:
            pt = self._sq_to_pt(dest)
            has_piece = self._board and self._board.piece_at(dest) is not None
            if has_piece:
                # Capture ring
                pen = QPen(QColor(t.hl_move), 3)
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(pt.x() + 3, pt.y() + 3, c - 6, c - 6)
                p.setPen(Qt.NoPen)
            else:
                # Subtle center dot
                r = max(4, c // 7)
                cx2, cy2 = pt.x() + c // 2, pt.y() + c // 2
                p.setBrush(QColor(t.hl_move))
                p.drawEllipse(cx2 - r, cy2 - r, r * 2, r * 2)

    def _paint_heatmap(self, p: QPainter) -> None:
        if not self._heatmap_data:
            return
        c = self._cell
        max_v = max(self._heatmap_data.values(), default=1)
        for s, v in self._heatmap_data.items():
            pt = self._sq_to_pt(s)
            alpha = int(160 * v / max_v)
            if self._heatmap_color == Color.WHITE:
                col = QColor(180, 200, 230, alpha)
            else:
                col = QColor(200, 110, 100, alpha)
            p.fillRect(pt.x(), pt.y(), c, c, col)

    def _paint_pieces(self, p: QPainter) -> None:
        if not self._board:
            return
        c = self._cell
        for s, piece in self._board.all_pieces():
            if s == self._anim_from and self._anim_t < 1.0:
                continue
            if s == self._drag_sq:
                continue
            pt = self._sq_to_pt(s)
            self._paint_piece_at(p, piece, pt.x(), pt.y(), c)

        # Animated piece (lerp)
        if self._anim_from is not None and self._anim_piece and self._anim_t < 1.0:
            p1 = self._sq_to_pt(self._anim_from)
            p2 = self._sq_to_pt(self._anim_to)
            t_ = self._ease_out(self._anim_t)
            x = int(p1.x() + (p2.x() - p1.x()) * t_)
            y = int(p1.y() + (p2.y() - p1.y()) * t_)
            self._paint_piece_at(p, self._anim_piece, x, y, c)

    def _paint_piece_at(self, p: QPainter, piece: Piece,
                        x: int, y: int, c: int) -> None:
        t = Theme.current()
        symbol = piece.symbol

        # Font — scale to cell
        font = QFont("Segoe UI Symbol", int(c * 0.68))
        font.setStyleStrategy(QFont.PreferAntialias)
        p.setFont(font)

        rect = QRect(x, y, c, c)

        # Subtle shadow pass
        p.setPen(QColor(0, 0, 0, 50 if Theme.is_dark() else 28))
        p.drawText(rect.adjusted(1, 2, 1, 2), Qt.AlignCenter, symbol)

        # Piece color
        if piece.color == Color.WHITE:
            fg = QColor(t.sq_light).lighter(125)
        else:
            fg = QColor(t.sq_dark).darker(160)

        p.setPen(fg)
        p.drawText(rect, Qt.AlignCenter, symbol)

    def _paint_coords(self, p: QPainter) -> None:
        t = Theme.current()
        c = self._cell
        ox, oy = self._ox, self._oy
        font = QFont("DM Mono, Consolas, monospace", 7)
        font.setWeight(QFont.Medium)
        p.setFont(font)

        files = "abcdefgh"
        for f in range(8):
            label = files[f if not self._flipped else 7 - f]
            is_light = f % 2 == 0
            col = QColor(t.sq_light if not is_light else t.sq_dark).darker(115)
            p.setPen(col)
            rx = ox + f * c
            p.drawText(QRect(rx, oy + 7 * c + c - 12, c, 12),
                       Qt.AlignRight | Qt.AlignBottom, label)

        for r in range(8):
            label = str(r + 1 if not self._flipped else 8 - r)
            display_r = 7 - r
            is_light = r % 2 == 0
            col = QColor(t.sq_light if not is_light else t.sq_dark).darker(115)
            p.setPen(col)
            p.drawText(QRect(ox + 1, oy + display_r * c + 1, 12, 12),
                       Qt.AlignLeft | Qt.AlignTop, label)

    @staticmethod
    def _ease_out(t: float) -> float:
        return 1 - (1 - t) ** 3

    # ── Mouse ─────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if not self._interactive or self._board is None:
            return
        if event.button() != Qt.LeftButton:
            return
        clicked = self._pt_to_sq(event.pos())
        if clicked is None:
            self.clear_selection(); return

        # Move on second click
        if self._selected_sq is not None and clicked in self._legal_dests:
            moves = [m for m in self._legal_moves
                     if m.from_sq == self._selected_sq and m.to_sq == clicked]
            if moves:
                move = next((m for m in moves
                             if m.promotion == PieceType.QUEEN or not m.is_promotion),
                            moves[0])
                self.move_requested.emit(move)
            self.clear_selection()
            return

        # Select piece
        piece = self._board.piece_at(clicked)
        if piece and piece.color == self._board.side_to_move:
            self._selected_sq = clicked
            self._legal_dests = {m.to_sq for m in self._legal_moves
                                 if m.from_sq == clicked}
            self.update()
        else:
            self.clear_selection()

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_sq is not None:
            released = self._pt_to_sq(event.pos())
            if released is not None and released in self._legal_dests:
                moves = [m for m in self._legal_moves
                         if m.from_sq == self._drag_sq and m.to_sq == released]
                if moves:
                    move = next((m for m in moves
                                 if m.promotion == PieceType.QUEEN or not m.is_promotion),
                                moves[0])
                    self.move_requested.emit(move)
            self._drag_sq = None
            self._drag_pos = None
            self.clear_selection()

    def mouseMoveEvent(self, event) -> None:
        if not self._interactive:
            return
        if event.buttons() & Qt.LeftButton:
            if self._drag_sq is None and self._selected_sq is not None:
                self._drag_sq  = self._selected_sq
                self._drag_pos = event.pos()
            elif self._drag_sq is not None:
                self._drag_pos = event.pos()
                self.update()
