"""Main application window."""

import re
import os
from collections import Counter
from urllib.parse import urlparse

import qtawesome as qta
import requests
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QComboBox, QLabel, QFrame, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QPushButton, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QProgressBar, QTextEdit, QMenu,
    QApplication,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QColor, QDesktopServices

from .constants import CATEGORY_COLORS, CSV_PATH, cat_icon, load_csv
from .workers import ScrapeWorker, StatusWorker


class EndpointViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Endpoint Scraper — Dashboard")
        self._window_icon = qta.icon("ph.crosshair-simple", color="#89b4fa")
        self.setWindowIcon(self._window_icon)
        self.setMinimumSize(1200, 750)
        self.worker = None
        self.data = load_csv(CSV_PATH)
        self.filtered = list(self.data)
        self._build_ui()
        self._connect_signals()
        self._apply_stats()
        self._populate_table()
        self._populate_tree()

    # ── UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 8)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Endpoint Scraper")
        title.setObjectName("headerLabel")
        hdr.addWidget(title)
        hdr.addStretch()
        self.lbl_total = QLabel()
        self.lbl_total.setObjectName("statLabel")
        hdr.addWidget(self.lbl_total)
        root.addLayout(hdr)

        # ── Landing page tab ────────────────────────────────────────────
        self.landing_widget = QWidget()
        landing_layout = QVBoxLayout(self.landing_widget)
        landing_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        landing_layout.setSpacing(20)

        big_icon = QLabel()
        big_icon.setPixmap(qta.icon("ph.crosshair-simple", color="#89b4fa").pixmap(64, 64))
        big_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        landing_layout.addWidget(big_icon)

        landing_title = QLabel("Start a New Scrape")
        landing_title.setStyleSheet("color: #89b4fa; font-size: 22px; font-weight: bold;")
        landing_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        landing_layout.addWidget(landing_title)

        landing_sub = QLabel("Paste a target URL and choose your scrape mode")
        landing_sub.setStyleSheet("color: #a6adc8; font-size: 14px;")
        landing_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        landing_layout.addWidget(landing_sub)

        landing_layout.addSpacing(10)

        url_row = QHBoxLayout()
        url_row.addStretch()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("  Paste target URL (e.g. https://example.com)")
        self.url_input.setFixedWidth(500)
        self.url_input.setMinimumHeight(38)
        url_row.addWidget(self.url_input)
        url_row.addStretch()
        landing_layout.addLayout(url_row)

        ctrl_row = QHBoxLayout()
        ctrl_row.addStretch()
        mode_label = QLabel("Mode:")
        mode_label.setStyleSheet("color: #a6adc8; font-size: 13px;")
        ctrl_row.addWidget(mode_label)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem(qta.icon("ph.file", color="#89b4fa"), "Single Page")
        self.mode_combo.addItem(qta.icon("ph.tree-structure", color="#89b4fa"), "Whole Site")
        self.mode_combo.setFixedWidth(180)
        ctrl_row.addWidget(self.mode_combo)
        ctrl_row.addSpacing(10)
        self.btn_scrape = QPushButton("  Start Scrape")
        self.btn_scrape.setIcon(qta.icon("ph.play", color="#a6adc8"))
        self.btn_scrape.setMinimumHeight(36)
        ctrl_row.addWidget(self.btn_scrape)
        ctrl_row.addStretch()
        landing_layout.addLayout(ctrl_row)

        # ── Filter bar ──────────────────────────────────────────────────
        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            "QFrame { background-color: #181825; border: 1px solid #313244; border-radius: 8px; }"
        )
        filt = QHBoxLayout(filter_frame)
        filt.setSpacing(10)
        filt.setContentsMargins(10, 8, 10, 8)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search endpoints\u2026")
        filt.addWidget(self.search, 1)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #313244;")
        sep.setFixedHeight(24)
        filt.addWidget(sep)

        self.exclude_input = QLineEdit()
        self.exclude_input.setPlaceholderText("Exclude regex\u2026")
        self.exclude_input.setFixedWidth(150)
        filt.addWidget(self.exclude_input)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color: #313244;")
        sep2.setFixedHeight(24)
        filt.addWidget(sep2)

        self.cat_filter = QComboBox()
        self.cat_filter.addItem("All Categories")
        cats = sorted({r["category"] for r in self.data})
        for c in cats:
            self.cat_filter.addItem(cat_icon(c), c)
        filt.addWidget(self.cat_filter, 1)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setStyleSheet("color: #313244;")
        sep3.setFixedHeight(24)
        filt.addWidget(sep3)

        self.btn_export = QPushButton("  Export")
        self.btn_export.setIcon(qta.icon("ph.export", color="#a6adc8"))
        self.btn_check_status = QPushButton("  Status")
        self.btn_check_status.setIcon(qta.icon("ph.wifi-high", color="#a6adc8"))
        filt.addWidget(self.btn_export)
        filt.addWidget(self.btn_check_status)
        root.addWidget(filter_frame)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, len(self.data) or 1)
        self.progress.setValue(len(self.data))
        root.addWidget(self.progress)

        # Tabs
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        # Tab 0 — Landing
        self.landing_tab_index = self.tabs.addTab(
            self.landing_widget, qta.icon("ph.rocket", color="#89b4fa"), "New Scrape"
        )

        # Tab 1 — Table
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["#", "Category", "URL / Value", "Path Depth", "Status"])
        hdr_view = self.table.horizontalHeader()
        hdr_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr_view.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr_view.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 55)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 70)
        self.table.doubleClicked.connect(self._open_url)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.tabs.addTab(self.table, qta.icon("ph.table", color="#89b4fa"), "Table View")

        # Tab 2 — Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Category / URL", "Count"])
        self.tree.setColumnCount(2)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.tree.setColumnWidth(0, 500)
        self.tree.setColumnWidth(1, 140)
        self.tabs.addTab(self.tree, qta.icon("ph.tree-structure", color="#89b4fa"), "Tree View")

        # Tab 3 — Stats
        self.stats_widget = QWidget()
        self.stats_layout = QVBoxLayout(self.stats_widget)
        self.stats_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.tabs.addTab(self.stats_widget, qta.icon("ph.chart-bar", color="#89b4fa"), "Statistics")

        # Tab 4 — Console
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Scrape logs will appear here...")
        self.tabs.addTab(self.log_area, qta.icon("ph.terminal", color="#89b4fa"), "Console")

        if self.data:
            self.tabs.setCurrentWidget(self.table)

    def _connect_signals(self):
        self.search.textChanged.connect(self._on_filter)
        self.cat_filter.currentIndexChanged.connect(self._on_filter)
        self.exclude_input.returnPressed.connect(self._on_filter)
        self.btn_export.clicked.connect(self._export)
        self.btn_check_status.clicked.connect(self._check_status)
        self.btn_scrape.clicked.connect(self._start_scrape)
        self.url_input.returnPressed.connect(self._start_scrape)

    def _show_landing(self):
        self.tabs.setCurrentIndex(self.landing_tab_index)
        self.url_input.setFocus()
        self.url_input.clear()

    # ── Scrape ──────────────────────────────────────────────────────────

    def _start_scrape(self):
        url = self.url_input.text().strip()
        if not url:
            return

        mode = "2" if self.mode_combo.currentIndex() == 0 else "1"

        self.btn_scrape.setEnabled(False)
        self.btn_scrape.setText("  Scraping...")
        self.btn_scrape.setIcon(qta.icon("ph.spinner", color="#a6adc8"))
        self.log_area.clear()

        console_index = self.tabs.indexOf(self.log_area)
        self.tabs.setCurrentIndex(console_index)

        self.worker = ScrapeWorker(url, mode)
        self.worker.log.connect(self._on_scrape_log)
        self.worker.finished.connect(self._on_scrape_done)
        self.worker.error.connect(self._on_scrape_error)
        self.worker.start()

    def _on_scrape_log(self, msg):
        self.log_area.append(msg)
        self.statusBar().showMessage(msg)

    def _on_scrape_done(self, rows):
        self.data = rows
        self.filtered = list(self.data)
        self._rebuild_category_filter()
        self._apply_stats()
        self._populate_table()
        self._populate_tree()
        self.progress.setRange(0, len(self.data))
        self.progress.setValue(len(self.data))
        self.btn_scrape.setEnabled(True)
        self.btn_scrape.setText("  Start Scrape")
        self.btn_scrape.setIcon(qta.icon("ph.play", color="#a6adc8"))
        self.tabs.setCurrentWidget(self.table)
        self.statusBar().showMessage(f"Scrape complete — {len(self.data)} endpoints")

    def _on_scrape_error(self, msg):
        self.log_area.append(f"ERROR: {msg}")
        self.btn_scrape.setEnabled(True)
        self.btn_scrape.setText("  Start Scrape")
        self.btn_scrape.setIcon(qta.icon("ph.play", color="#a6adc8"))
        self.statusBar().showMessage(f"Scrape failed: {msg}")
        self._show_landing()

    # ── Data ────────────────────────────────────────────────────────────

    def _rebuild_category_filter(self):
        self.cat_filter.clear()
        self.cat_filter.addItem(qta.icon("ph.squares-four", color="#89b4fa"), "All Categories")
        cats = sorted({r["category"] for r in self.data})
        for c in cats:
            self.cat_filter.addItem(cat_icon(c), c)

    def _on_filter(self):
        term = self.search.text().lower().strip()
        idx = self.cat_filter.currentIndex()
        cat_sel = None if idx == 0 else self.cat_filter.currentText()
        exclude_text = self.exclude_input.text().strip()

        exclude_re = None
        if exclude_text:
            try:
                exclude_re = re.compile(exclude_text, re.IGNORECASE)
            except re.error:
                exclude_re = None

        self.filtered = []
        for r in self.data:
            if term and term not in r["value"].lower() and term not in r["category"].lower():
                continue
            if cat_sel is not None and r["category"] != cat_sel:
                continue
            if exclude_re and exclude_re.search(r["value"]):
                continue
            self.filtered.append(r)

        self._populate_table()
        self._populate_tree()
        self.progress.setValue(len(self.filtered))
        self.statusBar().showMessage(f"Showing {len(self.filtered)} / {len(self.data)} endpoints")

    def _apply_stats(self):
        self.lbl_total.setText(f"{len(self.data)} endpoints")

        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
            elif item.widget():
                item.widget().deleteLater()

        counter = Counter(r["category"] for r in self.data)
        for cat, cnt in counter.most_common():
            color = CATEGORY_COLORS.get(cat, "#cdd6f4")
            row = QHBoxLayout()
            icon_lbl = QLabel()
            icon_lbl.setPixmap(cat_icon(cat, color).pixmap(18, 18))
            icon_lbl.setFixedWidth(26)
            text_lbl = QLabel(f"{cat}:  {cnt}")
            text_lbl.setStyleSheet(f"color: {color}; font-size: 14px; padding: 4px 0;")
            row.addWidget(icon_lbl)
            row.addWidget(text_lbl)
            row.addStretch()
            self.stats_layout.addLayout(row)

        self.stats_layout.addSpacing(20)
        dom_row = QHBoxLayout()
        dom_icon = QLabel()
        dom_icon.setPixmap(qta.icon("ph.globe-hemisphere-west", color="#89b4fa").pixmap(18, 18))
        dom_icon.setFixedWidth(26)
        h = QLabel("Top Domains")
        h.setStyleSheet("color: #89b4fa; font-weight: bold; font-size: 15px;")
        dom_row.addWidget(dom_icon)
        dom_row.addWidget(h)
        dom_row.addStretch()
        self.stats_layout.addLayout(dom_row)

        domains = Counter()
        for r in self.data:
            v = r["value"]
            if v.startswith("http"):
                try:
                    domains[urlparse(v).netloc] += 1
                except Exception:
                    pass
        for dom, cnt in domains.most_common(10):
            lbl = QLabel(f"  {dom}:  {cnt}")
            lbl.setStyleSheet("color: #a6adc8; font-size: 13px; padding-left: 26px;")
            self.stats_layout.addWidget(lbl)

    # ── Table ───────────────────────────────────────────────────────────

    def _populate_table(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.filtered))

        value_counts = Counter(r["value"] for r in self.filtered)
        dup_values = {v for v, c in value_counts.items() if c > 1}

        for i, r in enumerate(self.filtered):
            cat = r["category"]
            val = r["value"]
            color = QColor(CATEGORY_COLORS.get(cat, "#cdd6f4"))
            is_dup = val in dup_values

            idx_item = QTableWidgetItem(str(i + 1))
            idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            idx_item.setFlags(idx_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 0, idx_item)

            cat_item = QTableWidgetItem(cat)
            cat_item.setIcon(cat_icon(cat))
            cat_item.setForeground(color)
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 1, cat_item)

            val_item = QTableWidgetItem(val)
            val_item.setFlags(val_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            val_item.setToolTip(val)
            if is_dup:
                val_item.setBackground(QColor("#313244"))
                val_item.setForeground(QColor("#f9e2af"))
            self.table.setItem(i, 2, val_item)

            depth = val.count("/") - (2 if val.startswith("http") else 0)
            depth_item = QTableWidgetItem(str(max(0, depth)))
            depth_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            depth_item.setFlags(depth_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 3, depth_item)

            status_item = QTableWidgetItem(r.get("status", ""))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            status_code = r.get("status", "")
            if status_code.startswith("2"):
                status_item.setForeground(QColor("#a6e3a1"))
            elif status_code.startswith("3"):
                status_item.setForeground(QColor("#f9e2af"))
            elif status_code.startswith("4"):
                status_item.setForeground(QColor("#f38ba8"))
            elif status_code.startswith("5"):
                status_item.setForeground(QColor("#ef5350"))
            elif status_code == "ERR":
                status_item.setForeground(QColor("#6c7086"))
            self.table.setItem(i, 4, status_item)

        self.table.setSortingEnabled(True)

    # ── Tree ────────────────────────────────────────────────────────────

    def _populate_tree(self):
        self.tree.clear()
        grouped = {}
        for r in self.filtered:
            grouped.setdefault(r["category"], []).append(r["value"])
        for cat in sorted(grouped):
            vals = grouped[cat]
            parent = QTreeWidgetItem(self.tree, [cat, ""])
            parent.setIcon(0, cat_icon(cat))
            parent.setForeground(0, QColor(CATEGORY_COLORS.get(cat, "#cdd6f4")))
            parent.setExpanded(False)
            count_lbl = QLabel(str(len(vals)))
            count_lbl.setStyleSheet("color: #a6adc8; font-size: 12px; padding-right: 8px;")
            copy_btn = QPushButton("Copy All")
            copy_btn.setIcon(qta.icon("ph.copy", color="#a6adc8"))
            copy_btn.setFixedSize(76, 22)
            copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            copy_btn.setStyleSheet(
                "QPushButton { background-color: #313244; border: 1px solid #45475a;"
                " border-radius: 4px; padding: 2px 6px; color: #cdd6f4; font-size: 11px; }"
                " QPushButton:hover { background-color: #45475a; border: 1px solid #89b4fa; }"
            )
            copy_btn.clicked.connect(lambda checked, c=cat, v=vals: self._copy_category(c, v))
            wrapper = QWidget()
            wrapper.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            wrapper_layout = QHBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(0, 0, 4, 0)
            wrapper_layout.setSpacing(6)
            wrapper_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            wrapper_layout.addWidget(count_lbl)
            wrapper_layout.addWidget(copy_btn)
            self.tree.setItemWidget(parent, 1, wrapper)
            for v in vals:
                child = QTreeWidgetItem(parent, [v, ""])
                child.setToolTip(0, v)
        self.tree.expandAll()

    def _copy_category(self, cat, vals):
        QApplication.clipboard().setText("\n".join(vals))
        self.statusBar().showMessage(f"Copied {len(vals)} {cat} URLs to clipboard")

    # ── Actions ─────────────────────────────────────────────────────────

    def _open_url(self, index):
        row = index.row()
        url_item = self.table.item(row, 2)
        if url_item:
            url = url_item.text()
            if url.startswith("http"):
                QDesktopServices.openUrl(QUrl(url))

    def _show_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        self.table.selectRow(row)
        url = self.table.item(row, 2).text()

        menu = QMenu(self)
        act_copy = menu.addAction(qta.icon("ph.copy", color="#cdd6f4"), "Copy URL")
        act_copy_curl = menu.addAction(qta.icon("ph.terminal", color="#cdd6f4"), "Copy as cURL")
        menu.addSeparator()
        act_open = menu.addAction(qta.icon("ph.arrow-square-out", color="#89b4fa"), "Open in Browser")
        act_open.setEnabled(url.startswith("http"))
        act_status = menu.addAction(qta.icon("ph.wifi-high", color="#a6adc8"), "Check Status")
        act_status.setEnabled(url.startswith("http"))
        menu.addSeparator()
        act_delete = menu.addAction(qta.icon("ph.trash", color="#ef5350"), "Delete")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == act_copy:
            QApplication.clipboard().setText(url)
            self.statusBar().showMessage(f"Copied: {url}")
        elif action == act_copy_curl:
            curl = f'curl -X GET "{url}" -H "User-Agent: Mozilla/5.0"'
            QApplication.clipboard().setText(curl)
            self.statusBar().showMessage(f"Copied as cURL: {url}")
        elif action == act_open:
            QDesktopServices.openUrl(QUrl(url))
        elif action == act_status:
            self._check_status_single(row)
        elif action == act_delete:
            self._delete_rows([row])

    def _delete_rows(self, rows):
        rows = sorted(rows, reverse=True)
        for row in rows:
            url = self.table.item(row, 2).text()
            self.data = [r for r in self.data if r["value"] != url]
        self._on_filter()
        self._apply_stats()
        self.statusBar().showMessage(f"Deleted {len(rows)} endpoint(s)")

    def _check_status(self):
        urls = [r["value"] for r in self.filtered if r["value"].startswith("http")]
        if not urls:
            return
        self.btn_check_status.setEnabled(False)
        self.btn_check_status.setText("  Checking...")
        self.status_worker = StatusWorker(urls)
        self.status_worker.progress.connect(self._on_status_progress)
        self.status_worker.finished.connect(self._on_status_finished)
        self.status_worker.start()

    def _check_status_single(self, row):
        url = self.filtered[row]["value"]
        if not url.startswith("http"):
            return
        self.statusBar().showMessage(f"Checking status for {url}...")
        try:
            r = requests.head(url, timeout=8, allow_redirects=True)
            code = str(r.status_code)
        except Exception:
            code = "ERR"
        self._on_status_progress(row, code)
        self.statusBar().showMessage(f"Status: {code} — {url}")

    def _on_status_progress(self, row_idx, code):
        url = self.filtered[row_idx]["value"]
        for r in self.data:
            if r["value"] == url:
                r["status"] = code
                break
        self.filtered[row_idx]["status"] = code

        status_item = QTableWidgetItem(code)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if code.startswith("2"):
            status_item.setForeground(QColor("#a6e3a1"))
        elif code.startswith("3"):
            status_item.setForeground(QColor("#f9e2af"))
        elif code.startswith("4"):
            status_item.setForeground(QColor("#f38ba8"))
        elif code.startswith("5"):
            status_item.setForeground(QColor("#ef5350"))
        elif code == "ERR":
            status_item.setForeground(QColor("#6c7086"))
        self.table.setItem(row_idx, 4, status_item)

    def _on_status_finished(self):
        self.btn_check_status.setEnabled(True)
        self.btn_check_status.setText("  Status")
        self.statusBar().showMessage("Status check complete")

    def _export(self):
        out = os.path.join(os.path.dirname(CSV_PATH), "filtered_endpoints.csv")
        with open(out, "w", newline="", encoding="utf-8") as f:
            import csv
            w = csv.writer(f)
            w.writerow(["Category", "URL / Value"])
            for r in self.filtered:
                w.writerow([r["category"], r["value"]])
        self.statusBar().showMessage(f"Exported {len(self.filtered)} rows → {out}")
