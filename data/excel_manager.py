from pathlib import Path
from typing import Optional

import pandas as pd

from utils.constants import EXCEL_COLUMNS


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
