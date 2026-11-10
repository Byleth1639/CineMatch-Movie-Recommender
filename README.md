# CineMatch v2 — movie recommendation system

**A real web app with explainable ML recommendations, movie posters, movie details, a large searchable catalog, and a responsive cinema-style interface.** Python · FastAPI · scikit-learn · pandas · vanilla JavaScript.

### What's new

- **Real movie posters** displayed from TMDB's image CDN, with automatic styled placeholders for missing or blocked images.
- **Up to 8,000 searchable movies** when you run the included metadata import. The source is a *historical* TMDB snapshot, mostly movies from 2017 and earlier, **not a continuously updated feed**. Exactly how many movies pass the filters is reported by `/api/meta` after import.
- **Redesigned responsive website** featuring a poster hero, rich cards, search, genre chips, pagination, watchlist and recommendation screens.
- **Movie detail popups** with synopsis, release year, genres, runtime, TMDB community score (out of 10), TMDB link, and similar titles when metadata exists.
- **Same explainable recommender**, now also able to match plot descriptions, taglines and genres. The model uses TF-IDF vectors + cosine similarity. Optional historical MovieLens user ratings add item-based collaborative filtering.
- **No API key, account, or database required** to run the website. Internet is required for *external poster images* and to import the large catalog; small fallback demo works offline.

## Very important: How many movies and pictures will I see?

| Mode | Movies | Posters | Recommendation method |
|---|---:|---|---|
| Offline demo (included) | 257 | 12 known poster links, others use designed placeholders | Content-based |
| Expanded metadata catalog (run import) | Up to 8,000 | Poster links for all imported movies, subject to CDN availability | Content-based, including plots |
| With optional MovieLens ratings | Depends on the catalog | As above | Hybrid content + collaborative filtering |

The expanded metadata is **not shipped inside this ZIP**. Run the import below once or configure it in the Render build command to enable the large catalog. The historical snapshot **does not include recent films past 2017**, except for selected titles in the fallback demo. CineMatch does not claim current-release coverage, ML accuracy, or predicted audience ratings.

## 1. Launch on Windows

1. Extract the ZIP.
2. Open the `CineMatch_Movie_Recommender` folder.
3. Double-click `START_HERE_WINDOWS.bat` (Python 3.10+).
4. Open <http://127.0.0.1:8000>.

At this stage you can already browse 257 movies and see several real posters.

### Expand the catalog locally (recommended)

With the app directory open in PowerShell:

```powershell
# Install packages if you haven't started the app yet
py -3 -m pip install -r requirements.txt

# Download public movie metadata and generate data/catalog.csv
py -3 scripts/prepare_catalog.py --download

# Restart the application
py -3 -m uvicorn app.main:app --reload
```

Or double-click **`EXPAND_CATALOG_WINDOWS.bat`** after installing packages. You can also download `movies_metadata.csv` directly from [The Movies Dataset on Kaggle](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset), then run:

```powershell
py -3 scripts/prepare_catalog.py --input "C:\path\to\movies_metadata.csv"
```

The importer cleans messy rows, validates poster paths and title metadata, filters low-signal records, keeps the most widely rated movies, and writes only the useful fields to `data/catalog.csv`. By default it selects **up to 8,000** titles, not a guaranteed exact total.

**Source is historic:** It is based on *The Movies Dataset* (a TMDB metadata snapshot from 2017). It does not magically add 2026 movies. The included 257-title fallback contains some later films.

## 2. Update your existing GitHub & Render site

**Don't create a second Render service.** Extract this ZIP, copy its *contents* over the files in your existing `CineMatch-Movie-Recommender` repository folder, and overwrite matching files. Preserve the existing `.git` directory.

In PowerShell opened in your existing repository:

```powershell
git add -A
git commit -m "Upgrade CineMatch UI, posters, details and catalog"
git push origin main
```

Your existing Render auto-deploy will update the UI. **To make it load the large catalog**, go to your Render service → **Settings → Build & Deploy → Build Command** and set exactly:

```bash
pip install -r requirements.txt && python scripts/prepare_catalog.py --download
```

