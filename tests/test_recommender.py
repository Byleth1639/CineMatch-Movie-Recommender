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


def test_v2_demo_has_poster_urls_and_detail_fields():
    model = MovieRecommender(ROOT / "data")
    movie = model.movie(model.id_to_idx[1])
    assert movie["poster_url"].startswith("https://image.tmdb.org/t/p/w342/")
    assert movie["overview"]
    assert movie["catalog_rating"] is None  # demo does NOT invent star ratings
    assert model.stats()["posters_count"] >= 10
    detail = client.get("/api/movie/1").json()
    assert 0 < len(detail["similar"]) <= 6
    assert all(result["id"] != 1 for result in detail["similar"])


def test_clean_catalog_filters_invalid_and_retains_metadata():
    from scripts.prepare_catalog import clean_catalog
    valid = []
    for i in range(130):
        valid.append({
            "adult": "False", "id": str(5000 + i), "title": f"Example Film {i}",
            "genres": "[{'id': 18, 'name': 'Drama'}, {'id': 12, 'name': 'Adventure'}]",
            "release_date": "2009-04-20", "poster_path": "/1234567890abcd.jpg",
            "overview": "An example film with a plot long enough to pass the import checks.",
            "vote_count": 100 + i, "vote_average": 7.5,
            "popularity": 2.0, "runtime": 110, "tagline": "An example.",
            "original_language": "en", "status": "Released",
        })
    valid.append({**valid[0], "id": "not-an-int"})
    valid.append({**valid[0], "id": "1000000", "poster_path": "http://evil.example/x"})
    data = clean_catalog(pd.DataFrame(valid), limit=110)
    assert len(data) == 110
    assert data["movieId"].is_unique
    assert data["genres"].str.contains("Drama\\|Adventure").all()
    assert data["title"].str.endswith("(2009)").all()
    assert data["poster_path"].str.startswith("/").all()


def test_expanded_catalog_uses_tmdb_metadata_and_search(tmp_path):
    import csv
    with (tmp_path / "catalog.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["movieId", "title", "genres", "poster_path", "overview",
                                                  "tagline", "runtime", "vote_average", "vote_count", "popularity"])
        writer.writeheader()
        writer.writerows([
            {"movieId": 862, "title": "Toy Story (1995)", "genres": "Adventure|Animation|Comedy",
             "poster_path": "/rhIRbceoE9lR4veEXuwCC2wARtG.jpg", "overview": "Two toys learn to be friends.",
             "tagline": "", "runtime": 81, "vote_average": 7.7, "vote_count": 5415, "popularity": 20.0},
            {"movieId": 101, "title": "Robot Story (1996)", "genres": "Adventure|Animation|Comedy",
             "poster_path": "", "overview": "Two friendly robots learn about teamwork.",
             "tagline": "", "runtime": 88, "vote_average": 6.5, "vote_count": 100, "popularity": 10.0},
            {"movieId": 102, "title": "Scary Story (2001)", "genres": "Horror|Thriller",
             "poster_path": "", "overview": "A scary mystery film.",
             "tagline": "", "runtime": 92, "vote_average": 6.0, "vote_count": 50, "popularity": 4.0},
        ])
    model = MovieRecommender(tmp_path)
    assert model.source == "catalog"
    assert model.stats()["movie_count"] == 3
    assert model.browse(search="toy story")[1] == 1
    movie = model.movie(model.id_to_idx[862])
    assert movie["catalog_rating"] == 7.7
    assert movie["tmdb_url"].endswith("/862")
    assert "poster" in movie["poster_url"] or movie["poster_url"].startswith("https://image.tmdb.org")
    assert model.recommend([862], limit=1)[0]["id"] == 101
