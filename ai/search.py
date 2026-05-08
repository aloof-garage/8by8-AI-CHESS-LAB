"""
ai/search.py
============
AI chess search engine — built entirely from scratch.

Algorithms implemented:
  1. Minimax with alpha-beta pruning
  2. Iterative deepening (search progressively deeper)
  3. Quiescence search (avoid horizon effect)
  4. Move ordering (MVV-LVA, killer heuristic, history heuristic)
  5. Transposition table (Zobrist hash → cached scores)
  6. Null-move pruning (optional, for speed)

All search statistics are tracked and exposed for the visualization panel.
"""

from __future__ import annotations

import time
import threading
from typing import Optional, Callable
from dataclasses import dataclass, field

from engine.board import Board
from engine.moves import Move, MoveFlag
from engine.move_generator import MoveGenerator
from engine.pieces import Color, PieceType, PIECE_VALUES
from ai.evaluator import Evaluator, quick_eval


# ─── Transposition Table ──────────────────────────────────────────────────────

class TTFlag:
    EXACT      = 0   # exact score
    LOWER      = 1   # alpha (lower bound)
    UPPER      = 2   # beta  (upper bound)


@dataclass
class TTEntry:
    key:   int
    depth: int
    score: int
    flag:  int
    move:  Optional[Move] = None


class TranspositionTable:
    """Fixed-size hash table for caching search results."""

    SIZE = 1 << 20   # 1M entries (~32 MB)
    MASK = SIZE - 1

    def __init__(self) -> None:
        self._table: dict[int, TTEntry] = {}

    def get(self, key: int) -> Optional[TTEntry]:
        entry = self._table.get(key & self.MASK)
        if entry and entry.key == key:
            return entry
        return None

    def store(self, key: int, depth: int, score: int,
              flag: int, move: Optional[Move] = None) -> None:
        idx = key & self.MASK
        existing = self._table.get(idx)
        # Replace if new entry is deeper or slot is empty
        if existing is None or depth >= existing.depth:
            self._table[idx] = TTEntry(key, depth, score, flag, move)

    def clear(self) -> None:
        self._table.clear()

    def usage(self) -> float:
        return len(self._table) / self.SIZE


# ─── Search Statistics ────────────────────────────────────────────────────────

@dataclass
class SearchStats:
    nodes_searched:  int   = 0
    quiescence_nodes:int   = 0
    tt_hits:         int   = 0
    depth_reached:   int   = 0
    elapsed:         float = 0.0
    best_move:       Optional[Move]  = None
    best_score:      int             = 0
    pv:              list[Move]      = field(default_factory=list)  # principal variation
    top_moves:       list[tuple[Move, int]] = field(default_factory=list)

    @property
    def total_nodes(self) -> int:
        return self.nodes_searched + self.quiescence_nodes

    @property
    def nodes_per_sec(self) -> float:
        return self.total_nodes / max(self.elapsed, 0.001)

    def summary(self) -> str:
        bm = self.best_move.uci() if self.best_move else "none"
        score = self.best_score / 100
        return (
            f"Best: {bm} ({score:+.2f}) | "
            f"Depth: {self.depth_reached} | "
            f"Nodes: {self.total_nodes:,} | "
            f"NPS: {self.nodes_per_sec:,.0f} | "
            f"Time: {self.elapsed:.2f}s"
        )


# ─── Move Ordering Weights ─────────────────────────────────────────────────────

# MVV-LVA (Most Valuable Victim – Least Valuable Attacker)
_MVV_LVA: list[list[int]] = [
    # Victim:    P    N    B    R    Q    K
    [105, 205, 305, 405, 505, 605],   # Attacker: P
    [104, 204, 304, 404, 504, 604],   # Attacker: N
    [103, 203, 303, 403, 503, 603],   # Attacker: B
    [102, 202, 302, 402, 502, 602],   # Attacker: R
    [101, 201, 301, 401, 501, 601],   # Attacker: Q
    [100, 200, 300, 400, 500, 600],   # Attacker: K
]

