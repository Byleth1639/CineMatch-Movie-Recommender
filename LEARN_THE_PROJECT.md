# Learn CineMatch in 6 short sessions

You said you want to understand your resume projects instead of just launching them. Follow each task by reading the named source file and trying it yourself.

**Day 1 — What data do I have?** Read `data/demo_movies.csv`, then `scripts/prepare_catalog.py`. Learn `movieId`, genres, a plot, poster path and TMDB vote count. Visit `/api/meta` to see if you're in `demo`, `catalog` or `movielens` mode. The historical metadata snapshot is not a current TMDB feed.

**Day 2 — What is TF-IDF?** Read the corpus and `TfidfVectorizer` lines in `app/recommender.py`. Try comparing the genres of *Inception*, *Interstellar* and *The Notebook*. More distinctive words get larger weights; plot words are useful alongside genres.

**Day 3 — Why cosine similarity?** Find `recommend()` in `app/recommender.py`. It compares sparse vectors without computing every movie-vs-movie pair in advance. Search for `@ self.content.T`. Explain why a Sci-Fi movie tends to rank well for a Sci-Fi favorite.

**Day 4 — What does the backend do?** Read `app/main.py`. The GET endpoints send JSON data. POST `/api/recommend` receives up to eight IDs and validates them. Use `/docs` to make a request and inspect the JSON response.

**Day 5 — How does the UI work?** Read `app/static/app.js`. Trace a + click through `toggle()` and `updateChoices()`, then a recommendation through `recommend()`. Watch how movie details are fetched on demand and how browser `localStorage` remembers picks.

**Day 6 — How do I know it's correct?** Run `python -m pytest -q`. Add a movie and check it is excluded from its own recommendation list. Explain the difference between a TMDB community rating out of 10, an optional MovieLens rating out of 5, and a similarity score that is neither one.

## Five interview questions

1. **Why TF-IDF?** It creates sparse numeric vectors that express how distinctive movie words are, without the complexity of training a neural network.
2. **Why cosine similarity?** It compares vector directions, letting related movies rank together even if their descriptions vary in length.
3. **What is cold start?** You cannot personalize until the viewer selects favorites; content-based filtering can still recommend films with no historical audience ratings.
4. **How does hybrid recommendation work?** Optional MovieLens ratings add a sparse movie/user interaction similarity, blended with plot/genre similarity.
5. **What is a limitation?** The free historical metadata snapshot ends in 2017, and a content-based model may over-recommend similar genres. External poster images can fail to load.

**Practice explaining this:** “The browser sends my chosen movie IDs to FastAPI. The Python model converts the movie metadata into TF-IDF vectors, compares the vectors with cosine similarity, ranks related titles, and returns results with explanations.”
