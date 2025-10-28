#!/usr/bin/env bash
# exit on error
set -o errexit


apt-get install -y tesseract-ocr tesseract-ocr-eng

# After the system package is installed, we install the Python packages.
pip install -r requirements.txt