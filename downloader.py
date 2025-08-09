from flask import Flask, request, send_file, jsonify
import os
import io
import tempfile
import requests
from urllib.parse import urlparse, parse_qs
from pytubefix import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import shutil
import glob
import time
from flask import after_this_request
import mimetypes


app = Flask(__name__)

# New HTML template for the main page
# index.html
@app.route('/', methods=['GET'])
def index():
    # Serves the main page with all the tools
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Downloader & Tools</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            padding-top: 80px; /* Add padding to the body to prevent content from being hidden behind the fixed header */
        }
        /* Custom styles for the slide-out menu */
        .slide-in-menu {
            transform: translateX(100%);
            transition: transform 0.3s ease-in-out;
        }
        .slide-in-menu.open {
            transform: translateX(0);
        }
    </style>
</head>
<body class="bg-gray-900 text-white flex flex-col items-center min-h-screen p-4">

    <!-- Header containing the logo and navigation links, fixed to the top -->
    <header class="fixed top-0 left-0 w-full bg-gray-800 shadow-lg z-50 p-4 flex justify-between items-center">
        <!-- Brand name on the left -->
        <a href="/" class="flex items-center">
            <span class="text-2xl font-bold text-white tracking-widest">DeeTalk</span>
        </a>
        <!-- Desktop Navigation Links (hidden on small screens) -->
        <nav class="hidden lg:flex space-x-4">
            <a href="/contact" class="px-4 py-2 bg-gray-700 text-white font-medium rounded-lg hover:bg-gray-600 transition-colors duration-200">Contact</a>
            <a href="/about" class="px-4 py-2 bg-gray-700 text-white font-medium rounded-lg hover:bg-gray-600 transition-colors duration-200">About</a>
        </nav>
        <!-- Responsive Hamburger Menu (Top-Right) -->
        <button id="menu-button" class="p-2 text-white bg-gray-700 rounded-lg lg:hidden">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
            </svg>
        </button>
    </header>
    
    <!-- Slide-in Menu Panel -->
    <div id="menu-panel" class="fixed top-0 right-0 h-full w-64 bg-gray-800 shadow-lg p-6 z-40 slide-in-menu lg:hidden">
        <div class="flex justify-end mb-8">
            <button onclick="toggleMenu()" class="p-2 text-white bg-gray-700 rounded-lg">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
        </div>
        <nav class="flex flex-col space-y-4 text-xl">
            <a href="/" class="block p-2 text-blue-400 rounded-lg hover:bg-gray-700">YouTube Downloader</a>
            <a href="/tiktok" class="block p-2 text-white rounded-lg hover:bg-gray-700">TikTok Downloader</a>
            <a href="/instagram" class="block p-2 text-white rounded-lg hover:bg-gray-700">Instagram Downloader</a>
            <a href="/contact" class="block p-2 text-white rounded-lg hover:bg-gray-700">Contact</a>
            <a href="/about" class="block p-2 text-white rounded-lg hover:bg-gray-700">About</a>
        </nav>
    </div>

    <!-- Main content container -->
    <div class="bg-gray-800 p-12 rounded-2xl shadow-xl max-w-6xl w-full text-center mt-8 flex-grow">
        <h1 class="text-4xl font-bold mb-4">YouTube Downloader & Tools</h1>
        <p class="text-gray-400 mb-8">Enter a YouTube URL below and select an action.</p>
        
        <form id="actionForm" class="flex flex-col space-y-4">
            <input 
                id="urlInput"
                type="text" 
                name="url" 
                placeholder="e.g., https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                class="p-3 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500 text-white transition-colors duration-200"
                required>
            <div class="flex flex-wrap justify-center gap-4">
                <button type="button" onclick="submitForm('/download_audio')" 
                    class="p-3 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 transition-colors duration-200">
                    Download Audio (.m4a)
                </button>
                <button type="button" onclick="submitForm('/download_video')" 
                    class="p-3 bg-green-600 text-white font-bold rounded-lg hover:bg-green-700 transition-colors duration-200">
                    Download Video (.mp4)
                </button>
                <button type="button" onclick="submitForm('/download_thumbnail')" 
                    class="p-3 bg-yellow-600 text-white font-bold rounded-lg hover:bg-yellow-700 transition-colors duration-200">
                    Download Thumbnail
                </button>
            </div>
        </form>

        <div class="mt-8">
            <h2 class="text-2xl font-bold mb-4">Other Tools</h2>
            <div class="flex flex-wrap justify-center gap-4">
                <!-- Buttons to navigate to other pages -->
                <a href="/tiktok" class="p-3 bg-purple-600 text-white font-bold rounded-lg hover:bg-purple-700 transition-colors duration-200">
                    TikTok Downloader
                </a>
                <a href="/instagram" class="p-3 bg-pink-600 text-white font-bold rounded-lg hover:bg-pink-700 transition-colors duration-200">
                    Instagram Downloader
                </a>
            </div>
        </div>

        <!-- Custom message box to replace alert() -->
        <div id="messageBox" class="fixed top-0 left-0 w-full h-full flex items-center justify-center bg-gray-900 bg-opacity-75 z-50 hidden">
            <div class="bg-gray-800 p-6 rounded-lg shadow-xl max-w-sm w-full text-center">
                <p id="messageText" class="text-lg font-semibold mb-4"></p>
                <button onclick="document.getElementById('messageBox').classList.add('hidden')" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors duration-200">
                    OK
                </button>
            </div>
        </div>
    </div>

    <script>
        const menuPanel = document.getElementById('menu-panel');

        function showMessage(message) {
            document.getElementById('messageText').textContent = message;
            document.getElementById('messageBox').classList.remove('hidden');
        }

        function toggleMenu() {
            menuPanel.classList.toggle('open');
        }

        document.getElementById('menu-button').addEventListener('click', toggleMenu);

        async function submitForm(action) {
            const urlInput = document.getElementById('urlInput');

            if (!urlInput.value) {
                showMessage('Please enter a YouTube URL.');
                return;
            }
            
            const url = `${action}?url=${encodeURIComponent(urlInput.value)}`;

            window.location.href = url;
        }
    </script>
