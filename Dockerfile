# Use slim-bullseye as it's more minimal than slim
FROM python:3.10-slim-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TORCH_CUDA_ARCH_LIST="None" \
    FORCE_CUDA="0"

# Set the working directory
WORKDIR /app

# Install only the essential system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies with specific flags to avoid GPU/CUDA
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt \
    --no-deps sentence-transformers && \
    pip install --no-cache-dir transformers tqdm numpy scikit-learn scipy nltk

# Copy the rest of the application
COPY . .

# Make run.sh executable
RUN chmod +x run.sh

# Expose necessary ports
EXPOSE 8000 4200 8080

# Start the application
CMD ["./run.sh"]