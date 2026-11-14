# CineMatch

CineMatch is a movie recommender built with FastAPI, scikit-learn, pandas, and vanilla JavaScript. Browse the catalog by title or genre, open a movie to see its details, and pick up to eight favorites to get recommendations.

## How recommendations work

CineMatch uses TF-IDF to turn each movie’s genres, release decade, plot, and tagline into a feature vector. It uses cosine similarity to compare those vectors with your picks and rank similar movies. When MovieLens ratings are configured, the app can also use patterns from historical user ratings.

## Run locally

From the repository root, run:

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open [localhost:8000](http://localhost:8000). The app starts with a bundled catalog of 257 movies.

## Expand the catalog

To import up to 8,000 titles from a historical movie metadata snapshot, run:

```bash
python scripts/prepare_catalog.py --download
```

Restart the app after the import. The `/api/meta` endpoint shows the loaded catalog and movie count. Posters come from TMDB, and movies without a working image display a placeholder.

## Run tests

```bash
python -m pip install pytest httpx
python -m pytest -q
```

## Data sources

- [The Movies Dataset](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset) for the expanded movie catalog
- [TMDB](https://www.themoviedb.org/) for movie metadata and poster images
- [MovieLens](https://grouplens.org/datasets/movielens/) for optional ratings data
