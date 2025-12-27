"""
WSGI entry point for Eyesy Python Simulator
"""

import os
import sys

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from backend.app import app, socketio

if __name__ == "__main__":
    # This is for when running with gunicorn
    socketio.run(app)