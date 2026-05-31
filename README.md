# Store Intelligence API

This project processes the five supplied CCTV clips and exposes a production-aware Store Intelligence API for ingesting visitor events and querying retail metrics.

## Dataset

The provided ZIP contains only:

- `dataset/CCTV Footage/CAM 1.mp4`
- `dataset/CCTV Footage/CAM 2.mp4`
- `dataset/CCTV Footage/CAM 3.mp4`
- `dataset/CCTV Footage/CAM 4.mp4`
- `dataset/CCTV Footage/CAM 5.mp4`

The problem statement mentioned `store_layout.json`, POS transactions, sample events, and assertions, but those files were not present in this ZIP. I added a small default layout at `data/store_layout.json` and built the pipeline around the five available camera clips.

## Run In 5 Commands

```bash
docker compose up --build
```

In another terminal:

```bash
python pipeline/generate_events.py --clips-dir "dataset/CCTV Footage" --output events/generated_events.jsonl
python pipeline/generate_events.py --clips-dir "dataset/CCTV Footage" --api-url http://localhost:8000
curl http://localhost:8000/stores/STORE_PURPLLE_001/metrics
curl http://localhost:8000/stores/STORE_PURPLLE_001/funnel
```

Open the live dashboard at:

```text
http://localhost:8000/dashboard
```

To show real-time movement on the dashboard, replay the JSONL output into the running API:

```bash
python pipeline/replay_events.py --input events/detected_events.jsonl --api-url http://localhost:8000 --batch-size 10 --delay 1
```

## API

- `POST /events/ingest`: accepts up to 500 events per batch, validates each event, deduplicates by `event_id`, and returns partial success for malformed rows.
- `GET /stores/{id}/metrics`: unique visitors, conversion rate, dwell by zone, queue depth, abandonment rate.
- `GET /stores/{id}/funnel`: Entry to zone visit to billing queue to purchase, counted by visitor session.
- `GET /stores/{id}/heatmap`: normalized zone frequency and dwell data.
- `GET /stores/{id}/anomalies`: active operational anomalies.
- `GET /stores/{id}/live`: dashboard snapshot with metrics, funnel, heatmap, anomalies, and recent events.
- `GET /dashboard`: browser-based live dashboard that polls the API every 2 seconds.
- `GET /health`: service status and stale-feed warnings.

## Detection Pipeline

Primary Part A pipeline:

```bash
pip install -r requirements-cv.txt
python pipeline/detect.py --clips-dir "dataset/CCTV Footage" --model yolov8n.pt --output events/detected_events.jsonl --frame-stride 30
```

This runs YOLOv8 person detection on the five MP4 clips, tracks people with a centroid tracker, infers entry/exit from threshold crossings, maps tracked centroids into camera zones, emits dwell every 30 seconds, estimates billing queue depth, flags likely staff from torso color heuristics, and preserves detection confidence.

If a clip produces no reliable detections, the detector emits low-confidence coverage events for that camera rather than silently dropping the clip. This keeps camera coverage auditable while making uncertainty explicit through the `confidence` field.

For a faster debug pass:

```bash
python pipeline/detect.py --clips-dir "dataset/CCTV Footage" --model yolov8n.pt --output events/detected_events_sample.jsonl --max-frames 1500 --frame-stride 30
```

The lightweight generator remains available as a fallback/demo:

```bash
python pipeline/generate_events.py --clips-dir "dataset/CCTV Footage" --output events/generated_events.jsonl
```

All outputs are JSONL and each line follows the required challenge schema.

## Tests

Run locally after installing requirements:

```bash
pip install -r requirements.txt
pytest
```

The tests cover idempotent ingestion, malformed-event partial success, staff exclusion, conversion rate, re-entry funnel deduplication, heatmap confidence, anomaly detection, and five-clip pipeline coverage.

On Windows OneDrive folders, SQLite may raise a disk I/O error if the database is created inside the synced folder. For local non-Docker runs, set `STORE_DB_PATH` to a temp path:

```powershell
$env:STORE_DB_PATH="C:\Users\parth\AppData\Local\Temp\purplle_store.db"
```
"# Purplle-Challenge" 
