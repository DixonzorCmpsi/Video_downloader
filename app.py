import os
import sys
import io
import glob
import shutil
import tempfile
import mimetypes
import logging

from flask import (
    Flask, request, send_file, jsonify, render_template, after_this_request
)
from urllib.parse import urlparse, parse_qs
import requests
import yt_dlp
from pytubefix import YouTube
from youtube_transcript_api import YouTubeTranscriptApi

# --------------------------
# Flask app + paths
# --------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

# --------------------------
# Logging to stdout (Vercel)
# --------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
app.logger.setLevel(LOG_LEVEL)

@app.before_request
def _log_request():
    app.logger.info("➡️ %s %s", request.method, request.path)

@app.after_request
def _log_response(resp):
    app.logger.info("⬅️ %s %s %s", request.method, request.path, resp.status_code)
    return resp

# Optional: catch-all error logger (keeps JSON consistent for API-ish paths)
@app.errorhandler(Exception)
def _unhandled(e):
    app.logger.exception("Unhandled error")
    # If it looks like an API route (starts with /download_ or /get_), return JSON
    if request.path.startswith(("/download_", "/get_")):
        return jsonify({"error": str(e)}), 500
    # otherwise let Flask show HTML 500
    return ("Internal Server Error", 500)

# --------------------------
# Helpers
# --------------------------
def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None or shutil.which("ffmpeg.exe") is not None

def _final_download_path(ydl, info_dict: dict, temp_dir: str) -> str:
    for d in info_dict.get("requested_downloads", []):
        p = d.get("filepath")
        if p:
            return p
    return ydl.prepare_filename(info_dict)

# --------------------------
# Debug / health
# --------------------------
@app.route("/_health")
def _health():
    return "ok", 200

@app.route("/_debug/templates")
def _debug_templates():
    import pathlib
    p = pathlib.Path(BASE_DIR, "templates")
    listing = [str(x.relative_to(p)) for x in p.rglob("*") if x.is_file()] if p.exists() else []
    return jsonify({
        "base_dir": BASE_DIR,
        "templates_dir_exists": p.exists(),
        "templates": listing
    })

# Silence favicon 404 noise
@app.route("/favicon.ico")
def favicon():
    return ("", 204)

# --------------------------
# Pages
# --------------------------
@app.route("/", methods=["GET"])
def index():
    # If this fails, we’ll see the full traceback in Vercel logs because of @errorhandler above
    return render_template("index.html")

@app.route("/instagram", methods=["GET"])
def instagram_page():
    return render_template("instagram.html")

@app.route("/tiktok", methods=["GET"])
def tiktok_page():
    return render_template("tiktok.html")

@app.route("/about", methods=["GET"])
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET"])
def contact():
    return render_template("contact.html")

# --------------------------
# YouTube tools
# --------------------------
@app.route('/download_audio', methods=['GET'])
def download_audio():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    try:
        yt = YouTube(video_url)
        audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
        if not audio_stream:
            return jsonify({"error": "No audio stream found for the provided URL"}), 404
        buf = io.BytesIO()
        audio_stream.stream_to_buffer(buf)
        buf.seek(0)
        title = "".join(c for c in yt.title if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
        # m4a container (no ffmpeg on Vercel, so do NOT say mp3)
        return send_file(buf, as_attachment=True, mimetype="audio/mp4", download_name=f"{title}.m4a")
    except Exception as e:
        app.logger.exception("download_audio failed")
        return jsonify({"error": str(e)}), 500

@app.route('/download_video', methods=['GET'])
def download_video():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    try:
        yt = YouTube(video_url)
        stream = yt.streams.get_highest_resolution()
        if not stream:
            return jsonify({"error": "No video stream found for the provided URL"}), 404
        buf = io.BytesIO()
        stream.stream_to_buffer(buf)
        buf.seek(0)
        title = "".join(c for c in yt.title if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
        return send_file(buf, as_attachment=True, mimetype="video/mp4", download_name=f"{title}.mp4")
    except Exception as e:
        app.logger.exception("download_video failed")
        return jsonify({"error": str(e)}), 500

@app.route('/download_thumbnail', methods=['GET'])
def download_thumbnail():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    try:
        yt = YouTube(video_url)
        if not yt.thumbnail_url:
            return jsonify({"error": "No thumbnail found for the provided URL"}), 404
        image_data = requests.get(yt.thumbnail_url, timeout=15).content
        filename = "".join(c for c in yt.title if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
        return send_file(io.BytesIO(image_data), as_attachment=True, mimetype="image/jpeg",
                         download_name=f"{filename}_thumbnail.jpg")
    except Exception as e:
        app.logger.exception("download_thumbnail failed")
        return jsonify({"error": str(e)}), 500

@app.route('/get_transcript', methods=['GET'])
def get_transcript():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    try:
        video_id = parse_qs(urlparse(video_url).query).get('v', [None])[0]
        if not video_id:
            path = urlparse(video_url).path.strip('/')
            video_id = path if path and len(path) >= 8 else None
        if not video_id:
            return jsonify({"error": "Could not extract video ID from the provided URL."}), 400
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join(entry.get('text', '') for entry in transcript_list if entry.get('text'))
        return jsonify({"transcript": text})
    except Exception as e:
        app.logger.exception("get_transcript failed")
        return jsonify({"error": str(e)}), 500

# --------------------------
# Instagram / TikTok
# --------------------------
def _dl_with_ytdlp(target_url: str) -> str:
    temp_dir = tempfile.mkdtemp()
    try:
        fmt = ("bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best") if _has_ffmpeg() else "best[ext=mp4]/best"
        ydl_opts = {
            "outtmpl": os.path.join(temp_dir, "%(title)s [%(id)s].%(ext)s"),
            "format": fmt,
            "noplaylist": True,
            "restrictfilenames": True,
            "quiet": True,
            "logger": app.logger,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=True)
            final_path = _final_download_path(ydl, info, temp_dir)
        if not os.path.exists(final_path):
            candidates = glob.glob(os.path.join(temp_dir, "*"))
            if not candidates:
                raise FileNotFoundError("Download completed but file not found.")
            final_path = candidates[0]

        @after_this_request
        def _cleanup(resp):
            shutil.rmtree(temp_dir, ignore_errors=True)
            return resp

        return final_path
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

@app.route('/download_insta_video', methods=['GET'])
def download_insta_video():
    insta_url = request.args.get('url')
    if not insta_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    try:
        final_path = _dl_with_ytdlp(insta_url)
        guessed_mime = mimetypes.guess_type(final_path)[0] or "application/octet-stream"
        return send_file(final_path, as_attachment=True,
                         download_name=os.path.basename(final_path), mimetype=guessed_mime)
    except Exception as e:
        app.logger.exception("download_insta_video failed")
        return jsonify({"error": f"Failed to download Instagram video: {e}"}), 500

@app.route('/download_tiktok_video', methods=['GET'])
def download_tiktok_video():
    tiktok_url = request.args.get('url')
    if not tiktok_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    try:
        final_path = _dl_with_ytdlp(tiktok_url)
        guessed_mime = mimetypes.guess_type(final_path)[0] or "application/octet-stream"
        return send_file(final_path, as_attachment=True,
                         download_name=os.path.basename(final_path), mimetype=guessed_mime)
    except Exception as e:
        app.logger.exception("download_tiktok_video failed")
        return jsonify({"error": f"Failed to download TikTok video: {e}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