</body>
</html>
"""

# New routes for Instagram Downloader
@app.route('/instagram', methods=['GET'])
def instagram_page():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram Downloader</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap" rel="stylesheet">
    <style> 
        body { 
            font-family: 'Inter', sans-serif; 
            padding-top: 80px; /* Add padding to the body to prevent content from being hidden behind the fixed header */
        } 
    </style>
</head>
<body class="bg-gray-900 text-white flex flex-col items-center min-h-screen p-4">

    <!-- Header containing the logo and navigation links, fixed to the top -->
    <header class="fixed top-0 left-0 w-full bg-gray-800 shadow-lg z-50 p-4 flex justify-between items-center">
        <!-- Brand name on the left -->
        <a href="/" class="flex items-center">
            <span class="text-2xl font-bold text-white tracking-widest">DeeTalk</span>
        </a>
        <!-- Desktop Navigation Links (hidden on small screens) -->
        <nav class="hidden lg:flex space-x-4">
            <a href="/contact" class="px-4 py-2 bg-gray-700 text-white font-medium rounded-lg hover:bg-gray-600 transition-colors duration-200">Contact</a>
            <a href="/about" class="px-4 py-2 bg-gray-700 text-white font-medium rounded-lg hover:bg-gray-600 transition-colors duration-200">About</a>
        </nav>
    </header>

    <div class="bg-gray-800 p-12 rounded-2xl shadow-xl max-w-6xl w-full text-center mt-8 flex-grow">
        <h1 class="text-4xl font-bold mb-4">Instagram Downloader</h1>
        <p class="text-gray-400 mb-8">Enter an Instagram URL below to download a reel or post.</p>
        <form id="instaActionForm" class="flex flex-col space-y-4">
            <input 
                id="instaUrlInput"
                type="text" 
                name="url" 
                placeholder="e.g., https://www.instagram.com/p/Cg1t_c3oF2G/"
                class="p-3 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-pink-500 text-white transition-colors duration-200"
                required>
            <div class="flex flex-wrap justify-center gap-4">
                <button type="button" onclick="submitInstaForm('/download_insta_video')" 
                    class="p-3 bg-pink-600 text-white font-bold rounded-lg hover:bg-pink-700 transition-colors duration-200">
                    Download Video/Reel
                </button>
            </div>
        </form>
        <a href="/" class="p-3 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 transition-colors duration-200 mt-8 block">
            Go Back to YouTube Downloader
        </a>
    </div>

    <!-- Custom message box to replace alert() -->
    <div id="messageBox" class="fixed top-0 left-0 w-full h-full flex items-center justify-center bg-gray-900 bg-opacity-75 z-50 hidden">
        <div class="bg-gray-800 p-6 rounded-lg shadow-xl max-w-sm w-full text-center">
            <p id="messageText" class="text-lg font-semibold mb-4"></p>
            <button onclick="document.getElementById('messageBox').classList.add('hidden')" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors duration-200">
                OK
            </button>
        </div>
    </div>

    <script>
        function showMessage(message) {
            document.getElementById('messageText').textContent = message;
            document.getElementById('messageBox').classList.remove('hidden');
        }

        function submitInstaForm(action) {
            const urlInput = document.getElementById('instaUrlInput');
            if (!urlInput.value) {
                showMessage('Please enter an Instagram URL.');
                return;
            }
            window.location.href = `${action}?url=${encodeURIComponent(urlInput.value)}`;
        }
    </script>
</body>
</html>
"""

