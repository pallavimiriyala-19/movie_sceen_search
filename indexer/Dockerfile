FROM python:3.11-slim

ARG DEBIAN_FRONTEND=noninteractive

# Install system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ make ca-certificates \
    ffmpeg libsm6 libxext6 libgl1 libglx0 libgles2 \
    libglvnd-dev libdav1d-dev pkg-config wget curl git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /indexer
COPY . /indexer

RUN python -m pip install --upgrade pip setuptools wheel

# Install requirements if present
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt ; fi

# Install ultralytics (YOLOv8)
RUN pip install --no-cache-dir ultralytics==8.*

CMD ["python", "indexer.py"]

