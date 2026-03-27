#!/usr/bin/env bash
# Render build script
# https://render.com/docs/deploy-flask

set -o errexit  # Exit on error

pip install --upgrade pip
pip install -r requirements.txt
