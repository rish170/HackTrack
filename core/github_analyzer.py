from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Dict, List, Optional

import requests

from utils.constants import GITHUB_API_BASE
from utils.helpers import combine_messages, get_github_token, iso_to_datetime, parse_repo_from_url


@dataclass
class CommitEntry:
    sha: str
    message: str
    author: str
    date_utc: str
    total_lines: int = 0
    total_files: int = 0


@dataclass
class RepoSnapshot:
    team_key: str
    repo_url: str
    owner: str
    repo: str
    branch: str
    total_commits_at_snapshot: int
    languages: str
    readme_present: bool
    snapshot_timestamp_utc: str
    commits: list[CommitEntry]


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
        self.requests_remaining: Optional[int] = None
        self.requests_limit: Optional[int] = None
        # Fetch initial rate limit
        self.check_rate_limit()

    def check_rate_limit(self) -> Dict[str, Optional[int]]:
        """Explicitly check rate limit using the /rate_limit endpoint."""
        url = f"{GITHUB_API_BASE}/rate_limit"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                core = data.get("resources", {}).get("core", {})
                if not core: # Fallback for some API versions
                    core = data.get("rate", {})
                
                self.requests_remaining = core.get("remaining")
                self.requests_limit = core.get("limit")
            self._update_rate_limit(resp.headers)
        except Exception:
            pass
        return self.get_rate_limit_info()

    def _update_rate_limit(self, headers: Dict[str, str]) -> None:
        """Extract rate limit info from response headers."""
        remaining = headers.get("x-ratelimit-remaining")
        limit = headers.get("x-ratelimit-limit")
        if remaining is not None:
            self.requests_remaining = int(remaining)
        if limit is not None:
            self.requests_limit = int(limit)

    def get_rate_limit_info(self) -> Dict[str, Optional[int]]:
        """Return current rate limit status."""
        return {
            "remaining": self.requests_remaining,
            "limit": self.requests_limit
        }

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _get_json(self, url: str, timeout: int = 12) -> Optional[Dict]:
        resp = requests.get(url, headers=self._headers(), timeout=timeout)
        self._update_rate_limit(resp.headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def _get(self, url: str, timeout: int = 12) -> requests.Response:
        resp = requests.get(url, headers=self._headers(), timeout=timeout)
        self._update_rate_limit(resp.headers)
        if resp.status_code == 404:
            return resp
        resp.raise_for_status()
        return resp

    def _repo_metadata(self, owner: str, repo: str) -> Dict:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        return self._get_json(url) or {}

    def _get_tree(self, owner: str, repo: str, sha: str) -> Dict:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{sha}?recursive=1"
        return self._get_json(url) or {}

    def _get_line_count(self, owner: str, repo: str, blob_sha: str) -> int:
        if not hasattr(self, '_blob_cache'):
            self._blob_cache = {}
        
        if blob_sha in self._blob_cache:
            return self._blob_cache[blob_sha]

        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/blobs/{blob_sha}"
        
        try:
            resp = requests.get(url, headers=self._headers(), timeout=12)
            self._update_rate_limit(resp.headers)
            if resp.status_code != 200:
                return 0
            
            data = resp.json()
            # The GitHub API returns content in the 'content' field as a base64 string
            encoded = data.get("content", "")
            if not encoded:
                return 0
                
            import base64
            try:
                # Remove any potential whitespace/newlines in the base64 string
                cleaned_encoded = "".join(encoded.split())
                content_bytes = base64.b64decode(cleaned_encoded)
                
                # Heuristic check if content is binary
                if self._is_binary_content(content_bytes):
                    self._blob_cache[blob_sha] = 0
                    return 0

                content_str = content_bytes.decode("utf-8", errors="ignore")
                
                # Count lines accurately
                if not content_str:
                    lines = 0
                else:
                    lines = content_str.count('\n')
                    if not content_str.endswith('\n'):
                        lines += 1
                
                self._blob_cache[blob_sha] = lines
                return lines
            except Exception:
                return 0
        except Exception:
            return 0

    @staticmethod
    def _is_binary_content(content: bytes) -> bool:
        """Heuristic check if content is binary."""
        if not content:
            return False
        # Check first 1024 bytes for null bytes
        chunk = content[:1024]
        return b'\x00' in chunk

    @staticmethod
    def _is_binary(path: str) -> bool:
        # Minimal list to avoid skipping potential source code files
        binary_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.ico', '.webp', '.bmp', '.tiff',
            '.pdf', '.zip', '.gz', '.tar', '.exe', '.dll', '.bin', '.pyc',
            '.mp3', '.mp4', '.wav', '.avi', '.ttf', '.otf', '.woff', '.woff2',
            '.ds_store', '.sqlite', '.db'
        }
        import os
        _, ext = os.path.splitext(path.lower())
        
        # Always count lines for common code files
        code_extensions = {
            '.py', '.js', '.ts', '.html', '.css', '.c', '.cpp', '.h', '.hpp',
            '.java', '.json', '.yaml', '.yml', '.md', '.txt', '.sh', '.bat'
        }
        if ext in code_extensions:
            return False
            
        return ext in binary_extensions

    def _commits_page(self, owner: str, repo: str, branch: str, page: int, per_page: int = 100) -> List[Dict]:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits?per_page={per_page}&sha={branch}&page={page}"
        data = self._get_json(url)
        return data or []

    def _commit_count(self, owner: str, repo: str, branch: str) -> int:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits?per_page=1&sha={branch}"
        resp = self._get(url)
        if resp.status_code == 404:
            return 0

        link = resp.headers.get("Link", "")
        if "rel=\"last\"" in link:
            # ...page=N>; rel="last"
            parts = [p.strip() for p in link.split(",")]
            for part in parts:
                if "rel=\"last\"" in part:
                    match = re.search(r"[?&]page=(\d+)", part)
                    if match:
                        return int(match.group(1))
        data = resp.json() if resp.content else []
        return 1 if data else 0

    def _languages(self, owner: str, repo: str) -> Dict[str, int]:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/languages"
        data = self._get_json(url)
        return data or {}

    def _has_readme(self, owner: str, repo: str) -> bool:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/readme"
        resp = requests.get(url, headers=self._headers(), timeout=10)
        self._update_rate_limit(resp.headers)
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

        commits = self._commits_page(owner, repo, default_branch, page=1, per_page=30)
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

    def analyze_commit_history(
        self,
        team_key: str,
        repo_url: str,
        known_shas: Optional[set[str]] = None,
        progress_cb=None,
    ) -> RepoSnapshot:
        parsed = parse_repo_from_url(repo_url)
        if not parsed:
            raise ValueError(f"Invalid GitHub URL: {repo_url}")
        owner, repo = parsed

        meta = self._repo_metadata(owner, repo)
        branch = meta.get("default_branch", "main") if meta else "main"
        if progress_cb:
            progress_cb("fetch", 20, f"Repo metadata loaded for {repo}")

        languages_raw = self._languages(owner, repo)
        languages = self._format_languages(languages_raw)
        readme_present = self._has_readme(owner, repo)
        total_commits = self._commit_count(owner, repo, branch)
        if progress_cb:
            progress_cb("fetch", 50, f"Snapshot ready for {repo}")

        new_commits = self._fetch_new_commits(owner, repo, branch, known_shas or set(), progress_cb=progress_cb)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        if progress_cb:
            progress_cb("fetch", 100, f"GitHub fetch complete for {repo}")

        return RepoSnapshot(
            team_key=team_key,
            repo_url=repo_url,
            owner=owner,
            repo=repo,
            branch=branch,
            total_commits_at_snapshot=total_commits,
            languages=languages,
            readme_present=readme_present,
            snapshot_timestamp_utc=timestamp,
            commits=new_commits,
        )

    def _fetch_new_commits(
        self,
        owner: str,
        repo: str,
        branch: str,
        known_shas: set[str],
        progress_cb=None,
    ) -> list[CommitEntry]:
        results: list[CommitEntry] = []
        page = 1
        while True:
            commits = self._commits_page(owner, repo, branch, page=page, per_page=100)
            if not commits:
                break

            stop = False
            for c in commits:
                sha = str(c.get("sha", "")).strip()
                if not sha:
                    continue
                if sha in known_shas:
                    stop = True
                    break

                commit = c.get("commit", {}) or {}
                message = str(commit.get("message", "")).replace("\n", " ").strip()
                author = str((commit.get("author") or {}).get("name") or "")
                if not author:
                    author = str((commit.get("committer") or {}).get("name") or "")
                date_utc = str((commit.get("author") or {}).get("date") or "")
                if not date_utc:
                    date_utc = str((commit.get("committer") or {}).get("date") or "")

                # Fetch tree for this commit to count files and calculate total lines
                tree = self._get_tree(owner, repo, sha)
                total_files = 0
                total_lines = 0
                
                if tree and "tree" in tree:
                    for item in tree["tree"]:
                        if item.get("type") == "blob":
                            total_files += 1
                            path = item.get("path", "")
                            # Explicitly check for code files
                            if not self._is_binary(path):
                                blob_sha = item.get("sha")
                                lines = self._get_line_count(owner, repo, blob_sha)
                                total_lines += lines
                
                results.append(CommitEntry(
                    sha=sha, 
                    message=message, 
                    author=author, 
                    date_utc=date_utc,
                    total_lines=total_lines,
                    total_files=total_files
                ))

            if progress_cb:
                progress_cb("fetch", min(95, 50 + page * 10), f"Pulled commits page {page} for {repo}")

            if stop:
                break
            page += 1

        # API returns newest-first; append in chronological order for nicer history
        results.reverse()
        return results

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
