"""HackTrack desktop entrypoint.

Run locally:
    1) Activate your virtual environment.
    2) pip install -r requirements.txt
    3) python main.py

Google Sheets setup:
    - Create a Google Cloud service account with Sheets + Drive scopes.
    - Download its JSON key file and set env var GOOGLE_SERVICE_ACCOUNT_JSON to that path.
    - Share the target Google Sheet with the service account email.

GitHub API:
    - (Recommended) set GITHUB_TOKEN env var for higher rate limits.

Logo:
    - Place a 64x64+ PNG at assets/logo.png (placeholder exists).
"""

import sys
from pathlib import Path

from dotenv import load_dotenv
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow
from utils.constants import APP_NAME, LOGO_PATH


def main() -> None:
    load_dotenv()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    window = MainWindow()
    if Path(LOGO_PATH).exists():
        window.setWindowIcon(QIcon(str(LOGO_PATH)))
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
