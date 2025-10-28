#!/usr/bin/env bash
# exit on error
set -o errexit

# Directly install the required system dependencies
apt-get install -y tesseract-ocr tesseract-ocr-eng

# Install Python dependencies from requirements.txt
pip install -r requirements.txt