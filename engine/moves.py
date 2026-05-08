"""
engine/moves.py
===============
Move representation, flags, and algebraic notation helpers.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from engine.pieces import Piece, PieceType, Color


# ─── Move Flags ───────────────────────────────────────────────────────────────

class MoveFlag:
    NORMAL          = 0
    DOUBLE_PUSH     = 1   # pawn two-square advance
    EN_PASSANT      = 2   # en passant capture
    CASTLE_KINGSIDE = 3
    CASTLE_QUEENSIDE= 4
    PROMOTION       = 5


# ─── Square Helpers ───────────────────────────────────────────────────────────

def sq(rank: int, file: int) -> int:
    """Pack rank/file into a single square index 0-63."""
    return rank * 8 + file

def rank_of(square: int) -> int:
    return square >> 3

def file_of(square: int) -> int:
    return square & 7

def sq_to_alg(square: int) -> str:
    """Convert square index to algebraic notation (e.g. 0 -> 'a1')."""
    return "abcdefgh"[file_of(square)] + str(rank_of(square) + 1)

def alg_to_sq(notation: str) -> int:
    """Convert algebraic notation to square index (e.g. 'e4' -> 28)."""
    file = ord(notation[0]) - ord('a')
    rank = int(notation[1]) - 1
    return sq(rank, file)

def sq_name(square: int) -> str:
    return sq_to_alg(square)


# ─── Move Dataclass ───────────────────────────────────────────────────────────

@dataclass
class Move:
    """
    Represents a single chess move.

    Attributes:
        from_sq:          Source square index (0-63)
        to_sq:            Destination square index (0-63)
        piece:            The piece being moved
        captured:         Piece captured (None if quiet move)
        promotion:        Piece type for pawn promotion
        flag:             MoveFlag constant
        score:            Move ordering score (for search heuristics)
    """
    from_sq:    int
    to_sq:      int
    piece:      Piece
    captured:   Optional[Piece] = None
    promotion:  Optional[PieceType] = None
    flag:       int = MoveFlag.NORMAL
    score:      int = 0   # used internally for move ordering

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def is_capture(self) -> bool:
        return self.captured is not None

    @property
    def is_promotion(self) -> bool:
        return self.flag == MoveFlag.PROMOTION

    @property
    def is_castle(self) -> bool:
        return self.flag in (MoveFlag.CASTLE_KINGSIDE, MoveFlag.CASTLE_QUEENSIDE)

    @property
    def is_en_passant(self) -> bool:
        return self.flag == MoveFlag.EN_PASSANT

    @property
    def is_quiet(self) -> bool:
        return not self.is_capture and not self.is_promotion

    # ── Notation ──────────────────────────────────────────────────────────────

    def uci(self) -> str:
        """Return UCI-style move string, e.g. 'e2e4', 'e7e8q'."""
        promo = ""
        if self.is_promotion and self.promotion:
            promo = {
                PieceType.QUEEN:  "q",
                PieceType.ROOK:   "r",
                PieceType.BISHOP: "b",
                PieceType.KNIGHT: "n",
            }.get(self.promotion, "q")
        return sq_to_alg(self.from_sq) + sq_to_alg(self.to_sq) + promo

    def san_piece_prefix(self) -> str:
        if self.piece.piece_type == PieceType.PAWN:
            return ""
        return {
            PieceType.KNIGHT: "N",
            PieceType.BISHOP: "B",
            PieceType.ROOK:   "R",
            PieceType.QUEEN:  "Q",
            PieceType.KING:   "K",
        }.get(self.piece.piece_type, "")

    def to_san(self, board=None) -> str:
        """
        Return a simplified SAN string.
        For full disambiguation, board context is needed (passed as board).
        """
        if self.flag == MoveFlag.CASTLE_KINGSIDE:
            return "O-O"
        if self.flag == MoveFlag.CASTLE_QUEENSIDE:
            return "O-O-O"

        prefix = self.san_piece_prefix()
        capture_x = "x" if self.is_capture or self.is_en_passant else ""
        dest = sq_to_alg(self.to_sq)

        if self.piece.piece_type == PieceType.PAWN and self.is_capture:
            prefix = "abcdefgh"[file_of(self.from_sq)]

        promo = ""
        if self.is_promotion and self.promotion:
            promo = "=" + {
                PieceType.QUEEN:  "Q",
                PieceType.ROOK:   "R",
                PieceType.BISHOP: "B",
                PieceType.KNIGHT: "N",
            }.get(self.promotion, "Q")

        return f"{prefix}{capture_x}{dest}{promo}"

    # ── Equality / hashing ────────────────────────────────────────────────────

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Move):
            return False
        return (self.from_sq == other.from_sq and
                self.to_sq == other.to_sq and
                self.promotion == other.promotion)

    def __hash__(self) -> int:
        return hash((self.from_sq, self.to_sq, self.promotion))

    def __repr__(self) -> str:
        return f"Move({self.uci()})"

    def __str__(self) -> str:
        return self.uci()


# ─── Move History Entry ───────────────────────────────────────────────────────

@dataclass
class HistoryEntry:
    """Snapshot of all irreversible state before a move was made."""
    move:                   Move
    castling_rights:        dict          # copy of board castling rights
    en_passant_sq:          Optional[int] # ep target before move
    halfmove_clock:         int
    fullmove_number:        int
    position_key:           int           # Zobrist key before move
    san:                    str = ""
