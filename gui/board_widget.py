"""
gui/board_widget.py
===================
Interactive chessboard widget.

Features:
  - Beautiful rendered board (PySide6 QPainter)
  - Piece rendering with Unicode symbols and shadows
  - Square highlights: selected, legal moves, last move, check
  - Click-to-move interaction
  - Board flip support
  - Drag-and-drop move input
  - Attack heatmap overlay
  - Smooth animation for piece movement
"""

from __future__ import annotations

from typing import Optional, Callable
import math

from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, QRect, QPoint, QPropertyAnimation, QEasingCurve, Signal, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QRadialGradient,
    QLinearGradient, QPainterPath, QFontMetrics,
)

from engine.board import Board
from engine.moves import Move, rank_of, file_of, sq
from engine.pieces import Color, PieceType, Piece
from engine.move_generator import MoveGenerator
from gui.theme import Theme


# ─── Board Widget ─────────────────────────────────────────────────────────────

class BoardWidget(QWidget):
    """
    Renders the chessboard and handles click-to-move input.

    Signals:
        move_requested(Move) — emitted when the user clicks a valid move
    """

    move_requested = Signal(object)   # Move

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(400, 400)

        self._board:          Optional[Board]     = None
        self._legal_moves:    list[Move]          = []
        self._selected_sq:    Optional[int]       = None
        self._legal_dests:    set[int]            = set()
        self._last_move:      Optional[Move]      = None
        self._flipped:        bool                = False
        self._check_sq:       Optional[int]       = None
        self._show_heatmap:   bool                = False
        self._heatmap_color:  Optional[Color]     = None
        self._heatmap_data:   dict[int, int]      = {}   # sq → attack count
        self._interactive:    bool                = True
        self._show_coords:    bool                = True

        # Animation
        self._anim_from:  Optional[int]   = None
        self._anim_to:    Optional[int]   = None
        self._anim_piece: Optional[Piece] = None
        self._anim_t:     float           = 1.0  # 0-1 progress

        # Drag state
        self._drag_sq:    Optional[int]   = None
        self._drag_pos:   Optional[QPoint]= None

        self.setMouseTracking(True)

    # ── Public Interface ──────────────────────────────────────────────────────

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

    def set_interactive(self, value: bool) -> None:
        self._interactive = value

    def clear_selection(self) -> None:
        self._selected_sq  = None
        self._legal_dests  = set()
        self.update()

    def set_check_square(self, sq: Optional[int]) -> None:
        self._check_sq = sq
        self.update()

    def animate_move(self, move: Move, piece: Piece) -> None:
        self._anim_from  = move.from_sq
        self._anim_to    = move.to_sq
        self._anim_piece = piece
        self._anim_t     = 0.0

        timer = QTimer(self)
        timer.setInterval(16)   # ~60fps

        def _tick() -> None:
            self._anim_t += 0.08
            if self._anim_t >= 1.0:
                self._anim_t = 1.0
                timer.stop()
                self._anim_from = None
            self.update()

        timer.timeout.connect(_tick)
        timer.start()

    def set_heatmap(self, color: Optional[Color], data: dict[int, int]) -> None:
        self._show_heatmap  = color is not None
        self._heatmap_color = color
        self._heatmap_data  = data
        self.update()

    def clear_heatmap(self) -> None:
        self._show_heatmap = False
        self._heatmap_data = {}
        self.update()

    # ── Geometry Helpers ─────────────────────────────────────────────────────

    @property
    def _cell_size(self) -> int:
        return min(self.width(), self.height()) // 8

    @property
    def _board_offset_x(self) -> int:
        return (self.width() - self._cell_size * 8) // 2

    @property
    def _board_offset_y(self) -> int:
        return (self.height() - self._cell_size * 8) // 2

    def _sq_to_pixel(self, square: int) -> QPoint:
        """Top-left pixel of a square."""
        rank = rank_of(square)
        file = file_of(square)
        if self._flipped:
            display_rank = rank
            display_file = 7 - file
        else:
            display_rank = 7 - rank
            display_file = file
        x = self._board_offset_x + display_file * self._cell_size
        y = self._board_offset_y + display_rank * self._cell_size
        return QPoint(x, y)

    def _pixel_to_sq(self, pos: QPoint) -> Optional[int]:
        x = pos.x() - self._board_offset_x
        y = pos.y() - self._board_offset_y
        cell = self._cell_size
        if not (0 <= x < cell * 8 and 0 <= y < cell * 8):
            return None
        display_file = x // cell
        display_rank = y // cell
        if self._flipped:
            file = 7 - display_file
            rank = display_rank
        else:
            file = display_file
            rank = 7 - display_rank
        return sq(rank, file)

    # ── Painting ──────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        if self._board is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        self._draw_board(painter)
        self._draw_highlights(painter)
        if self._show_heatmap:
            self._draw_heatmap(painter)
        self._draw_pieces(painter)
        if self._drag_sq is not None and self._drag_pos:
            self._draw_dragged_piece(painter)
        if self._show_coords:
            self._draw_coordinates(painter)
        painter.end()

    def _draw_board(self, painter: QPainter) -> None:
        c = Theme.current()
        cell = self._cell_size
        ox, oy = self._board_offset_x, self._board_offset_y

        # Board shadow
        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(ox - 4, oy - 4,
                                   cell*8 + 8, cell*8 + 8, 6, 6)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 60))
        painter.drawPath(shadow_path)

        # Squares
        for rank in range(8):
            for file in range(8):
                square = sq(rank, file)
                p = self._sq_to_pixel(square)
                is_light = (rank + file) % 2 == 0
                color = QColor(c.board_light if is_light else c.board_dark)
                painter.fillRect(p.x(), p.y(), cell, cell, color)

    def _draw_highlights(self, painter: QPainter) -> None:
        c = Theme.current()
        cell = self._cell_size

        def fill_sq(square: int, color_str: str) -> None:
            p = self._sq_to_pixel(square)
            painter.fillRect(p.x(), p.y(), cell, cell, QColor(color_str))

        # Last move
        if self._last_move:
            fill_sq(self._last_move.from_sq, c.hl_last_from)
            fill_sq(self._last_move.to_sq,   c.hl_last_to)

        # Check
        if self._check_sq is not None:
            p = self._sq_to_pixel(self._check_sq)
            grad = QRadialGradient(
                p.x() + cell/2, p.y() + cell/2,
                cell * 0.7
            )
            grad.setColorAt(0.0, QColor(c.hl_check))
            grad.setColorAt(1.0, QColor(c.hl_check[:-2] + "00"))
            painter.fillRect(p.x(), p.y(), cell, cell, grad)

        # Selected square
        if self._selected_sq is not None:
            fill_sq(self._selected_sq, c.hl_selected)

        # Legal move destinations
        painter.setPen(Qt.NoPen)
        for dest in self._legal_dests:
            p = self._sq_to_pixel(dest)
            cx = p.x() + cell // 2
            cy = p.y() + cell // 2
            board_piece = self._board.piece_at(dest) if self._board else None
            if board_piece is not None:
                # Capture: ring highlight
                pen = QPen(QColor(c.hl_legal), 3)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(p.x() + 3, p.y() + 3, cell - 6, cell - 6)
                painter.setPen(Qt.NoPen)
            else:
                # Quiet: dot
                r = cell // 6
                painter.setBrush(QColor(c.hl_legal))
                painter.drawEllipse(cx - r, cy - r, r*2, r*2)

    def _draw_heatmap(self, painter: QPainter) -> None:
        cell = self._cell_size
        if not self._heatmap_data:
            return
        max_val = max(self._heatmap_data.values(), default=1)
        for square, val in self._heatmap_data.items():
            p = self._sq_to_pixel(square)
            alpha = int(180 * val / max_val)
            if self._heatmap_color == Color.WHITE:
                color = QColor(200, 220, 255, alpha)
            else:
                color = QColor(255, 100, 100, alpha)
            painter.fillRect(p.x(), p.y(), cell, cell, color)

    def _draw_pieces(self, painter: QPainter) -> None:
        if not self._board:
            return
        cell = self._cell_size

        for square, piece in self._board.all_pieces():
            # Skip animated piece at source
            if square == self._anim_from and self._anim_t < 1.0:
                continue
            # Skip dragged piece
            if square == self._drag_sq:
                continue
            p = self._sq_to_pixel(square)
            self._draw_piece(painter, piece, p.x(), p.y(), cell)

        # Draw animated piece (interpolated position)
        if self._anim_from is not None and self._anim_piece and self._anim_t < 1.0:
            p1 = self._sq_to_pixel(self._anim_from)
            p2 = self._sq_to_pixel(self._anim_to)
            t = self._ease_out_cubic(self._anim_t)
            x = p1.x() + (p2.x() - p1.x()) * t
            y = p1.y() + (p2.y() - p1.y()) * t
            self._draw_piece(painter, self._anim_piece, int(x), int(y), cell)

    def _draw_piece(self, painter: QPainter, piece: Piece,
                    x: int, y: int, cell: int) -> None:
        c = Theme.current()
        symbol = piece.symbol
        font_size = int(cell * 0.72)
        font = QFont("Segoe UI Symbol", font_size)
        font.setStyleStrategy(QFont.PreferAntialias)
        painter.setFont(font)

        # Shadow
        painter.setPen(QColor(0, 0, 0, 60))
        painter.drawText(QRect(x+2, y+2, cell, cell),
                         Qt.AlignCenter, symbol)

        # Piece
        piece_color = QColor(c.piece_white if piece.color == Color.WHITE
                             else c.piece_black)
        painter.setPen(piece_color)
        painter.drawText(QRect(x, y, cell, cell), Qt.AlignCenter, symbol)

    def _draw_dragged_piece(self, painter: QPainter) -> None:
        if not self._board or self._drag_sq is None:
            return
        piece = self._board.piece_at(self._drag_sq)
        if piece is None:
            return
        cell = self._cell_size
        pos = self._drag_pos
        self._draw_piece(painter, piece,
                         pos.x() - cell//2, pos.y() - cell//2,
                         cell)

    def _draw_coordinates(self, painter: QPainter) -> None:
        c = Theme.current()
        cell = self._cell_size
        ox, oy = self._board_offset_x, self._board_offset_y

        font = QFont("Segoe UI", 8, QFont.Bold)
        painter.setFont(font)

        files = "abcdefgh"
        for file in range(8):
            label = files[file if not self._flipped else 7-file]
            x = ox + file * cell + cell - 12
            y = oy + 8 * cell - 3
            is_light = file % 2 == 0
            color = QColor(c.board_dark if is_light else c.board_light)
            painter.setPen(color)
            painter.drawText(x, y, label)

        for rank in range(8):
            label = str(rank + 1 if not self._flipped else 8 - rank)
            x = ox + 3
            y = oy + (7 - rank) * cell + 14
            is_light = rank % 2 == 0
            color = QColor(c.board_dark if is_light else c.board_light)
            painter.setPen(color)
            painter.drawText(x, y, label)

    @staticmethod
    def _ease_out_cubic(t: float) -> float:
        return 1 - (1 - t) ** 3

    # ── Mouse Input ───────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if not self._interactive or self._board is None:
            return
        if event.button() != Qt.LeftButton:
            return

        clicked = self._pixel_to_sq(event.pos())
        if clicked is None:
            self.clear_selection()
            return

        # If a square is already selected, try to make a move
        if self._selected_sq is not None and clicked in self._legal_dests:
            # Find the matching move (handle promotions)
            moves = [m for m in self._legal_moves
                     if m.from_sq == self._selected_sq and m.to_sq == clicked]
            if moves:
                # If promotion, pick queen by default
                move = next((m for m in moves
                             if m.promotion == PieceType.QUEEN or not m.is_promotion),
                            moves[0])
                self.move_requested.emit(move)
            self.clear_selection()
            return

        # Select a piece
        piece = self._board.piece_at(clicked)
        if piece and piece.color == self._board.side_to_move:
            self._selected_sq = clicked
            self._legal_dests = {
                m.to_sq for m in self._legal_moves
                if m.from_sq == clicked
            }
            self.update()
        else:
            self.clear_selection()

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_sq is not None:
            released = self._pixel_to_sq(event.pos())
            if released is not None and released in self._legal_dests:
                moves = [m for m in self._legal_moves
                         if m.from_sq == self._drag_sq and m.to_sq == released]
                if moves:
                    move = next((m for m in moves
                                 if m.promotion == PieceType.QUEEN or not m.is_promotion),
                                moves[0])
                    self.move_requested.emit(move)
            self._drag_sq  = None
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
