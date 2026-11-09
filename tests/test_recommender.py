from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.recommender import MovieRecommender

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_loads_and_has_real_titles():
    model = MovieRecommender(ROOT / "data")
    assert model.source == "demo"
    assert len(model.movies) >= 250
    assert "Inception" in model.titles
    assert "Sci-Fi" in model.all_genres


def test_browse_case_insensitive_and_genres():
    model = MovieRecommender(ROOT / "data")
    hits, total = model.browse(search="INCEPTION")
    assert total == 1
    assert hits[0]["title"] == "Inception"
    items, total = model.browse(genre="Animation", limit=50)
    assert total >= 10
    assert all("Animation" in movie["genres"] for movie in items)


def test_excludes_liked_and_sorts_by_score():
    model = MovieRecommender(ROOT / "data")
    movie_id = model.movie_ids[model.titles.index("Inception")]
    result = model.recommend([int(movie_id)], limit=20)
    assert len(result) == 20
    assert all(item["id"] != movie_id for item in result)
    assert all(item["reason"] for item in result)
    assert [m["score"] for m in result] == sorted([m["score"] for m in result], reverse=True)


def test_personalizes_to_different_genres():
    model = MovieRecommender(ROOT / "data")
    sci = int(model.movie_ids[model.titles.index("Interstellar")])
    rom = int(model.movie_ids[model.titles.index("The Notebook")])
    sci_results = model.recommend([sci], limit=10)
    rom_results = model.recommend([rom], limit=10)
    sci_genres = [g for m in sci_results for g in m["genres"]]
    rom_genres = [g for m in rom_results for g in m["genres"]]
    assert sci_genres.count("Sci-Fi") > rom_genres.count("Sci-Fi")
    assert rom_genres.count("Romance") > sci_genres.count("Romance")


def test_movie_id_validation():
    model = MovieRecommender(ROOT / "data")
    with pytest.raises(ValueError, match="Unknown movie IDs"):
        model.recommend([-5])
    with pytest.raises(ValueError, match="at most 8"):
        model.recommend(list(range(1, 10)))


def test_hybrid_with_real_rating_structure(tmp_path):
    # Artificial fixture for a predictable unit test; NOT used in demo catalog.
    ml = tmp_path / "ml-latest-small"
    ml.mkdir()
    pd.DataFrame([
        [101,"Space Movie (2010)","Sci-Fi|Adventure"],
        [102,"Space Sequel (2012)","Sci-Fi|Adventure"],
        [103,"Romance Movie (2014)","Romance"],
        [104,"Another Romance (2016)","Romance"],
    ], columns=["movieId","title","genres"]).to_csv(ml / "movies.csv", index=False)
    pd.DataFrame([
        [1,101,5.0],[1,102,5.0],[1,103,1.0],
        [2,101,4.5],[2,102,4.5],[2,104,1.0],
        [3,103,5.0],[3,104,5.0],
    ],columns=["userId","movieId","rating"]).to_csv(ml / "ratings.csv",index=False)
    model = MovieRecommender(tmp_path)
    assert model.source == "movielens"
    assert model.stats()["algorithm"] == "hybrid"
    assert model.ratings_count == 8
    result = model.recommend([101], content_weight=0.3, limit=3)
    assert result[0]["id"] == 102
    assert result[0]["average_rating"] is not None


client = TestClient(app)


def test_web_api_and_validation():
    assert client.get("/").status_code == 200
    assert client.get("/api/health").json() == {"status":"ok"}
    assert client.get("/api/meta").json()["movie_count"] >= 250
    assert client.get("/api/movie/1").json()["title"] == "Inception"
    assert client.get("/api/movie/999999").status_code == 404
    res = client.get("/api/movies",params={"search":"arrival"})
    assert res.status_code == 200
    assert res.json()["total"] == 1
    rec = client.post("/api/recommend",json={"liked_ids":[1,2],"limit":5})
    assert rec.status_code == 200
    assert len(rec.json()["recommendations"]) == 5
    assert client.post("/api/recommend",json={"liked_ids":[-9]}).status_code == 400
    assert client.post("/api/recommend",json={"liked_ids":[]}).status_code == 422
    assert client.get("/api/movies",params={"limit":99999}).status_code == 422