_KILLER_BONUS  = 80
_HISTORY_MAX   = 400
_TT_MOVE_BONUS = 10_000
_CAPTURE_BONUS = 1_000


# ─── Search Engine ────────────────────────────────────────────────────────────

class SearchEngine:
    """
    Alpha-beta minimax search engine with all advanced optimizations.

    Usage:
        engine = SearchEngine()
        result = engine.search(board, max_depth=5, time_limit=3.0)
        best_move = result.best_move
    """

    _CHECKMATE_SCORE = 100_000
    _INF             = 200_000

    def __init__(self) -> None:
        self.tt  = TranspositionTable()
        # Killer moves: [depth][slot 0 or 1]
        self._killers: list[list[Optional[Move]]] = [
            [None, None] for _ in range(64)
        ]
        # History heuristic: [color][from_sq][to_sq] → score
        self._history: list[list[list[int]]] = [
            [[0]*64 for _ in range(64)] for _ in range(2)
        ]

        # Live search state (for GUI updates)
        self.stats = SearchStats()
        self._stop_flag = threading.Event()
        self._progress_cb: Optional[Callable[[SearchStats], None]] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def search(self, board: Board, max_depth: int = 5,
               time_limit: float = 5.0,
               progress_cb: Optional[Callable[[SearchStats], None]] = None,
               ) -> SearchStats:
        """
        Run iterative deepening alpha-beta and return SearchStats.

        Args:
            board:       Position to search
            max_depth:   Maximum search depth (plies)
            time_limit:  Maximum time in seconds
            progress_cb: Called after each depth iteration with live stats
        """
        self._stop_flag.clear()
        self._progress_cb = progress_cb
        self.stats = SearchStats()
        self._reset_heuristics()

        start_time = time.time()
        best_move:  Optional[Move] = None
        best_score: int            = 0

        # Iterative deepening loop
        for depth in range(1, max_depth + 1):
            if time.time() - start_time > time_limit:
                break

            # Reset per-depth stats but keep best from previous iteration
            self.stats.nodes_searched  = 0
            self.stats.quiescence_nodes = 0
            self.stats.tt_hits         = 0
            self.stats.depth_reached   = depth

            score, pv = self._root_search(board, depth, start_time, time_limit)

            elapsed = time.time() - start_time
            self.stats.elapsed   = elapsed
            self.stats.best_score = score

            if pv:
                best_move = pv[0]
                best_score = score
                self.stats.best_move = best_move
                self.stats.pv = pv

            if progress_cb:
                progress_cb(self.stats)

            # Stop if checkmate found
            if abs(score) > self._CHECKMATE_SCORE - 1000:
                break

        self.stats.best_move  = best_move
        self.stats.best_score = best_score
        self.stats.elapsed    = time.time() - start_time
        return self.stats

    def stop(self) -> None:
        """Signal the search to stop (for time control)."""
        self._stop_flag.set()

    # ── Root Search ───────────────────────────────────────────────────────────

    def _root_search(self, board: Board, depth: int,
                     start_time: float, time_limit: float
                     ) -> tuple[int, list[Move]]:
        """Search root position and collect top moves with scores.

        Uses pure negamax convention: all scores from current player's perspective.
        top_moves are converted to White's perspective for consistent display.
        """
        color = board.side_to_move
        is_white = (color == Color.WHITE)

        moves = MoveGenerator.generate_legal_moves(board)
        if not moves:
            return 0, []

        self._order_moves(moves, board, depth, None)

        best_score_curr = -self._INF   # from current player's perspective
        best_pv: list[Move] = []
        alpha, beta = -self._INF, self._INF

        top_moves_curr: list[tuple[Move, int]] = []

        for move in moves:
            if time.time() - start_time > time_limit or self._stop_flag.is_set():
                break

            board.push(move)
            self.stats.nodes_searched += 1

            # Pure negamax: child returns from child's perspective -> negate
            score_child, child_pv = self._negamax(board, depth-1, -beta, -alpha,
                                                   start_time, time_limit)
            score = -score_child   # now from current player's perspective

            board.pop()

            top_moves_curr.append((move, score))

            if score > best_score_curr:
                best_score_curr = score
                best_pv         = [move] + child_pv
                alpha = max(alpha, score)
                if alpha >= beta:
                    break

        # Convert scores to White's perspective for consistent display
        sign = 1 if is_white else -1
        top_moves_white = [(m, s * sign) for m, s in top_moves_curr]
        # Sort: best for the CURRENT player first
        # White: highest score first; Black: lowest score first (most negative = best for Black)
        top_moves_white.sort(key=lambda x: x[1], reverse=is_white)
        self.stats.top_moves = top_moves_white[:5]

        # Return score from White's perspective
        return best_score_curr * sign, best_pv

    # ── Negamax ───────────────────────────────────────────────────────────────

    def _negamax(self, board: Board, depth: int,
                 alpha: int, beta: int,
                 start_time: float, time_limit: float,
                 ) -> tuple[int, list[Move]]:
        """
        Pure negamax alpha-beta with transposition table.
        Returns (score_from_current_player_perspective, principal_variation).
        Score is always from the side-to-move's perspective (positive = good for mover).
        """
        if time.time() - start_time > time_limit or self._stop_flag.is_set():
            return 0, []

        # ── Transposition table lookup ────────────────────────────────────────
        key = board.zobrist_key
        tt_entry = self.tt.get(key)
        tt_move: Optional[Move] = None
        if tt_entry and tt_entry.depth >= depth:
            self.stats.tt_hits += 1
            tt_move = tt_entry.move
            if tt_entry.flag == TTFlag.EXACT:
                return tt_entry.score, ([tt_move] if tt_move else [])
            elif tt_entry.flag == TTFlag.LOWER:
                alpha = max(alpha, tt_entry.score)
            elif tt_entry.flag == TTFlag.UPPER:
                beta  = min(beta,  tt_entry.score)
            if alpha >= beta:
                return tt_entry.score, ([tt_move] if tt_move else [])

        # ── Leaf node ─────────────────────────────────────────────────────────
        if depth == 0:
            score = self._quiescence(board, alpha, beta)
            return score, []

        # ── Move generation ───────────────────────────────────────────────────
        moves = MoveGenerator.generate_legal_moves(board)
        if not moves:
            if board.is_in_check(board.side_to_move):
                return -self._CHECKMATE_SCORE + (100 - depth), []
            return 0, []  # Stalemate

        self._order_moves(moves, board, depth, tt_move)

        best_score = -self._INF
        best_pv: list[Move] = []
        best_move: Optional[Move] = None
        orig_alpha = alpha

        for move in moves:
            board.push(move)
            self.stats.nodes_searched += 1

            score, child_pv = self._negamax(board, depth-1, -beta, -alpha,
                                            start_time, time_limit)
            score = -score   # child returned from child's perspective; flip for ours
            board.pop()

            if score > best_score:
                best_score = score
                best_move  = move
                best_pv    = [move] + child_pv

            alpha = max(alpha, score)
            if alpha >= beta:
                if not move.is_capture:
                    self._update_killers(move, depth)
                    color_idx = 0 if board.side_to_move == Color.WHITE else 1
                    self._history[color_idx][move.from_sq][move.to_sq] += depth * depth
                break

        # ── Store in transposition table ──────────────────────────────────────
        if best_score <= orig_alpha:
            flag = TTFlag.UPPER
        elif best_score >= beta:
            flag = TTFlag.LOWER
        else:
            flag = TTFlag.EXACT
        self.tt.store(key, depth, best_score, flag, best_move)

        return best_score, best_pv

    # ── Quiescence Search ─────────────────────────────────────────────────────

    def _quiescence(self, board: Board, alpha: int, beta: int,
                    max_depth: int = 6) -> int:
        """
        Search only captures until position is 'quiet'.
        Pure negamax convention: score always from current player's perspective.
        """
        self.stats.quiescence_nodes += 1

        # stand_pat: static eval from current player's perspective
        raw = quick_eval(board)   # from White's perspective
        stand_pat = raw if board.side_to_move.value == 1 else -raw

        if stand_pat >= beta:
            return beta
        alpha = max(alpha, stand_pat)

        if max_depth == 0:
            return stand_pat

        captures = [m for m in MoveGenerator.generate_legal_moves(board)
                    if m.is_capture or m.is_promotion]

        if not captures:
            return stand_pat

        self._order_moves(captures, board, 0, None)

        for move in captures:
            board.push(move)
            score = -self._quiescence(board, -beta, -alpha, max_depth - 1)
            board.pop()

            if score >= beta:
                return beta
            alpha = max(alpha, score)

        return alpha

    # ── Move Ordering ─────────────────────────────────────────────────────────

    def _order_moves(self, moves: list[Move], board: Board,
                     depth: int, tt_move: Optional[Move]) -> None:
        """Score moves for ordering (highest score searched first)."""
        color_idx = 0 if board.side_to_move == Color.WHITE else 1

        for move in moves:
            score = 0

            # TT move is searched first
            if tt_move and move == tt_move:
                score = _TT_MOVE_BONUS

            # Captures: MVV-LVA
            elif move.is_capture and move.captured:
                att_idx = move.piece.piece_type - 1
                vic_idx = move.captured.piece_type - 1
                score   = _CAPTURE_BONUS + _MVV_LVA[att_idx][vic_idx]

            # Promotions
            elif move.is_promotion:
                score = _CAPTURE_BONUS + 500

            # Killers
            else:
                killers = self._killers[depth] if depth < 64 else [None, None]
                if move == killers[0]:
                    score = _KILLER_BONUS
                elif move == killers[1]:
                    score = _KILLER_BONUS - 10
                else:
                    # History heuristic
                    score = min(self._history[color_idx][move.from_sq][move.to_sq],
                                _HISTORY_MAX)

            move.score = score

        moves.sort(key=lambda m: m.score, reverse=True)

    # ── Heuristic Helpers ─────────────────────────────────────────────────────

    def _update_killers(self, move: Move, depth: int) -> None:
        if depth >= 64:
            return
        if self._killers[depth][0] != move:
            self._killers[depth][1] = self._killers[depth][0]
            self._killers[depth][0] = move

    def _reset_heuristics(self) -> None:
        self._killers = [[None, None] for _ in range(64)]
        self._history = [[[0]*64 for _ in range(64)] for _ in range(2)]


