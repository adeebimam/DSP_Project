#!/usr/bin/env bash
# Render build script
# https://render.com/docs/deploy-flask

set -o errexit  # Exit on error

# Install Tesseract OCR engine for receipt scanning
apt-get update && apt-get install -y tesseract-ocr

pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations — add any missing columns to existing tables
python migrate_db.py
