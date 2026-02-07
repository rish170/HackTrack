from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from utils.constants import APP_NAME, LOGO_PATH, STATUS_PHASES


class Dashboard(QWidget):
    start_requested = pyqtSignal(str, str, int)
    stop_requested = pyqtSignal()
    theme_toggled = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._progress_bars: dict[str, QProgressBar] = {}
        self._busy = False
        self._monitoring = False
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

        self.hour_box = QSpinBox()
        self.hour_box.setRange(0, 72)
        self.hour_box.setValue(1)
        self.minute_box = QSpinBox()
        self.minute_box.setRange(0, 59)
        self.second_box = QSpinBox()
        self.second_box.setRange(0, 59)

        time_layout = QHBoxLayout()
        time_layout.setSpacing(6)
        time_layout.addWidget(self.hour_box)
        time_layout.addWidget(QLabel(":"))
        time_layout.addWidget(self.minute_box)
        time_layout.addWidget(QLabel(":"))
        time_layout.addWidget(self.second_box)

        self.start_btn = QPushButton("Start Monitoring")
        self.start_btn.clicked.connect(self._emit_start)

        self.stop_btn = QPushButton("Stop Monitoring")
        self.stop_btn.setDisabled(True)
        self.stop_btn.clicked.connect(self.stop_requested.emit)

        grid.addWidget(QLabel("Excel File"), 0, 0)
        grid.addWidget(self.excel_edit, 0, 1)
        grid.addWidget(excel_btn, 0, 2)

        grid.addWidget(QLabel("Google Sheet URL"), 1, 0)
        grid.addWidget(self.sheet_edit, 1, 1)
        grid.addWidget(QLabel(""), 1, 2)

        grid.addWidget(QLabel("Interval (hh:mm:ss)"), 2, 0)
        grid.addLayout(time_layout, 2, 1)
        grid.addWidget(QLabel(""), 2, 2)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        grid.addLayout(btn_row, 3, 0, 1, 3)

        box.setLayout(grid)
        return box

    def _build_progress(self) -> QGroupBox:
        box = QGroupBox("Progress")
        layout = QGridLayout()
        for i, phase in enumerate(STATUS_PHASES):
            label = QLabel(STATUS_PHASES[phase])
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setFormat("%p%")
            bar.setTextVisible(True)
            # Force green chunk color
            bar.setStyleSheet("""
                QProgressBar::chunk {
                    background: #22c55e;
                    border-radius: 9px;
                    margin: 1px;
                }
            """)
            self._progress_bars[phase] = bar
            layout.addWidget(label, i, 0)
            layout.addWidget(bar, i, 1)
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
        interval_seconds = self.interval_seconds()
        self.start_requested.emit(excel_path, sheet_url, interval_seconds)

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
        self._busy = busy
        self._sync_buttons()

    def set_monitoring(self, monitoring: bool) -> None:
        self._monitoring = monitoring
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        self.start_btn.setDisabled(self._busy or self._monitoring)
        self.stop_btn.setDisabled(not self._monitoring)

    def set_theme_state(self, dark: bool) -> None:
        self.theme_button.setChecked(not dark)
        self.theme_button.setText("Switch to Dark" if not dark else "Switch to Light")

    def interval_seconds(self) -> int:
        hours = int(self.hour_box.value())
        minutes = int(self.minute_box.value())
        seconds = int(self.second_box.value())
        total = hours * 3600 + minutes * 60 + seconds
        return max(total, 1)

    def set_interval_seconds(self, total_seconds: int) -> None:
        if total_seconds <= 0:
            return
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        self.hour_box.setValue(min(hours, self.hour_box.maximum()))
        self.minute_box.setValue(minutes)
        self.second_box.setValue(seconds)

    def set_sources(self, excel_path: str, sheet_url: str) -> None:
        self.excel_edit.setText(excel_path)
        self.sheet_edit.setText(sheet_url)
