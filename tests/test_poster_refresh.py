"""Regression tests for popular-film overrides and optional TMDB poster recovery."""
import io
import json
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from app import posters
from app.main import app
from app.recommender import MovieRecommender


def test_poster_override_only_matches_exact_title_and_year(tmp_path: Path):
    # The old path looks valid but is outdated. Demo poster is preferred by title+year.
    demo_src = Path(__file__).resolve().parents[1] / 'data' / 'demo_movies.csv'
    (tmp_path / 'demo_movies.csv').write_bytes(demo_src.read_bytes())
    pd.DataFrame([
        dict(movieId=27205, title='Inception (2010)', genres='Action|Thriller',
             poster_path='/AAAAAAAAAAAAAAAAAAAA.jpg', overview='Dreams have many layers.'),
        dict(movieId=19995, title='Avatar (2009)', genres='Action',
             poster_path='/BBBBBBBBBBBBBBBBBBBB.jpg', overview='Planet of wonders.'),
        dict(movieId=1234, title='Inception (2001)', genres='Drama',
             poster_path='/CCCCCCCCCCCCCCCCCCCC.jpg', overview='Different story.'),
    ]).to_csv(tmp_path / 'catalog.csv', index=False)
    model = MovieRecommender(tmp_path)
    paths = dict(zip(model.movie_ids, model.poster_paths))
    assert paths[27205] == '/xlaY2zyzMfkhk0HSC5VUwzoZPU1.jpg'
    assert paths[19995] == '/kyeqWdyUXW608qlYkRqosgbbJyK.jpg'
    assert paths[1234] == '/CCCCCCCCCCCCCCCCCCCC.jpg'


def test_tmdb_url_format_is_validated():
    assert posters.poster_url('/goodposterfilename00000.jpg', 'w342') == (
        'https://image.tmdb.org/t/p/w342/goodposterfilename00000.jpg')
    assert posters.poster_url('https://example.com/x.jpg') is None
    assert posters.poster_url('//malicious/filename.jpg') is None


def test_tmdb_token_never_returns_to_browser(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"poster_path":"/newposterfilename0000000.jpg"}'

    def fake_urlopen(request, timeout):
        captured['request'] = request
        captured['timeout'] = timeout
        return io.BytesIO(b'{"poster_path":"/newposterfilename0000000.jpg"}')

    monkeypatch.setenv('TMDB_READ_ACCESS_TOKEN', 'super-private-test-token')
    monkeypatch.delenv('TMDB_API_KEY', raising=False)
    monkeypatch.setattr(posters, 'urlopen', fake_urlopen)
    posters.resolve_current_poster.cache_clear()
    assert posters.refreshed_poster(27205) == (
        'https://image.tmdb.org/t/p/w342/newposterfilename0000000.jpg')
    assert captured['request'].get_header('Authorization') == 'Bearer super-private-test-token'
    assert captured['timeout'] == 7


def test_refresh_endpoint_in_demo_mode_rejects_unknown_id():
    client = TestClient(app)
    assert client.get('/api/poster/99999999').status_code == 404
    assert 'poster_refresh_enabled' in client.get('/api/meta').json()
