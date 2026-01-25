import os
import re
from datetime import datetime
from typing import Callable, Optional, Tuple

from .constants import GITHUB_DATE_FORMAT


def get_github_token() -> Optional[str]:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    return token or None


def parse_repo_from_url(url: str) -> Optional[Tuple[str, str]]:
    pattern = r"github.com[:/]+([^/]+)/([^/]+?)(?:\.git)?$"
    match = re.search(pattern, url.strip())
    if not match:
        return None
    return match.group(1), match.group(2)


def iso_to_datetime(value: str) -> Optional[datetime]:
    try:
        return datetime.strptime(value, GITHUB_DATE_FORMAT)
    except Exception:
        return None


def format_timestamp(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M")


def combine_messages(messages: list[str], limit: int = 5) -> str:
    trimmed = [m.strip() for m in messages if m and m.strip()]
    return " | ".join(trimmed[:limit])


def safe_interval_hours(value: float) -> float:
    try:
        hours = float(value)
        return max(hours, 0.1)
    except Exception:
        return 1.0


def with_progress(progress: Callable[[str, int, str], None], phase: str, percent: int, message: str) -> None:
    if progress:
        progress(phase, percent, message)
