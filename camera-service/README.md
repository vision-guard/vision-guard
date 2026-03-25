# Vision Guard - Camera Service (Mock)

Mock camera service that reads local video files and publishes frames to RabbitMQ, simulating CCTV camera feeds.

## Setup

```bash
cd camera-service
python -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run RabbitMQ

```bash
docker-compose up -d
```

## Add test videos

Place `.mp4` / `.avi` / `.mov` files in a `videos/` folder:

```bash
mkdir videos
# copy sample video files here
```

## Start the service

```bash
uvicorn main:app --reload --port 8001
```

## API Usage

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Service health + active streams |
| `/videos` | GET | List available video files |
| `/stream/{camera_id}?filename=video.mp4` | POST | Start streaming a video |
| `/stop/{camera_id}` | POST | Remove camera from active list |

### Example

```bash
# Start streaming
curl -X POST "http://localhost:8001/stream/cam-1?filename=sample.mp4"

# Check status
curl http://localhost:8001/health
```
