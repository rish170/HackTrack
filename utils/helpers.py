import os
import re
from datetime import datetime
from typing import Callable, Optional, Tuple
from urllib.parse import urlparse

from .constants import GITHUB_DATE_FORMAT


def get_github_token() -> Optional[str]:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    return token or None


def parse_repo_from_url(url: str) -> Optional[Tuple[str, str]]:
    raw = url.replace("\u00a0", " ").strip().strip("'\"").strip("<>[](){} ")
    if not raw:
        return None

    # strip query/fragment
    raw = raw.split("?")[0].split("#")[0]

    owner = repo = None

    # SSH form: git@github.com:owner/repo.git
    if raw.startswith("git@"):
        parts = raw.split(":", 1)
        if len(parts) == 2:
            path = parts[1]
            owner_repo = path.lstrip("/").split("/")
            if len(owner_repo) >= 2:
                owner = owner_repo[0]
                repo = owner_repo[1]
    else:
        parsed = urlparse(raw if re.match(r"^https?://", raw, flags=re.IGNORECASE) else f"https://{raw}")
        host = parsed.netloc.lower()
        if "github.com" in host:
            segments = [s for s in parsed.path.lstrip("/").split("/") if s]
            if len(segments) >= 2:
                owner, repo = segments[0], segments[1]

    # Fallback regex search anywhere in the string
    if not (owner and repo):
        # tolerate missing second slash and embedded text
        match = re.search(r"github\.com[/:]+([^/\s]+)/([^/\s]+)", raw, flags=re.IGNORECASE)
        if match:
            owner, repo = match.group(1), match.group(2)

    # Bare owner/repo without host
    if not (owner and repo):
        if "/" in raw and " " not in raw:
            parts = raw.lstrip("/").split("/")
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]

    if repo:
        repo = repo.removesuffix(".git").rstrip(".,;:)")

    if owner and repo:
        return owner, repo
    return None


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


def safe_interval_seconds(value: float | int) -> int:
    try:
        seconds = int(float(value))
        return max(seconds, 1)
    except Exception:
        return 1


def with_progress(progress: Callable[[str, int, str], None], phase: str, percent: int, message: str) -> None:
    if progress:
        progress(phase, percent, message)
