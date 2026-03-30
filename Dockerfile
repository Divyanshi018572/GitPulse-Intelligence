# Use a slim, production-ready Python image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Install system dependencies (for building some Python packages if needed)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project code
COPY . .

# Ensure the .local_cache directory exists and is writable
RUN mkdir -p .local_cache && chmod 777 .local_cache

# Expose the FastAPI port
EXPOSE 8000

# Define a volume for the cache
VOLUME ["/app/.local_cache"]

# Run the FastAPI server using uvicorn (2 workers is safer for basic cloud tiers)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
