"""Content-based TF-IDF recommender with optional MovieLens collaborative signals.

The metadata catalog provides plots, TMDB vote averages and poster paths.
MovieLens historical user ratings are separate, optional, and never packaged.
Similarity scores are not predicted star ratings.
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

YEAR_PATTERN = re.compile(r"\((\d{4})\)$")
POSTER_PATTERN = re.compile(r"^/[A-Za-z0-9_-]{10,}\.(?:jpg|jpeg|png|webp)$", re.I)
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class MovieRecommender:
    """Movie metadata + sparse ML features; all similarities computed on demand."""

    def __init__(self, data_dir: Path | str = DEFAULT_DATA_DIR,
                 ratings_override: pd.DataFrame | None = None):
        self.data_dir = Path(data_dir)
        ml_dir = self.data_dir / "ml-latest-small"
        if (self.data_dir / "catalog.csv").is_file():
            self.source = "catalog"
            movie_path = self.data_dir / "catalog.csv"
        elif (ml_dir / "movies.csv").is_file():
            self.source = "movielens"
            movie_path = ml_dir / "movies.csv"
        else:
            self.source = "demo"
            movie_path = self.data_dir / "demo_movies.csv"
        if not movie_path.exists():
            raise FileNotFoundError(f"Catalog not found: {movie_path}")
        movies = pd.read_csv(movie_path).fillna("")
        if not {"movieId", "title", "genres"}.issubset(movies.columns):
            raise ValueError("Catalog requires movieId, title, genres")
        movies["movieId"] = movies["movieId"].astype(int)
        movies = movies.drop_duplicates("movieId").reset_index(drop=True)
        self.movies = movies
        self.movie_ids = movies["movieId"].to_numpy(dtype=int)
        self.id_to_idx = {int(mid): i for i, mid in enumerate(self.movie_ids)}
        self.titles = [YEAR_PATTERN.sub("", str(v)).strip() for v in movies["title"]]
        self.years = [int(m.group(1)) if (m := YEAR_PATTERN.search(str(v))) else None
                      for v in movies["title"]]
        self.genres = [[x for x in str(g).split("|") if x and x != "(no genres listed)"]
                       for g in movies["genres"]]
        self.search_titles = [t.casefold() for t in self.titles]
        self.genre_search = [set(g.casefold() for g in row) for row in self.genres]
        self.poster_paths = [str(v) if POSTER_PATTERN.fullmatch(str(v)) else ""
                             for v in movies.get("poster_path", pd.Series([""]*len(movies)))]
        # Our hand-curated offline demo includes a few up-to-date poster paths.
        # Prefer those for IDENTICAL title + year in the larger historical catalog.
        # Movie IDs cannot be matched here: demo IDs and TMDB IDs are different.
        if self.source == "catalog":
            demo_path = self.data_dir / "demo_movies.csv"
            if demo_path.is_file():
                demo = pd.read_csv(demo_path).fillna("")
                current = {str(row.title): str(row.poster_path) for row in demo.itertuples()
                           if POSTER_PATTERN.fullmatch(str(row.poster_path))}
                self.poster_paths = [current.get(str(title), path)
                                     for title, path in zip(movies["title"], self.poster_paths)]
                # Two extra first-page films not present in the demo's poster set.
                # TMDB IDs are stable; never match only by ambiguous movie titles.
                current_by_tmdb_id = {
                    27205: "/xlaY2zyzMfkhk0HSC5VUwzoZPU1.jpg",  # Inception (2010)
                    24428: "/RYMX2wcKCBAr24UyPD7xwmjaTn.jpg",  # The Avengers (2012)
                    19995: "/kyeqWdyUXW608qlYkRqosgbbJyK.jpg",  # Avatar (2009)
                }
                self.poster_paths = [current_by_tmdb_id.get(int(mid), path)
                                     for mid, path in zip(self.movie_ids, self.poster_paths)]
        self.overviews = [str(v) for v in movies.get("overview", pd.Series([""]*len(movies)))]
        self.taglines = [str(v) for v in movies.get("tagline", pd.Series([""]*len(movies)))]
        self.runtimes = pd.to_numeric(movies.get("runtime", pd.Series([0]*len(movies))),
                                      errors="coerce").fillna(0).astype(int).to_numpy()
        self.tmdb_avg = pd.to_numeric(movies.get("vote_average", pd.Series([0]*len(movies))),
                                      errors="coerce").fillna(0).to_numpy()
        self.tmdb_votes = pd.to_numeric(movies.get("vote_count", pd.Series([0]*len(movies))),
                                        errors="coerce").fillna(0).astype(int).to_numpy()

        if ratings_override is not None:
            ratings = ratings_override.copy()
        elif (ml_dir / "ratings.csv").is_file():
            ratings = pd.read_csv(ml_dir / "ratings.csv")
            if self.source == "catalog":
                links_file = ml_dir / "links.csv"
                if links_file.is_file():
                    links = pd.read_csv(links_file)[["movieId", "tmdbId"]].dropna()
                    links["tmdbId"] = links["tmdbId"].astype(int)
                    ratings = ratings.merge(links, on="movieId", how="inner")
                    ratings["movieId"] = ratings["tmdbId"]
                else:
                    ratings = ratings.iloc[0:0]
            elif self.source == "demo":
                ratings = ratings.iloc[0:0]
        else:
            ratings = pd.DataFrame(columns=["userId", "movieId", "rating"])

        self.ratings_count = 0
        self.counts = np.zeros(len(movies), dtype=int)
        self.avg_ratings = np.zeros(len(movies), dtype=float)
        self.collaborative = None
        self.user_count = 0
        if not ratings.empty:
            self._prepare_ratings(ratings)

        tag_map: dict[int, str] = {}
        tags_path = ml_dir / "tags.csv"
        if self.source == "movielens" and tags_path.is_file():
            tags = pd.read_csv(tags_path).dropna(subset=["tag"])
            tags["tag"] = tags["tag"].astype(str).str.lower().str.slice(0, 50)
            tag_map = tags.groupby("movieId")["tag"].agg(lambda values: " ".join(
                dict.fromkeys(values.tolist()[:20]))).to_dict()

        corpus = []
        for i, mid in enumerate(self.movie_ids):
            tokens = ["genre_" + g.lower().replace("-", "_").replace(" ", "_")
                      for g in self.genres[i]]
            decade = f"decade_{self.years[i] // 10 * 10}" if self.years[i] else ""
            # Genres repeated; plot provides finer-grained movie-to-movie signals.
            plot = re.sub(r"[^\w\s'-]", " ", self.overviews[i][:1000]).lower()
            corpus.append(" ".join(tokens * 5 + [decade, plot, self.taglines[i][:150],
                                                  tag_map.get(int(mid), "")]))
        self.vectorizer = TfidfVectorizer(stop_words="english", min_df=1,
                                          max_features=22000, sublinear_tf=True,
                                          token_pattern=r"(?u)\b[\w-]+\b")
        self.content = normalize(self.vectorizer.fit_transform(corpus), axis=1)
        self.all_genres = sorted(set(g for group in self.genres for g in group))
        if self.ratings_count:
            observed = self.counts > 0
            mean = float(np.average(self.avg_ratings[observed], weights=self.counts[observed]))
            shrunk = (self.counts * self.avg_ratings + 25*mean) / (self.counts+25)
            quality = np.clip((shrunk - 2.5)/2.5, 0, 1)
            confidence = np.log1p(self.counts) / max(np.log1p(self.counts.max()),1)
            self.popularity = quality*confidence
        else:
            self.popularity = np.zeros(len(movies),dtype=float)
        if self.source == "catalog":
            # TMDB votes, not MovieLens. Used for browsing, not a fake ML accuracy metric.
            self.popular_order = np.argsort(-np.log1p(self.tmdb_votes) - .14*self.tmdb_avg,
                                            kind="stable")
        elif self.ratings_count:
            self.popular_order = np.argsort(-self.popularity,kind="stable")
        else:
            self.popular_order = np.arange(len(movies))

    def _prepare_ratings(self, ratings: pd.DataFrame) -> None:
        ratings = ratings.dropna(subset=["userId", "movieId", "rating"]).copy()
        ratings["movieId"] = ratings["movieId"].astype(int)
        ratings = ratings[ratings["movieId"].isin(self.id_to_idx)]
        self.ratings_count = len(ratings)
        if not self.ratings_count:
            return
        grouped = ratings.groupby("movieId")["rating"].agg(["count", "mean"])
        for mid, row in grouped.iterrows():
            i = self.id_to_idx[int(mid)]
            self.counts[i] = int(row["count"])
            self.avg_ratings[i] = float(row["mean"])
        pos = ratings[ratings["rating"] >= 3.5]
        users = pd.Index(sorted(ratings["userId"].unique()))
        self.user_count = len(users)
        if pos.empty:
            return
        user_indices = {uid: n for n, uid in enumerate(users)}
        r = np.array([self.id_to_idx[int(mid)] for mid in pos["movieId"]])
        c = np.array([user_indices[uid] for uid in pos["userId"]])
        values = pos["rating"].to_numpy(dtype=float)-2.5
        matrix = sparse.csr_matrix((values,(r,c)),shape=(len(self.movie_ids),len(users)))
        self.collaborative = normalize(matrix,axis=1)

    def movie(self, i: int) -> dict[str, Any]:
        mid = int(self.movie_ids[i]); poster = self.poster_paths[i]
        return {
            "id": mid, "title": self.titles[i], "year": self.years[i],
            "genres": self.genres[i],
            "poster_url": f"https://image.tmdb.org/t/p/w342{poster}" if poster else None,
            "poster_large_url": f"https://image.tmdb.org/t/p/w780{poster}" if poster else None,
            "overview": self.overviews[i], "tagline": self.taglines[i],
            "runtime": int(self.runtimes[i]) or None,
            "catalog_rating": round(float(self.tmdb_avg[i]),1) if self.tmdb_votes[i] else None,
            "catalog_votes": int(self.tmdb_votes[i]),
            "tmdb_url": f"https://www.themoviedb.org/movie/{mid}" if self.source == "catalog" else None,
            "rating_count": int(self.counts[i]),
            "average_rating": round(float(self.avg_ratings[i]),2) if self.counts[i] else None,
        }

    def browse(self, search: str = "", genre: str = "", limit: int = 40,
               offset: int = 0) -> tuple[list[dict], int]:
        search = search.strip().casefold(); genre = genre.strip().casefold()
        matching = [int(i) for i in self.popular_order
                    if (not search or search in self.search_titles[int(i)])
                    and (not genre or genre in self.genre_search[int(i)])]
        return [self.movie(i) for i in matching[offset:offset+limit]],len(matching)

    def recommend(self, liked_ids: list[int], limit: int = 12,
                  content_weight: float = .65) -> list[dict]:
        liked = list(dict.fromkeys(int(x) for x in liked_ids))
        invalid = [mid for mid in liked if mid not in self.id_to_idx]
        if invalid:
            raise ValueError(f"Unknown movie IDs: {invalid[:5]}")
        if not liked:
            return []
        if len(liked)>8:
            raise ValueError("Choose at most 8 movies")
        seeds = [self.id_to_idx[mid] for mid in liked]
        similarity = (self.content[seeds] @ self.content.T).toarray()
        contentscore = .55*similarity.max(axis=0) + .45*similarity.mean(axis=0)
        collaborator = None
        if self.collaborative is not None:
            collaborator = (self.collaborative[seeds] @ self.collaborative.T).toarray()
            colscore = .55*collaborator.max(axis=0)+.45*collaborator.mean(axis=0)
            score = .93*(content_weight*contentscore+(1-content_weight)*colscore) + .07*self.popularity
        else:
            score = contentscore
        score[seeds] = -np.inf
        top = np.argsort(-score,kind="stable")[:limit]
        results = []
        for ix in top:
            ix = int(ix)
            seed = seeds[int(np.argmax(similarity[:,ix]))]
            shared = [g for g in self.genres[ix] if g in self.genres[seed]]
            if collaborator is not None and float(collaborator[:,ix].max()) > float(similarity[:,ix].max()) + .15:
                reason = f"Viewers who liked {self.titles[seed]} also liked this"
            elif shared:
                reason = f"Shares {', '.join(shared[:2])} with {self.titles[seed]}"
            else:
                reason = f"Similar story and themes to {self.titles[seed]}"
            results.append({**self.movie(ix), "score":round(float(score[ix]),4),"reason":reason})
        return results

    def stats(self) -> dict[str, Any]:
        return {
            "source": self.source, "movie_count":len(self.movies),
            "posters_count":sum(bool(p) for p in self.poster_paths),
            "ratings_count":self.ratings_count,"user_count":self.user_count,
            "genres":self.all_genres,
            "algorithm":"hybrid" if self.collaborative is not None else "content-based",
            "catalog_period":"Historical TMDB snapshot (through 2017)" if self.source=="catalog" else None,
        }
