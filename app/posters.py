"""Resolve retired TMDB poster paths safely, using optional server-side credentials.

TMDB API credentials are never returned to browsers or written to the catalog.
No API key is needed for ordinary TMDB CDN image requests; a key IS required
when a historical poster file has disappeared and its replacement must be looked up.
"""
from __future__ import annotations

from functools import lru_cache
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

POSTER_PATTERN = re.compile(r"^/[A-Za-z0-9_-]{10,}\.(?:jpg|jpeg|png|webp)$", re.I)


def poster_auth_available() -> bool:
    return bool(os.environ.get("TMDB_READ_ACCESS_TOKEN", "").strip() or
                os.environ.get("TMDB_API_KEY", "").strip())


def poster_url(path: str, size: str = "w342") -> str | None:
    if not POSTER_PATTERN.fullmatch(path):
        return None
    if size not in {"w185", "w342", "w500", "w780"}:
        raise ValueError("Unsupported poster size")
    return f"https://image.tmdb.org/t/p/{size}{path}"


@lru_cache(maxsize=8192)
def resolve_current_poster(tmdb_id: int, credential: str, bearer: bool = True) -> str | None:
    """Get an updated poster path for one catalog TMDB ID; memoized per worker.

    Missing posters, network failures and HTTP errors return None; the UI keeps a
    readable fallback card. Creds are only used in the server-to-server request.
    """
    if not 1 <= tmdb_id <= 2_000_000_000 or not credential:
        return None
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?language=en-US"
    headers = {"Accept": "application/json", "User-Agent": "CineMatch/2.1 (movie portfolio demo)"}
    if bearer:
        headers["Authorization"] = f"Bearer {credential}"
    else:
        url += "&" + urlencode({"api_key": credential})
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=7) as resp:
            payload = json.load(resp)
        path = payload.get("poster_path")
        return path if isinstance(path, str) and POSTER_PATTERN.fullmatch(path) else None
    except (HTTPError, URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError):
        return None


def refreshed_poster(tmdb_id: int) -> str | None:
    token = os.environ.get("TMDB_READ_ACCESS_TOKEN", "").strip()
    if token:
        return poster_url(resolve_current_poster(tmdb_id, token, bearer=True) or "")
    key = os.environ.get("TMDB_API_KEY", "").strip()
    if key:
        return poster_url(resolve_current_poster(tmdb_id, key, bearer=False) or "")
    return None
