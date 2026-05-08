"""
engine/zobrist.py
=================
Zobrist hashing for efficient position identification.

Each unique board position is assigned a 64-bit integer key by XOR-ing
pre-generated random numbers for every aspect of the position:
  - piece placement (piece × color × square)
  - side to move
  - castling rights (4 bits)
  - en-passant file (8 possible files)

Keys allow O(1) transposition-table lookups and repetition detection.
"""

import random
from engine.pieces import PieceType, Color

_RNG = random.Random(0xDEADBEEF_C0FFEE42)   # deterministic seed

def _r64() -> int:
    return _RNG.getrandbits(64)

# ─── Pre-generated Tables ─────────────────────────────────────────────────────

# PIECE_KEYS[color_index][piece_type_index][square]
# color_index: 0=WHITE, 1=BLACK
# piece_type_index: 1-6 (PieceType values)
PIECE_KEYS: list[list[list[int]]] = [
    [
        [_r64() for _ in range(64)]
        for _ in range(7)   # index 0 unused; 1-6 = PieceType
    ]
    for _ in range(2)       # 0=WHITE, 1=BLACK
]

SIDE_KEY: int = _r64()     # XOR when it's Black's turn

# Castling rights: 4 bits (WK, WQ, BK, BQ) → 16 distinct values
CASTLING_KEYS: list[int] = [_r64() for _ in range(16)]

# En-passant file: 0-7
EP_FILE_KEYS: list[int] = [_r64() for _ in range(8)]


# ─── Hashing Helpers ──────────────────────────────────────────────────────────

def piece_key(color: Color, piece_type: PieceType, square: int) -> int:
    color_idx = 0 if color == Color.WHITE else 1
    return PIECE_KEYS[color_idx][piece_type][square]

def side_key() -> int:
    return SIDE_KEY

def castling_key(rights: int) -> int:
    """rights is a 4-bit integer: bit0=WK, bit1=WQ, bit2=BK, bit3=BQ."""
    return CASTLING_KEYS[rights & 0xF]

def ep_key(ep_square: int | None) -> int:
    if ep_square is None:
        return 0
    return EP_FILE_KEYS[ep_square & 7]   # only file matters


# ─── Castling Rights Encoding ─────────────────────────────────────────────────

WK_CASTLE = 1   # White king-side
WQ_CASTLE = 2   # White queen-side
BK_CASTLE = 4   # Black king-side
BQ_CASTLE = 8   # Black queen-side

def encode_castling(rights: dict) -> int:
    """Convert {'WK':bool,'WQ':bool,'BK':bool,'BQ':bool} to 4-bit int."""
    bits = 0
    if rights.get("WK"): bits |= WK_CASTLE
    if rights.get("WQ"): bits |= WQ_CASTLE
    if rights.get("BK"): bits |= BK_CASTLE
    if rights.get("BQ"): bits |= BQ_CASTLE
    return bits
