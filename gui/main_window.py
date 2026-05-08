"""
gui/main_window.py
==================
Main window for 8by8 AI CHESS LAB — design.md warm-minimalist layout.

Layout:
  ┌─────────────────────────────────────────────────────────┐
  │  Toolbar 52px: brand · actions · difficulty · controls  │
  ├─────────────────────────┬───────────────────────────────┤
  │   EvalBar │ Board       │  Sidebar (360px)              │
  │           │  (square)   │   status / eval / engine      │
  │           │             │   candidates / history        │
  │           │  Status bar │   reasoning                   │
  ├─────────────────────────┴───────────────────────────────┤
  │   Charts strip (collapsible, 200px)                     │
  └─────────────────────────────────────────────────────────┘

Typography, color, spacing follow design.md tokens exactly.
"""
from __future__ import annotations

import time
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QPushButton, QComboBox, QLabel, QFileDialog, QMessageBox,
    QFrame, QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QTimer
from PySide6.QtGui import QFont

from engine.game import Game, GameResult
from engine.pieces import Color, PieceType
from engine.moves import Move
from engine.move_generator import MoveGenerator
from ai.player import AIPlayer, DIFFICULTY_CONFIGS
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
from gui.theme import Theme, FONT_UI, FONT_MONO, R_SM, R, R_LG
from gui.dialogs import PromotionDialog, NewGameDialog, SettingsDialog


# ─── AI Worker Thread ─────────────────────────────────────────────────────────

