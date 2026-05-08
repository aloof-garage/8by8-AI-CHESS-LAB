"""
gui/charts.py
=============
Analytics charts — matplotlib embedded in PySide6.
Styled to match design.md warm-minimalist palette.
"""
from __future__ import annotations

import matplotlib
try:
    matplotlib.use("QtAgg")
except Exception:
    try:
        matplotlib.use("Qt5Agg")
    except Exception:
        matplotlib.use("Agg")

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


def _style_axes(ax, fig, t) -> None:
    """Apply design.md token colors to a matplotlib axes."""
    fig.patch.set_facecolor(t.surface)
    ax.set_facecolor(t.bg2)
    for spine in ax.spines.values():
        spine.set_color(t.border)
    ax.tick_params(colors=t.ink4, labelsize=8)
    ax.xaxis.label.set_color(t.ink4)
    ax.yaxis.label.set_color(t.ink4)
    ax.grid(True, color=t.border, alpha=0.6, linewidth=0.5, linestyle="-")


class EvalChart(QFrame):
    """Evaluation over time — signed area chart."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._fig = Figure(figsize=(5, 2.2), dpi=96, tight_layout=True)
        self._ax  = self._fig.add_subplot(111)
        self._canvas = FigureCanvas(self._fig)
        layout.addWidget(self._canvas)
        self._draw_empty()

    def _draw_empty(self) -> None:
        t = Theme.current()
        self._ax.clear()
        _style_axes(self._ax, self._fig, t)
        self._ax.axhline(y=0, color=t.ink4, linewidth=0.8, linestyle="--", alpha=0.7)
        self._ax.set_ylabel("Eval", fontsize=8, color=t.ink4)
        self._ax.set_ylim(-5, 5)
        self._canvas.draw()

    def update_data(self, eval_history: list[float]) -> None:
        t = Theme.current()
        self._ax.clear()
        _style_axes(self._ax, self._fig, t)

        if not eval_history:
            self._draw_empty(); return

        x = list(range(len(eval_history)))
        y = [v / 100 for v in eval_history]

        # Warm-tone fills
        self._ax.fill_between(x, y, 0, where=[v > 0 for v in y],
                              color=t.sq_light, alpha=0.30, zorder=2)
        self._ax.fill_between(x, y, 0, where=[v < 0 for v in y],
                              color=t.sq_dark,  alpha=0.35, zorder=2)
        self._ax.plot(x, y, color=t.ink2, linewidth=1.4, zorder=3)
        self._ax.axhline(y=0, color=t.ink4, linewidth=0.8, linestyle="--", alpha=0.7)
        self._ax.set_ylabel("Eval", fontsize=8, color=t.ink4)
        ymax = max(4.0, max(abs(v) for v in y) * 1.2)
        self._ax.set_ylim(-ymax, ymax)
        self._canvas.draw()

    def clear(self) -> None:
        self._draw_empty()


class DepthNodesChart(QFrame):
    """Search depth bars + node count line."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._fig = Figure(figsize=(5, 2.2), dpi=96, tight_layout=True)
        self._ax1 = self._fig.add_subplot(111)
        self._ax2 = self._ax1.twinx()
        self._canvas = FigureCanvas(self._fig)
        layout.addWidget(self._canvas)
        self._draw_empty()

    def _draw_empty(self) -> None:
        t = Theme.current()
        for ax in (self._ax1, self._ax2):
            ax.clear()
            _style_axes(ax, self._fig, t)
        self._canvas.draw()

    def update_data(self, depth_data: list[int], nodes_data: list[int]) -> None:
        t = Theme.current()
        for ax in (self._ax1, self._ax2):
            ax.clear()
            _style_axes(ax, self._fig, t)
        if not depth_data:
            self._draw_empty(); return

        x = list(range(len(depth_data)))
        self._ax1.bar(x, depth_data, color=t.ink3, alpha=0.55, width=0.6, label="Depth")
        self._ax2.plot(x, [n / 1000 for n in nodes_data],
                       color=t.sq_light, linewidth=1.4, label="Nodes k")
        self._ax1.set_ylabel("Depth", fontsize=8, color=t.ink4)
        self._ax2.set_ylabel("Nodes k", fontsize=8, color=t.ink4)
        self._ax1.tick_params(axis="y", colors=t.ink4)
        self._ax2.tick_params(axis="y", colors=t.ink4)
        self._canvas.draw()

    def clear(self) -> None:
        self._draw_empty()


class MoveQualityChart(QFrame):
    """Move quality distribution bars."""

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
        t = Theme.current()
        self._ax.clear()
        _style_axes(self._ax, self._fig, t)
        self._canvas.draw()

    def update_data(self, white_counts: dict, black_counts: dict) -> None:
        from analytics.collector import MoveQuality
        t = Theme.current()
        self._ax.clear()
        _style_axes(self._ax, self._fig, t)

        labels  = [MoveQuality.BRILLIANT, MoveQuality.GREAT, MoveQuality.GOOD,
                   MoveQuality.INACCURACY, MoveQuality.MISTAKE, MoveQuality.BLUNDER]
        short   = ["!!", "!", "✓", "?!", "?", "??"]
        palette = [t.success, t.ink2, t.ink3, t.warning, t.danger, "#8B2020"]

        x = list(range(len(labels)))
        w = 0.35
        w_vals = [white_counts.get(q, 0) for q in labels]
        b_vals = [black_counts.get(q, 0) for q in labels]

        self._ax.bar([i - w/2 for i in x], w_vals, w,
                     color=palette, alpha=0.85, label="White")
        self._ax.bar([i + w/2 for i in x], b_vals, w,
                     color=palette, alpha=0.42, label="Black")
        self._ax.set_xticks(list(x))
        self._ax.set_xticklabels(short, fontsize=9, color=t.ink3)
        self._ax.set_ylabel("Count", fontsize=8, color=t.ink4)
        self._canvas.draw()

    def clear(self) -> None:
        self._draw_empty()


class AnalyticsChartsWidget(QFrame):
    """Tabbed container for all analytics charts."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()
        self.eval_chart    = EvalChart()
        self.depth_chart   = DepthNodesChart()
        self.quality_chart = MoveQualityChart()

        self._tabs.addTab(self.eval_chart,    "Evaluation")
        self._tabs.addTab(self.depth_chart,   "Depth")
        self._tabs.addTab(self.quality_chart, "Quality")
        layout.addWidget(self._tabs)

    def clear_all(self) -> None:
        self.eval_chart.clear()
        self.depth_chart.clear()
        self.quality_chart.clear()
