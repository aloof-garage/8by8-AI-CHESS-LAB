"""
engine/board.py
===============
Core board representation and state management.

The board is a flat list of 64 Optional[Piece] cells,
indexed rank-major: square = rank*8 + file (a1=0, h1=7, a8=56, h8=63).

Responsibilities:
  - Store piece positions
  - Track castling rights, en-passant square, clocks
  - Execute / undo moves
  - Clone the board for search
  - Maintain Zobrist hash for transposition / repetition
  - Detect check, material count, game-phase
"""

from __future__ import annotations
from copy import deepcopy
from typing import Optional

from engine.pieces import (
    Piece, PieceType, Color,
    W_PAWN, W_KNIGHT, W_BISHOP, W_ROOK, W_QUEEN, W_KING,
    B_PAWN, B_KNIGHT, B_BISHOP, B_ROOK, B_QUEEN, B_KING,
)
from engine.moves import Move, MoveFlag, HistoryEntry, sq, rank_of, file_of
from engine.zobrist import (
    piece_key, side_key, castling_key, ep_key,
    encode_castling, WK_CASTLE, WQ_CASTLE, BK_CASTLE, BQ_CASTLE,
)


# ─── Initial Position ─────────────────────────────────────────────────────────

_START_PIECES: list[tuple[int, Piece]] = [
    # White back rank
    (0,  W_ROOK), (1,  W_KNIGHT), (2,  W_BISHOP), (3,  W_QUEEN),
    (4,  W_KING), (5,  W_BISHOP), (6,  W_KNIGHT), (7,  W_ROOK),
    # White pawns
    *[(8+i, W_PAWN) for i in range(8)],
    # Black pawns
    *[(48+i, B_PAWN) for i in range(8)],
    # Black back rank
    (56, B_ROOK), (57, B_KNIGHT), (58, B_BISHOP), (59, B_QUEEN),
    (60, B_KING), (61, B_BISHOP), (62, B_KNIGHT), (63, B_ROOK),
]