# New routes for TikTok Downloader
@app.route('/tiktok', methods=['GET'])
def tiktok_page():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TikTok Downloader</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap" rel="stylesheet">
    <style> 
        body { 
            font-family: 'Inter', sans-serif; 
            padding-top: 80px; /* Add padding to the body to prevent content from being hidden behind the fixed header */
        } 
    </style>
</head>
<body class="bg-gray-900 text-white flex flex-col items-center min-h-screen p-4">

    <!-- Header containing the logo and navigation links, fixed to the top -->
    <header class="fixed top-0 left-0 w-full bg-gray-800 shadow-lg z-50 p-4 flex justify-between items-center">
        <!-- Brand name on the left -->
        <a href="/" class="flex items-center">
            <span class="text-2xl font-bold text-white tracking-widest">DeeTalk</span>
        </a>
        <!-- Desktop Navigation Links (hidden on small screens) -->
        <nav class="hidden lg:flex space-x-4">
            <a href="/contact" class="px-4 py-2 bg-gray-700 text-white font-medium rounded-lg hover:bg-gray-600 transition-colors duration-200">Contact</a>
            <a href="/about" class="px-4 py-2 bg-gray-700 text-white font-medium rounded-lg hover:bg-gray-600 transition-colors duration-200">About</a>
        </nav>
    </header>

    <!-- The container below now uses max-w-6xl to match the other pages for consistency. -->
    <div class="bg-gray-800 p-12 rounded-2xl shadow-xl max-w-6xl w-full text-center mt-8 flex-grow">
        <h1 class="text-4xl font-bold mb-4">TikTok Downloader</h1>
        <p class="text-gray-400 mb-8">Enter a TikTok URL below to download a video.</p>
        <form id="tiktokActionForm" class="flex flex-col space-y-4">
            <input 
                id="tiktokUrlInput"
                type="text" 
                name="url" 
                placeholder="e.g., https://www.tiktok.com/@user/video/1234567890123456789"
                class="p-3 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-purple-500 text-white transition-colors duration-200"
                required>
            <div class="flex flex-wrap justify-center gap-4">
                <button type="button" onclick="submitTiktokForm('/download_tiktok_video')" 
                    class="p-3 bg-purple-600 text-white font-bold rounded-lg hover:bg-purple-700 transition-colors duration-200">
                    Download Video
                </button>
            </div>
        </form>
        <a href="/" class="p-3 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 transition-colors duration-200 mt-8 block">
            Go Back to YouTube Downloader
        </a>
    </div>

    <!-- Custom message box to replace alert() -->
    <div id="messageBox" class="fixed top-0 left-0 w-full h-full flex items-center justify-center bg-gray-900 bg-opacity-75 z-50 hidden">
        <div class="bg-gray-800 p-6 rounded-lg shadow-xl max-w-sm w-full text-center">
            <p id="messageText" class="text-lg font-semibold mb-4"></p>
            <button onclick="document.getElementById('messageBox').classList.add('hidden')" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors duration-200">
                OK
            </button>
        </div>
    </div>

    <script>
        function showMessage(message) {
            document.getElementById('messageText').textContent = message;
            document.getElementById('messageBox').classList.remove('hidden');
        }

        function submitTiktokForm(action) {
            const urlInput = document.getElementById('tiktokUrlInput');
            if (!urlInput.value) {
                showMessage('Please enter a TikTok URL.');
                return;
            }
            window.location.href = `${action}?url=${encodeURIComponent(urlInput.value)}`;
        }
    </script>
