from pathlib import Path

APP_NAME = "HackTrack"
DEFAULT_INTERVAL_HOURS = 1
GITHUB_API_BASE = "https://api.github.com"
GITHUB_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
LOGO_PATH = ASSETS_DIR / "logo.png"

EXCEL_COLUMNS = [
    "Team Name",
    "GitHub Repo URL",
    "Track",
    "Members",
    "Public/Private",
    "Default Branch",
    "Total Commits",
    "Last Commit",
    "Recent Messages",
    "README Present",
    "Top Languages",
]

COMMIT_HISTORY_HEADERS = [
    "Sno",
    "Commit Date",
    "Commit Time",
    "Commit Message",
    "Total Lines",
    "Total Files",
    "Languages",
    "Snapshot Timestamp",
]

STATUS_PHASES = {
    "fetch": "Fetching from GitHub",
    "process": "Processing data",
    "sheets": "Saving to Google Sheets",
}
