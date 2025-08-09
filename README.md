# DeeTalk: Video & Audio Downloader (YouTube • Instagram • TikTok)

Fast, ad-free media downloader built with **Flask + yt-dlp**, packaged with a clean Tailwind UI and deployable to **Vercel** (serverless) or any container host via **Docker**.

Supports:

* **YouTube**: video, audio, thumbnail, transcripts
* **Instagram**: reels/posts video (single-file fallback when FFmpeg isn’t available)
* **TikTok**: video (single-file fallback)

> Please respect platform Terms and creator rights. Download only content you own or have permission to use.

---

## Features

* Minimal **Flask** app with separated **templates** & **static** assets
* **yt-dlp** integration + safe temp cleanup after responses
* **FFmpeg** support for best quality (merges) with no-FFmpeg fallback
* **Serverless-ready** (`/api/index.py` + `vercel.json`)
* **Docker-ready** (Dockerfile + .dockerignore)
* In-memory streaming for YouTube; temp-dir pattern for IG/TikTok

---

## Project Structure

```text
.
├─ app.py                  # Flask app (routes/controllers)
├─ requirements.txt
├─ vercel.json             # Vercel rewrites & function config (serverless)
├─ Dockerfile              # Container image (includes FFmpeg)
├─ .dockerignore
├─ api/
│  └─ index.py             # Exposes Flask app to Vercel (WSGI)
├─ static/
│  └─ app.js               # Shared JS (menu, modal, form handlers)
├─ templates/
│  ├─ base.html            # Shared layout, header, modal, scripts
│  ├─ index.html           # YouTube tools
│  ├─ instagram.html
│  ├─ tiktok.html
│  ├─ about.html
│  └─ contact.html
└─ assets/                 # (optional) screenshots/GIFs for README
```

---

## Quick Start (Local)

```bash
# 1) Create and activate a virtualenv
python -m venv .venv
# Windows PowerShell
. .venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate

# 2) Install deps
pip install --upgrade pip
pip install -r requirements.txt

# 3) (Optional) Install FFmpeg for best merges
# Windows: winget install Gyan.FFmpeg | scoop install ffmpeg | choco install ffmpeg
# macOS:   brew install ffmpeg
# Linux:   sudo apt-get install ffmpeg

# 4) Run
python app.py
# ➜ http://127.0.0.1:5000
```

---

## Run with Docker

Container image includes **FFmpeg**, so merges work out of the box.

```bash
# Build (from repo root; note the trailing dot)
docker build -t deetalk-downloader .

# Run on port 8000
docker run --rm -p 8000:8000 deetalk-downloader
# ➜ http://localhost:8000
```

**Windows note:** Docker Desktop + WSL2 is required. After install, run `docker run hello-world` to verify.

**Ports:** If 8000 is busy, map another: `-p 5050:8000` → [http://localhost:5050](http://localhost:5050)

---

## Deploy (Vercel + GitHub)

1. **Push to GitHub**

   ```bash
   git init -b main
   git add .
   git commit -m "initial commit"
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```
2. **Vercel → New Project → Import Git Repository**
   Vercel detects `api/index.py` (Python WSGI) and installs `requirements.txt`.
   `vercel.json` rewrites all paths (e.g., `/instagram`) to your Flask function.
3. **Open your URL** and test `/`, `/instagram`, `/tiktok`.

> Serverless caveat: long downloads can hit timeouts. This repo sets `"maxDuration": 60` in `vercel.json`. For heavier use, consider a container host (Render/Railway/Fly/Hetzner/VPS).

---

## API Endpoints

All endpoints are `GET` with a `url` query param.

| Path                     | Description                       | Returns               |
| ------------------------ | --------------------------------- | --------------------- |
| `/`                      | UI (YouTube tools)                | HTML                  |
| `/instagram`             | UI (Instagram tools)              | HTML                  |
| `/tiktok`                | UI (TikTok tools)                 | HTML                  |
| `/download_video`        | YouTube video (highest res)       | `video/mp4`           |
| `/download_audio`        | YouTube audio (best)              | `audio/mp4` (m4a)     |
| `/download_thumbnail`    | YouTube thumbnail                 | `image/jpeg`          |
| `/get_transcript`        | YouTube transcript (if available) | JSON `{ transcript }` |
| `/download_insta_video`  | Instagram reel/post video         | `video/*`             |
| `/download_tiktok_video` | TikTok video                      | `video/*`             |

**Under the hood**

* IG/TikTok use `yt-dlp` in a temp dir, then stream the file, cleaning up **after** response via `after_this_request`.
* YouTube uses `pytubefix` and streams to `BytesIO` (no temp files).

---

## Configuration

* **FFmpeg**: optional locally; included in Docker; not present on Vercel by default.
  Code gracefully falls back to single-file MP4 when merges aren’t possible.
* **Private/age-gated content**: typically requires authenticated cookies. (Planned in Roadmap.)

---

## Design Decisions (What reviewers look for)

* **Separation of concerns**: routes vs templates vs client JS.
* **Serverless-friendly**: no long-running state; safe temp deletion after send.
* **Resilience**: format selectors + graceful FFmpeg fallback to avoid merge failures.
* **Minimal surface**: only endpoints needed for the UI; clear error JSON.

---

## Manual Testing

* Try multiple public URLs (short clips first).
* Edge cases:

  * Missing/invalid URL → JSON error
  * IG/TikTok without FFmpeg (on Vercel) → still get MP4 via fallback
  * YouTube with/without transcripts
* (Optional) add `pytest` for helpers like `_has_ffmpeg` and `_final_download_path`.

---

## Security & Compliance

* No persistent user data stored.
* Downloads happen per request; files are cleaned up immediately after response.
* Users are responsible for complying with platform policies and rights.

---

## Roadmap

* [ ] Cookie support for private IG/TikTok (`yt-dlp` `cookiefile` + secure env storage)
* [ ] Instagram **audio-only** endpoint
* [ ] Rate limiting / abuse protection
* [ ] **Docker Compose** dev stack (hot reload)
* [ ] CI (lint/test) + pre-commit hooks (black, isort, flake8)
* [ ] Basic e2e tests against a mock page

---

## Tech Stack

* **Backend**: Flask (WSGI), yt-dlp, pytubefix
* **UI**: Jinja2, Tailwind CSS, vanilla JS
* **Deploy**: Vercel (Python serverless) or Docker (Gunicorn)
* **Media**: FFmpeg (merging/conversion)

---

## Author

**Dixon Zor** — AI Application Specialist @ Penn State

* YouTube: Deetalk
* GitHub: `@DixonzorCmpsi`
* LinkedIn: [https://www.linkedin.com/in/dixon-zor](https://www.linkedin.com/in/dixon-zor)
* Email: [dixonfzor@gmail.com](mailto:dixonfzor@gmail.com)

---

## License

MIT License — add `LICENSE` at repo root.

---

Need a `docker-compose.yml` with hot reload next? I can add a tidy dev stack with volume mounts and `watchfiles` for auto-reload.
