"""Create a portable CineMatch catalog from The Movies Dataset (TMDB metadata).

Usage:
    python scripts/prepare_catalog.py --download
    python scripts/prepare_catalog.py --input path/to/movies_metadata.csv

The source data is a historic snapshot (films up to 2017), not a live API.
TMDB imagery is served from TMDB's CDN and requires attribution; see README.
"""
from __future__ import annotations

import argparse
import ast
import io
import math
import re
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "catalog.csv"
URLS = (
    "https://raw.githubusercontent.com/nmsohn/kaggle-movie/master/movies_metadata.csv",
    "https://raw.githubusercontent.com/sachinmasti/movie-data-cleaning/main/movies_metadata.csv",
)
POSTER_RE = re.compile(r"^/[A-Za-z0-9_-]{10,}\.(?:jpg|jpeg|png|webp)$", re.I)
COLS = ("adult", "genres", "id", "title", "overview", "poster_path", "release_date",
        "vote_average", "vote_count", "popularity", "runtime", "tagline", "original_language", "status")


def download() -> io.BytesIO:
    for url in URLS:
        try:
            print(f"Downloading catalog metadata: {url}")
            request = urllib.request.Request(url, headers={"User-Agent": "CineMatch-LearningProject/2.0"})
            with urllib.request.urlopen(request, timeout=100) as response:
                content = response.read()
            if len(content) < 500_000:
                raise ValueError("Response is too small to be the dataset")
            return io.BytesIO(content)
        except Exception as exc:
            print(f"  Source unavailable: {exc}")
    raise RuntimeError("All download sources failed. Download 'movies_metadata.csv' from "
                       "https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset "
                       "and run: python scripts/prepare_catalog.py --input PATH")


def genres_from_raw(raw: object) -> str:
    try:
        data = ast.literal_eval(str(raw))
        if not isinstance(data, list):
            return ""
        names = [str(x.get("name", "")).strip().replace("|", " ") for x in data if isinstance(x, dict)]
        return "|".join(v for v in names if v)
    except (ValueError, SyntaxError, TypeError):
        return ""


def clean_catalog(raw: pd.DataFrame, limit: int = 8000) -> pd.DataFrame:
    needed = {"id", "title", "genres", "release_date", "poster_path", "overview", "vote_count"}
    if not needed.issubset(raw.columns):
        raise ValueError(f"Missing columns from source: {sorted(needed - set(raw.columns))}")
    df = raw.copy()
    for c in COLS:
        if c not in df:
            df[c] = ""
    df["movieId"] = pd.to_numeric(df["id"], errors="coerce")
    df["year"] = pd.to_numeric(df["release_date"].astype(str).str.slice(0, 4), errors="coerce")
    for col in ("vote_count", "vote_average", "popularity", "runtime"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["genres"] = df["genres"].map(genres_from_raw)
    for col in ("poster_path", "overview", "title", "tagline", "original_language"):
        df[col] = df[col].fillna("").astype(str).str.strip()
    mask = (df["movieId"].notna() & df["year"].between(1900, 2026)
            & df["adult"].astype(str).str.lower().ne("true")
            & df["title"].str.len().between(2, 130)
            & df["genres"].str.len().gt(0)
            & df["overview"].str.len().ge(30)
            & df["poster_path"].str.fullmatch(POSTER_RE)
            & df["vote_count"].ge(15))
    df = df.loc[mask].copy()
    df = df.drop_duplicates("movieId", keep="first")
    # Filter low-signal entries but retain a variety of genres and decades.
    df["rank"] = (df["vote_count"].map(lambda v: math.log1p(v))
                  + .26 * df["popularity"].clip(lower=0).map(lambda v: math.log1p(v))
                  + .1 * df["vote_average"])
    df = df.sort_values("rank", ascending=False).head(limit)
    df["movieId"] = df["movieId"].astype("int64")
    df["year"] = df["year"].astype(int)
    df["title"] = df["title"] + " (" + df["year"].astype(str) + ")"
    df["vote_average"] = df["vote_average"].clip(0, 10).round(2)
    df["vote_count"] = df["vote_count"].clip(lower=0).astype(int)
    df["runtime"] = df["runtime"].clip(lower=0).astype(int)
    df["overview"] = df["overview"].str.slice(0, 1100)
    df["tagline"] = df["tagline"].str.slice(0, 180)
    cols = ["movieId", "title", "genres", "poster_path", "overview", "tagline",
            "runtime", "vote_average", "vote_count", "popularity", "original_language"]
    return df[cols].sort_values(["vote_count", "vote_average"], ascending=False).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--download", action="store_true")
    source.add_argument("--input", type=Path)
    parser.add_argument("--limit", type=int, default=8000)
    args = parser.parse_args()
    if not 100 <= args.limit <= 25_000:
        parser.error("--limit must be from 100 to 25000")
    data = download() if args.download else args.input
    raw = pd.read_csv(data, low_memory=False, on_bad_lines="skip", dtype={"id": str})
    clean = clean_catalog(raw, limit=args.limit)
    if len(clean) < 100:
        raise ValueError("Too few movies after cleaning; check source file")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(OUTPUT, index=False)
    print(f"Created {OUTPUT} with {len(clean):,} movies ({OUTPUT.stat().st_size/1_000_000:.1f} MB)")
    print("Catalog is historic (through 2017); TMDB images require visible attribution.")


if __name__ == "__main__":
    main()
