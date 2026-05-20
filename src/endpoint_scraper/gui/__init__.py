"""Endpoint Scraper GUI package."""

import sys
from PyQt6.QtWidgets import QApplication
from .styles import style
from .window import EndpointViewer


def run():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(style())
    win = EndpointViewer()
    win.show()
    sys.exit(app.exec())
