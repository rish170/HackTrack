from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from utils.helpers import safe_interval_hours


class Scheduler(QObject):
    tick = pyqtSignal(int)  # seconds remaining
    triggered = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._interval_seconds = 0
        self._countdown = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

    def start(self, hours: float) -> None:
        self._interval_seconds = int(safe_interval_hours(hours) * 3600)
        self._countdown = 0
        self._emit_tick()
        self._timer.start()
        self.triggered.emit()  # immediate run

    def stop(self) -> None:
        self._timer.stop()
        self._countdown = 0
        self._emit_tick()

    def _on_tick(self) -> None:
        if self._countdown <= 0:
            self._countdown = self._interval_seconds
            self.triggered.emit()
        else:
            self._countdown -= 1
        self._emit_tick()

    def _emit_tick(self) -> None:
        self.tick.emit(max(self._countdown, 0))
