#!/usr/bin/env python3
"""
Vercel serverless function entry point
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.api import app

# Export the Flask app for Vercel
app = app
