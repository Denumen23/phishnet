# Stage 1: Base image with Python
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install Python dependencies
# This is done before copying the rest of the code to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Install Playwright's browsers and system dependencies.
# The --with-deps flag handles the installation of necessary system libraries.
RUN playwright install --with-deps

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
