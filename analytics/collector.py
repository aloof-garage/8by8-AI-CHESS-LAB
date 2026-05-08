"""
analytics/collector.py
======================
Collects and stores game analytics data for charts and export.

Tracks:
  - Evaluation score after each move
  - AI search depth / node count / time per move
  - Move quality classification (brilliant / good / inaccuracy / mistake / blunder)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

from engine.pieces import Color


# ─── Move Quality ─────────────────────────────────────────────────────────────

class MoveQuality:
    BRILLIANT   = "Brilliant"   # !! (saves a losing position or huge win)
    GREAT       = "Great"       # !
    GOOD        = "Good"        # (normal)
    INACCURACY  = "Inaccuracy"  # ?! (loses 0.5–1.5 pawns)
    MISTAKE     = "Mistake"     # ? (loses 1.5–3.0 pawns)
    BLUNDER     = "Blunder"     # ?? (loses 3+ pawns)

    @staticmethod
    def classify(eval_before: float, eval_after: float, color: Color) -> str:
        """
        Classify a move by how much evaluation changed.
        eval_* are in pawns from White's perspective.
        """
        if color == Color.WHITE:
            delta = eval_after - eval_before   # positive = better for White
        else:
            delta = eval_before - eval_after   # positive = better for Black

        if   delta >=  1.0: return MoveQuality.BRILLIANT
        elif delta >=  0.2: return MoveQuality.GREAT
        elif delta >= -0.3: return MoveQuality.GOOD
        elif delta >= -1.0: return MoveQuality.INACCURACY
        elif delta >= -2.5: return MoveQuality.MISTAKE
        else:               return MoveQuality.BLUNDER

    @staticmethod
    def symbol(quality: str) -> str:
        return {
            MoveQuality.BRILLIANT:  "!!",
            MoveQuality.GREAT:      "!",
            MoveQuality.GOOD:       "",
            MoveQuality.INACCURACY: "?!",
            MoveQuality.MISTAKE:    "?",
            MoveQuality.BLUNDER:    "??",
        }.get(quality, "")

    @staticmethod
    def color(quality: str) -> str:
        return {
            MoveQuality.BRILLIANT:  "#00d4ff",
            MoveQuality.GREAT:      "#4caf50",
            MoveQuality.GOOD:       "#aaaaaa",
            MoveQuality.INACCURACY: "#ff9800",
            MoveQuality.MISTAKE:    "#f44336",
            MoveQuality.BLUNDER:    "#d32f2f",
        }.get(quality, "#aaaaaa")


# ─── Data Records ─────────────────────────────────────────────────────────────

@dataclass
class MoveDataPoint:
    move_number:    int
    color:          str         # "White" / "Black"
    san:            str
    eval_before:    float       # pawns
    eval_after:     float       # pawns
    quality:        str
    depth:          int
    nodes:          int
    time_taken:     float
    nps:            float       # nodes per second

    @property
    def eval_delta(self) -> float:
        if self.color == "White":
            return self.eval_after - self.eval_before
        return self.eval_before - self.eval_after


@dataclass
class GameAnalytics:
    move_data:      list[MoveDataPoint] = field(default_factory=list)
    eval_history:   list[float]         = field(default_factory=list)  # after each half-move
    start_time:     float               = field(default_factory=time.time)
    end_time:       Optional[float]     = None
    result:         str                 = "ongoing"

    # ── Aggregate Stats ───────────────────────────────────────────────────────

    def avg_depth(self, color: Optional[str] = None) -> float:
        data = [d for d in self.move_data if color is None or d.color == color]
        if not data: return 0.0
        return sum(d.depth for d in data) / len(data)

    def avg_nodes(self, color: Optional[str] = None) -> float:
        data = [d for d in self.move_data if color is None or d.color == color]
        if not data: return 0.0
        return sum(d.nodes for d in data) / len(data)

    def avg_time(self, color: Optional[str] = None) -> float:
        data = [d for d in self.move_data if color is None or d.color == color]
        if not data: return 0.0
        return sum(d.time_taken for d in data) / len(data)

    def quality_counts(self, color: Optional[str] = None) -> dict[str, int]:
        data = [d for d in self.move_data if color is None or d.color == color]
        counts: dict[str, int] = {}
        for d in data:
            counts[d.quality] = counts.get(d.quality, 0) + 1
        return counts

    def accuracy(self, color: str) -> float:
        """
        Estimate accuracy 0-100% based on move quality distribution.
        """
        weights = {
            MoveQuality.BRILLIANT:  100,
            MoveQuality.GREAT:      90,
            MoveQuality.GOOD:       75,
            MoveQuality.INACCURACY: 45,
            MoveQuality.MISTAKE:    20,
            MoveQuality.BLUNDER:    0,
        }
        data = [d for d in self.move_data if d.color == color]
        if not data: return 0.0
        total = sum(weights.get(d.quality, 75) for d in data)
        return total / len(data)

    def total_blunders(self, color: Optional[str] = None) -> int:
        return self.quality_counts(color).get(MoveQuality.BLUNDER, 0)

    def total_mistakes(self, color: Optional[str] = None) -> int:
        return self.quality_counts(color).get(MoveQuality.MISTAKE, 0)

    # ── Export ────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "result":         self.result,
            "duration":       round((self.end_time or time.time()) - self.start_time, 1),
            "move_data":      [asdict(d) for d in self.move_data],
            "eval_history":   self.eval_history,
            "avg_depth":      round(self.avg_depth(), 1),
            "avg_nodes":      round(self.avg_nodes()),
            "avg_time":       round(self.avg_time(), 3),
            "white_accuracy": round(self.accuracy("White"), 1),
            "black_accuracy": round(self.accuracy("Black"), 1),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def analysis_report(self) -> str:
        lines = [
            "=" * 50,
            "AI CHESS LAB — GAME ANALYSIS REPORT",
            "=" * 50,
            f"Result:          {self.result}",
            f"Total moves:     {len(self.move_data)}",
            f"Duration:        {round((self.end_time or time.time()) - self.start_time, 1)}s",
            "",
            f"{'Metric':<22} {'White':>10} {'Black':>10}",
            "─" * 44,
            f"{'Accuracy':<22} {self.accuracy('White'):>9.1f}% {self.accuracy('Black'):>9.1f}%",
            f"{'Avg Search Depth':<22} {self.avg_depth('White'):>10.1f} {self.avg_depth('Black'):>10.1f}",
            f"{'Avg Nodes/Move':<22} {self.avg_nodes('White'):>10,.0f} {self.avg_nodes('Black'):>10,.0f}",
            f"{'Avg Time/Move (s)':<22} {self.avg_time('White'):>10.2f} {self.avg_time('Black'):>10.2f}",
            f"{'Blunders':<22} {self.total_blunders('White'):>10} {self.total_blunders('Black'):>10}",
            f"{'Mistakes':<22} {self.total_mistakes('White'):>10} {self.total_mistakes('Black'):>10}",
            "",
            "MOVE LOG:",
            "─" * 44,
        ]
        for d in self.move_data:
            q_sym = MoveQuality.symbol(d.quality)
            score = f"{d.eval_after:+.2f}"
            lines.append(
                f"  {d.move_number:>3}. {'...' if d.color=='Black' else ''}"
                f"{d.san}{q_sym:<3}  eval={score}  "
                f"d={d.depth} n={d.nodes:,}"
            )

        return "\n".join(lines)


# ─── Collector ────────────────────────────────────────────────────────────────

class AnalyticsCollector:
    """Collects analytics during a game."""

    def __init__(self) -> None:
        self.data = GameAnalytics()
        self._last_eval: float = 0.0

    def record_move(self, move_number: int, color: Color, san: str,
                    eval_before: float, eval_after: float,
                    depth: int, nodes: int,
                    time_taken: float) -> MoveDataPoint:
        quality = MoveQuality.classify(eval_before, eval_after, color)
        nps = nodes / max(time_taken, 0.001)
        color_str = "White" if color == Color.WHITE else "Black"

        dp = MoveDataPoint(
            move_number=move_number,
            color=color_str,
            san=san,
            eval_before=eval_before,
            eval_after=eval_after,
            quality=quality,
            depth=depth,
            nodes=nodes,
            time_taken=time_taken,
            nps=nps,
        )
        self.data.move_data.append(dp)
        self.data.eval_history.append(eval_after)
        self._last_eval = eval_after
        return dp

    def set_result(self, result: str) -> None:
        import time as _t
        self.data.result   = result
        self.data.end_time = _t.time()

    def reset(self) -> None:
        self.data = GameAnalytics()
        self._last_eval = 0.0
