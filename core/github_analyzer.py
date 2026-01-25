from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

from utils.constants import GITHUB_API_BASE
from utils.helpers import combine_messages, get_github_token, iso_to_datetime, parse_repo_from_url


@dataclass
class RepoAnalysis:
    team_name: str
    repo_url: str
    track: str
    members: str
    is_private: bool = False
    default_branch: str = ""
    total_commits: int = 0
    last_commit: str = ""
    recent_messages: str = ""
    readme_present: bool = False
    top_languages: str = ""


class GitHubAnalyzer:
    def __init__(self, token: Optional[str] = None) -> None:
        self.token = token or get_github_token()

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _get_json(self, url: str, timeout: int = 12) -> Optional[Dict]:
        resp = requests.get(url, headers=self._headers(), timeout=timeout)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def _repo_metadata(self, owner: str, repo: str) -> Dict:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        return self._get_json(url) or {}

    def _commits(self, owner: str, repo: str, branch: str) -> List[Dict]:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits?per_page=30&sha={branch}"
        data = self._get_json(url)
        return data or []

    def _languages(self, owner: str, repo: str) -> Dict[str, int]:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/languages"
        data = self._get_json(url)
        return data or {}

    def _has_readme(self, owner: str, repo: str) -> bool:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/readme"
        resp = requests.get(url, headers=self._headers(), timeout=10)
        return resp.status_code == 200

    def analyze(self, team_name: str, repo_url: str, track: str, members: str, progress_cb=None) -> RepoAnalysis:
        parsed = parse_repo_from_url(repo_url)
        if not parsed:
            raise ValueError(f"Invalid GitHub URL: {repo_url}")
        owner, repo = parsed

        meta = self._repo_metadata(owner, repo)
        default_branch = meta.get("default_branch", "main") if meta else "main"
        if progress_cb:
            progress_cb("fetch", 20, f"Repo metadata loaded for {repo}")

        commits = self._commits(owner, repo, default_branch)
        commit_messages = [c.get("commit", {}).get("message", "") for c in commits]
        last_commit_date = None
        if commits:
            last_commit_date = iso_to_datetime(commits[0].get("commit", {}).get("committer", {}).get("date", ""))
        if progress_cb:
            progress_cb("fetch", 60, f"Commit history pulled for {repo}")

        languages = self._languages(owner, repo)
        if progress_cb:
            progress_cb("fetch", 80, f"Languages analyzed for {repo}")

        readme_present = self._has_readme(owner, repo)
        if progress_cb:
            progress_cb("fetch", 100, f"README checked for {repo}")

        top_languages = self._format_languages(languages)
        recent_messages = combine_messages(commit_messages, limit=5)
        last_commit_str = last_commit_date.strftime("%Y-%m-%d %H:%M") if last_commit_date else ""

        return RepoAnalysis(
            team_name=team_name,
            repo_url=repo_url,
            track=track,
            members=members,
            is_private=bool(meta.get("private", False)),
            default_branch=default_branch,
            total_commits=len(commits),
            last_commit=last_commit_str,
            recent_messages=recent_messages,
            readme_present=readme_present,
            top_languages=top_languages,
        )

    @staticmethod
    def _format_languages(data: Dict[str, int]) -> str:
        if not data:
            return ""
        total = sum(data.values())
        parts = []
        for lang, size in sorted(data.items(), key=lambda i: i[1], reverse=True):
            pct = (size / total * 100) if total else 0
            parts.append(f"{lang} ({pct:.0f}%)")
        return ", ".join(parts)
