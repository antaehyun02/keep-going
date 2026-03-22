#!/bin/bash
# SkinAI Flask AI Service — Production
cd "$(dirname "$0")"
gunicorn -w 2 -b 0.0.0.0:${FLASK_PORT:-5001} "app:create_app()"