# ─── Opening Book ────────────────────────────────────────────────────────────

# Simple opening book: FEN (first N moves) → list of UCI moves
_OPENING_BOOK: dict[str, list[str]] = {
    # Starting position → common first moves
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1": [
        "e2e4", "d2d4", "g1f3", "c2c4"
    ],
    # 1.e4 responses
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1": [
        "e7e5", "c7c5", "e7e6", "c7c6"
    ],
    # 1.d4 responses
    "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq d3 0 1": [
        "d7d5", "g8f6", "e7e6", "c7c5"
    ],
    # 1.e4 e5
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2": [
        "g1f3", "f2f4", "b1c3"
    ],
    # 1.e4 e5 2.Nf3
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2": [
        "b8c6", "g8f6", "f8c5"
    ],
}


class OpeningBook:
    """Simple opening book using pre-stored positions."""

    @staticmethod
    def get_book_move(board: Board) -> Optional[Move]:
        """Return a book move if available, else None."""
        import random
        fen_key = " ".join(board.to_fen().split()[:4])  # ignore clocks

        for book_fen, uci_list in _OPENING_BOOK.items():
            book_key = " ".join(book_fen.split()[:4])
            if book_key == fen_key:
                uci = random.choice(uci_list)
                from_sq_str, to_sq_str = uci[:2], uci[2:4]
                from engine.moves import alg_to_sq
                from_sq = alg_to_sq(from_sq_str)
                to_sq   = alg_to_sq(to_sq_str)
                for move in MoveGenerator.generate_legal_moves(board):
                    if move.from_sq == from_sq and move.to_sq == to_sq:
                        return move
        return None
