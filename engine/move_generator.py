"""
engine/move_generator.py
========================
Full legal-move generation for all pieces.

Pipeline:
  1. generate_pseudo_legal_moves() — all moves ignoring check
  2. generate_legal_moves()        — filter out moves that leave king in check

Special moves handled:
  - Castling (with attack checks on intermediate squares)
  - En passant
  - Pawn promotion (all four promotion pieces)
  - Double pawn push
"""

from __future__ import annotations
from typing import Optional, Iterator

from engine.board import Board
from engine.moves import Move, MoveFlag, sq, rank_of, file_of
from engine.pieces import Piece, PieceType, Color


# ─── Move Generator ───────────────────────────────────────────────────────────

class MoveGenerator:
    """Stateless move generator — all methods are static or class methods."""

    # ── Public API ────────────────────────────────────────────────────────────

    @staticmethod
    def generate_legal_moves(board: Board) -> list[Move]:
        """Return all fully legal moves for the side to move."""
        pseudo = MoveGenerator._pseudo_legal(board)
        legal  = []
        for move in pseudo:
            board.push(move)
            # After pushing, side_to_move flipped — check the mover's king
            if not board.is_in_check(board.side_to_move.opponent()):
                legal.append(move)
            board.pop()
        return legal

    @staticmethod
    def generate_legal_moves_from(board: Board, from_sq: int) -> list[Move]:
        """Return legal moves for the piece on `from_sq`."""
        piece = board.piece_at(from_sq)
        if piece is None or piece.color != board.side_to_move:
            return []
        return [m for m in MoveGenerator.generate_legal_moves(board)
                if m.from_sq == from_sq]

    @staticmethod
    def has_any_legal_move(board: Board) -> bool:
        """Quick check — True if side to move has at least one legal move."""
        for move in MoveGenerator._pseudo_legal(board):
            board.push(move)
            in_check = board.is_in_check(board.side_to_move.opponent())
            board.pop()
            if not in_check:
                return True
        return False

    # ── Pseudo-Legal Generation ───────────────────────────────────────────────

    @staticmethod
    def _pseudo_legal(board: Board) -> list[Move]:
        moves: list[Move] = []
        color = board.side_to_move
        for from_sq, piece in board.pieces_of(color):
            pt = piece.piece_type
            if   pt == PieceType.PAWN:   MoveGenerator._pawn_moves(board, from_sq, piece, moves)
            elif pt == PieceType.KNIGHT: MoveGenerator._knight_moves(board, from_sq, piece, moves)
            elif pt == PieceType.BISHOP: MoveGenerator._sliding_moves(board, from_sq, piece, moves, diagonal=True,  straight=False)
            elif pt == PieceType.ROOK:   MoveGenerator._sliding_moves(board, from_sq, piece, moves, diagonal=False, straight=True)
            elif pt == PieceType.QUEEN:  MoveGenerator._sliding_moves(board, from_sq, piece, moves, diagonal=True,  straight=True)
            elif pt == PieceType.KING:   MoveGenerator._king_moves(board, from_sq, piece, moves)
        return moves

    # ── Pawn ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _pawn_moves(board: Board, from_sq: int, piece: Piece, moves: list) -> None:
        color   = piece.color
        rank    = rank_of(from_sq)
        file    = file_of(from_sq)
        fwd     = 1 if color == Color.WHITE else -1
        start_rank  = 1 if color == Color.WHITE else 6
        promo_rank  = 7 if color == Color.WHITE else 0

        # Single push
        to_sq = sq(rank + fwd, file)
        if 0 <= rank + fwd < 8 and board.is_empty(to_sq):
            if rank + fwd == promo_rank:
                MoveGenerator._add_promotions(from_sq, to_sq, piece, None, moves)
            else:
                moves.append(Move(from_sq, to_sq, piece, flag=MoveFlag.NORMAL))

            # Double push from start rank
            if rank == start_rank:
                to_sq2 = sq(rank + 2*fwd, file)
                if board.is_empty(to_sq2):
                    moves.append(Move(from_sq, to_sq2, piece, flag=MoveFlag.DOUBLE_PUSH))

        # Captures (diagonal)
        for df in (-1, 1):
            if not (0 <= file + df < 8):
                continue
            r2, f2 = rank + fwd, file + df
            if not (0 <= r2 < 8):
                continue
            cap_sq = sq(r2, f2)
            captured = board.piece_at(cap_sq)

            # Normal capture
            if captured and captured.color != color:
                if r2 == promo_rank:
                    MoveGenerator._add_promotions(from_sq, cap_sq, piece, captured, moves)
                else:
                    moves.append(Move(from_sq, cap_sq, piece, captured=captured))

            # En passant
            elif board.en_passant_sq == cap_sq:
                ep_pawn_sq = sq(rank, file + df)   # the captured pawn's square
                ep_pawn = board.piece_at(ep_pawn_sq)
                moves.append(Move(from_sq, cap_sq, piece,
                                  captured=ep_pawn, flag=MoveFlag.EN_PASSANT))

    @staticmethod
    def _add_promotions(from_sq: int, to_sq: int, piece: Piece,
                        captured: Optional[Piece], moves: list) -> None:
        for promo in (PieceType.QUEEN, PieceType.ROOK,
                      PieceType.BISHOP, PieceType.KNIGHT):
            moves.append(Move(from_sq, to_sq, piece,
                              captured=captured,
                              promotion=promo,
                              flag=MoveFlag.PROMOTION))

    # ── Knight ────────────────────────────────────────────────────────────────

    _KNIGHT_DELTAS = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]

    @staticmethod
    def _knight_moves(board: Board, from_sq: int, piece: Piece, moves: list) -> None:
        rank = rank_of(from_sq)
        file = file_of(from_sq)
        for dr, df in MoveGenerator._KNIGHT_DELTAS:
            r2, f2 = rank + dr, file + df
            if not (0 <= r2 < 8 and 0 <= f2 < 8):
                continue
            to_sq = sq(r2, f2)
            target = board.piece_at(to_sq)
            if target is None:
                moves.append(Move(from_sq, to_sq, piece))
            elif target.color != piece.color:
                moves.append(Move(from_sq, to_sq, piece, captured=target))

    # ── Sliding Pieces ────────────────────────────────────────────────────────

    _DIAG_DIRS   = [(-1,-1),(-1,1),(1,-1),(1,1)]
    _STRAIGHT_DIRS = [(-1,0),(1,0),(0,-1),(0,1)]

    @staticmethod
    def _sliding_moves(board: Board, from_sq: int, piece: Piece,
                       moves: list, diagonal: bool, straight: bool) -> None:
        rank = rank_of(from_sq)
        file = file_of(from_sq)
        dirs = []
        if diagonal: dirs.extend(MoveGenerator._DIAG_DIRS)
        if straight: dirs.extend(MoveGenerator._STRAIGHT_DIRS)

        for dr, df in dirs:
            r2, f2 = rank + dr, file + df
            while 0 <= r2 < 8 and 0 <= f2 < 8:
                to_sq = sq(r2, f2)
                target = board.piece_at(to_sq)
                if target is None:
                    moves.append(Move(from_sq, to_sq, piece))
                elif target.color != piece.color:
                    moves.append(Move(from_sq, to_sq, piece, captured=target))
                    break
                else:
                    break   # blocked by own piece
                r2 += dr; f2 += df

    # ── King ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _king_moves(board: Board, from_sq: int, piece: Piece, moves: list) -> None:
        rank = rank_of(from_sq)
        file = file_of(from_sq)
        color = piece.color

        for dr in (-1, 0, 1):
            for df in (-1, 0, 1):
                if dr == 0 and df == 0:
                    continue
                r2, f2 = rank + dr, file + df
                if not (0 <= r2 < 8 and 0 <= f2 < 8):
                    continue
                to_sq = sq(r2, f2)
                target = board.piece_at(to_sq)
                if target is None:
                    moves.append(Move(from_sq, to_sq, piece))
                elif target.color != color:
                    moves.append(Move(from_sq, to_sq, piece, captured=target))

        # Castling
        opp = color.opponent()
        if color == Color.WHITE:
            if (board.castling.get("WK") and
                    board.is_empty(5) and board.is_empty(6) and
                    not board.is_square_attacked(4, opp) and
                    not board.is_square_attacked(5, opp) and
                    not board.is_square_attacked(6, opp)):
                moves.append(Move(4, 6, piece, flag=MoveFlag.CASTLE_KINGSIDE))
            if (board.castling.get("WQ") and
                    board.is_empty(3) and board.is_empty(2) and board.is_empty(1) and
                    not board.is_square_attacked(4, opp) and
                    not board.is_square_attacked(3, opp) and
                    not board.is_square_attacked(2, opp)):
                moves.append(Move(4, 2, piece, flag=MoveFlag.CASTLE_QUEENSIDE))
        else:
            if (board.castling.get("BK") and
                    board.is_empty(61) and board.is_empty(62) and
                    not board.is_square_attacked(60, opp) and
                    not board.is_square_attacked(61, opp) and
                    not board.is_square_attacked(62, opp)):
                moves.append(Move(60, 62, piece, flag=MoveFlag.CASTLE_KINGSIDE))
            if (board.castling.get("BQ") and
                    board.is_empty(59) and board.is_empty(58) and board.is_empty(57) and
                    not board.is_square_attacked(60, opp) and
                    not board.is_square_attacked(59, opp) and
                    not board.is_square_attacked(58, opp)):
                moves.append(Move(60, 58, piece, flag=MoveFlag.CASTLE_QUEENSIDE))

    # ── Attack Maps ───────────────────────────────────────────────────────────

    @staticmethod
    def attacked_squares(board: Board, color: Color) -> set[int]:
        """Return all squares attacked by `color`."""
        attacked: set[int] = set()
        temp = Board.__new__(Board)
        temp.squares = board.squares
        for from_sq, piece in board.pieces_of(color):
            pt = piece.piece_type
            rank = rank_of(from_sq)
            file = file_of(from_sq)

            if pt == PieceType.PAWN:
                fwd = 1 if color == Color.WHITE else -1
                for df in (-1, 1):
                    r2, f2 = rank + fwd, file + df
                    if 0 <= r2 < 8 and 0 <= f2 < 8:
                        attacked.add(sq(r2, f2))

            elif pt == PieceType.KNIGHT:
                for dr, df in MoveGenerator._KNIGHT_DELTAS:
                    r2, f2 = rank + dr, file + df
                    if 0 <= r2 < 8 and 0 <= f2 < 8:
                        attacked.add(sq(r2, f2))

            elif pt in (PieceType.BISHOP, PieceType.QUEEN):
                for dr, df in MoveGenerator._DIAG_DIRS:
                    r2, f2 = rank + dr, file + df
                    while 0 <= r2 < 8 and 0 <= f2 < 8:
                        s = sq(r2, f2)
                        attacked.add(s)
                        if board.squares[s] is not None:
                            break
                        r2 += dr; f2 += df

            if pt in (PieceType.ROOK, PieceType.QUEEN):
                for dr, df in MoveGenerator._STRAIGHT_DIRS:
                    r2, f2 = rank + dr, file + df
                    while 0 <= r2 < 8 and 0 <= f2 < 8:
                        s = sq(r2, f2)
                        attacked.add(s)
                        if board.squares[s] is not None:
                            break
                        r2 += dr; f2 += df

            elif pt == PieceType.KING:
                for dr in (-1, 0, 1):
                    for df in (-1, 0, 1):
                        if dr == 0 and df == 0:
                            continue
                        r2, f2 = rank + dr, file + df
                        if 0 <= r2 < 8 and 0 <= f2 < 8:
                            attacked.add(sq(r2, f2))

        return attacked
