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
    # Ensure all required source columns exist
    required_cols = ["Team Name", "GitHub Repo URL", "Track", "Members"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""
    return df[required_cols]


def is_valid_excel(path: str) -> bool:
    return Path(path).suffix.lower() in {".xlsx", ".xlsm"}
