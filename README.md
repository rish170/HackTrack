# HackTrack

A production-focused PyQt6 desktop app to monitor GitHub submissions for 24-hour hackathons. It ingests Excel or Google Sheets, analyzes repos via the GitHub API, and updates reports back to Excel and Google Sheets on a schedule without blocking the UI.

## Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Setup](#setup)
- [Configuration](#configuration)
- [Running the App](#running-the-app)
- [Input/Output Sheet Formats](#inputoutput-sheet-formats)
- [Google Sheets Setup](#google-sheets-setup)
- [GitHub API Notes](#github-api-notes)
- [Scheduling Behavior](#scheduling-behavior)
- [UI/UX](#uiux)
- [Folder Structure](#folder-structure)
- [Troubleshooting](#troubleshooting)

## Features
- Read submissions from Excel (.xlsx/.xlsm) and/or Google Sheets.
- Analyze each GitHub repository: visibility, default branch, commits, last commit time, recent messages, README presence, language breakdown.
- Generate structured reports and write back to Excel and Google Sheets with de-duplication.
- Interval-based monitoring with immediate first run; QTimer-driven countdown updates every second.
- Dark/Light themes with modern rounded UI and responsive layout.
- Non-blocking UI via worker threads; live per-phase progress bars.

## Architecture
- **UI (PyQt6)**: `ui/main_window.py`, `ui/dashboard.py`, `ui/styles.py`
- **Core logic**: GitHub analysis (`core/github_analyzer.py`), report shaping (`core/report_generator.py`), scheduler (`core/scheduler.py`)
- **Data layer**: Excel I/O (`data/excel_manager.py`), Google Sheets I/O (`data/google_sheets_manager.py`)
- **Utilities**: constants and helpers (`utils/constants.py`, `utils/helpers.py`)

## Requirements
- Python 3.11+
- See `requirements.txt`:
  - PyQt6
  - pandas, openpyxl
  - requests
  - gspread, google-auth
  - python-dotenv (if you want to load env vars from `.env`)

Install dependencies:
```bash
pip install -r requirements.txt
```

## Setup
1) (Optional) Create and activate a virtual environment.
2) Install dependencies: `pip install -r requirements.txt`.
3) Place a logo at `assets/logo.png` (any PNG; 64x64+). A placeholder exists.
4) Configure environment variables (see below). You may place them in a `.env` file if using python-dotenv.

## Configuration
Environment variables:
- `GOOGLE_SERVICE_ACCOUNT_JSON` — full path to your Google service account JSON key (required for Sheets).
- `GITHUB_TOKEN` — optional; improves GitHub rate limits and access to private repos the token can see.

## Running the App
```bash
python main.py
```
- Select an Excel file and/or paste a Google Sheet URL.
- Set the interval (hours). First run is immediate; subsequent runs follow the interval.
- Click **Start Monitoring**. Progress bars and status text will update per phase; the countdown shows time to next run.

## Input/Output Sheet Formats
**Input (Excel or Google Sheet)** — headers must match exactly:
- Team Name
- GitHub Repo URL
- Track
- Members

**Output columns (written back / updated):**
- Team Name
- GitHub Repo URL
- Track
- Members
- Public/Private ("Public" / "Private")
- Default Branch
- Total Commits
- Last Commit (UTC, `YYYY-MM-DD HH:MM`)
- Recent Messages (latest commit messages joined with ` | `)
- README Present ("Yes" / "No")
- Top Languages (e.g., `Python (60%), JavaScript (40%)`)

De-duplication: rows are keyed on `[Team Name, GitHub Repo URL]`, keeping the latest data.

## Google Sheets Setup
1) In Google Cloud, create a service account with Sheets + Drive file access scopes.
2) Generate and download its JSON key.
3) Set `GOOGLE_SERVICE_ACCOUNT_JSON` to the absolute path of that JSON file.
4) Share the target Google Sheet with the service account email.

## GitHub API Notes
- Uses GitHub REST API (v3 endpoints) via `requests`.
- Tokenless calls are rate-limited; set `GITHUB_TOKEN` for higher limits and to access private repos you permit.
- Data pulled per repo: metadata, default branch, up to 30 recent commits on the default branch, languages, README presence.

## Scheduling Behavior
- Uses `QTimer` to tick every second.
- First analysis run happens immediately when you click **Start Monitoring**.
- Countdown resets after each run; subsequent runs follow the configured interval.
- UI stays responsive; network and processing run in a worker thread.

## UI/UX
- Fully resizable window; minimize/maximize supported.
- Dark/Light theme toggle with modern rounded controls and hover/pressed states.
- Sections: top bar (logo/title/theme toggle), inputs (Excel/Sheet/interval), progress (per-phase bars), countdown display.

## Folder Structure
```
HackTrack/
├── main.py
├── requirements.txt
├── README.md
├── ui/
│   ├── main_window.py
│   ├── dashboard.py
│   └── styles.py
├── core/
│   ├── github_analyzer.py
│   ├── scheduler.py
│   └── report_generator.py
├── data/
│   ├── excel_manager.py
│   └── google_sheets_manager.py
├── utils/
│   ├── constants.py
│   ├── helpers.py
│   └── state_store.py
├── assets/
│   └── logo.png
└── testers/
    └── sheet_tester.py (optional, user-added)
```


## Troubleshooting
- **Google Sheets auth errors**: Ensure `GOOGLE_SERVICE_ACCOUNT_JSON` points to a valid key and the Sheet is shared with the service account email.
- **Rate limit or 403 from GitHub**: Set `GITHUB_TOKEN`; ensure the token has repo scope for private repos.
- **No data written**: Confirm input headers exactly match the expected names. Ensure at least one source (Excel or Sheet) is provided.
- **UI appears frozen**: Network calls run in a worker thread; if truly stuck, check connectivity and tokens, then restart the app.
- **Languages/commits empty**: Repo may be empty or private without proper access token.
