"""Minimal FastAPI server: JSON endpoints + static UI, no API keys required."""
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.recommender import MovieRecommender
from app.posters import poster_auth_available, refreshed_poster

HERE = Path(__file__).resolve().parent
app = FastAPI(title="CineMatch", version="2.1.0",
              description="An explainable movie recommender with optional MovieLens hybrid filtering")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


@lru_cache(maxsize=1)
def model() -> MovieRecommender:
    return MovieRecommender()


class RecommendationRequest(BaseModel):
    liked_ids: list[int] = Field(min_length=1, max_length=8)
    limit: int = Field(default=12, ge=1, le=30)
    content_weight: float = Field(default=.65, ge=0, le=1)


@app.get("/")
def home():
    return FileResponse(HERE / "static" / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def metadata():
    return {**model().stats(),
            "poster_refresh_enabled": model().source == "catalog" and poster_auth_available()}


@app.get("/api/poster/{movie_id}")
def refresh_poster(movie_id: int):
    """Try an updated poster only for a known catalog movie, never expose a TMDB key."""
    recommender = model()
    if movie_id not in recommender.id_to_idx:
        raise HTTPException(status_code=404, detail="Movie not found")
    if recommender.source != "catalog":
        raise HTTPException(status_code=404, detail="Poster refresh requires catalog mode")
    if not poster_auth_available():
        raise HTTPException(status_code=503, detail="Poster lookup is not configured")
    return {"poster_url": refreshed_poster(movie_id)}


@app.get("/api/movies")
def movies(
    search: Annotated[str, Query(max_length=100)] = "",
    genre: Annotated[str, Query(max_length=40)] = "",
    limit: Annotated[int, Query(ge=1, le=100)] = 36,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    items, total = model().browse(search=search, genre=genre, limit=limit, offset=offset)
    return {"movies": items, "total": total, "offset": offset}


@app.get("/api/movie/{movie_id}")
def movie_detail(movie_id: int):
    recommender = model()
    index = recommender.id_to_idx.get(movie_id)
    if index is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    result = recommender.movie(index)
    result["similar"] = recommender.recommend([movie_id], limit=6)
    return result


@app.post("/api/recommend")
def recommendations(req: RecommendationRequest):
    try:
        results = model().recommend(req.liked_ids, limit=req.limit,
                                    content_weight=req.content_weight)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"recommendations": results, "count": len(results)}

