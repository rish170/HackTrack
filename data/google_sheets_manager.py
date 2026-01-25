import os
from typing import Optional

import gspread
import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials

from utils.constants import EXCEL_COLUMNS

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
