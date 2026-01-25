from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from utils.constants import APP_NAME, LOGO_PATH, STATUS_PHASES


class Dashboard(QWidget):
    start_requested = pyqtSignal(str, str, float)
    theme_toggled = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._progress_bars: dict[str, QProgressBar] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        top_bar = self._build_top_bar()
        main_layout.addLayout(top_bar)

        inputs = self._build_inputs()
        main_layout.addWidget(inputs)

        progress = self._build_progress()
        main_layout.addWidget(progress)

        countdown = self._build_countdown()
        main_layout.addWidget(countdown)

        main_layout.addStretch(1)

    def _build_top_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        logo_label = QLabel()
        logo_label.setFixedSize(38, 38)
        logo_label.setStyleSheet("border-radius: 10px; background: #1f2937;")
        if Path(LOGO_PATH).exists():
            pixmap = QPixmap(str(LOGO_PATH)).scaled(38, 38)
            logo_label.setPixmap(pixmap)

        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 22px; font-weight: 700;")

        spacer = QSpacerItem(20, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.theme_button = QPushButton("Toggle Theme")
        self.theme_button.setCheckable(True)
        self.theme_button.clicked.connect(self.theme_toggled.emit)

        layout.addWidget(logo_label)
        layout.addSpacing(10)
        layout.addWidget(title)
        layout.addItem(spacer)
        layout.addWidget(self.theme_button)
        return layout

    def _build_inputs(self) -> QGroupBox:
        box = QGroupBox("Submission Sources")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.excel_edit = QLineEdit()
        self.excel_edit.setPlaceholderText("Select Excel file (.xlsx)")
        excel_btn = QPushButton("Browse Excel")
        excel_btn.clicked.connect(self._choose_excel)

        self.sheet_edit = QLineEdit()
        self.sheet_edit.setPlaceholderText("Google Sheet URL (optional)")

        self.interval_input = QDoubleSpinBox()
        self.interval_input.setRange(0.1, 72.0)
        self.interval_input.setSingleStep(0.5)
        self.interval_input.setValue(1.0)
        self.interval_input.setSuffix(" h")

        self.start_btn = QPushButton("Start Monitoring")
        self.start_btn.clicked.connect(self._emit_start)

        grid.addWidget(QLabel("Excel File"), 0, 0)
        grid.addWidget(self.excel_edit, 0, 1)
        grid.addWidget(excel_btn, 0, 2)

        grid.addWidget(QLabel("Google Sheet URL"), 1, 0)
        grid.addWidget(self.sheet_edit, 1, 1)
        grid.addWidget(QLabel(""), 1, 2)

        grid.addWidget(QLabel("Interval (hours)"), 2, 0)
        grid.addWidget(self.interval_input, 2, 1)
        grid.addWidget(QLabel(""), 2, 2)

        grid.addWidget(self.start_btn, 3, 0, 1, 3)

        box.setLayout(grid)
        return box

    def _build_progress(self) -> QGroupBox:
        box = QGroupBox("Progress")
        layout = QGridLayout()
        for row, key in enumerate(["fetch", "process", "excel", "sheets"]):
            label = QLabel(STATUS_PHASES.get(key, key.title()))
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            self._progress_bars[key] = bar
            layout.addWidget(label, row, 0)
            layout.addWidget(bar, row, 1)
        self.status_label = QLabel("Idle")
        self.status_label.setObjectName("status-label")
        layout.addWidget(self.status_label, len(self._progress_bars), 0, 1, 2)
        box.setLayout(layout)
        return box

    def _build_countdown(self) -> QGroupBox:
        box = QGroupBox("Countdown")
        layout = QVBoxLayout()
        self.countdown_label = QLabel("Not scheduled")
        self.countdown_label.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addWidget(self.countdown_label)
        box.setLayout(layout)
        return box

    def _choose_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Excel file", str(Path.home()), "Excel Files (*.xlsx *.xlsm)")
        if path:
            self.excel_edit.setText(path)

    def _emit_start(self) -> None:
        excel_path = self.excel_edit.text().strip()
        sheet_url = self.sheet_edit.text().strip()
        interval = float(self.interval_input.value())
        self.start_requested.emit(excel_path, sheet_url, interval)

    def update_progress(self, phase: str, percent: int, message: str) -> None:
        if phase in self._progress_bars:
            self._progress_bars[phase].setValue(max(0, min(100, percent)))
        self.status_label.setText(message)

    def reset_progress(self) -> None:
        for bar in self._progress_bars.values():
            bar.setValue(0)
        self.status_label.setText("Idle")

    def set_countdown(self, seconds: int) -> None:
        if seconds <= 0:
            self.countdown_label.setText("Fetching report now")
        else:
            hrs = seconds // 3600
            mins = (seconds % 3600) // 60
            secs = seconds % 60
            self.countdown_label.setText(f"Next fetch in {hrs:02d}:{mins:02d}:{secs:02d}")

    def set_busy(self, busy: bool) -> None:
        self.start_btn.setDisabled(busy)

    def set_theme_state(self, dark: bool) -> None:
        self.theme_button.setChecked(not dark)
        self.theme_button.setText("Switch to Dark" if not dark else "Switch to Light")
