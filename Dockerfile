FROM python:3.11-slim

WORKDIR /app

# Install required system packages
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libssl-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy source files
COPY requirements.txt ./
COPY scripts/fetch_articles.py ./
COPY scripts/utils.py ./
COPY docs/ ./docs/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "fetch_articles.py"]
