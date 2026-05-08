"""
gui/main_window.py
==================
Main application window for 8by8 AI CHESS LAB.

Layout:
  ┌─────────────────────────────────────────────────────┐
  │  Toolbar: New Game | Undo | Flip | Theme | Settings  │
  ├──────────────────────────┬──────────────────────────┤
  │                          │  Status bar              │
  │   Chess Board            │  ── ── ── ── ──          │
  │   (BoardWidget)          │  Eval breakdown          │
  │                          │  ── ── ── ── ──          │
  │                          │  AI thinking panel       │
  │                          │  Top candidates          │
  │                          │  ── ── ── ── ──          │
  │                          │  Move history            │
  │                          │  AI explanation          │
  ├──────────────────────────┴──────────────────────────┤
  │   Analytics charts (collapsible)                    │
  └─────────────────────────────────────────────────────┘

Orchestrates:
  - Game state (engine.game.Game)
  - AI players (ai.player.AIPlayer)
  - GUI components (board, panels, charts)
  - Analytics collection
  - PGN / log export
"""

from __future__ import annotations

import random
import time
import os
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QPushButton, QComboBox, QLabel, QFileDialog, QMessageBox,
    QFrame, QToolBar, QSizePolicy, QScrollArea,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QTimer
from PySide6.QtGui import QFont, QAction, QIcon

from engine.game import Game, GameResult
from engine.pieces import Color, PieceType
from engine.moves import Move
from engine.move_generator import MoveGenerator
from ai.player import AIPlayer, AIvsAIController, DIFFICULTY_CONFIGS
from ai.search import SearchStats
from ai.evaluator import Evaluator

from analytics.collector import AnalyticsCollector, MoveQuality

from gui.board_widget import BoardWidget
from gui.panels import (
    EvalBar, MoveHistoryPanel, CapturedPiecesPanel,
    AIThinkingPanel, TopMovesPanel, EvalBreakdownPanel,
    AIExplanationPanel, GameStatusPanel,
)
from gui.charts import AnalyticsChartsWidget
from gui.theme import Theme
from gui.dialogs import PromotionDialog, NewGameDialog, SettingsDialog


# ─── AI Worker Thread ─────────────────────────────────────────────────────────

class AIWorker(QObject):
    """
    Runs AI search in a background QThread.
    Emits signals to update the GUI safely from the main thread.
    """
    thinking_update = Signal(object)       # SearchStats
    move_selected   = Signal(object, object, str)  # Move, SearchStats, explanation

    def __init__(self, ai: AIPlayer) -> None:
        super().__init__()
        self._ai = ai

    def request(self, game: Game) -> None:
        board = game.board.clone()
        self._ai.request_move(
            board,
            result_callback=self._on_result,
            progress_callback=self._on_progress,
        )

    def _on_progress(self, stats: SearchStats) -> None:
        self.thinking_update.emit(stats)

    def _on_result(self, move: Optional[Move], stats: SearchStats,
                   explanation: str) -> None:
        self.move_selected.emit(move, stats, explanation)

    def stop(self) -> None:
        self._ai.stop()


