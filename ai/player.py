"""
ai/player.py
============
AI player controller. Wraps SearchEngine + OpeningBook.

Provides difficulty presets, threaded search, and move explanation generation.
"""

from __future__ import annotations

import threading
import random
import time
from typing import Optional, Callable
from dataclasses import dataclass

from engine.board import Board
from engine.moves import Move
from engine.move_generator import MoveGenerator
from engine.pieces import Color, PieceType
from ai.search import SearchEngine, SearchStats, OpeningBook
from ai.evaluator import Evaluator


# ─── Difficulty Presets ───────────────────────────────────────────────────────

@dataclass
class DifficultyConfig:
    name:        str
    max_depth:   int
    time_limit:  float   # seconds
    use_book:    bool
    randomness:  float   # 0.0 = deterministic, 1.0 = random top-N pick
    top_n_moves: int     # pick randomly from top N moves (for lower difficulties)


DIFFICULTY_CONFIGS: dict[str, DifficultyConfig] = {
    "Easy":   DifficultyConfig("Easy",   max_depth=2, time_limit=0.5,  use_book=False, randomness=0.7, top_n_moves=4),
    "Medium": DifficultyConfig("Medium", max_depth=3, time_limit=1.0,  use_book=True,  randomness=0.3, top_n_moves=2),
    "Hard":   DifficultyConfig("Hard",   max_depth=5, time_limit=3.0,  use_book=True,  randomness=0.05,top_n_moves=1),
    "Expert": DifficultyConfig("Expert", max_depth=7, time_limit=10.0, use_book=True,  randomness=0.0, top_n_moves=1),
}


# ─── Move Explanation ─────────────────────────────────────────────────────────

def generate_explanation(board: Board, move: Move, stats: SearchStats) -> str:
    """
    Generate a human-readable explanation of why the AI chose this move.
    Uses real evaluation deltas to build the explanation.
    """
    reasons = []
    piece_name = {
        PieceType.PAWN:   "pawn",
        PieceType.KNIGHT: "knight",
        PieceType.BISHOP: "bishop",
        PieceType.ROOK:   "rook",
        PieceType.QUEEN:  "queen",
        PieceType.KING:   "king",
    }.get(move.piece.piece_type, "piece")

    from engine.moves import sq_to_alg
    dest = sq_to_alg(move.to_sq)
    san  = move.to_san()

    # Capture
    if move.is_capture and move.captured:
        cap_name = {
            PieceType.PAWN: "pawn", PieceType.KNIGHT: "knight",
            PieceType.BISHOP: "bishop", PieceType.ROOK: "rook",
            PieceType.QUEEN: "queen",
        }.get(move.captured.piece_type, "piece")
        reasons.append(f"captures the opponent's {cap_name}")

    # Promotion
    if move.is_promotion:
        reasons.append("promotes the pawn to a queen")

    # Castling
    if move.is_castle:
        reasons.append("safely castles the king and activates the rook")

    # Evaluate before/after
    score_before, bd_before = Evaluator.evaluate(board, detail=True)
    board.push(move)
    score_after, bd_after = Evaluator.evaluate(board, detail=True)
    board.pop()

    delta = score_after - score_before
    if bd_before and bd_after:
        mobility_delta = bd_after.mobility - bd_before.mobility
        center_delta   = bd_after.center - bd_before.center
        king_delta     = bd_after.king_safety - bd_before.king_safety
        pst_delta      = bd_after.position - bd_before.position

        if move.piece.color == Color.BLACK:
            mobility_delta = -mobility_delta
            center_delta   = -center_delta
            king_delta     = -king_delta

        if pst_delta > 10:
            reasons.append("improves piece placement")
        if mobility_delta > 8:
            reasons.append("increases mobility")
        if center_delta > 10:
            reasons.append("gains center control")
        if king_delta > 10:
            reasons.append("improves king safety")

    # Check
    board.push(move)
    in_check = board.is_in_check(board.side_to_move)
    board.pop()
    if in_check:
        reasons.append("delivers check")

    # Depth context
    depth = stats.depth_reached
    nodes = stats.total_nodes
    score = stats.best_score / 100
    sign  = "+" if score >= 0 else ""

    if not reasons:
        reasons.append("is the best evaluated continuation")

    reason_str = ", ".join(reasons)
    return (
        f"AI played {san} because it {reason_str}. "
        f"Evaluated at {sign}{score:.2f} pawns after searching {nodes:,} nodes "
        f"to depth {depth}."
    )


# ─── AI Player ────────────────────────────────────────────────────────────────

