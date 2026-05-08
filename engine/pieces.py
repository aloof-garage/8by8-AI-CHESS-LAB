"""
engine/pieces.py
================
Piece definitions, values, symbols, and piece-square tables (PSTs).

PSTs are indexed by square (rank*8 + file), rank 0 = a1-h1.
White uses PST directly; Black XORs square with 56 to mirror vertically.
"""

from enum import IntEnum
from dataclasses import dataclass
from typing import Optional


# ─── Colors ──────────────────────────────────────────────────────────────────

class Color(IntEnum):
    WHITE = 1
    BLACK = -1

    def opponent(self) -> "Color":
        return Color.BLACK if self == Color.WHITE else Color.WHITE

    def __str__(self) -> str:
        return "White" if self == Color.WHITE else "Black"


# ─── Piece Types ─────────────────────────────────────────────────────────────

class PieceType(IntEnum):
    PAWN   = 1
    KNIGHT = 2
    BISHOP = 3
    ROOK   = 4
    QUEEN  = 5
    KING   = 6


# ─── Material Values (centipawns) ─────────────────────────────────────────────

PIECE_VALUES: dict[PieceType, int] = {
    PieceType.PAWN:   100,
    PieceType.KNIGHT: 320,
    PieceType.BISHOP: 330,
    PieceType.ROOK:   500,
    PieceType.QUEEN:  900,
    PieceType.KING:   20_000,
}

# ─── Unicode Symbols ──────────────────────────────────────────────────────────

PIECE_UNICODE: dict[tuple, str] = {
    (Color.WHITE, PieceType.KING):   "♔",
    (Color.WHITE, PieceType.QUEEN):  "♕",
    (Color.WHITE, PieceType.ROOK):   "♖",
    (Color.WHITE, PieceType.BISHOP): "♗",
    (Color.WHITE, PieceType.KNIGHT): "♘",
    (Color.WHITE, PieceType.PAWN):   "♙",
    (Color.BLACK, PieceType.KING):   "♚",
    (Color.BLACK, PieceType.QUEEN):  "♛",
    (Color.BLACK, PieceType.ROOK):   "♜",
    (Color.BLACK, PieceType.BISHOP): "♝",
    (Color.BLACK, PieceType.KNIGHT): "♞",
    (Color.BLACK, PieceType.PAWN):   "♟",
}

PIECE_LETTERS: dict[tuple, str] = {
    (Color.WHITE, PieceType.KING):   "K",
    (Color.WHITE, PieceType.QUEEN):  "Q",
    (Color.WHITE, PieceType.ROOK):   "R",
    (Color.WHITE, PieceType.BISHOP): "B",
    (Color.WHITE, PieceType.KNIGHT): "N",
    (Color.WHITE, PieceType.PAWN):   "P",
    (Color.BLACK, PieceType.KING):   "k",
    (Color.BLACK, PieceType.QUEEN):  "q",
    (Color.BLACK, PieceType.ROOK):   "r",
    (Color.BLACK, PieceType.BISHOP): "b",
    (Color.BLACK, PieceType.KNIGHT): "n",
    (Color.BLACK, PieceType.PAWN):   "p",
}

# ─── Piece-Square Tables ──────────────────────────────────────────────────────
# Values in centipawns, from White's perspective.
# Square index = rank*8 + file, rank 0 = a1..h1, rank 7 = a8..h8.
# Black mirrors: access PST at (sq ^ 56).

PAWN_PST = [
     0,  0,  0,  0,  0,  0,  0,  0,   # rank 1
     5, 10, 10,-20,-20, 10, 10,  5,   # rank 2
     5, -5,-10,  0,  0,-10, -5,  5,   # rank 3
     0,  0,  0, 20, 20,  0,  0,  0,   # rank 4
     5,  5, 10, 25, 25, 10,  5,  5,   # rank 5
    10, 10, 20, 30, 30, 20, 10, 10,   # rank 6
    50, 50, 50, 50, 50, 50, 50, 50,   # rank 7
     0,  0,  0,  0,  0,  0,  0,  0,   # rank 8
]

KNIGHT_PST = [
    -50,-40,-30,-30,-30,-30,-40,-50,  # rank 1
    -40,-20,  0,  5,  5,  0,-20,-40,  # rank 2
    -30,  5, 10, 15, 15, 10,  5,-30,  # rank 3
    -30,  0, 15, 20, 20, 15,  0,-30,  # rank 4
    -30,  5, 15, 20, 20, 15,  5,-30,  # rank 5
    -30,  0, 10, 15, 15, 10,  0,-30,  # rank 6
    -40,-20,  0,  0,  0,  0,-20,-40,  # rank 7
    -50,-40,-30,-30,-30,-30,-40,-50,  # rank 8
]

BISHOP_PST = [
    -20,-10,-10,-10,-10,-10,-10,-20,  # rank 1
    -10,  5,  0,  0,  0,  0,  5,-10,  # rank 2
    -10, 10, 10, 10, 10, 10, 10,-10,  # rank 3
    -10,  0, 10, 10, 10, 10,  0,-10,  # rank 4
    -10,  5,  5, 10, 10,  5,  5,-10,  # rank 5
    -10,  0,  5, 10, 10,  5,  0,-10,  # rank 6
    -10,  0,  0,  0,  0,  0,  0,-10,  # rank 7
    -20,-10,-10,-10,-10,-10,-10,-20,  # rank 8
]

