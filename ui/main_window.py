from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox

import pandas as pd

from pathlib import Path

from core.github_analyzer import GitHubAnalyzer
from core.github_analyzer import RepoSnapshot
from core.scheduler import Scheduler
from data.excel_manager import is_valid_excel, read_excel
from data.google_sheets_manager import append_commit_history_rows, get_existing_commit_shas, get_or_create_team_worksheet
from ui.dashboard import Dashboard
from ui.styles import DARK, LIGHT, apply_palette, stylesheet
from utils.constants import APP_NAME
from utils.state_store import load_state, save_state


class AnalyzeWorker(QThread):
    progress = pyqtSignal(str, int, str)
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)
    rate_limit = pyqtSignal(int, int)  # remaining, limit

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
        if not self.excel_path:
            raise ValueError("Excel input is required for team list.")

        analyzer = GitHubAnalyzer()
        # Initial rate limit emit
        rl_info = analyzer.get_rate_limit_info()
        if rl_info["remaining"] is not None:
            self.rate_limit.emit(rl_info["remaining"], rl_info["limit"])

        self.progress.emit("process", 10, "Reading Excel submissions")
        df = read_excel(self.excel_path)
        df.drop_duplicates(subset=["Team Name", "GitHub Repo URL"], keep="last", inplace=True)
        total = len(df)

        if self.sheet_url:
            self.progress.emit("sheets", 5, "Preparing Google Sheets output")

        for idx, row in df.iterrows():
            repo_url = str(row.get("GitHub Repo URL", "")).strip()
            if not repo_url:
                continue
            team_name = str(row.get("Team Name", "")).strip()
            pct = int(((idx + 1) / max(total, 1)) * 100)
            self.progress.emit("fetch", min(95, pct), f"Fetching commits for {repo_url}")

            known_shas: set[str] = set()
            worksheet_title = team_name

            if self.sheet_url:
                ws = get_or_create_team_worksheet(self.sheet_url, team_title=worksheet_title)
                known_shas = get_existing_commit_shas(ws)

            snapshot = analyzer.analyze_commit_history(
                team_key=worksheet_title,
                repo_url=repo_url,
                known_shas=known_shas,
                progress_cb=self.progress.emit,
            )

            # Emit rate limit after fetch
            rl_info = analyzer.get_rate_limit_info()
            if rl_info["remaining"] is not None:
                self.rate_limit.emit(rl_info["remaining"], rl_info["limit"])

            rows = self._snapshot_to_rows(snapshot)

            # Google Sheets append
            if self.sheet_url:
                ws = get_or_create_team_worksheet(self.sheet_url, team_title=worksheet_title)
                existing = get_existing_commit_shas(ws)
                new_rows = [r for r in rows if r and r[0] and r[0] not in existing]
                append_commit_history_rows(ws, new_rows)

                # Emit rate limit after sheet write (though append doesn't use GitHub API, it's good practice)
                rl_info = analyzer.get_rate_limit_info()
                if rl_info["remaining"] is not None:
                    self.rate_limit.emit(rl_info["remaining"], rl_info["limit"])

        if self.sheet_url:
            self.progress.emit("sheets", 100, "Google Sheets updated")

        self.progress.emit("process", 100, "Done")
        self.finished.emit("Monitoring snapshot complete")

    @staticmethod
    def _snapshot_to_rows(snapshot: RepoSnapshot) -> list[list[str]]:
        rows: list[list[str]] = []
        for i, c in enumerate(snapshot.commits, start=1):
            # Parse date and time from date_utc (format: 2024-02-25T12:34:56Z)
            try:
                dt = datetime.strptime(c.date_utc, "%Y-%m-%dT%H:%M:%SZ")
                commit_date = dt.strftime("%Y-%m-%d")
                commit_time = dt.strftime("%H:%M:%S")
            except Exception:
                commit_date = c.date_utc
                commit_time = ""

            rows.append(
                [
                    str(i),                    # Sno
                    commit_date,               # Commit Date
                    commit_time,               # Commit Time
                    c.message,                 # Commit Message
                    str(c.total_lines),        # Total Lines
                    str(c.total_files),        # Total Files
                    snapshot.languages,        # Languages
                    snapshot.snapshot_timestamp_utc, # Snapshot Timestamp
                ]
            )
        return rows


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
        self.dashboard.stop_requested.connect(self._handle_stop)
        self.dashboard.theme_toggled.connect(self._toggle_theme)

        self._current_worker: Optional[AnalyzeWorker] = None
        self._monitoring = False
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
        self._monitoring = True
        self.dashboard.set_monitoring(True)
        self.scheduler.start(interval_seconds)

    def _handle_stop(self) -> None:
        self.scheduler.stop()
        self._monitoring = False
        self.dashboard.set_monitoring(False)
        if not (self._current_worker and self._current_worker.isRunning()):
            self.dashboard.set_busy(False)
            self.dashboard.set_countdown(0)

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
        self._current_worker.rate_limit.connect(self.dashboard.set_rate_limit)
        self._current_worker.finished.connect(self._on_finished)
        self._current_worker.failed.connect(self._on_failed)
        self._current_worker.start()

    def _on_finished(self, message: str) -> None:
        self.dashboard.update_progress("fetch", 100, message)
        self.dashboard.set_busy(False)
        self.dashboard.update_progress("process", 100, message)
        if self._monitoring:
            self.dashboard.set_monitoring(True)
        self._current_worker = None

    def _on_failed(self, error: str) -> None:
        self.dashboard.update_progress("fetch", 0, "")
        self.dashboard.set_busy(False)
        message = error or "Unknown error"
        self.dashboard.update_progress("process", 0, f"Error: {message}")
        QMessageBox.critical(self, "Run failed", message)
        if self._monitoring:
            self.dashboard.set_monitoring(True)
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
