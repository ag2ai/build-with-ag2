FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY agent.py .

# Create coding directory for code execution
RUN mkdir -p coding

# Expose port (if you add a web server later)
EXPOSE 8080

# Run the application
CMD ["python", "agent.py"]