</body>
</html>
"""

# New route for the About Me page
@app.route('/about', methods=['GET'])
def about():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>About Me</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap" rel="stylesheet">
    <style> 
        body { 
            font-family: 'Inter', sans-serif; 
            padding-top: 80px;
        }
        /* Custom styles for the slide-out menu */
        .slide-in-menu {
            transform: translateX(100%);
            transition: transform 0.3s ease-in-out;
        }
        .slide-in-menu.open {
            transform: translateX(0);
        }
    </style>
</head>
<body class="bg-gray-900 text-white flex flex-col items-center min-h-screen p-4">

    <header class="fixed top-0 left-0 w-full bg-gray-800 shadow-lg z-50 p-4 flex justify-between items-center">
        <a href="/" class="flex items-center">
            <span class="text-2xl font-bold text-white tracking-widest">DeeTalk</span>
        </a>
        <nav class="hidden lg:flex space-x-4">
            <a href="/contact" class="px-4 py-2 bg-gray-700 text-white font-medium rounded-lg hover:bg-gray-600 transition-colors duration-200">Contact</a>
            <a href="/about" class="px-4 py-2 bg-gray-700 text-white font-medium rounded-lg hover:bg-gray-600 transition-colors duration-200">About</a>
        </nav>
        <button id="menu-button" class="p-2 text-white bg-gray-700 rounded-lg lg:hidden">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
            </svg>
        </button>
    </header>
    
    <div id="menu-panel" class="fixed top-0 right-0 h-full w-64 bg-gray-800 shadow-lg p-6 z-40 slide-in-menu lg:hidden">
        <div class="flex justify-end mb-8">
            <button onclick="toggleMenu()" class="p-2 text-white bg-gray-700 rounded-lg">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
        </div>
        <nav class="flex flex-col space-y-4 text-xl">
            <a href="/" class="block p-2 text-blue-400 rounded-lg hover:bg-gray-700">YouTube Downloader</a>
            <a href="/tiktok" class="block p-2 text-white rounded-lg hover:bg-gray-700">TikTok Downloader</a>
            <a href="/instagram" class="block p-2 text-white rounded-lg hover:bg-gray-700">Instagram Downloader</a>
            <a href="/contact" class="block p-2 text-white rounded-lg hover:bg-gray-700">Contact</a>
            <a href="/about" class="block p-2 text-white rounded-lg hover:bg-gray-700">About</a>
        </nav>
    </div>

    <div class="bg-gray-800 p-12 rounded-2xl shadow-xl max-w-6xl w-full text-center mt-8 flex-grow">
        <h1 class="text-4xl font-bold mb-4">About Me</h1>
        <p class="text-gray-400 mb-8 leading-relaxed text-left">
            Hi, My name is Dixon. I am a computer science graduate who currently works at Penn State as an AI Application Specialist. My passion is building software that helps make the mundane a little more manageable. My journey to creating this free tool began out of frustration; I once tried using other downloaders and was bombarded with a sheer amount of crazy ads and even a virus. That's why I created this free, ad-free tool, so others can download content without the risk and hassle I experienced. If you have any suggestions or would like to see more features added, please don't hesitate to reach out!
        </p>
        <a href="/" class="p-3 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 transition-colors duration-200 mt-8 block">
            Go Back to YouTube Downloader
        </a>
    </div>

    <script>
        const menuPanel = document.getElementById('menu-panel');
        function toggleMenu() {
            menuPanel.classList.toggle('open');
        }
        document.getElementById('menu-button').addEventListener('click', toggleMenu);
    </script>
</body>
</html>
"""

