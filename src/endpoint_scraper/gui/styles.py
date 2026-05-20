"""Catppuccin Mocha stylesheet for the GUI."""


def style():
    return """
    QMainWindow, QWidget {
        background-color: #1e1e2e;
        color: #cdd6f4;
        font-family: 'Segoe UI', sans-serif;
        font-size: 13px;
    }
    QLineEdit {
        background-color: #313244;
        border: 1px solid #45475a;
        border-radius: 6px;
        padding: 8px 12px;
        color: #cdd6f4;
        font-size: 14px;
    }
    QLineEdit:focus { border: 1px solid #89b4fa; }
    QComboBox {
        background-color: #313244;
        border: 1px solid #45475a;
        border-radius: 6px;
        padding: 6px 12px;
        color: #cdd6f4;
        min-width: 160px;
    }
    QComboBox::drop-down { border: none; }
    QComboBox QAbstractItemView {
        background-color: #313244;
        color: #cdd6f4;
        selection-background-color: #45475a;
    }
    QTableWidget {
        background-color: #181825;
        alternate-background-color: #1e1e2e;
        gridline-color: #313244;
        border: 1px solid #313244;
        border-radius: 8px;
        color: #cdd6f4;
        font-size: 13px;
    }
    QTableWidget::item { padding: 6px; }
    QTableWidget::item:selected { background-color: #45475a; }
    QHeaderView::section {
        background-color: #313244;
        color: #89b4fa;
        font-weight: bold;
        font-size: 13px;
        padding: 8px;
        border: none;
        border-right: 1px solid #45475a;
        border-bottom: 2px solid #89b4fa;
    }
    QTreeWidget {
        background-color: #181825;
        border: 1px solid #313244;
        border-radius: 8px;
        color: #cdd6f4;
    }
    QTreeWidget::item { padding: 4px; }
    QTreeWidget::item:selected { background-color: #45475a; }
    QProgressBar {
        background-color: #313244;
        border: none;
        border-radius: 4px;
        height: 8px;
        text-align: center;
    }
    QProgressBar::chunk { background-color: #89b4fa; border-radius: 4px; }
    QPushButton {
        background-color: #313244;
        border: 1px solid #45475a;
        border-radius: 6px;
        padding: 6px 14px;
        color: #cdd6f4;
    }
    QPushButton:hover { background-color: #45475a; border: 1px solid #89b4fa; }
    QPushButton:disabled { color: #585b70; }
    QTabWidget::pane { border: 1px solid #313244; border-radius: 6px; }
    QTabBar::tab {
        background-color: #313244;
        color: #a6adc8;
        padding: 8px 18px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
    }
    QTabBar::tab:selected { background-color: #45475a; color: #89b4fa; }
    QStatusBar { background-color: #181825; color: #a6adc8; }
    QLabel#statLabel { color: #a6adc8; font-size: 12px; }
    QLabel#headerLabel { color: #89b4fa; font-size: 18px; font-weight: bold; }
    QTextEdit {
        background-color: #181825;
        border: 1px solid #313244;
        border-radius: 8px;
        color: #a6adc8;
        font-family: 'Cascadia Code', 'Consolas', monospace;
        font-size: 12px;
        padding: 6px;
    }
    QScrollBar:vertical {
        background: #181825;
        width: 10px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical {
        background: #45475a;
        border-radius: 5px;
        min-height: 30px;
    }
    QScrollBar::handle:vertical:hover { background: #585b70; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    """
