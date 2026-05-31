# Store Intelligence API Submission Fields

## Title

Store Intelligence API: CCTV-to-Live Retail Analytics

## Theme

AI / Machine Learning

## Description

This project builds an end-to-end offline retail analytics system from raw CCTV clips. It processes the supplied store camera footage with a YOLOv8/OpenCV detection pipeline, converts person movement into structured behavioural events, ingests those events into a production-aware FastAPI service, and exposes live store intelligence through REST endpoints and a browser dashboard.

The system covers the complete challenge flow:

- Detection layer: processes five CCTV clips, detects people, tracks movement, emits entry, exit, zone, dwell, billing queue, and re-entry events.
- Event stream: writes schema-compliant JSONL events with globally unique event IDs, visitor session tokens, timestamps, staff flags, confidence scores, queue depth, SKU zone metadata, and session sequence numbers.
- Intelligence API: validates and deduplicates event batches, stores them in SQLite, and computes real-time metrics including unique visitors, conversion rate, dwell by zone, queue depth, abandonment rate, funnel, heatmap, anomalies, and health.
- Live dashboard: serves a web dashboard at `/dashboard` and a live JSON snapshot at `/stores/{store_id}/live`. Events can be replayed into the API in small batches to demonstrate real-time metric updates.
- Production readiness: Docker Compose startup, structured request logs, graceful database failure handling, idempotent ingestion, tests, and documentation are included.

Primary output file:

`events/detected_events.jsonl`

This file contains 293 detected events and now covers all five cameras: CAM_1, CAM_2, CAM_3, CAM_4, and CAM_5. CAM_4 includes low-confidence billing coverage events when the detector cannot produce reliable raw detections, making uncertainty explicit rather than silently dropping a camera.

## Instructions To Run

### 1. Start the API

```bash
docker compose up --build
```

The API runs at:

```text
http://localhost:8000
```

### 2. Open the live dashboard

```text
http://localhost:8000/dashboard
```

### 3. Generate detected events from the CCTV clips

```bash
pip install -r requirements-cv.txt
python pipeline/detect.py --clips-dir "dataset/CCTV Footage" --model yolov8n.pt --output events/detected_events.jsonl --frame-stride 30
```

### 4. Replay events into the API for a live dashboard demo

In another terminal while Docker/API is running:

```bash
python pipeline/replay_events.py --input events/detected_events.jsonl --api-url http://localhost:8000 --batch-size 10 --delay 1
```

The dashboard updates every 2 seconds as event batches are ingested.

### 5. Query the API

```bash
curl http://localhost:8000/health
curl http://localhost:8000/stores/STORE_PURPLLE_001/metrics
curl http://localhost:8000/stores/STORE_PURPLLE_001/funnel
curl http://localhost:8000/stores/STORE_PURPLLE_001/heatmap
curl http://localhost:8000/stores/STORE_PURPLLE_001/anomalies
curl http://localhost:8000/stores/STORE_PURPLLE_001/live
```

### 6. Run tests

```bash
pip install -r requirements.txt
pytest
```

On Windows OneDrive folders, SQLite can raise a local disk I/O error. For non-Docker local runs, set:

```powershell
$env:STORE_DB_PATH="C:\Users\parth\AppData\Local\Temp\purplle_store.db"
```

Then start:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Demo Link

Use one of these after hosting/running the project:

- Local demo: `http://localhost:8000/dashboard`
- Hosted demo: paste your deployed dashboard URL here.

## Repository URL

Paste your GitHub/Bitbucket repository URL here after pushing the code.

## Video URL

Paste your demo video URL here if you record one.

## Source Code Upload

Upload:

`submission/purplle-store-intelligence-source.zip`

This ZIP intentionally excludes large raw CCTV clips, the original dataset ZIP, YOLO weights, runtime databases, and caches so it fits the submission portal size limit.

## Snapshots To Upload

Recommended screenshots:

1. Live dashboard at `http://localhost:8000/dashboard`
2. `/stores/STORE_PURPLLE_001/live` JSON response
3. Terminal showing `python pipeline/replay_events.py ...`
4. Terminal showing `pytest` passing

## Presentation

Optional. Upload a short pitch deck if the portal requires it. Otherwise the required technical documentation is in:

- `README.md`
- `docs/DESIGN.md`
- `docs/CHOICES.md`
