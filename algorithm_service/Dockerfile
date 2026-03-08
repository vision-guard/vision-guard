FROM python:3.9-slim

WORKDIR /app

# Install system dependencies (e.g. for OpenCV if needed by cv2-python-headless for reading)
# Although we receive bytes, cv2.imdecode might need libraries.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install PyTorch (default pypi version includes CUDA)
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

CMD ["python", "-u", "-m", "app.main"]
