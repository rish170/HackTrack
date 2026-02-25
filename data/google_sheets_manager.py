import os
import re
from typing import Iterable, Optional

import gspread
import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials

from utils.constants import COMMIT_HISTORY_HEADERS, EXCEL_COLUMNS

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def _get_credentials(service_account_path: Optional[str] = None) -> Credentials:
    json_path = service_account_path or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not json_path:
        raise ValueError("Service account JSON path not provided. Set GOOGLE_SERVICE_ACCOUNT_JSON or pass path explicitly.")
    credentials = Credentials.from_service_account_file(json_path, scopes=SCOPES)
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    return credentials


def read_sheet(sheet_url: str, worksheet: Optional[str] = None, service_account_path: Optional[str] = None) -> pd.DataFrame:
    creds = _get_credentials(service_account_path)
    client = gspread.authorize(creds)
    sh = client.open_by_url(sheet_url)
    ws = sh.worksheet(worksheet) if worksheet else sh.sheet1
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    for col in EXCEL_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[EXCEL_COLUMNS]


def write_sheet(sheet_url: str, df: pd.DataFrame, worksheet: Optional[str] = None, service_account_path: Optional[str] = None) -> None:
    creds = _get_credentials(service_account_path)
    client = gspread.authorize(creds)
    sh = client.open_by_url(sheet_url)
    ws = sh.worksheet(worksheet) if worksheet else sh.sheet1
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.values.tolist())


def update_rows(sheet_url: str, new_df: pd.DataFrame, worksheet: Optional[str] = None, service_account_path: Optional[str] = None) -> None:
    current = read_sheet(sheet_url, worksheet=worksheet, service_account_path=service_account_path)
    if current.empty:
        merged = new_df
    else:
        merged = pd.concat([current, new_df], ignore_index=True)
        merged.drop_duplicates(subset=["Team Name", "GitHub Repo URL"], keep="last", inplace=True)
    write_sheet(sheet_url, merged[EXCEL_COLUMNS], worksheet=worksheet, service_account_path=service_account_path)


def sanitize_worksheet_title(value: str) -> str:
    title = (value or "").strip()
    title = re.sub(r"[\\/\?\*\[\]:]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    if not title:
        title = "Team"
    if len(title) > 100:
        title = title[:100].rstrip()
    return title


def _open_spreadsheet(sheet_url: str, service_account_path: Optional[str] = None):
    creds = _get_credentials(service_account_path)
    client = gspread.authorize(creds)
    return client.open_by_url(sheet_url)


def get_or_create_team_worksheet(
    sheet_url: str,
    team_title: str,
    service_account_path: Optional[str] = None,
):
    sh = _open_spreadsheet(sheet_url, service_account_path=service_account_path)
    base = sanitize_worksheet_title(team_title)
    try:
        ws = sh.worksheet(base)
    except Exception:
        title = base
        existing_titles = {w.title for w in sh.worksheets()}
        if title in existing_titles:
            idx = 2
            while True:
                candidate = f"{base} {idx}"
                if candidate not in existing_titles:
                    title = candidate
                    break
                idx += 1
        ws = sh.add_worksheet(title=title, rows=1000, cols=len(COMMIT_HISTORY_HEADERS))

    values = ws.row_values(1)
    if not values:
        ws.update([COMMIT_HISTORY_HEADERS])
    elif values != COMMIT_HISTORY_HEADERS:
        ws.update("A1", [COMMIT_HISTORY_HEADERS])
    return ws


def get_existing_commit_shas(ws) -> set[str]:
    values = ws.col_values(1)
    if not values:
        return set()
    shas = {v.strip() for v in values[1:] if v and str(v).strip()}
    return shas


def append_commit_history_rows(ws, rows: list[list[str]]) -> None:
    # Always append a blank row first to separate from the last session
    blank_row = [""] * len(COMMIT_HISTORY_HEADERS)
    
    if not rows:
        # If no new commits, add blank row then a row with dashes
        separator_row = ["-"] * len(COMMIT_HISTORY_HEADERS)
        ws.append_rows([blank_row, separator_row], value_input_option="RAW")
    else:
        # If new commits found, add blank row then the commit data
        ws.append_rows([blank_row] + rows, value_input_option="RAW")
