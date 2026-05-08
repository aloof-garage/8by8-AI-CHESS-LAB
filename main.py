#!/usr/bin/env python3
"""
main.py
=======
8by8 AI CHESS LAB — Application entry point.

Usage:
    python main.py

Requires: PySide6, matplotlib
"""

import sys
import os

# Ensure project root is on the path (useful when running from a subdirectory)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from gui.main_window import MainWindow
from gui.theme import Theme


def main() -> None:
    # Enable high-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("8by8 AI CHESS LAB")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("8by8 AI CHESS LAB")

    # Apply global font
    font = QFont("Segoe UI", 11)
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)

    # Apply global stylesheet
    Theme.set_dark()
    app.setStyleSheet(Theme.stylesheet())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