# ─── Main Window ─────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """8by8 AI CHESS LAB main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("8by8 AI CHESS LAB")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 820)

        # Application settings
        self._settings = {
            "dark_mode":   True,
            "show_coords": True,
            "animations":  True,
            "sounds":      False,
        }

        # Game state
        self._game: Game             = Game()
        self._mode: str              = "Human vs AI"
        self._player_color: Color    = Color.WHITE
        self._ai_difficulty: str     = "Hard"
        self._ai_difficulty2: str    = "Medium"

        # AI components
        self._ai_player:  AIPlayer   = AIPlayer(Color.BLACK, "Hard")
        self._ai_worker:  AIWorker   = AIWorker(self._ai_player)
        self._ai_thread:  QThread    = QThread()
        self._ai_worker.moveToThread(self._ai_thread)
        self._ai_worker.thinking_update.connect(self._on_ai_thinking)
        self._ai_worker.move_selected.connect(self._on_ai_move)
        self._ai_thread.start()

        # AI vs AI second player
        self._ai2_player: AIPlayer   = AIPlayer(Color.WHITE, "Medium")
        self._ai2_worker: AIWorker   = AIWorker(self._ai2_player)
        self._ai2_thread: QThread    = QThread()
        self._ai2_worker.moveToThread(self._ai2_thread)
        self._ai2_worker.thinking_update.connect(self._on_ai_thinking)
        self._ai2_worker.move_selected.connect(self._on_ai_move)
        self._ai2_thread.start()

        # Analytics
        self._analytics = AnalyticsCollector()
        self._last_eval: float = 0.0
        self._move_start_time: float = 0.0

        # AI vs AI auto-play timer
        self._aivsai_timer = QTimer(self)
        self._aivsai_timer.setSingleShot(True)
        self._aivsai_timer.timeout.connect(self._trigger_ai_move)

        # Build UI
        self._build_ui()
        self._apply_theme()
        self._init_board_display()

    # ── Initial Board Display ─────────────────────────────────────────────────

    def _init_board_display(self) -> None:
        """Initialize board widget and panels after UI is built."""
        self._board_widget.set_board(self._game.board)
        self._board_widget.set_legal_moves(self._game.legal_moves())
        self._board_widget.set_interactive(True)
        self._update_eval()
        self._update_status()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toolbar
        toolbar = self._build_toolbar()
        main_layout.addWidget(toolbar)

        # Main content splitter (board | sidebar)
        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setHandleWidth(1)

        # ── Left: Board + eval bar ────────────────────────────────────────────
        board_area = QWidget()
        board_layout = QHBoxLayout(board_area)
        board_layout.setContentsMargins(16, 12, 8, 8)
        board_layout.setSpacing(8)

        self._eval_bar = EvalBar()
        board_layout.addWidget(self._eval_bar, 0, Qt.AlignTop)

        board_container = QVBoxLayout()
        board_container.setSpacing(6)

        self._status_panel = GameStatusPanel()
        board_container.addWidget(self._status_panel)

        self._board_widget = BoardWidget()
        self._board_widget.move_requested.connect(self._on_player_move)
        board_container.addWidget(self._board_widget, 1)

        self._captured_panel = CapturedPiecesPanel()
        board_container.addWidget(self._captured_panel)

        board_layout.addLayout(board_container, 1)
        content_splitter.addWidget(board_area)

        # ── Right: Sidebar ────────────────────────────────────────────────────
        sidebar = self._build_sidebar()
        content_splitter.addWidget(sidebar)

        content_splitter.setSizes([700, 380])
        content_splitter.setStretchFactor(0, 3)
        content_splitter.setStretchFactor(1, 2)

        # ── Bottom: Charts ────────────────────────────────────────────────────
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(content_splitter)

        self._charts = AnalyticsChartsWidget()
        self._charts.setMinimumHeight(180)
        self._charts.setMaximumHeight(260)
        main_splitter.addWidget(self._charts)

        main_splitter.setSizes([560, 200])
        main_splitter.setHandleWidth(2)
        main_layout.addWidget(main_splitter, 1)

    def _build_toolbar(self) -> QFrame:
        c = Theme.current()
        bar = QFrame()
        bar.setFixedHeight(52)
        bar.setStyleSheet(f"background: {c.bg_dark}; border-bottom: 1px solid {c.separator};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(8)

        # App title
        title = QLabel("♟ 8by8 AI CHESS LAB")
        title.setStyleSheet(f"color: {c.text_primary}; font-size: 15px; "
                            f"font-weight: 700; background: transparent;")
        layout.addWidget(title)
        layout.addSpacing(16)

        def _btn(text: str, slot, accent: bool = False,
                 tooltip: str = "") -> QPushButton:
            btn = QPushButton(text)
            btn.setFixedHeight(34)
            btn.setMinimumWidth(80)
            btn.setToolTip(tooltip)
            if accent:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {c.accent}; color: white; border: none;
                        border-radius: 6px; font-weight: 600; font-size: 12px;
                        padding: 0 14px;
                    }}
                    QPushButton:hover {{ background: {c.accent_hover}; }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {c.bg_medium}; color: {c.text_primary};
                        border: 1px solid {c.bg_light}; border-radius: 6px;
                        font-size: 12px; padding: 0 12px;
                    }}
                    QPushButton:hover {{ background: {c.bg_highlight}; }}
                """)
            btn.clicked.connect(slot)
            return btn

        layout.addWidget(_btn("⊕ New Game", self._new_game_dialog,
                              accent=True, tooltip="Start a new game"))
        layout.addWidget(_btn("↩ Undo",     self._undo_move,
                              tooltip="Undo last move"))
        layout.addWidget(_btn("⇌ Flip",     self._flip_board,
                              tooltip="Flip board orientation"))

        layout.addSpacing(8)

        # Difficulty selector
        diff_label = QLabel("Difficulty:")
        diff_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 12px; "
                                 f"background: transparent;")
        layout.addWidget(diff_label)

        self._diff_combo = QComboBox()
        self._diff_combo.addItems(list(DIFFICULTY_CONFIGS.keys()))
        self._diff_combo.setCurrentText("Hard")
        self._diff_combo.setFixedHeight(34)
        self._diff_combo.setMinimumWidth(100)
        self._diff_combo.currentTextChanged.connect(self._on_difficulty_changed)
        layout.addWidget(self._diff_combo)

        layout.addStretch()

        # Heatmap toggle
        layout.addWidget(_btn("🔥 Heatmap",  self._toggle_heatmap,
                              tooltip="Toggle attack heatmap"))
        layout.addWidget(_btn("📊 Export",   self._export_pgn,
                              tooltip="Export game as PGN"))
        layout.addWidget(_btn("⚙ Settings", self._open_settings,
                              tooltip="Application settings"))

        # Theme toggle
        self._theme_btn = _btn("☀ Light", self._toggle_theme,
                               tooltip="Toggle dark/light theme")
        layout.addWidget(self._theme_btn)

        return bar

    def _build_sidebar(self) -> QWidget:
        c = Theme.current()
        sidebar = QScrollArea()
        sidebar.setWidgetResizable(True)
        sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sidebar.setFixedWidth(370)
        sidebar.setStyleSheet(f"background: {c.bg_darkest}; border: none;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Eval breakdown
        self._eval_breakdown = EvalBreakdownPanel()
        layout.addWidget(self._eval_breakdown)

        # AI thinking
        self._ai_panel = AIThinkingPanel()
        layout.addWidget(self._ai_panel)

        # Top candidates
        self._top_moves = TopMovesPanel()
        layout.addWidget(self._top_moves)

        # Move history
        self._move_history = MoveHistoryPanel()
        self._move_history.setMinimumHeight(180)
        layout.addWidget(self._move_history)

        # AI explanation
        self._explanation = AIExplanationPanel()
        layout.addWidget(self._explanation)

        layout.addStretch()
        sidebar.setWidget(container)
        return sidebar

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _apply_theme(self) -> None:
        if self._settings["dark_mode"]:
            Theme.set_dark()
            if hasattr(self, "_theme_btn"):
                self._theme_btn.setText("☀ Light")
        else:
            Theme.set_light()
            if hasattr(self, "_theme_btn"):
                self._theme_btn.setText("🌙 Dark")
        self.setStyleSheet(Theme.stylesheet())

    def _toggle_theme(self) -> None:
        self._settings["dark_mode"] = not self._settings["dark_mode"]
        self._apply_theme()

    # ── Game Initialization ───────────────────────────────────────────────────

    def _new_game_dialog(self) -> None:
        dlg = NewGameDialog(self)
        if dlg.exec():
            cfg = dlg.get_config()
            self._start_new_game(
                mode=cfg["mode"],
                player_color_str=cfg["player_color"],
                difficulty=cfg["difficulty"],
                difficulty2=cfg["difficulty2"],
            )

    def _start_new_game(self, mode: str = "Human vs AI",
                        player_color_str: str = "White",
                        difficulty: str = "Hard",
                        difficulty2: str = "Medium") -> None:
        # Stop any running AI
        self._ai_player.stop()
        self._ai2_player.stop()

        self._game = Game()
        self._mode = mode
        self._player_color = (Color.WHITE if player_color_str == "White"
                               else Color.BLACK)
        self._ai_difficulty  = difficulty
        self._ai_difficulty2 = difficulty2

        self._ai_player.color      = Color.BLACK if self._player_color == Color.WHITE else Color.WHITE
        self._ai_player.difficulty = difficulty
        self._ai_player.engine.tt.clear()

        self._ai2_player.color      = Color.WHITE
        self._ai2_player.difficulty = difficulty2
        self._ai2_player.engine.tt.clear()

        self._analytics.reset()
        self._last_eval = 0.0
        self._charts.clear_all()

        self._board_widget.set_board(self._game.board)
        self._board_widget.set_legal_moves(self._game.legal_moves())
        self._board_widget.set_last_move(None)
        self._board_widget.clear_selection()
        self._board_widget.clear_heatmap()

        self._ai_panel.reset()
        self._top_moves.clear()
        self._eval_breakdown.clear()
        self._explanation.clear()
        self._move_history.clear()
        self._eval_bar.set_score(0)

        # Set interactivity
        is_human_turn = (mode != "AI vs AI") and (
            self._game.side_to_move == self._player_color)
        self._board_widget.set_interactive(is_human_turn)

        self._update_status()
        self._update_eval()

        # Trigger AI if needed
        if mode == "AI vs AI":
            self._board_widget.set_interactive(False)
            self._aivsai_timer.start(800)
        elif mode == "Human vs AI" and self._player_color == Color.BLACK:
            # AI plays White first
            self._trigger_ai_move()

    # ── Player Move ───────────────────────────────────────────────────────────

    def _on_player_move(self, move: Move) -> None:
        if self._game.result != GameResult.ONGOING:
            return
        if self._mode == "AI vs AI":
            return

        # Handle promotion: ask player
        if (move.piece.piece_type == PieceType.PAWN and
                move.is_promotion and move.promotion is None):
            dlg = PromotionDialog(move.piece.color, self)
            if dlg.exec():
                move = Move(move.from_sq, move.to_sq, move.piece,
                            captured=move.captured,
                            promotion=dlg.chosen_piece(),
                            flag=move.flag)

        start_t = self._move_start_time or time.time()
        elapsed = time.time() - start_t

        # Evaluate before move
        eval_before, _ = Evaluator.evaluate(self._game.board)

        if not self._game.push_move(move):
            return

        # Evaluate after move
        eval_after, bd = Evaluator.evaluate(self._game.board, detail=True)

        # Record analytics
        record = self._analytics.record_move(
            move_number=self._game.board.fullmove_number,
            color=self._player_color,
            san=self._game.move_records[-1].san if self._game.move_records else "",
            eval_before=eval_before / 100,
            eval_after=eval_after / 100,
            depth=0,
            nodes=0,
            time_taken=elapsed,
        )

        self._post_move_update(move, eval_after, bd, is_ai=False)

        if self._game.result == GameResult.ONGOING:
            self._board_widget.set_interactive(False)
            self._trigger_ai_move()

    def _trigger_ai_move(self) -> None:
        if self._game.result != GameResult.ONGOING:
            return

        color = self._game.side_to_move
        self._ai_panel.set_thinking(True)
        self._move_start_time = time.time()

        if self._mode == "AI vs AI":
            ai = self._ai_player if color == Color.BLACK else self._ai2_player
            worker = self._ai_worker if color == Color.BLACK else self._ai2_worker
        else:
            ai   = self._ai_player
            worker = self._ai_worker

        worker.request(self._game)

    def _on_ai_thinking(self, stats: SearchStats) -> None:
        self._ai_panel.update_stats(stats)
        if stats.top_moves:
            self._top_moves.update_moves(stats.top_moves)

    def _on_ai_move(self, move: Optional[Move], stats: SearchStats,
                    explanation: str) -> None:
        self._ai_panel.set_thinking(False)

        if self._game.result != GameResult.ONGOING or move is None:
            return

        elapsed = time.time() - self._move_start_time
        eval_before, _ = Evaluator.evaluate(self._game.board)

        if not self._game.push_move(move, eval_score=stats.best_score/100,
                                    time_taken=elapsed):
            return

        eval_after, bd = Evaluator.evaluate(self._game.board, detail=True)

        # Record analytics for AI move
        color = move.piece.color
        self._analytics.record_move(
            move_number=self._game.board.fullmove_number,
            color=color,
            san=self._game.move_records[-1].san if self._game.move_records else "",
            eval_before=eval_before / 100,
            eval_after=eval_after / 100,
            depth=stats.depth_reached,
            nodes=stats.total_nodes,
            time_taken=elapsed,
        )

        if bd:
            self._eval_breakdown.update_breakdown(bd)
        self._explanation.set_explanation(explanation)
        self._ai_panel.update_stats(stats)
        if stats.top_moves:
            self._top_moves.update_moves(stats.top_moves)

        self._post_move_update(move, eval_after, bd, is_ai=True)

        # Continue AI vs AI
        if self._mode == "AI vs AI" and self._game.result == GameResult.ONGOING:
            self._aivsai_timer.start(600)
        elif self._game.result == GameResult.ONGOING:
            self._board_widget.set_interactive(True)

    # ── Post-Move Updates ─────────────────────────────────────────────────────

    def _post_move_update(self, move: Move, eval_after: int,
                          bd, is_ai: bool) -> None:
        # Board widget
        self._board_widget.set_board(self._game.board)
        self._board_widget.set_legal_moves(self._game.legal_moves())
        self._board_widget.set_last_move(move)
        self._board_widget.clear_selection()

        # Animate piece
        if self._settings["animations"]:
            self._board_widget.animate_move(move, move.piece)

        # Check highlight
        check_sq = None
        if self._game.is_in_check:
            check_sq = self._game.board.king_square(self._game.side_to_move)
        self._board_widget.set_check_square(check_sq)

        # Move history
        self._move_history.update_moves(self._game.san_history())

        # Eval bar
        self._eval_bar.set_score(eval_after)
        self._last_eval = eval_after

        # Captured pieces
        self._captured_panel.update_captured(
            self._game.captured_white,
            self._game.captured_black,
        )

        # Charts
        self._charts.eval_chart.update_data(
            self._analytics.data.eval_history)

        dp_list   = self._analytics.data.move_data
        depths    = [d.depth for d in dp_list]
        nodes_lst = [d.nodes for d in dp_list]
        self._charts.depth_chart.update_data(depths, nodes_lst)

        wq = self._analytics.data.quality_counts("White")
        bq = self._analytics.data.quality_counts("Black")
        self._charts.quality_chart.update_data(wq, bq)

        # Status
        self._update_status()

    def _update_eval(self) -> None:
        score, bd = Evaluator.evaluate(self._game.board, detail=True)
        self._eval_bar.set_score(score)
        if bd:
            self._eval_breakdown.update_breakdown(bd)

    def _update_status(self) -> None:
        result = self._game.result
        result_text = "" if result == GameResult.ONGOING else result.display_text()
        self._status_panel.update_status(
            self._game.side_to_move,
            self._game.is_in_check,
            result_text,
        )
        if result != GameResult.ONGOING:
            self._analytics.set_result(result_text)
            self._board_widget.set_interactive(False)

    # ── Controls ──────────────────────────────────────────────────────────────

    def _undo_move(self) -> None:
        if self._game.result != GameResult.ONGOING:
            self._game.result = GameResult.ONGOING
        # Undo twice if AI just moved (undo AI + human)
        for _ in range(2):
            if self._game.undo():
                if self._analytics.data.move_data:
                    self._analytics.data.move_data.pop()
                if self._analytics.data.eval_history:
                    self._analytics.data.eval_history.pop()

        self._board_widget.set_board(self._game.board)
        self._board_widget.set_legal_moves(self._game.legal_moves())
        last = (self._game.move_records[-1].move
                if self._game.move_records else None)
        self._board_widget.set_last_move(last)
        self._board_widget.clear_selection()
        self._board_widget.set_check_square(None)
        self._board_widget.set_interactive(True)

        self._move_history.update_moves(self._game.san_history())
        self._eval_breakdown.clear()
        self._explanation.clear()
        self._ai_panel.reset()
        self._update_eval()
        self._update_status()

        self._charts.eval_chart.update_data(self._analytics.data.eval_history)

    def _flip_board(self) -> None:
        self._board_widget.flip()

    def _toggle_heatmap(self) -> None:
        if self._board_widget._show_heatmap:
            self._board_widget.clear_heatmap()
        else:
            # Show attacked squares for the side to move
            color = self._game.side_to_move
            attacked = MoveGenerator.attacked_squares(self._game.board, color)
            data = {sq: 1 for sq in attacked}
            self._board_widget.set_heatmap(color, data)

    def _on_difficulty_changed(self, difficulty: str) -> None:
        self._ai_difficulty = difficulty
        self._ai_player.set_difficulty(difficulty)

    # ── Export ────────────────────────────────────────────────────────────────

    def _export_pgn(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Game", "game.pgn", "PGN files (*.pgn);;All files (*)")
        if path:
            pgn = self._game.to_pgn()
            with open(path, "w") as f:
                f.write(pgn)
            # Also write analytics JSON alongside
            json_path = path.replace(".pgn", "_analysis.json")
            with open(json_path, "w") as f:
                f.write(self._analytics.data.to_json())
            QMessageBox.information(self, "Export",
                                    f"Game saved to:\n{path}\n\nAnalysis saved to:\n{json_path}")

    def _export_analysis(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Analysis", "analysis.txt",
            "Text files (*.txt);;All files (*)")
        if path:
            report = self._analytics.data.analysis_report()
            with open(path, "w") as f:
                f.write(report)

    # ── Settings ──────────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self._settings, self)
        if dlg.exec():
            new = dlg.get_settings()
            self._settings.update(new)
            self._board_widget._show_coords = new["show_coords"]
            self._board_widget.update()
            self._apply_theme()

    # ── Closing ───────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self._ai_player.stop()
        self._ai2_player.stop()
        self._ai_thread.quit()
        self._ai2_thread.quit()
        self._ai_thread.wait(500)
        self._ai2_thread.wait(500)
        event.accept()