Leave **Start Command** as:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Now select **Manual Deploy → Deploy latest commit**. In the Render logs, look for `Created /opt/render/project/src/data/catalog.csv with X movies` (actual directory varies). Once running, `/api/meta` will say `"source":"catalog"` and show your exact count. If the dataset mirror is blocked or unavailable, that build command will fail; download the Kaggle metadata on your own computer, run `prepare_catalog.py --input ...`, commit `data/catalog.csv`, and change the Build Command back to `pip install -r requirements.txt`.

**Alternative:** A `render.yaml` Blueprint is included for a *new* Render service. If you already have one, editing its settings is easier.

The CDN must be reachable from users' browsers for posters to load. A placeholder appears on failed images. No key is needed just to construct CDN image URLs from downloaded poster paths.

## 3. How recommendations work (important for interviews)

1. Each movie gets a text document using its *genres, release decade, plot and tagline* (where available).
2. `TfidfVectorizer` converts these descriptions into weighted numerical feature vectors.
3. `cosine similarity` compares a user's 1–8 liked movies with other films.
4. CineMatch combines closest-match and average-match similarities, ranks other titles and explains the overlapping genres or stories.
5. If you separately enable MovieLens ratings, positive ratings form a sparse movie × user matrix. Shared historical viewers provide a secondary collaborative similarity signal.

**TMDB community rating ≠ MovieLens rating ≠ recommendation score.** TMDB community scores are out of 10 and displayed with the film; MovieLens historical user ratings are out of 5, and the model similarity score only ranks related movies. There is no model-generated rating or fabricated user data.

### Optional historical MovieLens ratings

Read [GroupLens terms](https://grouplens.org/datasets/movielens/) and [latest-small README](https://files.grouplens.org/datasets/movielens/ml-latest-small-README.html) before use. For non-commercial research/educational use, you can run:

```bash
python scripts/download_movielens.py --accept-license
```

When `data/catalog.csv` is present, the project joins MovieLens `links.csv` with TMDB IDs to match ratings to catalog titles. Restart the server after changing datasets. Do **not** commit `data/ml-latest-small/` without reviewing GroupLens distribution terms. Render by default does not download MovieLens.

## 4. Run and test manually

```bash
pip install -r requirements.txt
pip install pytest httpx
python -m pytest -q
uvicorn app.main:app --reload
```

Check <http://127.0.0.1:8000/docs> and <http://127.0.0.1:8000/api/meta>.

**Smoke test:** Browse movies and check poster loading, search `Inception`, click a poster to open details, add 2–3 favorites, select **Find my matches**, then reopen a recommended movie. Try the website on a phone-sized screen as well.

## 5. Code map

```text
app/main.py                   FastAPI routes and JSON validation
app/recommender.py            TF-IDF, cosine similarity, collaborative filtering
app/static/index.html        Site sections and accessible details dialog
app/static/styles.css        Responsive cinema-inspired design
app/static/app.js            Browser state, movie cards, local favorites, detail popups
scripts/prepare_catalog.py   Clean and import historical movie metadata
scripts/download_movielens.py  Optional MovieLens (read its license)
data/demo_movies.csv          257-film fallback; a few known poster links
render.yaml                   Blueprint configuration for a new Render service
Dockerfile                   Optional container deployment
LEARN_THE_PROJECT.md          Beginner study guide
```

**API:** `GET /api/health`, `GET /api/meta`, `GET /api/movies?search=&genre=&offset=&limit=`, `GET /api/movie/{id}`, `POST /api/recommend`.

## 6. Source and rights

The large metadata input comes from [The Movies Dataset by Rounak Banik](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset), credited to TMDB; the source dataset was published under CC0, but imagery and TMDB trademarks have separate rights. No poster artwork is bundled. Image URLs point to [TMDB](https://www.themoviedb.org) and must respect [TMDB's attribution and non-commercial rules](https://developer.themoviedb.org/docs/faq). CineMatch includes the required TMDB logo and notice in the footer. **Do not use film images or TMDB data commercially without verifying licensing.** MovieLens has separate GroupLens terms.

## 7. Resume note

Accurate after you understand the code: “Built a FastAPI movie recommender that uses TF-IDF and cosine similarity to rank films across a cleaned movie metadata catalog, featuring poster-based discovery, search, personalized watchlists, and transparent recommendation explanations.” Don't claim you trained a neural network, fine-tuned a generative model, achieved an accuracy percentage, or use live 2026 catalog updates.