# New route for the Contact page
@app.route('/contact', methods=['GET'])
def contact():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contact Me</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap" rel="stylesheet">
    <style> 
        body { 
            font-family: 'Inter', sans-serif; 
            padding-top: 80px;
        }
        /* Custom styles for the slide-out menu */
        .slide-in-menu {
            transform: translateX(100%);
            transition: transform 0.3s ease-in-out;
        }
        .slide-in-menu.open {
            transform: translateX(0);
        }
    </style>
</head>
<body class="bg-gray-900 text-white flex flex-col items-center min-h-screen p-4">

    <header class="fixed top-0 left-0 w-full bg-gray-800 shadow-lg z-50 p-4 flex justify-between items-center">
        <a href="/" class="flex items-center">
            <span class="text-2xl font-bold text-white tracking-widest">DeeTalk</span>
        </a>
        <nav class="hidden lg:flex space-x-4">
            <a href="/contact" class="px-4 py-2 bg-gray-700 text-white font-medium rounded-lg hover:bg-gray-600 transition-colors duration-200">Contact</a>
            <a href="/about" class="px-4 py-2 bg-gray-700 text-white font-medium rounded-lg hover:bg-gray-600 transition-colors duration-200">About</a>
        </nav>
        <button id="menu-button" class="p-2 text-white bg-gray-700 rounded-lg lg:hidden">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
            </svg>
        </button>
    </header>
    
    <div id="menu-panel" class="fixed top-0 right-0 h-full w-64 bg-gray-800 shadow-lg p-6 z-40 slide-in-menu lg:hidden">
        <div class="flex justify-end mb-8">
            <button onclick="toggleMenu()" class="p-2 text-white bg-gray-700 rounded-lg">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
        </div>
        <nav class="flex flex-col space-y-4 text-xl">
            <a href="/" class="block p-2 text-blue-400 rounded-lg hover:bg-gray-700">YouTube Downloader</a>
            <a href="/tiktok" class="block p-2 text-white rounded-lg hover:bg-gray-700">TikTok Downloader</a>
            <a href="/instagram" class="block p-2 text-white rounded-lg hover:bg-gray-700">Instagram Downloader</a>
            <a href="/contact" class="block p-2 text-white rounded-lg hover:bg-gray-700">Contact</a>
            <a href="/about" class="block p-2 text-white rounded-lg hover:bg-gray-700">About</a>
        </nav>
    </div>

    <div class="bg-gray-800 p-12 rounded-2xl shadow-xl max-w-6xl w-full text-center mt-8 flex-grow">
        <h1 class="text-4xl font-bold mb-4">Contact Me</h1>
        <div class="text-left space-y-4">
            <p><strong>Email:</strong> <a href="mailto:dixonfzor@gmail.com" class="text-blue-400 hover:underline">dixonfzor@gmail.com</a></p>
            <p><strong>YouTube Channel:</strong> <a href="https://www.youtube.com/channel/UCD1QlTxgKdpxBvy1zPjND9w" class="text-red-400 hover:underline" target="_blank">Deetalk</a></p>
            <p><strong>LinkedIn:</strong> <a href="https://www.linkedin.com/in/dixon-zor" class="text-blue-500 hover:underline" target="_blank">linkedin.com/in/dixon-zor</a></p>
            <p><strong>GitHub:</strong> <a href="https://github.com/DixonzorCmpsi" class="text-gray-400 hover:underline" target="_blank">github.com/DixonzorCmpsi</a></p>
        </div>
        <a href="/" class="p-3 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 transition-colors duration-200 mt-8 block">
            Go Back to YouTube Downloader
        </a>
    </div>

    <script>
        const menuPanel = document.getElementById('menu-panel');
        function toggleMenu() {
            menuPanel.classList.toggle('open');
        }
        document.getElementById('menu-button').addEventListener('click', toggleMenu);
    </script>
