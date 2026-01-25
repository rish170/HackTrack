from __future__ import annotations

import pandas as pd

from utils.constants import EXCEL_COLUMNS
from core.github_analyzer import RepoAnalysis


def to_dataframe(results: list[RepoAnalysis]) -> pd.DataFrame:
    rows = []
    for r in results:
        rows.append(
            {
                "Team Name": r.team_name,
                "GitHub Repo URL": r.repo_url,
                "Track": r.track,
                "Members": r.members,
                "Public/Private": "Private" if r.is_private else "Public",
                "Default Branch": r.default_branch,
                "Total Commits": r.total_commits,
                "Last Commit": r.last_commit,
                "Recent Messages": r.recent_messages,
                "README Present": "Yes" if r.readme_present else "No",
                "Top Languages": r.top_languages,
            }
        )
    df = pd.DataFrame(rows, columns=EXCEL_COLUMNS)
    return df
