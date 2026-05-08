"""
engine/game.py
==============
High-level game manager. Wraps Board + MoveGenerator + rule checking.

Tracks:
  - Current board state
  - Move history with SAN notation
  - Game result (checkmate / stalemate / draw)
  - Captured pieces per side
  - PGN export / import
"""

from __future__ import annotations
from enum import Enum, auto
from typing import Optional
from dataclasses import dataclass, field

from engine.board import Board
from engine.moves import Move, MoveFlag, sq_to_alg, alg_to_sq, sq
from engine.move_generator import MoveGenerator
from engine.pieces import Color, PieceType, Piece, PIECE_VALUES


# ─── Game Result ─────────────────────────────────────────────────────────────

class GameResult(Enum):
    ONGOING          = auto()
    CHECKMATE        = auto()
    STALEMATE        = auto()
    DRAW_50_MOVE     = auto()
    DRAW_REPETITION  = auto()
    DRAW_INSUFFICIENT= auto()
    DRAW_AGREED      = auto()
    RESIGN_WHITE     = auto()
    RESIGN_BLACK     = auto()

    def is_draw(self) -> bool:
        return self in (
            GameResult.STALEMATE,
            GameResult.DRAW_50_MOVE,
            GameResult.DRAW_REPETITION,
            GameResult.DRAW_INSUFFICIENT,
            GameResult.DRAW_AGREED,
        )

    def winner(self) -> Optional[Color]:
        if self == GameResult.CHECKMATE:
            return None  # determined by whose turn it WAS
        if self == GameResult.RESIGN_WHITE:
            return Color.BLACK
        if self == GameResult.RESIGN_BLACK:
            return Color.WHITE
        return None

    def display_text(self) -> str:
        return {
            GameResult.ONGOING:           "Game in progress",
            GameResult.CHECKMATE:         "Checkmate",
            GameResult.STALEMATE:         "Stalemate – Draw",
            GameResult.DRAW_50_MOVE:      "Draw by 50-move rule",
            GameResult.DRAW_REPETITION:   "Draw by threefold repetition",
            GameResult.DRAW_INSUFFICIENT: "Draw – insufficient material",
            GameResult.DRAW_AGREED:       "Draw by agreement",
            GameResult.RESIGN_WHITE:      "White resigned",
            GameResult.RESIGN_BLACK:      "Black resigned",
        }.get(self, "Unknown")


# ─── Move Record ─────────────────────────────────────────────────────────────

@dataclass
class MoveRecord:
    move:         Move
    san:          str
    fen_after:    str
    eval_score:   Optional[float] = None   # centipawn eval after move
    move_number:  int = 1
    color:        Color = Color.WHITE
    time_taken:   float = 0.0              # seconds


# ─── Game Manager ─────────────────────────────────────────────────────────────

