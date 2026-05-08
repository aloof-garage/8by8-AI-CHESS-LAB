"""
gui/charts.py
=============
Matplotlib-based analytics charts embedded in PySide6.

Charts:
  - Evaluation graph (score over moves)
  - Search depth graph
  - Node count graph
  - Move quality distribution
"""

from __future__ import annotations
from typing import Optional

import matplotlib
try:
    matplotlib.use("QtAgg")  # Works with PySide6 in matplotlib >= 3.5
except Exception:
    matplotlib.use("Agg")    # Fallback non-interactive

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except ImportError:
    try:
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    except ImportError:
        from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QTabWidget
from PySide6.QtCore import Qt

from gui.theme import Theme


def _apply_dark_style(ax, fig, c) -> None:
    """Apply dark/light theme styling to a matplotlib axes."""
    bg = c.bg_medium
    fg = c.text_secondary
    grid_c = c.bg_light

    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)
    ax.tick_params(colors=fg, labelsize=8)
    ax.spines["bottom"].set_color(grid_c)
    ax.spines["left"].set_color(grid_c)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.label.set_color(fg)
    ax.yaxis.label.set_color(fg)
    ax.grid(True, color=grid_c, alpha=0.5, linewidth=0.6)


class EvalChart(QFrame):
    """Evaluation over time line chart."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        c = Theme.current()
        self._fig = Figure(figsize=(5, 2.4), dpi=96, tight_layout=True)
        self._ax  = self._fig.add_subplot(111)
        self._canvas = FigureCanvas(self._fig)
        self._canvas.setStyleSheet("background: transparent;")
        layout.addWidget(self._canvas)

        self._eval_history: list[float] = []
        self._draw_empty()

    def _draw_empty(self) -> None:
        c = Theme.current()
        self._ax.clear()
        _apply_dark_style(self._ax, self._fig, c)
        self._ax.axhline(y=0, color=c.text_muted, linewidth=0.8, linestyle="--")
        self._ax.set_ylabel("Eval (pawns)", fontsize=8, color=c.text_secondary)
        self._ax.set_xlabel("Half-move", fontsize=8, color=c.text_secondary)
        self._ax.set_ylim(-5, 5)
        self._canvas.draw()

    def update_data(self, eval_history: list[float]) -> None:
        c = Theme.current()
        self._eval_history = eval_history
        self._ax.clear()
        _apply_dark_style(self._ax, self._fig, c)

        if not eval_history:
            self._draw_empty()
            return

        x = list(range(len(eval_history)))
        y = [v / 100 for v in eval_history]

        # Fill positive/negative areas
        self._ax.fill_between(x, y, 0,
                              where=[v > 0 for v in y],
                              color=c.eval_white, alpha=0.25)
        self._ax.fill_between(x, y, 0,
                              where=[v < 0 for v in y],
                              color=c.eval_black, alpha=0.35)
        self._ax.plot(x, y, color=c.accent, linewidth=1.5, zorder=3)
        self._ax.axhline(y=0, color=c.text_muted, linewidth=0.8, linestyle="--")
        self._ax.set_ylabel("Eval (pawns)", fontsize=8, color=c.text_secondary)
        self._ax.set_xlabel("Half-move", fontsize=8, color=c.text_secondary)
        ymax = max(5.0, max(abs(v) for v in y) * 1.2)
        self._ax.set_ylim(-ymax, ymax)
        self._canvas.draw()

    def clear(self) -> None:
        self._draw_empty()


class DepthNodesChart(QFrame):
    """Combined depth and node count chart."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._fig = Figure(figsize=(5, 2.4), dpi=96, tight_layout=True)
        self._ax1 = self._fig.add_subplot(111)
        self._ax2 = self._ax1.twinx()
        self._canvas = FigureCanvas(self._fig)
        layout.addWidget(self._canvas)

        self._depth_data:  list[int]   = []
        self._nodes_data:  list[int]   = []
        self._draw_empty()

    def _draw_empty(self) -> None:
        c = Theme.current()
        for ax in (self._ax1, self._ax2):
            ax.clear()
            _apply_dark_style(ax, self._fig, c)
        self._ax1.set_ylabel("Depth", fontsize=8, color=c.accent)
        self._ax2.set_ylabel("Nodes (k)", fontsize=8, color=c.success)
        self._canvas.draw()

    def update_data(self, depth_data: list[int], nodes_data: list[int]) -> None:
        c = Theme.current()
        self._depth_data = depth_data
        self._nodes_data = nodes_data

        for ax in (self._ax1, self._ax2):
            ax.clear()
            _apply_dark_style(ax, self._fig, c)

        if not depth_data:
            self._draw_empty()
            return

        x = list(range(len(depth_data)))
        self._ax1.bar(x, depth_data, color=c.accent, alpha=0.5, label="Depth")
        self._ax2.plot(x, [n/1000 for n in nodes_data],
                       color=c.success, linewidth=1.5, label="Nodes(k)")
        self._ax1.set_ylabel("Depth", fontsize=8, color=c.accent)
        self._ax2.set_ylabel("Nodes (k)", fontsize=8, color=c.success)
        self._ax1.tick_params(axis="y", colors=c.accent)
        self._ax2.tick_params(axis="y", colors=c.success)
        self._canvas.draw()

    def clear(self) -> None:
        self._depth_data = []
        self._nodes_data = []
        self._draw_empty()