ROOK_PST = [
     0,  0,  0,  5,  5,  0,  0,  0,  # rank 1
    -5,  0,  0,  0,  0,  0,  0, -5,  # rank 2
    -5,  0,  0,  0,  0,  0,  0, -5,  # rank 3
    -5,  0,  0,  0,  0,  0,  0, -5,  # rank 4
    -5,  0,  0,  0,  0,  0,  0, -5,  # rank 5
    -5,  0,  0,  0,  0,  0,  0, -5,  # rank 6
     5, 10, 10, 10, 10, 10, 10,  5,  # rank 7
     0,  0,  0,  0,  0,  0,  0,  0,  # rank 8
]

QUEEN_PST = [
    -20,-10,-10, -5, -5,-10,-10,-20,  # rank 1
    -10,  0,  5,  0,  0,  0,  0,-10,  # rank 2
    -10,  5,  5,  5,  5,  5,  0,-10,  # rank 3
      0,  0,  5,  5,  5,  5,  0, -5,  # rank 4
     -5,  0,  5,  5,  5,  5,  0, -5,  # rank 5
    -10,  0,  5,  5,  5,  5,  0,-10,  # rank 6
    -10,  0,  0,  0,  0,  0,  0,-10,  # rank 7
    -20,-10,-10, -5, -5,-10,-10,-20,  # rank 8
]

KING_MIDDLEGAME_PST = [
     20, 30, 10,  0,  0, 10, 30, 20,  # rank 1
     20, 20,  0,  0,  0,  0, 20, 20,  # rank 2
    -10,-20,-20,-20,-20,-20,-20,-10,  # rank 3
    -20,-30,-30,-40,-40,-30,-30,-20,  # rank 4
    -30,-40,-40,-50,-50,-40,-40,-30,  # rank 5
    -30,-40,-40,-50,-50,-40,-40,-30,  # rank 6
    -30,-40,-40,-50,-50,-40,-40,-30,  # rank 7
    -30,-40,-40,-50,-50,-40,-40,-30,  # rank 8
]

KING_ENDGAME_PST = [
    -50,-30,-30,-30,-30,-30,-30,-50,  # rank 1
    -30,-30,  0,  0,  0,  0,-30,-30,  # rank 2
    -30,-10, 20, 30, 30, 20,-10,-30,  # rank 3
    -30,-10, 30, 40, 40, 30,-10,-30,  # rank 4
    -30,-10, 30, 40, 40, 30,-10,-30,  # rank 5
    -30,-10, 20, 30, 30, 20,-10,-30,  # rank 6
    -30,-20,-10,  0,  0,-10,-20,-30,  # rank 7
    -50,-40,-30,-20,-20,-30,-40,-50,  # rank 8
]

# Map PieceType → PST (for non-king pieces)
PST_MAP: dict[PieceType, list[int]] = {
    PieceType.PAWN:   PAWN_PST,
    PieceType.KNIGHT: KNIGHT_PST,
    PieceType.BISHOP: BISHOP_PST,
    PieceType.ROOK:   ROOK_PST,
    PieceType.QUEEN:  QUEEN_PST,
}


def get_pst_value(piece_type: PieceType, color: Color, square: int,
                  is_endgame: bool = False) -> int:
    """Return positional bonus for a piece on a given square."""
    mirrored_sq = square ^ 56 if color == Color.BLACK else square

    if piece_type == PieceType.KING:
        table = KING_ENDGAME_PST if is_endgame else KING_MIDDLEGAME_PST
        return table[mirrored_sq]

    table = PST_MAP.get(piece_type)
    if table is None:
        return 0
    return table[mirrored_sq]


# ─── Piece Dataclass ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Piece:
    color: Color
    piece_type: PieceType

    @property
    def value(self) -> int:
        return PIECE_VALUES[self.piece_type]

    @property
    def symbol(self) -> str:
        return PIECE_UNICODE[(self.color, self.piece_type)]

    @property
    def letter(self) -> str:
        return PIECE_LETTERS[(self.color, self.piece_type)]

    def __repr__(self) -> str:
        return f"{self.color.name[0]}{self.piece_type.name[:2]}"

    def __str__(self) -> str:
        return self.symbol


# ─── Convenience constants ────────────────────────────────────────────────────

W_PAWN   = Piece(Color.WHITE, PieceType.PAWN)
W_KNIGHT = Piece(Color.WHITE, PieceType.KNIGHT)
W_BISHOP = Piece(Color.WHITE, PieceType.BISHOP)
W_ROOK   = Piece(Color.WHITE, PieceType.ROOK)
W_QUEEN  = Piece(Color.WHITE, PieceType.QUEEN)
W_KING   = Piece(Color.WHITE, PieceType.KING)

B_PAWN   = Piece(Color.BLACK, PieceType.PAWN)
B_KNIGHT = Piece(Color.BLACK, PieceType.KNIGHT)
B_BISHOP = Piece(Color.BLACK, PieceType.BISHOP)
B_ROOK   = Piece(Color.BLACK, PieceType.ROOK)
B_QUEEN  = Piece(Color.BLACK, PieceType.QUEEN)
B_KING   = Piece(Color.BLACK, PieceType.KING)
