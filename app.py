from flask import Flask, request, send_file, jsonify, render_template, after_this_request
import os, io, tempfile, requests, yt_dlp, shutil, glob, mimetypes
from urllib.parse import urlparse, parse_qs
from pytubefix import YouTube
from youtube_transcript_api import YouTubeTranscriptApi

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)



# ---------- helpers ----------
def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None or shutil.which("ffmpeg.exe") is not None

def _final_download_path(ydl, info_dict: dict, temp_dir: str) -> str:
    for d in info_dict.get("requested_downloads", []):
        p = d.get("filepath")
        if p:
            return p
    return ydl.prepare_filename(info_dict)

# ---------- pages ----------
@app.route("/", methods=["GET"])
def index():
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



# ---------- YouTube tools ----------
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
        file_data = io.BytesIO()
        audio_stream.stream_to_buffer(file_data)
        file_data.seek(0)
        title = "".join(c for c in yt.title if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
        return send_file(file_data, as_attachment=True, mimetype="audio/mp3", download_name=f"{title}.mp3")
    except Exception as e:
        print(f"[download_audio] {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/download_video', methods=['GET'])
def download_video():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    try:
        yt = YouTube(video_url)
        video_stream = yt.streams.get_highest_resolution()
        if not video_stream:
            return jsonify({"error": "No video stream found for the provided URL"}), 404
        file_data = io.BytesIO()
        video_stream.stream_to_buffer(file_data)
        file_data.seek(0)
        title = "".join(c for c in yt.title if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
        return send_file(file_data, as_attachment=True, mimetype="video/mp4", download_name=f"{title}.mp4")
    except Exception as e:
        print(f"[download_video] {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/download_thumbnail', methods=['GET'])
def download_thumbnail():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    try:
        yt = YouTube(video_url)
        thumbnail_url = yt.thumbnail_url
        if not thumbnail_url:
            return jsonify({"error": "No thumbnail found for the provided URL"}), 404
        image_data = requests.get(thumbnail_url, timeout=15).content
        return send_file(io.BytesIO(image_data), as_attachment=True, mimetype="image/jpeg",
                         download_name=f"{yt.title}_thumbnail.jpg")
    except Exception as e:
        print(f"[download_thumbnail] {e}")
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
        print(f"[get_transcript] {e}")
        return jsonify({"error": str(e)}), 500

# ---------- Instagram / TikTok ----------
@app.route('/download_insta_video', methods=['GET'])
def download_insta_video():
    insta_url = request.args.get('url')
    if not insta_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    temp_dir = tempfile.mkdtemp()
    try:
        fmt = ("bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
               if _has_ffmpeg() else "best[ext=mp4]/best")
        ydl_opts = {
            "outtmpl": os.path.join(temp_dir, "%(title)s [%(id)s].%(ext)s"),
            "format": fmt, "noplaylist": True, "restrictfilenames": True, "quiet": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(insta_url, download=True)
            final_path = _final_download_path(ydl, info, temp_dir)
        if not os.path.exists(final_path):
            candidates = glob.glob(os.path.join(temp_dir, "*"))
            if not candidates:
                raise FileNotFoundError("Could not find downloaded file.")
            final_path = candidates[0]
        guessed_mime = mimetypes.guess_type(final_path)[0] or "application/octet-stream"

        @after_this_request
        def _cleanup(resp):
            shutil.rmtree(temp_dir, ignore_errors=True)
            return resp

        return send_file(final_path, as_attachment=True,
                         download_name=os.path.basename(final_path), mimetype=guessed_mime)
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"[download_insta_video] {e}")
        return jsonify({"error": f"Failed to download Instagram video: {e}"}), 500

@app.route('/download_tiktok_video', methods=['GET'])
def download_tiktok_video():
    tiktok_url = request.args.get('url')
    if not tiktok_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    temp_dir = tempfile.mkdtemp()
    try:
        fmt = ("bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
               if _has_ffmpeg() else "best[ext=mp4]/best")
        ydl_opts = {
            "outtmpl": os.path.join(temp_dir, "%(title)s [%(id)s].%(ext)s"),
            "format": fmt, "noplaylist": True, "restrictfilenames": True, "quiet": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(tiktok_url, download=True)
            final_path = _final_download_path(ydl, info, temp_dir)
        if not os.path.exists(final_path):
            candidates = glob.glob(os.path.join(temp_dir, "*"))
            if not candidates:
                raise FileNotFoundError("Could not find downloaded file.")
            final_path = candidates[0]
        guessed_mime = mimetypes.guess_type(final_path)[0] or "application/octet-stream"

        @after_this_request
        def _cleanup(resp):
            shutil.rmtree(temp_dir, ignore_errors=True)
            return resp

        return send_file(final_path, as_attachment=True,
                         download_name=os.path.basename(final_path), mimetype=guessed_mime)
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"[download_tiktok_video] {e}")
        return jsonify({"error": f"Failed to download TikTok video: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
