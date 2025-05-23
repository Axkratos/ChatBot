# Dockerfile for AI Chatbot Assistant (Streamlit)

# 1. Base image: use official Python slim
FROM python:3.11-slim

# 2. Set environment variables to prevent Python buffering and ensure UTF-8
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# 3. Create and set working directory
WORKDIR /app

# 4. Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl && \
    rm -rf /var/lib/apt/lists/*

# 5. Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copy application code
COPY . /app

# 7. Expose Streamlit port
EXPOSE 8501

# 8. Entrypoint: run Streamlit
ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
