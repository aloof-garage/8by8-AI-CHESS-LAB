"""
ai/evaluator.py
===============
Advanced positional evaluation function.

Returns a score in centipawns from White's perspective.
Positive = White advantage, Negative = Black advantage.

Components:
  - Material balance
  - Piece-square table bonuses
  - Mobility (legal move count)
  - King safety (pawn shelter, open files near king, attack count)
  - Center control (occupation + influence)
  - Pawn structure (doubled, isolated, backward, passed)
  - Piece activity (rook open/semi-open files, bishop pair, knight outposts)
  - Endgame king activity
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from engine.board import Board
from engine.move_generator import MoveGenerator
from engine.pieces import (
    Piece, PieceType, Color,
    PIECE_VALUES, get_pst_value,
)
from engine.moves import sq, rank_of, file_of


# ─── Evaluation Breakdown ─────────────────────────────────────────────────────

@dataclass
class EvalBreakdown:
    total:        float = 0.0
    material:     float = 0.0
    position:     float = 0.0
    mobility:     float = 0.0
    king_safety:  float = 0.0
    center:       float = 0.0
    pawn_struct:  float = 0.0
    piece_activity: float = 0.0
    endgame:      float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "Total":          round(self.total        / 100, 2),
            "Material":       round(self.material     / 100, 2),
            "Position":       round(self.position     / 100, 2),
            "Mobility":       round(self.mobility     / 100, 2),
            "King Safety":    round(self.king_safety  / 100, 2),
            "Center Control": round(self.center       / 100, 2),
            "Pawn Structure": round(self.pawn_struct  / 100, 2),
            "Piece Activity": round(self.piece_activity/100, 2),
            "Endgame":        round(self.endgame      / 100, 2),
        }

    def summary(self) -> str:
        d = self.to_dict()
        lines = [f"{'Component':<18} {'Score':>7}"]
        lines.append("─" * 27)
        for k, v in d.items():
            sign = "+" if v >= 0 else ""
            lines.append(f"{k:<18} {sign}{v:>6.2f}")
        return "\n".join(lines)


# ─── Constants ────────────────────────────────────────────────────────────────

# Squares in the extended center (d4/d5/e4/e5 + surrounding ring)
_CENTER_SQUARES = {sq(3,3), sq(3,4), sq(4,3), sq(4,4)}
_EXTENDED_CENTER = {sq(r,f) for r in range(2,6) for f in range(2,6)}

_MOBILITY_WEIGHT   = 4    # cp per extra legal move
_CENTER_OCC_BONUS  = 15   # cp per center square occupied
_CENTER_INF_BONUS  = 3    # cp per center square attacked
_DOUBLED_PAWN_PEN  = -20
_ISOLATED_PAWN_PEN = -15
_BACKWARD_PAWN_PEN = -12
_PASSED_PAWN_BONUS = [0, 10, 20, 35, 55, 80, 120, 0]  # by rank (White)
_BISHOP_PAIR_BONUS = 30
_ROOK_OPEN_BONUS   = 20
_ROOK_SEMIOPEN_BONUS = 10
_OUTPOST_BONUS     = 18

# King safety: penalty per attacker near king zone
_KING_ATTACK_WEIGHT = 8
_OPEN_FILE_NEAR_KING_PEN = -25
_NO_CASTLE_PEN = -35


# ─── Evaluator ────────────────────────────────────────────────────────────────

class Evaluator:
    """Static evaluation of a chess position."""

    @staticmethod
    def evaluate(board: Board, detail: bool = False
                 ) -> tuple[int, Optional[EvalBreakdown]]:
        """
        Return (score, breakdown) from White's perspective.
        If detail=False, breakdown is None (faster).
        """
        bd = EvalBreakdown() if detail else None

        phase = board.game_phase()   # 1.0 = middlegame, 0.0 = endgame
        is_endgame = phase < 0.35

        # ── Collect piece data ────────────────────────────────────────────────
        white_pieces = board.pieces_of(Color.WHITE)
        black_pieces = board.pieces_of(Color.BLACK)

        # Material + PST
        mat  = 0
        pst  = 0
        for s, p in white_pieces:
            mat += PIECE_VALUES[p.piece_type]
            pst += get_pst_value(p.piece_type, Color.WHITE, s, is_endgame)
        for s, p in black_pieces:
            mat -= PIECE_VALUES[p.piece_type]
            pst -= get_pst_value(p.piece_type, Color.BLACK, s, is_endgame)

        if bd:
            bd.material = mat
            bd.position = pst

        # ── Mobility (pseudo-legal count for speed) ───────────────────────────
        white_moves = Evaluator._count_moves(board, Color.WHITE)
        black_moves = Evaluator._count_moves(board, Color.BLACK)
        mobility = (white_moves - black_moves) * _MOBILITY_WEIGHT
        if bd:
            bd.mobility = mobility

        # ── Center control ────────────────────────────────────────────────────
        center = Evaluator._center_control(board)
        if bd:
            bd.center = center

        # ── Pawn structure ────────────────────────────────────────────────────
        pawn_score = Evaluator._pawn_structure(board)
        if bd:
            bd.pawn_struct = pawn_score

        # ── King safety ───────────────────────────────────────────────────────
        king_safe = Evaluator._king_safety(board, phase)
        if bd:
            bd.king_safety = king_safe

        # ── Piece activity ────────────────────────────────────────────────────
        activity = Evaluator._piece_activity(board)
        if bd:
            bd.piece_activity = activity

        # ── Endgame bonuses ───────────────────────────────────────────────────
        eg_bonus = 0
        if is_endgame:
            eg_bonus = Evaluator._endgame_bonus(board)
        if bd:
            bd.endgame = eg_bonus

        total = mat + pst + mobility + center + pawn_score + king_safe + activity + eg_bonus
        if bd:
            bd.total = total
        return total, bd

    # ── Mobility Helper ───────────────────────────────────────────────────────

    @staticmethod
    def _count_moves(board: Board, color: Color) -> int:
        """Count pseudo-legal moves for a given color without legal filtering."""
        from engine.move_generator import MoveGenerator as MG
        count = 0
        for from_sq, piece in board.pieces_of(color):
            pt = piece.piece_type
            temp: list = []
            if   pt == PieceType.PAWN:   MG._pawn_moves(board, from_sq, piece, temp)
            elif pt == PieceType.KNIGHT: MG._knight_moves(board, from_sq, piece, temp)
            elif pt == PieceType.BISHOP: MG._sliding_moves(board, from_sq, piece, temp, True, False)
            elif pt == PieceType.ROOK:   MG._sliding_moves(board, from_sq, piece, temp, False, True)
            elif pt == PieceType.QUEEN:  MG._sliding_moves(board, from_sq, piece, temp, True, True)
            elif pt == PieceType.KING:   MG._king_moves(board, from_sq, piece, temp)
            count += len(temp)
        return count

    # ── Center Control ────────────────────────────────────────────────────────

    @staticmethod
    def _center_control(board: Board) -> int:
        score = 0
        w_attacks = MoveGenerator.attacked_squares(board, Color.WHITE)
        b_attacks = MoveGenerator.attacked_squares(board, Color.BLACK)

        for s in _CENTER_SQUARES:
            p = board.piece_at(s)
            if p:
                bonus = _CENTER_OCC_BONUS * (1 if p.color == Color.WHITE else -1)
                score += bonus

        for s in _EXTENDED_CENTER:
            if s in w_attacks:
                score += _CENTER_INF_BONUS
            if s in b_attacks:
                score -= _CENTER_INF_BONUS

        return score

    # ── Pawn Structure ────────────────────────────────────────────────────────

    @staticmethod
    def _pawn_structure(board: Board) -> int:
        score = 0
        w_pawn_files: list[list[int]] = [[] for _ in range(8)]
        b_pawn_files: list[list[int]] = [[] for _ in range(8)]

        for s, p in board.all_pieces():
            if p.piece_type == PieceType.PAWN:
                f = file_of(s)
                r = rank_of(s)
                if p.color == Color.WHITE:
                    w_pawn_files[f].append(r)
                else:
                    b_pawn_files[f].append(r)

        score += Evaluator._pawn_file_score(w_pawn_files, b_pawn_files, Color.WHITE)
        score -= Evaluator._pawn_file_score(b_pawn_files, w_pawn_files, Color.BLACK)
        return score

    @staticmethod
    def _pawn_file_score(own_files: list[list[int]],
                         opp_files: list[list[int]],
                         color: Color) -> int:
        score = 0
        for f, ranks in enumerate(own_files):
            if not ranks:
                continue
            # Doubled pawns
            if len(ranks) > 1:
                score += _DOUBLED_PAWN_PEN * (len(ranks) - 1)

            # Isolated pawns
            has_neighbor = (
                (f > 0 and own_files[f-1]) or
                (f < 7 and own_files[f+1])
            )
            if not has_neighbor:
                score += _ISOLATED_PAWN_PEN * len(ranks)

            # Passed & backward pawns
            for r in ranks:
                # Passed pawn: no opposing pawn ahead on same or adjacent files
                opp_ahead = False
                for ff in range(max(0, f-1), min(8, f+2)):
                    for opp_r in opp_files[ff]:
                        if color == Color.WHITE and opp_r > r:
                            opp_ahead = True
                        elif color == Color.BLACK and opp_r < r:
                            opp_ahead = True
                if not opp_ahead:
                    bonus_rank = r if color == Color.WHITE else (7 - r)
                    score += _PASSED_PAWN_BONUS[bonus_rank]

                # Backward pawn: behind all friendly pawns, can't advance safely
                support_ranks = []
                for ff in range(max(0, f-1), min(8, f+2)):
                    support_ranks.extend(own_files[ff])
                if support_ranks:
                    min_sup = min(support_ranks)
                    if color == Color.WHITE and r < min_sup:
                        score += _BACKWARD_PAWN_PEN
                    elif color == Color.BLACK and r > min_sup:
                        score += _BACKWARD_PAWN_PEN

        return score

    # ── King Safety ───────────────────────────────────────────────────────────

    @staticmethod
    def _king_safety(board: Board, phase: float) -> int:
        """King safety is most important in middlegame (phase ≈ 1)."""
        if phase < 0.1:
            return 0

        score = 0
        for color in (Color.WHITE, Color.BLACK):
            ks = board.king_square(color)
            kr, kf = rank_of(ks), file_of(ks)
            sign = 1 if color == Color.WHITE else -1
            opp  = color.opponent()
            opp_attacks = MoveGenerator.attacked_squares(board, opp)

            # Count attackers near king zone
            attack_count = 0
            for dr in range(-2, 3):
                for df in range(-2, 3):
                    r2, f2 = kr + dr, kf + df
                    if 0 <= r2 < 8 and 0 <= f2 < 8:
                        s = sq(r2, f2)
                        if s in opp_attacks:
                            attack_count += 1

            score -= sign * attack_count * _KING_ATTACK_WEIGHT * phase

            # Open files near king
            for df in range(-1, 2):
                f2 = kf + df
                if not (0 <= f2 < 8):
                    continue
                file_pawns = [
                    p for s, p in board.all_pieces()
                    if file_of(s) == f2 and p.piece_type == PieceType.PAWN
                    and p.color == color
                ]
                if not file_pawns:
                    score += sign * _OPEN_FILE_NEAR_KING_PEN * phase

            # Bonus for having castled (king on g/c file)
            home_rank = 0 if color == Color.WHITE else 7
            if kr != home_rank:
                score += sign * _NO_CASTLE_PEN * phase

        return int(score)

    # ── Piece Activity ────────────────────────────────────────────────────────

    @staticmethod
    def _piece_activity(board: Board) -> int:
        score = 0

        # Bishop pair bonus
        w_bishops = sum(1 for _, p in board.pieces_of(Color.WHITE)
                        if p.piece_type == PieceType.BISHOP)
        b_bishops = sum(1 for _, p in board.pieces_of(Color.BLACK)
                        if p.piece_type == PieceType.BISHOP)
        if w_bishops >= 2: score += _BISHOP_PAIR_BONUS
        if b_bishops >= 2: score -= _BISHOP_PAIR_BONUS

        # Rooks on open/semi-open files
        for s, p in board.all_pieces():
            if p.piece_type != PieceType.ROOK:
                continue
            f = file_of(s)
            sign = 1 if p.color == Color.WHITE else -1
            own_pawns = any(
                p2.piece_type == PieceType.PAWN and p2.color == p.color
                for s2, p2 in board.all_pieces()
                if file_of(s2) == f
            )
            opp_pawns = any(
                p2.piece_type == PieceType.PAWN and p2.color != p.color
                for s2, p2 in board.all_pieces()
                if file_of(s2) == f
            )
            if not own_pawns and not opp_pawns:
                score += sign * _ROOK_OPEN_BONUS
            elif not own_pawns:
                score += sign * _ROOK_SEMIOPEN_BONUS

        # Knight outposts (knight on a square not attackable by opponent pawn)
        for s, p in board.all_pieces():
            if p.piece_type != PieceType.KNIGHT:
                continue
            r, f = rank_of(s), file_of(s)
            sign = 1 if p.color == Color.WHITE else -1
            opp  = p.color.opponent()
            opp_fwd = -1 if opp == Color.WHITE else 1

            # Check if any opponent pawn can attack this square
            is_outpost = True
            for df in (-1, 1):
                r2, f2 = r + opp_fwd, f + df
                if 0 <= r2 < 8 and 0 <= f2 < 8:
                    piece = board.piece_at(sq(r2, f2))
                    if piece and piece.color == opp and piece.piece_type == PieceType.PAWN:
                        is_outpost = False
                        break

            if is_outpost:
                # Extra bonus if in extended center
                bonus = _OUTPOST_BONUS + (8 if s in _EXTENDED_CENTER else 0)
                score += sign * bonus

        return score

    # ── Endgame ───────────────────────────────────────────────────────────────

    @staticmethod
    def _endgame_bonus(board: Board) -> int:
        """In endgames, reward king activity and passed-pawn advancement."""
        score = 0
        w_king_sq = board.king_square(Color.WHITE)
        b_king_sq = board.king_square(Color.BLACK)

        # Reward White king moving toward center in endgame
        w_dist = abs(rank_of(w_king_sq) - 3) + abs(file_of(w_king_sq) - 3)
        b_dist = abs(rank_of(b_king_sq) - 3) + abs(file_of(b_king_sq) - 3)
        score += (b_dist - w_dist) * 10  # White king closer = better for White

        return score


# ─── Quick Evaluation (no breakdown) ─────────────────────────────────────────

def quick_eval(board: Board) -> int:
    score, _ = Evaluator.evaluate(board, detail=False)
    return score
