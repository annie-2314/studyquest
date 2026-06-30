# StudyQuest AI — backend (FastAPI + WebSockets)
FROM python:3.12-slim

# System libs some wheels expect at runtime (PyMuPDF, etc.) stay minimal.
WORKDIR /app

# Install deps first for layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
# $PORT is honored on hosts like Render; defaults to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
