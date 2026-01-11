# ============================================
# Dockerfile for FastAPI + Dapr Application
# ============================================
# This creates a Docker container with your app

# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Copy requirements first (Docker caching optimization)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Expose port 8000 (FastAPI default)
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================
# Build Instructions:
# ============================================
# 
# 1. Build the image:
#    docker build -t dapr-fastapi-demo .
#
# 2. Run with Dapr:
#    dapr run --app-id order-service \
#             --app-port 8000 \
#             --dapr-http-port 3500 \
#             -- docker run -p 8000:8000 dapr-fastapi-demo
#
# ============================================