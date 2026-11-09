"""Minimal FastAPI server: JSON endpoints + static UI, no API keys required."""
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.recommender import MovieRecommender

HERE = Path(__file__).resolve().parent
app = FastAPI(title="CineMatch", version="1.0.0",
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
    return model().stats()


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
    return recommender.movie(index)


@app.post("/api/recommend")
def recommendations(req: RecommendationRequest):
    try:
        results = model().recommend(req.liked_ids, limit=req.limit,
                                    content_weight=req.content_weight)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"recommendations": results, "count": len(results)}

