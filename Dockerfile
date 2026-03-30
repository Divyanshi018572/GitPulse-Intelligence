# Use a slim, production-ready Python image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user (Hugging Face runs as UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set working directory to user home or stay in /app but fix permissions
WORKDIR /home/user/app

# Copy the entire project code (ensuring the user owns it)
COPY --chown=user . .

# Ensure the .local_cache directory exists and is writable
RUN mkdir -p .local_cache

# Expose the Hugging Face default port
EXPOSE 7860

# Run the FastAPI server using uvicorn on port 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "2"]
