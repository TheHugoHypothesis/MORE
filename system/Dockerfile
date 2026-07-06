FROM python:3.10-slim

# Install JRE (required by Pellet reasoner via Owlready2) and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre-headless \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the Java Home path to the Debian default symlink
ENV JAVA_HOME=/usr/lib/jvm/default-java

WORKDIR /app

# Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend files
COPY . .

# Create necessary directories for runtime files if they do not exist
RUN mkdir -p models users_subgraph ontology

# Expose Uvicorn/FastAPI port
EXPOSE 8000

# Start the application using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
