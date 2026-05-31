# Choices

## 1. Detection Model And Pipeline Approach

Options considered: YOLOv8 with ByteTrack, YOLOv8 with a simple centroid tracker, a VLM-based frame classifier, manual OpenCV background subtraction, and a deterministic event-emission pipeline.

AI suggested YOLOv8 plus ByteTrack as the most realistic starting point for people detection and tracking. I agree that ByteTrack is the better production tracker, but for this submission I chose YOLOv8 nano plus a local centroid tracker. That choice keeps the code small enough to explain in follow-up questions while still processing real pixels from the five CCTV clips.

The implemented detector uses `yolov8n.pt` for class `person`, samples every N frames, assigns tracks by nearest centroid, and converts trajectories into business events. The trade-off is that it is less robust than ByteTrack under heavy occlusion and does not perform true appearance-based cross-camera re-identification. The benefit is that it is runnable, transparent, and produces schema-valid events directly from the provided MP4s.

## 2. Event Schema Design

Options considered: store raw detections only, store normalized business events only, or store both detections and events. The challenge required a specific event schema, so I centered the system on normalized business events.

AI suggested keeping confidence and metadata on every event instead of only on detection-specific rows. I accepted that suggestion. Confidence is useful downstream because the API can later expose data-quality indicators, and metadata supports queue depth and SKU-zone context without adding many sparse top-level columns.

I also chose to preserve low-confidence events. Dropping them would make metrics look cleaner but would hide uncertainty. In real retail analytics, low-confidence clips often correspond to occlusion, crowded billing, or camera overlap, which are exactly the conditions operators need to understand.

## 3. API Architecture Choice

Options considered: FastAPI with SQLite, FastAPI with PostgreSQL, and a pure in-memory service. AI suggested PostgreSQL for production realism, especially if 40 stores streamed events continuously. I chose SQLite for this challenge because it keeps `docker compose up` simple, requires no separate database service, and is enough for five short clips.

The API is still structured so storage can be swapped. All persistence is isolated in `app/storage.py`, ingestion in `app/ingestion.py`, and analytics in `app/analytics.py`. If this moved to a real 40-store deployment, the first change would be PostgreSQL with indexed event tables or a stream store. The second change would be pre-aggregated metric tables for high-volume endpoints. For the challenge, computing metrics at request time keeps correctness easy to inspect and test.