class Board:
    """Full chess board state."""

    # ── Construction ──────────────────────────────────────────────────────────

    def __init__(self) -> None:
        self.squares: list[Optional[Piece]] = [None] * 64
        self.side_to_move: Color = Color.WHITE
        self.castling: dict[str, bool] = {
            "WK": True, "WQ": True, "BK": True, "BQ": True
        }
        self.en_passant_sq: Optional[int] = None
        self.halfmove_clock: int = 0        # for 50-move rule
        self.fullmove_number: int = 1

        self.history: list[HistoryEntry] = []
        self.position_counts: dict[int, int] = {}  # Zobrist key → count

        # Piece lists for fast iteration
        self._white_king_sq: int = 4
        self._black_king_sq: int = 60

        self.zobrist_key: int = 0

        self._setup_start()

    def _setup_start(self) -> None:
        for s, piece in _START_PIECES:
            self.squares[s] = piece
        self._white_king_sq = 4
        self._black_king_sq = 60
        self.zobrist_key = self._compute_zobrist()
        self.position_counts[self.zobrist_key] = 1

    def _compute_zobrist(self) -> int:
        key = 0
        for s, piece in enumerate(self.squares):
            if piece:
                key ^= piece_key(piece.color, piece.piece_type, s)
        if self.side_to_move == Color.BLACK:
            key ^= side_key()
        key ^= castling_key(encode_castling(self.castling))
        key ^= ep_key(self.en_passant_sq)
        return key

    # ── Accessors ─────────────────────────────────────────────────────────────

    def piece_at(self, square: int) -> Optional[Piece]:
        return self.squares[square]

    def king_square(self, color: Color) -> int:
        return self._white_king_sq if color == Color.WHITE else self._black_king_sq

    def is_empty(self, square: int) -> bool:
        return self.squares[square] is None

    def pieces_of(self, color: Color) -> list[tuple[int, Piece]]:
        """Return list of (square, piece) for all pieces of given color."""
        return [(s, p) for s, p in enumerate(self.squares)
                if p is not None and p.color == color]

    def all_pieces(self) -> list[tuple[int, Piece]]:
        return [(s, p) for s, p in enumerate(self.squares) if p is not None]

    # ── Internal Helpers ──────────────────────────────────────────────────────

    def _place(self, square: int, piece: Optional[Piece]) -> None:
        """Place or remove a piece, updating Zobrist hash."""
        old = self.squares[square]
        if old:
            self.zobrist_key ^= piece_key(old.color, old.piece_type, square)
        self.squares[square] = piece
        if piece:
            self.zobrist_key ^= piece_key(piece.color, piece.piece_type, square)
            if piece.piece_type == PieceType.KING:
                if piece.color == Color.WHITE:
                    self._white_king_sq = square
                else:
                    self._black_king_sq = square

    def _set_ep(self, ep_sq: Optional[int]) -> None:
        self.zobrist_key ^= ep_key(self.en_passant_sq)
        self.en_passant_sq = ep_sq
        self.zobrist_key ^= ep_key(self.en_passant_sq)

    def _update_castling(self, new_rights: dict) -> None:
        self.zobrist_key ^= castling_key(encode_castling(self.castling))
        self.castling = dict(new_rights)
        self.zobrist_key ^= castling_key(encode_castling(self.castling))

    # ── Move Execution ────────────────────────────────────────────────────────

    def push(self, move: Move, san: str = "") -> None:
        """Execute move, saving undo state to history."""
        entry = HistoryEntry(
            move=move,
            castling_rights=dict(self.castling),
            en_passant_sq=self.en_passant_sq,
            halfmove_clock=self.halfmove_clock,
            fullmove_number=self.fullmove_number,
            position_key=self.zobrist_key,
            san=san,
        )
        self.history.append(entry)

        # Toggle side in Zobrist
        self.zobrist_key ^= side_key()

        # Clear old EP target
        self._set_ep(None)

        moving_piece = self.squares[move.from_sq]
        assert moving_piece is not None, f"No piece on {move.from_sq}"

        # 50-move clock
        if move.is_capture or moving_piece.piece_type == PieceType.PAWN:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        flag = move.flag

        # ── Castling ──────────────────────────────────────────────────────────
        if flag == MoveFlag.CASTLE_KINGSIDE:
            self._execute_castle(move.piece.color, kingside=True)
        elif flag == MoveFlag.CASTLE_QUEENSIDE:
            self._execute_castle(move.piece.color, kingside=False)

        # ── En Passant ────────────────────────────────────────────────────────
        elif flag == MoveFlag.EN_PASSANT:
            self._place(move.from_sq, None)
            self._place(move.to_sq, moving_piece)
            # Remove captured pawn
            ep_pawn_sq = move.to_sq + (-8 if move.piece.color == Color.WHITE else 8)
            self._place(ep_pawn_sq, None)

        # ── Promotion ─────────────────────────────────────────────────────────
        elif flag == MoveFlag.PROMOTION:
            promo_type = move.promotion or PieceType.QUEEN
            promoted = Piece(move.piece.color, promo_type)
            self._place(move.from_sq, None)
            self._place(move.to_sq, promoted)

        # ── Normal / Double Push ──────────────────────────────────────────────
        else:
            self._place(move.from_sq, None)
            self._place(move.to_sq, moving_piece)

            if flag == MoveFlag.DOUBLE_PUSH:
                # Set en-passant target square (behind the pawn)
                direction = -8 if moving_piece.color == Color.WHITE else 8
                self._set_ep(move.to_sq + direction)

        # ── Update castling rights ────────────────────────────────────────────
        new_castling = dict(self.castling)
        self._revoke_castling_rights(new_castling, move)
        self._update_castling(new_castling)

        # ── Fullmove counter ──────────────────────────────────────────────────
        if self.side_to_move == Color.BLACK:
            self.fullmove_number += 1

        self.side_to_move = self.side_to_move.opponent()

        # Record position for repetition detection
        self.position_counts[self.zobrist_key] = \
            self.position_counts.get(self.zobrist_key, 0) + 1

    def _execute_castle(self, color: Color, kingside: bool) -> None:
        if color == Color.WHITE:
            king_from, king_to = 4, (6 if kingside else 2)
            rook_from, rook_to = (7 if kingside else 0), (5 if kingside else 3)
        else:
            king_from, king_to = 60, (62 if kingside else 58)
            rook_from, rook_to = (63 if kingside else 56), (61 if kingside else 59)

        king = self.squares[king_from]
        rook = self.squares[rook_from]
        self._place(king_from, None)
        self._place(rook_from, None)
        self._place(king_to, king)
        self._place(rook_to, rook)

    def _revoke_castling_rights(self, rights: dict, move: Move) -> None:
        """Remove castling rights based on king/rook movement or capture."""
        fq = move.from_sq
        tq = move.to_sq
        # King moves
        if fq == 4:  rights["WK"] = rights["WQ"] = False
        if fq == 60: rights["BK"] = rights["BQ"] = False
        # Rook moves
        if fq == 7  or tq == 7:  rights["WK"] = False
        if fq == 0  or tq == 0:  rights["WQ"] = False
        if fq == 63 or tq == 63: rights["BK"] = False
        if fq == 56 or tq == 56: rights["BQ"] = False

    # ── Move Undo ─────────────────────────────────────────────────────────────

    def pop(self) -> Move:
        """Undo the last move and restore board state."""
        if not self.history:
            raise IndexError("No moves to undo")

        entry = self.history.pop()
        move = entry.move

        # Decrement position count
        cnt = self.position_counts.get(self.zobrist_key, 1)
        if cnt <= 1:
            self.position_counts.pop(self.zobrist_key, None)
        else:
            self.position_counts[self.zobrist_key] = cnt - 1

        # Restore castling, EP, clocks (Zobrist restored by recomputing)
        self.castling = entry.castling_rights
        self.en_passant_sq = entry.en_passant_sq
        self.halfmove_clock = entry.halfmove_clock
        self.fullmove_number = entry.fullmove_number
        self.side_to_move = self.side_to_move.opponent()
        self.zobrist_key = entry.position_key

        flag = move.flag

        if flag == MoveFlag.CASTLE_KINGSIDE:
            self._undo_castle(move.piece.color, kingside=True)
        elif flag == MoveFlag.CASTLE_QUEENSIDE:
            self._undo_castle(move.piece.color, kingside=False)
        elif flag == MoveFlag.EN_PASSANT:
            self.squares[move.to_sq] = None
            self.squares[move.from_sq] = move.piece
            ep_pawn_sq = move.to_sq + (-8 if move.piece.color == Color.WHITE else 8)
            self.squares[ep_pawn_sq] = move.captured
            # Restore king squares
            self._sync_king_squares()
        elif flag == MoveFlag.PROMOTION:
            self.squares[move.to_sq] = move.captured
            self.squares[move.from_sq] = move.piece
            self._sync_king_squares()
        else:
            self.squares[move.from_sq] = move.piece
            self.squares[move.to_sq] = move.captured
            self._sync_king_squares()

        return move

    def _undo_castle(self, color: Color, kingside: bool) -> None:
        if color == Color.WHITE:
            king_from, king_to = 4, (6 if kingside else 2)
            rook_from, rook_to = (7 if kingside else 0), (5 if kingside else 3)
        else:
            king_from, king_to = 60, (62 if kingside else 58)
            rook_from, rook_to = (63 if kingside else 56), (61 if kingside else 59)

        king = self.squares[king_to]
        rook = self.squares[rook_to]
        self.squares[king_to] = None
        self.squares[rook_to] = None
        self.squares[king_from] = king
        self.squares[rook_from] = rook
        self._sync_king_squares()

    def _sync_king_squares(self) -> None:
        for s, p in enumerate(self.squares):
            if p and p.piece_type == PieceType.KING:
                if p.color == Color.WHITE:
                    self._white_king_sq = s
                else:
                    self._black_king_sq = s

    # ── Attack Detection ──────────────────────────────────────────────────────

    def is_square_attacked(self, square: int, by_color: Color) -> bool:
        """Return True if `square` is attacked by any piece of `by_color`."""
        opp = by_color

        # Pawn attacks
        pawn_dir = -1 if opp == Color.WHITE else 1  # direction attacker's pawn moves
        rank = rank_of(square)
        file = file_of(square)
        for df in (-1, 1):
            r2 = rank + pawn_dir
            f2 = file + df
            if 0 <= r2 < 8 and 0 <= f2 < 8:
                p = self.squares[sq(r2, f2)]
                if p and p.color == opp and p.piece_type == PieceType.PAWN:
                    return True

        # Knight attacks
        for dr, df in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
            r2, f2 = rank+dr, file+df
            if 0 <= r2 < 8 and 0 <= f2 < 8:
                p = self.squares[sq(r2, f2)]
                if p and p.color == opp and p.piece_type == PieceType.KNIGHT:
                    return True

        # Sliding attacks (Bishop/Queen diagonals)
        for dr, df in [(-1,-1),(-1,1),(1,-1),(1,1)]:
            r2, f2 = rank+dr, file+df
            while 0 <= r2 < 8 and 0 <= f2 < 8:
                p = self.squares[sq(r2, f2)]
                if p:
                    if p.color == opp and p.piece_type in (PieceType.BISHOP, PieceType.QUEEN):
                        return True
                    break
                r2 += dr; f2 += df

        # Sliding attacks (Rook/Queen straights)
        for dr, df in [(-1,0),(1,0),(0,-1),(0,1)]:
            r2, f2 = rank+dr, file+df
            while 0 <= r2 < 8 and 0 <= f2 < 8:
                p = self.squares[sq(r2, f2)]
                if p:
                    if p.color == opp and p.piece_type in (PieceType.ROOK, PieceType.QUEEN):
                        return True
                    break
                r2 += dr; f2 += df

        # King attacks
        for dr in (-1, 0, 1):
            for df in (-1, 0, 1):
                if dr == 0 and df == 0:
                    continue
                r2, f2 = rank+dr, file+df
                if 0 <= r2 < 8 and 0 <= f2 < 8:
                    p = self.squares[sq(r2, f2)]
                    if p and p.color == opp and p.piece_type == PieceType.KING:
                        return True

        return False

    def is_in_check(self, color: Color) -> bool:
        return self.is_square_attacked(self.king_square(color), color.opponent())

    # ── Game Phase ────────────────────────────────────────────────────────────

    def game_phase(self) -> float:
        """
        Return 0.0 = full endgame, 1.0 = full middlegame.
        Based on remaining non-pawn material.
        """
        from engine.pieces import PIECE_VALUES
        total_material = (
            PIECE_VALUES[PieceType.QUEEN] * 2 +
            PIECE_VALUES[PieceType.ROOK]  * 4 +
            PIECE_VALUES[PieceType.BISHOP]* 4 +
            PIECE_VALUES[PieceType.KNIGHT]* 4
        )
        current = sum(
            PIECE_VALUES[p.piece_type]
            for _, p in self.all_pieces()
            if p.piece_type not in (PieceType.PAWN, PieceType.KING)
        )
        return min(1.0, current / total_material)

    # ── Clone ─────────────────────────────────────────────────────────────────

    def clone(self) -> Board:
        """Fast shallow clone for search (does NOT copy history)."""
        b = Board.__new__(Board)
        b.squares = list(self.squares)
        b.side_to_move = self.side_to_move
        b.castling = dict(self.castling)
        b.en_passant_sq = self.en_passant_sq
        b.halfmove_clock = self.halfmove_clock
        b.fullmove_number = self.fullmove_number
        b.history = []
        b.position_counts = dict(self.position_counts)
        b._white_king_sq = self._white_king_sq
        b._black_king_sq = self._black_king_sq
        b.zobrist_key = self.zobrist_key
        return b

    # ── FEN ───────────────────────────────────────────────────────────────────

    def to_fen(self) -> str:
        rows = []
        for rank in range(7, -1, -1):
            empty = 0
            row = ""
            for file in range(8):
                p = self.squares[sq(rank, file)]
                if p is None:
                    empty += 1
                else:
                    if empty:
                        row += str(empty)
                        empty = 0
                    row += p.letter
            if empty:
                row += str(empty)
            rows.append(row)
        board_str = "/".join(rows)

        side = "w" if self.side_to_move == Color.WHITE else "b"

        castle = ""
        if self.castling.get("WK"): castle += "K"
        if self.castling.get("WQ"): castle += "Q"
        if self.castling.get("BK"): castle += "k"
        if self.castling.get("BQ"): castle += "q"
        if not castle: castle = "-"

        from engine.moves import sq_to_alg
        ep = sq_to_alg(self.en_passant_sq) if self.en_passant_sq is not None else "-"

        return f"{board_str} {side} {castle} {ep} {self.halfmove_clock} {self.fullmove_number}"

    @staticmethod
    def from_fen(fen: str) -> Board:
        """Parse a FEN string and return a Board."""
        from engine.moves import alg_to_sq
        board = Board.__new__(Board)
        board.squares = [None] * 64
        board.history = []
        board.position_counts = {}

        parts = fen.strip().split()
        rows = parts[0].split("/")

        letter_map = {
            'P': W_PAWN,   'N': W_KNIGHT, 'B': W_BISHOP,
            'R': W_ROOK,   'Q': W_QUEEN,  'K': W_KING,
            'p': B_PAWN,   'n': B_KNIGHT, 'b': B_BISHOP,
            'r': B_ROOK,   'q': B_QUEEN,  'k': B_KING,
        }

        for rank_idx, row in enumerate(reversed(rows)):
            file_idx = 0
            for ch in row:
                if ch.isdigit():
                    file_idx += int(ch)
                else:
                    board.squares[sq(rank_idx, file_idx)] = letter_map[ch]
                    file_idx += 1

        board.side_to_move = Color.WHITE if parts[1] == "w" else Color.BLACK
        castle_str = parts[2]
        board.castling = {
            "WK": "K" in castle_str,
            "WQ": "Q" in castle_str,
            "BK": "k" in castle_str,
            "BQ": "q" in castle_str,
        }
        board.en_passant_sq = alg_to_sq(parts[3]) if parts[3] != "-" else None
        board.halfmove_clock = int(parts[4])
        board.fullmove_number = int(parts[5])

        board._white_king_sq = 4
        board._black_king_sq = 60
        board._sync_king_squares()
        board.zobrist_key = board._compute_zobrist()
        board.position_counts[board.zobrist_key] = 1
        return board

    # ── Debug ─────────────────────────────────────────────────────────────────

    def __str__(self) -> str:
        lines = []
        for rank in range(7, -1, -1):
            row = f"{rank+1} │"
            for file in range(8):
                p = self.squares[sq(rank, file)]
                row += f" {p.symbol if p else '·'}"
            lines.append(row)
        lines.append("  └─────────────────")
        lines.append("    a b c d e f g h")
        return "\n".join(lines)
