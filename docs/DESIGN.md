# Design

## Overview

The system is split into two parts: a five-clip event generation pipeline and a FastAPI intelligence API. The pipeline reads the available `CAM 1.mp4` through `CAM 5.mp4` files from `dataset/CCTV Footage`, assigns each clip a camera identity, and emits schema-compliant behavioral events as JSONL. The API ingests those events, stores them in SQLite, and computes store analytics on demand.

The challenge PDF described a larger dataset containing 5 stores, 3 camera angles each, POS records, layouts, sample events, and assertions. The ZIP provided here contained only five video clips, so I treated those clips as the complete input surface. I added `data/store_layout.json` to define a single store, five camera IDs, and the zones each camera can cover. This keeps the submission runnable and makes the assumptions explicit rather than hiding missing data.

## Pipeline

`pipeline/detect.py` is the primary Part A pipeline. It runs YOLOv8 nano person detection over the five supplied clips, samples frames using a configurable stride, and passes person boxes into a centroid tracker. The tracker keeps a visitor token per active trajectory, maintains zone state, and emits structured events when a trajectory crosses an entry line, enters or exits a mapped zone, remains in a zone long enough to dwell, or joins the billing zone while other tracked customers are present.

`pipeline/generate_events.py` remains as a fallback/demo event generator. It is useful when a machine cannot install CV dependencies, but the real challenge path is `pipeline/detect.py`.

Detected events include `confidence` values from YOLO, staff flags from a simple uniform-color heuristic, session sequence numbers, queue depth, and SKU-zone metadata. Low-confidence rows are preserved instead of dropped, which matches the challenge requirement that uncertain detections should remain visible to downstream systems.

## API

The API uses FastAPI with Pydantic validation at the boundary. Ingestion accepts up to 500 events, validates row by row, deduplicates using `event_id`, and returns partial success if one row is malformed. SQLite is used as the storage engine because it is simple to operate in Docker, easy to inspect, and enough for the five-clip challenge scale. The database is stored under `data/`, which is volume-mounted in Docker Compose.

Metrics are computed from stored events at request time. Staff events are excluded from customer analytics. The funnel uses visitor session tokens rather than raw event counts, so a re-entry event for the same token does not inflate the visitor count. The heatmap normalizes zone visits from 0 to 100 and marks data confidence as low when there are fewer than 20 sessions.

`GET /dashboard` serves a browser dashboard and `GET /stores/{id}/live` returns a compact live snapshot containing metrics, funnel, heatmap, anomalies, and recent events. The dashboard polls the live snapshot every two seconds. For the bonus workflow, `pipeline/replay_events.py` replays a JSONL output file into `/events/ingest` in small delayed batches, so the dashboard visibly updates while the same API endpoints used for scoring receive events.

## Production Readiness

`docker compose up --build` starts the API with no manual service setup. The API logs structured request records with endpoint, method, latency, status code, and trace ID. Ingestion is idempotent by `event_id`. Unexpected persistence failures return a structured 503 response rather than a raw stack trace.

This is now a real computer-vision pipeline, but it is still intentionally lightweight. The main production gaps are stronger re-identification across cameras, calibrated staff classification using labeled uniforms, and camera-specific zone polygons drawn from a real store layout rather than defaults inferred from the five clip names.

The detector also includes a low-confidence coverage fallback for clips that yield no reliable events, especially billing camera views where occlusion can suppress YOLO output. Those fallback rows are not treated as high-quality detections; they exist so missing camera coverage is explicit and downstream metrics can still show uncertainty instead of silently ignoring an input clip.

## AI-Assisted Decisions

1. I used AI to compare whether to make a heavyweight YOLO-based pipeline immediately or a deterministic pipeline that can run in the provided environment. The first scaffold used deterministic events to get the API working. After confirming OpenCV and Ultralytics were available, I upgraded Part A to YOLOv8 plus centroid tracking.

2. I used AI to shape the event schema validation and partial-ingest behavior. I accepted the suggestion to validate each event independently because that matches production ingestion better than failing the whole batch when one event is bad.

3. I used AI to critique the funnel logic. The important correction was that sessions, not raw events, must be counted. That led to set-based stage counts by `visitor_id`, which handles re-entry without double-counting.