class Game:
    """Central controller for a chess game session."""

    def __init__(self, fen: Optional[str] = None) -> None:
        if fen:
            self.board = Board.from_fen(fen)
        else:
            self.board = Board()

        self.move_records:   list[MoveRecord] = []
        self.result:         GameResult       = GameResult.ONGOING
        self.captured_white: list[Piece]      = []   # pieces White captured
        self.captured_black: list[Piece]      = []   # pieces Black captured
        self._legal_cache:   Optional[list[Move]] = None
        self._position_before_move: Optional[str] = None

    # ── Legal Move Access ─────────────────────────────────────────────────────

    def legal_moves(self) -> list[Move]:
        if self._legal_cache is None:
            self._legal_cache = MoveGenerator.generate_legal_moves(self.board)
        return self._legal_cache

    def legal_moves_from(self, from_sq: int) -> list[Move]:
        return [m for m in self.legal_moves() if m.from_sq == from_sq]

    def is_legal(self, move: Move) -> bool:
        return move in self.legal_moves()

    # ── Make Move ─────────────────────────────────────────────────────────────

    def push_move(self, move: Move, eval_score: Optional[float] = None,
                  time_taken: float = 0.0) -> bool:
        """
        Execute a move if legal. Returns True on success.
        Updates game result after move.
        """
        if self.result != GameResult.ONGOING:
            return False
        if not self.is_legal(move):
            return False

        san   = self._to_san(move)
        color = self.board.side_to_move
        num   = self.board.fullmove_number

        # Track captures
        if move.captured:
            if color == Color.WHITE:
                self.captured_white.append(move.captured)
            else:
                self.captured_black.append(move.captured)
        if move.is_en_passant and move.captured:
            if color == Color.WHITE:
                self.captured_white.append(move.captured)
            else:
                self.captured_black.append(move.captured)

        self.board.push(move, san=san)
        self._legal_cache = None

        fen = self.board.to_fen()
        record = MoveRecord(
            move=move, san=san, fen_after=fen,
            eval_score=eval_score,
            move_number=num, color=color,
            time_taken=time_taken,
        )
        self.move_records.append(record)

        self._update_result()
        return True

    def push_uci(self, uci: str) -> bool:
        """Push a move given in UCI notation (e.g. 'e2e4', 'e7e8q')."""
        from_sq = alg_to_sq(uci[:2])
        to_sq   = alg_to_sq(uci[2:4])
        promo_map = {"q": PieceType.QUEEN, "r": PieceType.ROOK,
                     "b": PieceType.BISHOP, "n": PieceType.KNIGHT}
        promo = promo_map.get(uci[4:5]) if len(uci) > 4 else None

        for move in self.legal_moves():
            if move.from_sq == from_sq and move.to_sq == to_sq:
                if promo is None or move.promotion == promo:
                    return self.push_move(move)
        return False

    # ── Undo ──────────────────────────────────────────────────────────────────

    def undo(self) -> bool:
        if not self.move_records:
            return False
        record = self.move_records.pop()
        self.board.pop()
        self._legal_cache = None
        self.result = GameResult.ONGOING

        # Restore capture lists
        if record.move.captured:
            color = record.color
            lst = self.captured_white if color == Color.WHITE else self.captured_black
            for i in range(len(lst)-1, -1, -1):
                if lst[i] == record.move.captured:
                    lst.pop(i)
                    break
        return True

    # ── Game Result Detection ─────────────────────────────────────────────────

    def _update_result(self) -> None:
        if self._has_no_legal_moves():
            if self.board.is_in_check(self.board.side_to_move):
                self.result = GameResult.CHECKMATE
            else:
                self.result = GameResult.STALEMATE
            return

        if self.board.halfmove_clock >= 100:
            self.result = GameResult.DRAW_50_MOVE
            return

        if self._is_repetition():
            self.result = GameResult.DRAW_REPETITION
            return

        if self._is_insufficient_material():
            self.result = GameResult.DRAW_INSUFFICIENT
            return

    def _has_no_legal_moves(self) -> bool:
        return len(self.legal_moves()) == 0

    def _is_repetition(self) -> bool:
        return self.board.position_counts.get(self.board.zobrist_key, 0) >= 3

    def _is_insufficient_material(self) -> bool:
        pieces = [(p.color, p.piece_type) for _, p in self.board.all_pieces()]
        types = [pt for _, pt in pieces]
        # Only kings
        if all(pt == PieceType.KING for pt in types):
            return True
        # King + bishop vs King or King + knight vs King
        non_kings = [(c, pt) for c, pt in pieces if pt != PieceType.KING]
        if len(non_kings) == 1:
            return non_kings[0][1] in (PieceType.BISHOP, PieceType.KNIGHT)
        # King + bishop vs King + bishop (same color squares)
        if len(non_kings) == 2:
            if all(pt == PieceType.BISHOP for _, pt in non_kings):
                sqs = [s for s, p in self.board.all_pieces()
                       if p.piece_type == PieceType.BISHOP]
                if len(sqs) == 2:
                    # Same color square
                    if (sqs[0] + sqs[0]//8) % 2 == (sqs[1] + sqs[1]//8) % 2:
                        return True
        return False

    def resign(self, color: Color) -> None:
        self.result = (GameResult.RESIGN_WHITE if color == Color.WHITE
                       else GameResult.RESIGN_BLACK)

    def offer_draw(self) -> None:
        self.result = GameResult.DRAW_AGREED

    # ── SAN Generation ────────────────────────────────────────────────────────

    def _to_san(self, move: Move) -> str:
        """Generate SAN string with check/checkmate suffixes."""
        from engine.moves import file_of, sq_to_alg

        if move.flag == MoveFlag.CASTLE_KINGSIDE:
            base = "O-O"
        elif move.flag == MoveFlag.CASTLE_QUEENSIDE:
            base = "O-O-O"
        else:
            piece = move.piece
            pt    = piece.piece_type
            color = piece.color

            prefix = "" if pt == PieceType.PAWN else {
                PieceType.KNIGHT: "N", PieceType.BISHOP: "B",
                PieceType.ROOK: "R",   PieceType.QUEEN:  "Q",
                PieceType.KING: "K",
            }[pt]

            # Disambiguation
            disambig = ""
            if pt != PieceType.PAWN:
                ambiguous = [
                    m for m in self.legal_moves()
                    if m.piece.piece_type == pt and m.to_sq == move.to_sq
                    and m.from_sq != move.from_sq
                ]
                if ambiguous:
                    from_files = {file_of(m.from_sq) for m in ambiguous}
                    from_ranks = {m.from_sq // 8 for m in ambiguous}
                    my_file = file_of(move.from_sq)
                    my_rank = move.from_sq // 8
                    if my_file not in from_files:
                        disambig = "abcdefgh"[my_file]
                    elif my_rank not in from_ranks:
                        disambig = str(my_rank + 1)
                    else:
                        disambig = sq_to_alg(move.from_sq)

            cap = "x" if move.is_capture or move.is_en_passant else ""
            if pt == PieceType.PAWN and cap:
                prefix = "abcdefgh"[file_of(move.from_sq)]

            dest = sq_to_alg(move.to_sq)
            promo = ""
            if move.is_promotion and move.promotion:
                promo = "=" + {
                    PieceType.QUEEN: "Q", PieceType.ROOK: "R",
                    PieceType.BISHOP: "B", PieceType.KNIGHT: "N",
                }[move.promotion]

            base = f"{prefix}{disambig}{cap}{dest}{promo}"

        # Test for check / checkmate
        self.board.push(move)
        legal_after = MoveGenerator.generate_legal_moves(self.board)
        in_check    = self.board.is_in_check(self.board.side_to_move)
        self.board.pop()

        if in_check:
            if len(legal_after) == 0:
                base += "#"
            else:
                base += "+"

        return base

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def side_to_move(self) -> Color:
        return self.board.side_to_move

    @property
    def is_in_check(self) -> bool:
        return self.board.is_in_check(self.board.side_to_move)

    @property
    def move_count(self) -> int:
        return len(self.move_records)

    def material_balance(self) -> int:
        """Return material balance in centipawns (positive = White ahead)."""
        total = 0
        for _, p in self.board.all_pieces():
            if p.piece_type != PieceType.KING:
                v = PIECE_VALUES[p.piece_type]
                total += v if p.color == Color.WHITE else -v
        return total

    def san_history(self) -> list[str]:
        return [r.san for r in self.move_records]

    # ── PGN Export ────────────────────────────────────────────────────────────

    def to_pgn(self, white_name: str = "White", black_name: str = "Black",
               event: str = "8by8 AI CHESS LAB") -> str:
        import datetime
        date_str = datetime.date.today().strftime("%Y.%m.%d")

        result_str = {
            GameResult.CHECKMATE:         ("1-0" if self.move_records and
                                           self.move_records[-1].color == Color.WHITE
                                           else "0-1"),
            GameResult.RESIGN_WHITE:      "0-1",
            GameResult.RESIGN_BLACK:      "1-0",
            GameResult.STALEMATE:         "1/2-1/2",
            GameResult.DRAW_50_MOVE:      "1/2-1/2",
            GameResult.DRAW_REPETITION:   "1/2-1/2",
            GameResult.DRAW_INSUFFICIENT: "1/2-1/2",
            GameResult.DRAW_AGREED:       "1/2-1/2",
            GameResult.ONGOING:           "*",
        }.get(self.result, "*")

        header = (
            f'[Event "{event}"]\n'
            f'[Date "{date_str}"]\n'
            f'[White "{white_name}"]\n'
            f'[Black "{black_name}"]\n'
            f'[Result "{result_str}"]\n\n'
        )

        moves_str = ""
        for i, record in enumerate(self.move_records):
            if record.color == Color.WHITE:
                moves_str += f"{record.move_number}. {record.san} "
            else:
                moves_str += f"{record.san} "

        return header + moves_str + result_str

    # ── Reset ──────────────────────────────────────────────────────────────────

    def reset(self) -> None:
        self.__init__()
