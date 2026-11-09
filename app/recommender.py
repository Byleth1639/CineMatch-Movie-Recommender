"""Explainable content-based and collaborative-filtering movie recommendations.

The recommender learns *similarity*, not a user's probability of enjoying a film.
MovieLens data is never redistributed by this project; see README for licensing.
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
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class MovieRecommender:
    """Load a movie catalog and optionally an interaction matrix of actual ratings."""

    def __init__(self, data_dir: Path | str = DEFAULT_DATA_DIR,
                 ratings_override: pd.DataFrame | None = None):
        self.data_dir = Path(data_dir)
        movielens_dir = self.data_dir / "ml-latest-small"
        movies_path = movielens_dir / "movies.csv"
        self.source = "movielens" if movies_path.is_file() else "demo"
        if self.source == "demo":
            movies_path = self.data_dir / "demo_movies.csv"
        if not movies_path.is_file():
            raise FileNotFoundError(f"No movie catalog found at {movies_path}")

        movies = pd.read_csv(movies_path).fillna("")
        required = {"movieId", "title", "genres"}
        if not required.issubset(movies.columns):
            raise ValueError(f"Movie catalog must contain {required}")
        movies["movieId"] = movies["movieId"].astype(int)
        movies = movies.drop_duplicates("movieId").reset_index(drop=True)
        self.movies = movies
        self.movie_ids = movies["movieId"].to_numpy(dtype=int)
        self.id_to_idx = {movie_id: i for i, movie_id in enumerate(self.movie_ids)}
        self.titles = [YEAR_PATTERN.sub("", value).strip() for value in movies["title"].astype(str)]
        self.years = [int(m.group(1)) if (m := YEAR_PATTERN.search(str(title))) else None
                      for title in movies["title"]]
        self.genres = [[g for g in str(value).split("|") if g and g != "(no genres listed)"]
                       for value in movies["genres"]]

        ratings_file = movielens_dir / "ratings.csv"
        if ratings_override is not None:
            ratings = ratings_override.copy()
        elif self.source == "movielens" and ratings_file.is_file():
            ratings = pd.read_csv(ratings_file)
        else:
            ratings = pd.DataFrame(columns=["userId", "movieId", "rating"])

        self.ratings_count = len(ratings)
        self.counts = np.zeros(len(movies), dtype=int)
        self.avg_ratings = np.zeros(len(movies), dtype=float)
        self.collaborative = None
        self.user_count = 0
        if not ratings.empty:
            self._prepare_ratings(ratings)

        # A movie's content text consists of its genres, (optionally) real user tags,
        # and decade. Repeating genres prevents noisy user tags from dominating.
        tag_map: dict[int, str] = {}
        tags_path = movielens_dir / "tags.csv"
        if self.source == "movielens" and tags_path.is_file():
            tags = pd.read_csv(tags_path).dropna(subset=["tag"])
            tags["tag"] = tags["tag"].astype(str).str.lower().str.slice(0, 50)
            tag_map = (tags.groupby("movieId")["tag"]
                       .agg(lambda values: " ".join(dict.fromkeys(values.tolist()[:20])))
                       .to_dict())

        corpus = []
        for i, movie_id in enumerate(self.movie_ids):
            genre_tokens = [g.lower().replace("-", "_").replace(" ", "_")
                            for g in self.genres[i]]
            year_token = f"decade_{self.years[i] // 10 * 10}" if self.years[i] else ""
            corpus.append(" ".join(genre_tokens * 4 + [year_token, tag_map.get(movie_id, "")]))
        self.vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b[\w-]+\b", sublinear_tf=True)
        self.content = normalize(self.vectorizer.fit_transform(corpus), norm="l2", axis=1)

        self.all_genres = sorted(set(g for group in self.genres for g in group))
        if self.ratings_count:
            # Bayesian-shrunk mean rating and a confidence factor protect against
            # recommending a 5-star movie that has only one rating.
            observed = self.counts > 0
            global_mean = float(np.average(self.avg_ratings[observed],
                                           weights=self.counts[observed]))
            shrunk = (self.counts * self.avg_ratings + 25 * global_mean) / (self.counts + 25)
            quality = np.clip((shrunk - 2.5) / 2.5, 0, 1)
            confidence = np.log1p(self.counts) / max(np.log1p(self.counts.max()), 1)
            self.popularity = (quality * confidence).astype(float)
        else:
            self.popularity = np.zeros(len(movies), dtype=float)

        self.popular_order = (np.argsort(-self.popularity, kind="stable")
                              if self.ratings_count else np.arange(len(self.movies)))

    def _prepare_ratings(self, ratings: pd.DataFrame) -> None:
        ratings = ratings.dropna(subset=["userId", "movieId", "rating"]).copy()
        ratings["movieId"] = ratings["movieId"].astype(int)
        ratings = ratings[ratings["movieId"].isin(self.id_to_idx)]
        self.ratings_count = len(ratings)
        grouped = ratings.groupby("movieId")["rating"].agg(["count", "mean"])
        for movie_id, row in grouped.iterrows():
            i = self.id_to_idx[int(movie_id)]
            self.counts[i] = int(row["count"])
            self.avg_ratings[i] = float(row["mean"])
        # Only positive co-ratings contribute to item-to-item collaborative
        # similarity. These are *real* MovieLens votes, never generated votes.
        positive = ratings[ratings["rating"] >= 3.5]
        users = pd.Index(sorted(ratings["userId"].unique()))
        self.user_count = len(users)
        if positive.empty:
            return
        user_to_idx = {user: i for i, user in enumerate(users)}
        row = np.array([self.id_to_idx[int(mid)] for mid in positive["movieId"]])
        col = np.array([user_to_idx[user] for user in positive["userId"]])
        data = positive["rating"].to_numpy(dtype=float) - 2.5
        matrix = sparse.csr_matrix((data, (row, col)),
                                   shape=(len(self.movie_ids), len(users)))
        self.collaborative = normalize(matrix, axis=1, norm="l2")

    def movie(self, i: int) -> dict[str, Any]:
        item = {
            "id": int(self.movie_ids[i]),
            "title": self.titles[i],
            "year": self.years[i],
            "genres": self.genres[i],
            "rating_count": int(self.counts[i]),
            "average_rating": round(float(self.avg_ratings[i]), 2) if self.counts[i] else None,
        }
        return item

    def browse(self, search: str = "", genre: str = "", limit: int = 40,
               offset: int = 0) -> tuple[list[dict], int]:
        search = search.strip().casefold()
        genre = genre.strip().casefold()
        result = []
        for i in self.popular_order:
            if search and search not in self.titles[i].casefold():
                continue
            if genre and genre not in [g.casefold() for g in self.genres[i]]:
                continue
            result.append(int(i))
        total = len(result)
        return [self.movie(i) for i in result[offset:offset + limit]], total

    def recommend(self, liked_ids: list[int], limit: int = 12,
                  content_weight: float = .65) -> list[dict]:
        liked = list(dict.fromkeys(int(value) for value in liked_ids))
        invalid = [mid for mid in liked if mid not in self.id_to_idx]
        if invalid:
            raise ValueError(f"Unknown movie IDs: {invalid[:5]}")
        if not liked:
            return []
        if len(liked) > 8:
            raise ValueError("Choose at most 8 movies")
        seed_indices = [self.id_to_idx[mid] for mid in liked]

        # Similarity is computed at request time for the selected films only;
        # no dense all-movies x all-movies matrix is needed.
        content_sim = (self.content[seed_indices] @ self.content.T).toarray()
        content_score = .55 * content_sim.max(axis=0) + .45 * content_sim.mean(axis=0)

        collab_sim = None
        if self.collaborative is not None:
            collab_sim = (self.collaborative[seed_indices] @ self.collaborative.T).toarray()
            collab_score = .55 * collab_sim.max(axis=0) + .45 * collab_sim.mean(axis=0)
            score = content_weight * content_score + (1 - content_weight) * collab_score
            score = .93 * score + .07 * self.popularity
        else:
            score = content_score

        score[seed_indices] = -np.inf
        top = np.argsort(-score, kind="stable")[:limit]
        recommendations = []
        for index in top:
            index = int(index)
            nearest_seed_position = int(np.argmax(content_sim[:, index]))
            nearest_seed_idx = seed_indices[nearest_seed_position]
            shared = [g for g in self.genres[index] if g in self.genres[nearest_seed_idx]]
            via_collaboration = (
                collab_sim is not None
                and float(collab_sim[:, index].max()) > float(content_sim[:, index].max()) + .15
            )
            seed_title = self.titles[nearest_seed_idx]
            if via_collaboration:
                explanation = f"MovieLens users who liked {seed_title} also liked this"
            elif shared:
                explanation = f"Shares {', '.join(shared[:2])} with {seed_title}"
            else:
                explanation = f"Similar viewing profile to {seed_title}"
            recommendations.append({
                **self.movie(index),
                "score": round(float(score[index]), 4),
                "reason": explanation,
            })
        return recommendations

    def stats(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "movie_count": len(self.movies),
            "ratings_count": self.ratings_count,
            "user_count": self.user_count,
            "genres": self.all_genres,
            "algorithm": "hybrid" if self.collaborative is not None else "content-based",
        }
