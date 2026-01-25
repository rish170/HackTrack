from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

STATE_FILE = Path(__file__).resolve().parent.parent / "last_state.json"


def load_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(data: Dict[str, Any]) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        # Silently ignore persistence errors to avoid breaking UI
        pass
