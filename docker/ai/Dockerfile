FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY ai/inference/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY ai/ /app/ai/

# Environment defaults
ENV FLASK_ENV=production \
    FLASK_PORT=5001 \
    FLASK_DEBUG=0 \
    MODEL_PATH=/app/ai/checkpoints/aihub/best.pth \
    MODEL_BACKBONE=densenet121 \
    DATA_CSV=/app/ai/preprocessing/processed_aihub/train.csv \
    DEVICE=auto

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5001/health')" || exit 1

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5001", "--chdir", "/app/ai/inference", "app:create_app()"]
