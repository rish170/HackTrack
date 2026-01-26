from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox

import pandas as pd

from core.github_analyzer import GitHubAnalyzer
from core.report_generator import to_dataframe
from core.scheduler import Scheduler
from data.excel_manager import is_valid_excel, read_excel, update_rows as update_excel
from data.google_sheets_manager import read_sheet, update_rows as update_sheet
from ui.dashboard import Dashboard
from ui.styles import DARK, LIGHT, apply_palette, stylesheet
from utils.constants import APP_NAME
from utils.state_store import load_state, save_state


class AnalyzeWorker(QThread):
    progress = pyqtSignal(str, int, str)
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(
        self,
        excel_path: str,
        sheet_url: str,
        parent: Optional[QMainWindow] = None,
    ) -> None:
        super().__init__(parent)
        self.excel_path = excel_path
        self.sheet_url = sheet_url

    def run(self) -> None:
        try:
            self._execute()
        except Exception as exc:  # pylint: disable=broad-except
            message = str(exc).strip() or repr(exc)
            self.failed.emit(message)

    def _execute(self) -> None:
        sources = []
        if self.excel_path:
            self.progress.emit("process", 10, "Reading Excel submissions")
            excel_df = read_excel(self.excel_path)
            sources.append(excel_df)
        if self.sheet_url:
            self.progress.emit("process", 15, "Reading Google Sheet submissions")
            sheet_df = read_sheet(self.sheet_url)
            sources.append(sheet_df)

        if not sources:
            raise ValueError("Provide an Excel file and/or a Google Sheet URL.")

        df = pd.concat(sources, ignore_index=True)
        df.drop_duplicates(subset=["Team Name", "GitHub Repo URL"], keep="last", inplace=True)

        analyzer = GitHubAnalyzer()
        results = []
        total = len(df)
        for idx, row in df.iterrows():
            repo_url = str(row.get("GitHub Repo URL", "")).strip()
            if not repo_url:
                continue
            team_name = str(row.get("Team Name", "")).strip()
            track = str(row.get("Track", "")).strip()
            members = str(row.get("Members", "")).strip()
            pct = int(((idx + 1) / max(total, 1)) * 100)
            self.progress.emit("fetch", min(95, pct), f"Analyzing {repo_url}")
            analysis = analyzer.analyze(team_name, repo_url, track, members, progress_cb=self.progress.emit)
            results.append(analysis)

        report_df = to_dataframe(results)
        self.progress.emit("process", 80, "Report generated")

        if self.excel_path:
            self.progress.emit("excel", 10, "Writing Excel")
            update_excel(self.excel_path, report_df)
            self.progress.emit("excel", 100, "Excel updated")

        if self.sheet_url:
            self.progress.emit("sheets", 10, "Updating Google Sheet")
            update_sheet(self.sheet_url, report_df)
            self.progress.emit("sheets", 100, "Google Sheet updated")

        self.progress.emit("process", 100, "Done")
        self.finished.emit(f"Completed {len(results)} repositories")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1000, 720)

        self.dashboard = Dashboard()
        self.setCentralWidget(self.dashboard)

        self.scheduler = Scheduler()
        self.scheduler.tick.connect(self.dashboard.set_countdown)
        self.scheduler.triggered.connect(self._run_cycle)

        self.dashboard.start_requested.connect(self._handle_start)
        self.dashboard.theme_toggled.connect(self._toggle_theme)

        self._current_worker: Optional[AnalyzeWorker] = None
        self._dark = True
        self._apply_theme()

        # restore last state if present
        state = load_state()
        excel_path = state.get("excel_path", "") if isinstance(state, dict) else ""
        sheet_url = state.get("sheet_url", "") if isinstance(state, dict) else ""
        interval_seconds = state.get("interval_seconds", 0) if isinstance(state, dict) else 0
        self.dashboard.set_sources(excel_path, sheet_url)
        if interval_seconds:
            self.dashboard.set_interval_seconds(interval_seconds)

    def _handle_start(self, excel_path: str, sheet_url: str, interval_seconds: int) -> None:
        if not excel_path and not sheet_url:
            QMessageBox.warning(self, "Input Required", "Please select an Excel file or provide a Google Sheet URL.")
            return
        if excel_path and not is_valid_excel(excel_path):
            QMessageBox.warning(self, "Invalid File", "Please choose a valid Excel (.xlsx or .xlsm) file.")
            return

        save_state({"excel_path": excel_path, "sheet_url": sheet_url, "interval_seconds": interval_seconds})
        self.dashboard.reset_progress()
        self.dashboard.set_busy(True)
        self.scheduler.start(interval_seconds)

    def _run_cycle(self) -> None:
        if self._current_worker and self._current_worker.isRunning():
            return

        excel_path = self.dashboard.excel_edit.text().strip()
        sheet_url = self.dashboard.sheet_edit.text().strip()
        interval_seconds = self.dashboard.interval_seconds()

        self.dashboard.reset_progress()
        self.dashboard.set_busy(True)
        self._current_worker = AnalyzeWorker(excel_path, sheet_url, parent=self)
        self._current_worker.progress.connect(self.dashboard.update_progress)
        self._current_worker.finished.connect(self._on_finished)
        self._current_worker.failed.connect(self._on_failed)
        self._current_worker.start()

    def _on_finished(self, message: str) -> None:
        self.dashboard.set_busy(False)
        self.dashboard.update_progress("process", 100, message)
        self._current_worker = None

    def _on_failed(self, error: str) -> None:
        self.dashboard.set_busy(False)
        message = error or "Unknown error"
        self.dashboard.update_progress("process", 0, f"Error: {message}")
        QMessageBox.critical(self, "Run failed", message)
        self._current_worker = None

    def _toggle_theme(self) -> None:
        self._dark = not self._dark
        self._apply_theme()

    def _apply_theme(self) -> None:
        theme = DARK if self._dark else LIGHT
        app = QApplication.instance()
        if app:
            apply_palette(app, theme)
            app.setStyleSheet(stylesheet(theme))
        self.dashboard.set_theme_state(self._dark)
