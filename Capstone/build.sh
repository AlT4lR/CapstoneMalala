#!/usr/bin/env bash
# exit on error
set -o errexit

# --- START OF MODIFICATION ---
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng
# --- END OF MODIFICATION ---

# Install Python dependencies from requirements.txt
pip install -r requirements.txt