# Learn CineMatch step by step (for a sophomore CS student)

You don't need to know ML before starting. Work through these steps **in this order** and actually change some code. If you cannot explain a line on your resume, don't claim you designed or implemented it yourself.

## Day 1 — Understand the data (30–45 minutes)

Open `data/demo_movies.csv`. Each row is a movie, with an ID, title, and genre list. There are **no user ratings** in this demo. Start the site, search for *Interstellar*, and click `+` to add it. Read the recommendation explanation. Choose *The Notebook* instead; notice how the recommendations change.

**Key idea:** A machine-learning system needs input features. For the offline demo, they are **genres and release decade**, not plot summaries or posters.

## Day 2 — Understand the API (30–45 minutes)

Start the Python server and open `http://127.0.0.1:8000/docs`. Try:

```
GET /api/movies?search=Interstellar
```

Then try the `POST /api/recommend` endpoint with:

```json
{"liked_ids": [1, 2], "limit": 5, "content_weight": 0.65}
```

Trace `app/main.py` to `app/recommender.py`. The website is only a frontend that calls these endpoints. The backend decides the ranking.

## Day 3 — Understand the ML (45–60 minutes)

Read `app/recommender.py` and look for:

- `TfidfVectorizer`: Turns genre words into numeric vectors.
- `normalize`: Changes vectors to length 1 so dot products become cosine similarity.
- `content_sim`: Dot products between selected movies and all candidate movies.
- `np.argsort(-score)`: Sorts movies from highest to lowest ranking score.
- `score[seed_indices] = -np.inf`: Removes already selected movies from recommendations.

**Experiment:** Change `content_score = .55 * ... + .45 * ...` to `.8 * ... + .2 * ...` and compare recommendations from three different favorite films. You're changing how much the best-matching favorite influences the results.

## Day 4 — Understand collaborative filtering (45–60 minutes)

Download the optional MovieLens data using the README instructions. Restart the app. Now `app/recommender.py` loads historical `ratings.csv` and builds a sparse movie-by-user matrix. An entry means a user rated that movie positively. Similar patterns across users increase the collaborative similarity between movies.

Move the **recommendation style** slider to compare genre similarity against audience patterns. Explain why two movies can have different genres but still attract similar audiences.

## Day 5 — Measure the model (30–45 minutes)

Run:

```
python scripts/evaluate.py --users 100 --k 10
```

It removes one positive rating per test user before training and checks whether the held-out movie appears in the top 10. Compare CineMatch to a baseline that just recommends popular movies. This is a basic experiment, **not** a proof that the algorithm is universally better. Do not claim an accuracy number until you actually run this command.

## Day 6 — Make a change of your own

Choose one practical improvement, implement it, and add a test. Ideas:

- Support disliked movies and penalize similar recommendations.
- Add an endpoint that lists the top 10 movies in a selected genre.
- Make a poster placeholder style that visually distinguishes genres.
- Compare a content-only model against the hybrid approach using held-out ratings.

## How to explain CineMatch in an interview

**Question: What did you build?** “A movie recommendation website. It uses the movies a user selects to find similar movies through a machine-learning model.”

**Question: How does it make recommendations?** “I represent each movie using a numeric feature vector from its genres and release decade. Cosine similarity gives a similarity score. With MovieLens data, I combine that with patterns from user ratings.”

**Question: How is this AI?** “It uses classical machine-learning techniques to transform features and rank similar items. It doesn't call a generative AI API or train a neural network.”

**Question: What are the limitations?** “The demo has only manually curated metadata. MovieLens gives historical preferences, not current preferences. With no user favorites, there's no personalized profile. Genre-based matches cannot fully understand plots, themes, or moods.”

**Question: What did YOU build?** Be specific about the code you personally reviewed, changed, tested, and understood. Using AI tools to help produce code doesn't mean you should claim independent design work you haven't done.
