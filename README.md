# Vision Guard

Vision Guard is a local-only microservices architecture for detecting violence in video streams using deep learning.

## Architecture

- **Camera Service**: Captures video (Webcam/File), streams MJPEG to client, publishes frames to RabbitMQ.
- **Algorithm Service**: Consumes frames, runs PyTorch inference (`UltimateGladiator` model), detects violence, alerts via RabbitMQ. Supports CPU/GPU.
- **Orchestration Service**: Consumes alerts, saves video clips to Minio, metadata to PostgreSQL, provides API.
- **Client**: React/Vite dashboard for live monitoring and incident review.
- **Infrastructure**: RabbitMQ, PostgreSQL, Minio.

## Prerequisites

- Docker & Docker Compose
- NVIDIA GPU (Optional, requires nvidia-container-toolkit)
- `titan_model.pth` weights file

## Setup

1. **Place Model Weights**:
   Put your `titan_model.pth` file in the `algorithm_service/` directory.

2. **Add Video Files (Optional)**:
   If not using a webcam, place your video files (`.mp4`, `.avi`) in `camera_service/videos/`.

3. **Configure Environment**:
   - Update `docker-compose.yml` if needed (e.g., `USE_WEBCAM`, `USE_GPU`).
   - Default: `USE_WEBCAM=False`, `USE_GPU=False`.

4. **Run**:
   ```bash
   docker-compose up --build
   ```

5. **Access**:
   - **Dashboard**: [http://localhost:3000](http://localhost:3000)
   - **Minio Console**: [http://localhost:9001](http://localhost:9001) (User: `minio_user`, Pass: `minio_password`)
   - **RabbitMQ**: [http://localhost:15672](http://localhost:15672) (User: `guest`, Pass: `guest`)

## Hardware Constraints

- **Memory**: Strict limits are applied (Camera: 512MB, Algo: 2.5GB, Orch: 512MB, Client: 256MB).
- **GPU**: Enabled for `algorithm_service` if `USE_GPU=True`. Ensure your host has drivers and `nvidia-container-toolkit` installed.
