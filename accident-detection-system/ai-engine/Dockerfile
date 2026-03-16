FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxrender1 libxext6 libgl1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install AI/CV dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    ultralytics==8.2.0 \
    opencv-python-headless==4.9.0.80 \
    numpy==1.26.4 \
    kafka-python==2.0.2 \
    aiokafka==0.10.0 \
    structlog==24.1.0 \
    Pillow==10.3.0 \
    torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY . .

RUN mkdir -p /models/weights

# Non-root execution
RUN groupadd -r aiuser && useradd -r -g aiuser aiuser && \
    chown -R aiuser:aiuser /app /models
USER aiuser

CMD ["python", "stream_processor.py"]
