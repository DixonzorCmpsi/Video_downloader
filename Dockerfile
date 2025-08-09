# Small, fast base
FROM python:3.11-slim

# Safe defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps (FFmpeg enables best merges for yt-dlp)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
 && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Install Python deps first for better layer caching
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# App code (templates/static included)
COPY . .

# Non-root user
RUN useradd -m app && chown -R app:app /app
USER app

# Gunicorn web server
EXPOSE 8000
CMD ["gunicorn", "-w", "2", "-k", "gthread", "--threads", "8", "-b", "0.0.0.0:8000", "app:app"]
