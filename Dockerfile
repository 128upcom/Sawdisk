FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    file \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy workspace
COPY workspace/ /app/workspace/

# Create necessary directories
RUN mkdir -p /app/data /app/logs

# Set default command
CMD ["python", "-c", "import sys; print(sys.version)"]

