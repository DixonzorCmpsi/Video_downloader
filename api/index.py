# Ensure the function can import modules from the repo root
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # add project root to sys.path

from app import app  # Flask instance defined in app.py
