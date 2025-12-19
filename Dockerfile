# Stage 1: Base image with Python
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install Tesseract OCR Engine and other system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Install Playwright's browsers and system dependencies.
RUN playwright install --with-deps

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
