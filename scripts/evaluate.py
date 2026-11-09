"""Leakage-aware holdout evaluation for the optional MovieLens data.

Removes each evaluation user's hidden positive rating from the training set,
then tests whether it appears in the top-K recommendations. The goal is a
repeatable learning exercise, not a publishable benchmark.
"""
import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.recommender import MovieRecommender  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate MovieLens hit-rate@K with held-out user ratings")
    parser.add_argument("--users", type=int, default=100, help="Maximum number of users to evaluate")
    parser.add_argument("--k", type=int, default=10, help="Number of movies recommended")
    parser.add_argument("--seed", type=int, default=42, help="Repeatable random split seed")
    args = parser.parse_args()
    if args.users < 1 or args.k < 1 or args.k > 30:
        parser.error("--users must be positive; --k must be between 1 and 30")
    rating_path = ROOT / 'data' / 'ml-latest-small' / 'ratings.csv'
    if not rating_path.is_file():
        parser.error("MovieLens data missing. See README: python scripts/download_movielens.py --accept-license")

    ratings = pd.read_csv(rating_path)
    rng = np.random.default_rng(args.seed)
    positives = ratings[ratings['rating'] >= 4.0]
    candidates = [(user, group['movieId'].astype(int).tolist())
                  for user, group in positives.groupby('userId') if len(group) >= 6]
    rng.shuffle(candidates)
    candidates = candidates[:args.users]

    heldout_indices = []
    cases = []
    for user, movie_ids in candidates:
        target = int(rng.choice(movie_ids))
        # Exclude this user/target observation from model fitting.
        match = ratings.index[(ratings['userId'] == user) &
                              (ratings['movieId'] == target)]
        if len(match) != 1:
            continue
        heldout_indices.append(int(match[0]))
        seeds = [mid for mid in movie_ids if mid != target]
        rng.shuffle(seeds)
        cases.append((seeds[:5], target))

    training = ratings.drop(index=heldout_indices)
    model = MovieRecommender(ROOT / 'data', ratings_override=training)
    if model.collaborative is None:
        parser.error('Could not create a collaborative rating matrix')
    ours = 0
    baseline = 0
    count = 0
    for seeds, target in cases:
        if target not in model.id_to_idx or any(mid not in model.id_to_idx for mid in seeds):
            continue
        choices = {m['id'] for m in model.recommend(seeds, limit=args.k)}
        popular = [int(model.movie_ids[i]) for i in model.popular_order
                   if int(model.movie_ids[i]) not in seeds][:args.k]
        ours += target in choices
        baseline += target in popular
        count += 1
    if count == 0:
        parser.error('No eligible users to evaluate')
    print(f'Evaluation: {count} users, one positive held-out rating per user, top-{args.k}')
    print(f'CineMatch HitRate@{args.k}: {ours/count:.3f} ({ours}/{count})')
    print(f'Popularity HitRate@{args.k}: {baseline/count:.3f} ({baseline}/{count})')
    print('A hit means the held-out liked movie was in the top-K results.')
    print('Note: approximate random holdout, not a time-based or production benchmark.')


if __name__ == '__main__':
    main()