class AIWorker(QObject):
    thinking_update = Signal(object)
    move_selected   = Signal(object, object, str)

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
    """8by8 AI CHESS LAB — main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("8by8 AI CHESS LAB")
        self.setMinimumSize(1060, 700)
        self.resize(1240, 800)

        self._settings = {
            "dark_mode":   True,
            "show_coords": True,
            "animations":  True,
            "sounds":      False,
        }

        # Game state
        self._game:           Game       = Game()
        self._mode:           str        = "Human vs AI"
        self._player_color:   Color      = Color.WHITE
        self._ai_difficulty:  str        = "Hard"
        self._ai_difficulty2: str        = "Medium"

        # AI
        self._ai_player  = AIPlayer(Color.BLACK, "Hard")
        self._ai_worker  = AIWorker(self._ai_player)
        self._ai_thread  = QThread()
        self._ai_worker.moveToThread(self._ai_thread)
        self._ai_worker.thinking_update.connect(self._on_ai_thinking)
        self._ai_worker.move_selected.connect(self._on_ai_move)
        self._ai_thread.start()

        self._ai2_player = AIPlayer(Color.WHITE, "Medium")
        self._ai2_worker = AIWorker(self._ai2_player)
        self._ai2_thread = QThread()
        self._ai2_worker.moveToThread(self._ai2_thread)
        self._ai2_worker.thinking_update.connect(self._on_ai_thinking)
        self._ai2_worker.move_selected.connect(self._on_ai_move)
        self._ai2_thread.start()

        # Analytics
        self._analytics       = AnalyticsCollector()
        self._last_eval:float = 0.0
        self._move_start_t:float = 0.0

        # AI vs AI auto-play
        self._aivsai_timer = QTimer(self)
        self._aivsai_timer.setSingleShot(True)
        self._aivsai_timer.timeout.connect(self._trigger_ai_move)

        self._build_ui()
        self._apply_theme()
        self._init_board_display()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _init_board_display(self) -> None:
        self._board_widget.set_board(self._game.board)
        self._board_widget.set_legal_moves(self._game.legal_moves())
        self._board_widget.set_interactive(True)
        self._update_eval()
        self._update_status()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Toolbar
        root.addWidget(self._build_toolbar())

        # Main splitter: board+sidebar / charts
        outer = QSplitter(Qt.Vertical)
        outer.setHandleWidth(1)

        # Content: board | sidebar
        inner = QSplitter(Qt.Horizontal)
        inner.setHandleWidth(1)
        inner.addWidget(self._build_board_area())
        inner.addWidget(self._build_sidebar())
        inner.setSizes([740, 360])
        inner.setStretchFactor(0, 3)
        inner.setStretchFactor(1, 2)

        # Charts strip
        self._charts = AnalyticsChartsWidget()
        self._charts.setMinimumHeight(160)
        self._charts.setMaximumHeight(240)

        outer.addWidget(inner)
        outer.addWidget(self._charts)
        outer.setSizes([580, 200])
        root.addWidget(outer, 1)

    def _build_toolbar(self) -> QFrame:
        t = Theme.current()
        bar = QFrame()
        bar.setObjectName("toolbar")
        bar.setFixedHeight(52)
        bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(6)

        # Brand
        brand = QLabel("8by8")
        brand.setStyleSheet(
            f"color:{t.ink}; font-size:15px; font-weight:700;"
            f"letter-spacing:-0.02em; background:transparent;"
        )
        layout.addWidget(brand)

        sub = QLabel("AI CHESS LAB")
        sub.setStyleSheet(
            f"color:{t.ink4}; font-size:10px; font-weight:500;"
            f"letter-spacing:0.12em; font-family:{FONT_MONO};"
            f"background:transparent; padding-top:2px;"
        )
        layout.addWidget(sub)

        # Thin vertical separator
        def _vsep():
            s = QFrame()
            s.setFixedWidth(1)
            s.setFixedHeight(20)
            s.setStyleSheet(f"background:{t.border}; border:none;")
            return s

        layout.addSpacing(10)
        layout.addWidget(_vsep())
        layout.addSpacing(6)

        # Action buttons
        def _tbtn(text: str, slot, tooltip: str = "", accent: bool = False) -> QPushButton:
            btn = QPushButton(text)
            btn.setToolTip(tooltip)
            btn.setFixedHeight(32)
            btn.setMinimumWidth(72)
            if accent:
                btn.setObjectName("accent")
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background:{t.accent}; color:{t.accent_fg};
                        border:none; border-radius:{R_SM}px;
                        font-weight:600; font-size:12px;
                        font-family:{FONT_UI};
                        padding:0 16px; min-height:32px;
                    }}
                    QPushButton:hover {{ background:{t.ink2}; }}
                    QPushButton:pressed {{ background:{t.ink}; }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background:transparent; color:{t.ink3};
                        border:1px solid {t.border}; border-radius:{R_SM}px;
                        font-size:12px; font-family:{FONT_UI};
                        padding:0 12px; min-height:32px;
                    }}
                    QPushButton:hover {{
                        background:{t.surface};
                        color:{t.ink};
                        border-color:{t.border2};
                    }}
                    QPushButton:pressed {{ background:{t.surface2}; }}
                """)
            btn.clicked.connect(slot)
            return btn

        layout.addWidget(_tbtn("New Game",  self._new_game_dialog,
                               "Start a new game", accent=True))
        layout.addWidget(_tbtn("Undo",      self._undo_move,
                               "Undo last move"))
        layout.addWidget(_tbtn("Flip",      self._flip_board,
                               "Flip board orientation"))
        layout.addWidget(_tbtn("Heatmap",   self._toggle_heatmap,
                               "Toggle attack heatmap"))

        layout.addSpacing(6)
        layout.addWidget(_vsep())
        layout.addSpacing(6)

        # Difficulty
        diff_lbl = QLabel("Difficulty")
        diff_lbl.setStyleSheet(
            f"color:{t.ink4}; font-size:10px; font-weight:500;"
            f"letter-spacing:0.08em; font-family:{FONT_MONO};"
            f"background:transparent; text-transform:uppercase;"
        )
        layout.addWidget(diff_lbl)

        self._diff_combo = QComboBox()
        self._diff_combo.addItems(list(DIFFICULTY_CONFIGS.keys()))
        self._diff_combo.setCurrentText("Hard")
        self._diff_combo.setFixedHeight(32)
        self._diff_combo.setStyleSheet(f"""
            QComboBox {{
                background:{t.surface}; color:{t.ink2};
                border:1px solid {t.border}; border-radius:{R_SM}px;
                padding:0 10px; font-size:12px;
                font-family:{FONT_UI}; min-height:32px; min-width:90px;
            }}
            QComboBox:hover {{ border-color:{t.border2}; color:{t.ink}; }}
            QComboBox::drop-down {{ border:none; width:18px; }}
            QComboBox QAbstractItemView {{
                background:{t.surface}; border:1px solid {t.border2};
                color:{t.ink}; selection-background-color:{t.surface2};
                border-radius:{R_SM}px; padding:4px; outline:none;
            }}
        """)
        self._diff_combo.currentTextChanged.connect(self._on_difficulty_changed)
        layout.addWidget(self._diff_combo)

        layout.addStretch()

        # Right controls
        layout.addWidget(_tbtn("Export",   self._export_pgn,   "Export PGN + analysis"))
        layout.addWidget(_tbtn("Settings", self._open_settings, "Settings"))

        self._theme_btn = _tbtn("Light", self._toggle_theme, "Toggle theme")
        layout.addWidget(self._theme_btn)
        return bar

    def _build_board_area(self) -> QWidget:
        t = Theme.current()
        area = QWidget()
        area.setStyleSheet(f"background:{t.bg};")
        layout = QHBoxLayout(area)
        layout.setContentsMargins(20, 16, 12, 16)
        layout.setSpacing(10)

        # Eval bar (thin, left)
        self._eval_bar = EvalBar()
        layout.addWidget(self._eval_bar, 0, Qt.AlignTop)

        # Board column
        col = QVBoxLayout()
        col.setSpacing(8)

        # Status bar above board
        self._status_panel = GameStatusPanel()
        self._status_panel.setFixedHeight(40)
        col.addWidget(self._status_panel)

        # Board
        self._board_widget = BoardWidget()
        self._board_widget.move_requested.connect(self._on_player_move)
        col.addWidget(self._board_widget, 1)

        # Captured pieces below board
        self._captured_panel = CapturedPiecesPanel()
        self._captured_panel.setFixedHeight(36)
        self._captured_panel.setStyleSheet(f"background:transparent;")
        col.addWidget(self._captured_panel)

        layout.addLayout(col, 1)
        return area

    def _build_sidebar(self) -> QWidget:
        t = Theme.current()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFixedWidth(360)
        scroll.setStyleSheet(
            f"background:{t.bg2}; border:none; border-left:1px solid {t.border};"
        )

        container = QWidget()
        container.setStyleSheet(f"background:{t.bg2};")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Eval breakdown
        self._eval_breakdown = EvalBreakdownPanel()
        layout.addWidget(self._eval_breakdown)

        # AI thinking
        self._ai_panel = AIThinkingPanel()
        layout.addWidget(self._ai_panel)

        # Top candidates
        self._top_moves = TopMovesPanel()
        layout.addWidget(self._top_moves)

        # Move history (flexible height)
        self._move_history = MoveHistoryPanel()
        self._move_history.setMinimumHeight(160)
        layout.addWidget(self._move_history, 1)

        # AI reasoning
        self._explanation = AIExplanationPanel()
        layout.addWidget(self._explanation)

        scroll.setWidget(container)
        return scroll

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _apply_theme(self) -> None:
        if self._settings["dark_mode"]:
            Theme.set_dark()
        else:
            Theme.set_light()
        self.setStyleSheet(Theme.stylesheet())
        if hasattr(self, "_theme_btn"):
            self._theme_btn.setText("Light" if Theme.is_dark() else "Dark")

    def _toggle_theme(self) -> None:
        self._settings["dark_mode"] = not self._settings["dark_mode"]
        self._apply_theme()

    # ── Game Initialization ───────────────────────────────────────────────────

    def _new_game_dialog(self) -> None:
        dlg = NewGameDialog(self)
        if dlg.exec():
            cfg = dlg.get_config()
            self._start_new_game(cfg["mode"], cfg["player_color"],
                                 cfg["difficulty"], cfg["difficulty2"])

    def _start_new_game(self, mode: str = "Human vs AI",
                        player_color_str: str = "White",
                        difficulty: str = "Hard",
                        difficulty2: str = "Medium") -> None:
        self._ai_player.stop()
        self._ai2_player.stop()

        self._game            = Game()
        self._mode            = mode
        self._player_color    = (Color.WHITE if player_color_str == "White"
                                 else Color.BLACK)
        self._ai_difficulty   = difficulty
        self._ai_difficulty2  = difficulty2

        self._ai_player.color      = self._player_color.opponent()
        self._ai_player.difficulty = difficulty
        self._ai_player.engine.tt.clear()

        self._ai2_player.color      = Color.WHITE
        self._ai2_player.difficulty = difficulty2
        self._ai2_player.engine.tt.clear()

        self._analytics.reset()
        self._last_eval    = 0.0
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

        is_human = (mode != "AI vs AI") and (
            self._game.side_to_move == self._player_color)
        self._board_widget.set_interactive(is_human)

        self._update_status()
        self._update_eval()

        if mode == "AI vs AI":
            self._board_widget.set_interactive(False)
            self._aivsai_timer.start(800)
        elif mode == "Human vs AI" and self._player_color == Color.BLACK:
            self._trigger_ai_move()

    # ── Human Move ────────────────────────────────────────────────────────────

    def _on_player_move(self, move: Move) -> None:
        if self._game.result != GameResult.ONGOING:
            return
        if self._mode == "AI vs AI":
            return

        # Promotion dialog
        if (move.piece.piece_type == PieceType.PAWN
                and move.is_promotion and move.promotion is None):
            dlg = PromotionDialog(move.piece.color, self)
            if dlg.exec():
                move = Move(move.from_sq, move.to_sq, move.piece,
                            captured=move.captured,
                            promotion=dlg.chosen_piece(),
                            flag=move.flag)

        elapsed       = max(0.0, time.time() - self._move_start_t)
        eval_before,_ = Evaluator.evaluate(self._game.board)

        if not self._game.push_move(move):
            return

        eval_after, bd = Evaluator.evaluate(self._game.board, detail=True)
        self._analytics.record_move(
            self._game.board.fullmove_number,
            self._player_color,
            self._game.move_records[-1].san if self._game.move_records else "",
            eval_before / 100, eval_after / 100,
            0, 0, elapsed,
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
        self._move_start_t = time.time()

        if self._mode == "AI vs AI":
            worker = self._ai_worker if color == Color.BLACK else self._ai2_worker
        else:
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

        elapsed       = max(0.0, time.time() - self._move_start_t)
        eval_before,_ = Evaluator.evaluate(self._game.board)

        if not self._game.push_move(move, eval_score=stats.best_score / 100,
                                    time_taken=elapsed):
            return

        eval_after, bd = Evaluator.evaluate(self._game.board, detail=True)
        color = move.piece.color
        self._analytics.record_move(
            self._game.board.fullmove_number, color,
            self._game.move_records[-1].san if self._game.move_records else "",
            eval_before / 100, eval_after / 100,
            stats.depth_reached, stats.total_nodes, elapsed,
        )

        if bd:
            self._eval_breakdown.update_breakdown(bd)
        self._explanation.set_explanation(explanation)
        self._ai_panel.update_stats(stats)
        if stats.top_moves:
            self._top_moves.update_moves(stats.top_moves)

        self._post_move_update(move, eval_after, bd, is_ai=True)

        if self._mode == "AI vs AI" and self._game.result == GameResult.ONGOING:
            self._aivsai_timer.start(600)
        elif self._game.result == GameResult.ONGOING:
            self._board_widget.set_interactive(True)

    # ── Post-move ─────────────────────────────────────────────────────────────

    def _post_move_update(self, move: Move, eval_after: int, bd, is_ai: bool) -> None:
        self._board_widget.set_board(self._game.board)
        self._board_widget.set_legal_moves(self._game.legal_moves())
        self._board_widget.set_last_move(move)
        self._board_widget.clear_selection()

        if self._settings["animations"]:
            self._board_widget.animate_move(move, move.piece)

        check_sq = None
        if self._game.is_in_check:
            check_sq = self._game.board.king_square(self._game.side_to_move)
        self._board_widget.set_check_square(check_sq)

        self._move_history.update_moves(self._game.san_history())
        self._eval_bar.set_score(eval_after)
        self._last_eval = eval_after

        self._captured_panel.update_captured(
            self._game.captured_white,
            self._game.captured_black,
        )

        # Charts
        self._charts.eval_chart.update_data(self._analytics.data.eval_history)
        dp = self._analytics.data.move_data
        self._charts.depth_chart.update_data(
            [d.depth for d in dp], [d.nodes for d in dp])
        self._charts.quality_chart.update_data(
            self._analytics.data.quality_counts("White"),
            self._analytics.data.quality_counts("Black"),
        )
        self._update_status()

    def _update_eval(self) -> None:
        score, bd = Evaluator.evaluate(self._game.board, detail=True)
        self._eval_bar.set_score(score)
        if bd:
            self._eval_breakdown.update_breakdown(bd)

    def _update_status(self) -> None:
        result = self._game.result
        text   = "" if result == GameResult.ONGOING else result.display_text()
        self._status_panel.update_status(
            self._game.side_to_move, self._game.is_in_check, text)
        if result != GameResult.ONGOING:
            self._analytics.set_result(text)
            self._board_widget.set_interactive(False)

    # ── Controls ──────────────────────────────────────────────────────────────

    def _undo_move(self) -> None:
        if self._game.result != GameResult.ONGOING:
            self._game.result = GameResult.ONGOING
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
            color = self._game.side_to_move
            attacked = MoveGenerator.attacked_squares(self._game.board, color)
            self._board_widget.set_heatmap(color, {s: 1 for s in attacked})

    def _on_difficulty_changed(self, d: str) -> None:
        self._ai_difficulty = d
        self._ai_player.set_difficulty(d)

    # ── Export ────────────────────────────────────────────────────────────────

    def _export_pgn(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Game", "game.pgn", "PGN files (*.pgn);;All files (*)")
        if not path:
            return
        pgn = self._game.to_pgn(white_name="Player", black_name="8by8 AI")
        with open(path, "w") as f:
            f.write(pgn)
        json_path = path.replace(".pgn", "_analysis.json")
        with open(json_path, "w") as f:
            f.write(self._analytics.data.to_json())
        QMessageBox.information(
            self, "Export Complete",
            f"PGN saved to:\n{path}\n\nAnalysis saved to:\n{json_path}")

    # ── Settings ──────────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self._settings, self)
        if dlg.exec():
            new = dlg.get_settings()
            self._settings.update(new)
            self._board_widget._show_coords = new["show_coords"]
            self._board_widget.update()
            self._apply_theme()

    # ── Close ─────────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self._ai_player.stop()
        self._ai2_player.stop()
        self._ai_thread.quit();  self._ai_thread.wait(500)
        self._ai2_thread.quit(); self._ai2_thread.wait(500)
        event.accept()
