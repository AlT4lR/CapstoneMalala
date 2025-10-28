# Use an official Python runtime as a parent image
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Grant root access and install system dependencies (Tesseract)
# This is the step that fixes the permission errors
RUN apt-get update && apt-get install -y tesseract-ocr-eng

# Copy the file that lists the Python dependencies
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Tell Render what command to run when the container starts
CMD ["waitress-serve", "--host=0.0.0.0", "--port=10000", "main:app"]