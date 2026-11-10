FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scripts/prepare_catalog.py ./scripts/prepare_catalog.py
COPY data/demo_movies.csv ./data/demo_movies.csv
# Download thousands of titles at build time. Keep the demo as a fallback when offline.
RUN python scripts/prepare_catalog.py --download || echo "Using offline demo catalog"
COPY app ./app
ENV PORT=8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