class MoveQualityChart(QFrame):
    """Horizontal bar chart for move quality distribution."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._fig = Figure(figsize=(5, 2.0), dpi=96, tight_layout=True)
        self._ax  = self._fig.add_subplot(111)
        self._canvas = FigureCanvas(self._fig)
        layout.addWidget(self._canvas)
        self._draw_empty()

    def _draw_empty(self) -> None:
        c = Theme.current()
        self._ax.clear()
        _apply_dark_style(self._ax, self._fig, c)
        self._canvas.draw()

    def update_data(self, white_counts: dict, black_counts: dict) -> None:
        from analytics.collector import MoveQuality
        c = Theme.current()
        self._ax.clear()
        _apply_dark_style(self._ax, self._fig, c)

        labels = [MoveQuality.BRILLIANT, MoveQuality.GREAT, MoveQuality.GOOD,
                  MoveQuality.INACCURACY, MoveQuality.MISTAKE, MoveQuality.BLUNDER]
        colors = [MoveQuality.color(q) for q in labels]
        w_vals = [white_counts.get(q, 0) for q in labels]
        b_vals = [black_counts.get(q, 0) for q in labels]

        x = range(len(labels))
        width = 0.35
        self._ax.bar([i - width/2 for i in x], w_vals, width, color=colors,
                     alpha=0.85, label="White")
        self._ax.bar([i + width/2 for i in x], b_vals, width, color=colors,
                     alpha=0.45, label="Black")
        short_labels = ["!!", "!", "✓", "?!", "?", "??"]
        self._ax.set_xticks(list(x))
        self._ax.set_xticklabels(short_labels, fontsize=9, color=c.text_primary)
        self._ax.set_ylabel("Count", fontsize=8, color=c.text_secondary)
        self._canvas.draw()

    def clear(self) -> None:
        self._draw_empty()


class AnalyticsChartsWidget(QFrame):
    """Tab widget containing all analytics charts."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        tabs = QTabWidget()
        c = Theme.current()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: {c.bg_dark}; }}
            QTabBar::tab {{
                background: {c.bg_medium}; color: {c.text_secondary};
                padding: 5px 14px; border: none; border-radius: 4px;
                margin-right: 2px; font-size: 11px;
            }}
            QTabBar::tab:selected {{
                background: {c.accent_dim}; color: {c.accent};
                font-weight: 600;
            }}
        """)

        self.eval_chart   = EvalChart()
        self.depth_chart  = DepthNodesChart()
        self.quality_chart= MoveQualityChart()

        tabs.addTab(self.eval_chart,    "Evaluation")
        tabs.addTab(self.depth_chart,   "Search Depth")
        tabs.addTab(self.quality_chart, "Move Quality")

        layout.addWidget(tabs)

    def clear_all(self) -> None:
        self.eval_chart.clear()
        self.depth_chart.clear()
        self.quality_chart.clear()
