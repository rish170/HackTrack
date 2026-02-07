from pathlib import Path
from typing import Optional

import pandas as pd
from openpyxl import Workbook, load_workbook

from utils.constants import EXCEL_COLUMNS
from utils.constants import COMMIT_HISTORY_HEADERS


def read_excel(path: str) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame(columns=EXCEL_COLUMNS)
    df = pd.read_excel(file_path)
    for col in EXCEL_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[EXCEL_COLUMNS]


def write_excel(path: str, df: pd.DataFrame) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(file_path, index=False)


def update_rows(path: str, new_df: pd.DataFrame) -> None:
    current = read_excel(path)
    if current.empty:
        merged = new_df
    else:
        merged = pd.concat([current, new_df], ignore_index=True)
        merged.drop_duplicates(subset=["Team Name", "GitHub Repo URL"], keep="last", inplace=True)
    write_excel(path, merged[EXCEL_COLUMNS])


def is_valid_excel(path: str) -> bool:
    return Path(path).suffix.lower() in {".xlsx", ".xlsm"}


def append_team_commit_history(path: str, team_sheet: str, rows: list[list[str]]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if file_path.exists():
        wb = load_workbook(file_path)
    else:
        wb = Workbook()
        wb.remove(wb.active)

    title = team_sheet.strip()[:31] if team_sheet else "Team"
    if title in wb.sheetnames:
        ws = wb[title]
    else:
        ws = wb.create_sheet(title=title)

    if ws.max_row == 1 and ws.max_column == 1 and ws.cell(row=1, column=1).value is None:
        ws.append(COMMIT_HISTORY_HEADERS)
    elif ws.max_row == 0:
        ws.append(COMMIT_HISTORY_HEADERS)
    else:
        header_row = [ws.cell(row=1, column=i + 1).value for i in range(len(COMMIT_HISTORY_HEADERS))]
        if not header_row or header_row[0] != COMMIT_HISTORY_HEADERS[0]:
            ws.insert_rows(1)
            for i, h in enumerate(COMMIT_HISTORY_HEADERS, start=1):
                ws.cell(row=1, column=i).value = h

    existing = set()
    for r in range(2, ws.max_row + 1):
        val = ws.cell(row=r, column=1).value
        if val:
            existing.add(str(val).strip())

    to_append = [row for row in rows if row and str(row[0]).strip() and str(row[0]).strip() not in existing]
    for row in to_append:
        ws.append(row)

    wb.save(file_path)
