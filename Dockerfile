FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY data/demo_movies.csv ./data/demo_movies.csv
# This image uses the included demo catalog. If you want the full
# MovieLens mode, supply data/ml-latest-small separately under its license.
ENV PORT=8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
