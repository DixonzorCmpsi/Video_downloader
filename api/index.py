# /api/index.py
# Just import and re-expose your Flask app defined in app.py at the project root.
from app import app  # IMPORTANT: `app` must be the Flask instance in app.py