</body>
</html>
"""
def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None or shutil.which("ffmpeg.exe") is not None

def _final_download_path(ydl, info_dict: dict, temp_dir: str) -> str:
    # Prefer paths returned by requested_downloads (when download=True)
    paths = []
    for d in info_dict.get("requested_downloads", []):
        p = d.get("filepath")
        if p: paths.append(p)
    if paths:
        return paths[0]
    # Fallback: yt-dlp's prepared filename
    return ydl.prepare_filename(info_dict)

# YouTube Downloader Routes
@app.route('/download_audio', methods=['GET'])
def download_audio():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    try:
        yt = YouTube(video_url)
        audio_stream = (
            yt.streams.filter(only_audio=True)
            .order_by('abr').desc().first()
        )
        if not audio_stream:
            return jsonify({"error": "No audio stream found for the provided URL"}), 404

        # Download stream data directly into a BytesIO object
        file_data = io.BytesIO()
        audio_stream.stream_to_buffer(file_data)
        file_data.seek(0) # Reset pointer to the beginning of the file

        sanitized_title = "".join(c for c in yt.title if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')

        return send_file(
            file_data,
            as_attachment=True,
            mimetype="audio/mp4",
            download_name=f"{sanitized_title}.mp4"
        )
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

        # Download stream data directly into a BytesIO object
        file_data = io.BytesIO()
        video_stream.stream_to_buffer(file_data)
        file_data.seek(0) # Reset pointer to the beginning of the file

        sanitized_title = "".join(c for c in yt.title if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')

        return send_file(
            file_data,
            as_attachment=True,
            mimetype="video/mp4",
            download_name=f"{sanitized_title}.mp4"
        )
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
        return send_file(
            io.BytesIO(image_data),
            as_attachment=True,
            mimetype="image/jpeg",
            download_name=f"{yt.title}_thumbnail.jpg"
        )
    except Exception as e:
        print(f"[download_thumbnail] {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_transcript', methods=['GET'])
def get_transcript():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    try:
        # Extract video id (handles typical YouTube URL formats)
        video_id = parse_qs(urlparse(video_url).query).get('v', [None])[0]
        if not video_id:
            # support youtu.be/<id> format
            path = urlparse(video_url).path.strip('/')
            video_id = path if path and len(path) >= 8 else None

        if not video_id:
            return jsonify({"error": "Could not extract video ID from the provided URL."}), 400

        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join(entry.get('text', '') for entry in transcript_list if entry.get('text'))
        return jsonify({"transcript": text})
    except Exception as e:
        # Common cases: captions disabled, not available, or rate-limited
        print(f"[get_transcript] {e}")
        return jsonify({"error": str(e)}), 500

# NEW: Instagram Downloader Route
@app.route('/download_insta_video', methods=['GET'])
def download_insta_video():
    insta_url = request.args.get('url')
    if not insta_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    temp_dir = tempfile.mkdtemp()
    try:
        fmt = ("bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
               if _has_ffmpeg() else
               "best[ext=mp4]/best")

        ydl_opts = {
            "outtmpl": os.path.join(temp_dir, "%(title)s [%(id)s].%(ext)s"),
            "format": fmt,
            "noplaylist": True,
            "restrictfilenames": True,
            "quiet": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(insta_url, download=True)
            final_path = _final_download_path(ydl, info, temp_dir)

        if not os.path.exists(final_path):
            # As a last resort, pick whatever landed in the temp dir
            candidates = glob.glob(os.path.join(temp_dir, "*"))
            if not candidates:
                raise FileNotFoundError("Could not find downloaded file.")
            final_path = candidates[0]

        guessed_mime = mimetypes.guess_type(final_path)[0] or "application/octet-stream"

        @after_this_request
        def _cleanup(response):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
            return response

        return send_file(
            final_path,
            as_attachment=True,
            download_name=os.path.basename(final_path),
            mimetype=guessed_mime
        )

    except Exception as e:
        # Make sure to clean up if we error before after_this_request is set
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
               if _has_ffmpeg() else
               "best[ext=mp4]/best")

        ydl_opts = {
            "outtmpl": os.path.join(temp_dir, "%(title)s [%(id)s].%(ext)s"),
            "format": fmt,
            "noplaylist": True,
            "restrictfilenames": True,
            "quiet": True,
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
        def _cleanup(response):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
            return response

        return send_file(
            final_path,
            as_attachment=True,
            download_name=os.path.basename(final_path),
            mimetype=guessed_mime
        )

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"[download_tiktok_video] {e}")
        return jsonify({"error": f"Failed to download TikTok video: {e}"}), 500



if __name__ == '__main__':
    app.run(debug=True)