class AIPlayer:
    """
    Full AI player with configurable difficulty.

    Runs search in a background thread to keep the GUI responsive.
    Calls result_callback(move, stats, explanation) when done.
    """

    def __init__(self, color: Color = Color.BLACK,
                 difficulty: str = "Hard") -> None:
        self.color      = color
        self.difficulty = difficulty
        self.engine     = SearchEngine()
        self._thread:   Optional[threading.Thread] = None
        self._thinking  = False

    # ── Config ────────────────────────────────────────────────────────────────

    @property
    def config(self) -> DifficultyConfig:
        return DIFFICULTY_CONFIGS.get(self.difficulty,
                                      DIFFICULTY_CONFIGS["Hard"])

    def set_difficulty(self, difficulty: str) -> None:
        assert difficulty in DIFFICULTY_CONFIGS
        self.difficulty = difficulty

    # ── Main Search Interface ─────────────────────────────────────────────────

    def request_move(
        self,
        board: Board,
        result_callback: Callable[[Move, SearchStats, str], None],
        progress_callback: Optional[Callable[[SearchStats], None]] = None,
    ) -> None:
        """
        Start a background search.

        Args:
            board:            Position to search (will be cloned internally)
            result_callback:  Called with (best_move, stats, explanation) when done
            progress_callback: Called repeatedly during search with live stats
        """
        if self._thinking:
            return
        self._thinking = True
        board_clone = board.clone()

        self._thread = threading.Thread(
            target=self._search_worker,
            args=(board_clone, result_callback, progress_callback),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self.engine.stop()

    def is_thinking(self) -> bool:
        return self._thinking

    # ── Worker (background thread) ────────────────────────────────────────────

    def _search_worker(
        self,
        board: Board,
        result_callback: Callable,
        progress_callback: Optional[Callable],
    ) -> None:
        try:
            cfg = self.config

            # Try opening book first
            if cfg.use_book:
                book_move = OpeningBook.get_book_move(board)
                if book_move:
                    stats = SearchStats()
                    stats.best_move  = book_move
                    stats.best_score = 0
                    stats.depth_reached = 0
                    stats.elapsed = 0.0
                    explanation = f"AI played book move {book_move.to_san()}."
                    self._thinking = False
                    result_callback(book_move, stats, explanation)
                    return

            # Run iterative deepening search
            stats = self.engine.search(
                board,
                max_depth=cfg.max_depth,
                time_limit=cfg.time_limit,
                progress_cb=progress_callback,
            )

            # Apply randomness for lower difficulties
            move = self._apply_randomness(board, stats, cfg)

            if move is None:
                # No move found (shouldn't happen in non-terminal positions)
                legal = MoveGenerator.generate_legal_moves(board)
                move = random.choice(legal) if legal else None

            if move:
                explanation = generate_explanation(board, move, stats)
                stats.best_move = move
            else:
                explanation = "No move available."

            self._thinking = False
            result_callback(move, stats, explanation)

        except Exception as e:
            self._thinking = False
            # Fallback: random legal move
            legal = MoveGenerator.generate_legal_moves(board)
            if legal:
                move = random.choice(legal)
                stats = SearchStats()
                stats.best_move = move
                result_callback(move, stats, f"Fallback random move ({e})")

    def _apply_randomness(self, board: Board, stats: SearchStats,
                          cfg: DifficultyConfig) -> Optional[Move]:
        """
        For lower difficulties, randomly select from the top N moves
        with some probability, simulating imperfect play.
        """
        if not stats.top_moves:
            return stats.best_move

        if cfg.randomness == 0.0 or cfg.top_n_moves <= 1:
            return stats.best_move

        if random.random() < cfg.randomness:
            pool = stats.top_moves[:cfg.top_n_moves]
            if pool:
                return random.choice(pool)[0]

        return stats.best_move


# ─── AI vs AI Controller ──────────────────────────────────────────────────────

class AIvsAIController:
    """Manages two AI players playing against each other."""

    def __init__(self, white_difficulty: str = "Hard",
                 black_difficulty: str = "Hard") -> None:
        self.white_ai = AIPlayer(Color.WHITE, white_difficulty)
        self.black_ai = AIPlayer(Color.BLACK, black_difficulty)
        self._active  = False
        self._pause   = threading.Event()
        self._pause.set()   # not paused by default

    def current_ai(self, color: Color) -> AIPlayer:
        return self.white_ai if color == Color.WHITE else self.black_ai

    def pause(self) -> None:
        self._pause.clear()

    def resume(self) -> None:
        self._pause.set()

    def stop(self) -> None:
        self._active = False
        self.white_ai.stop()
        self.black_ai.stop()
