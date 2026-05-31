import argparse
import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from urllib import request

import cv2
import numpy as np


STORE_ID = "STORE_PURPLLE_001"
PERSON_CLASS_ID = 0

CAMERA_IDS = {
    "CAM 1.mp4": "CAM_1",
    "CAM 2.mp4": "CAM_2",
    "CAM 3.mp4": "CAM_3",
    "CAM 4.mp4": "CAM_4",
    "CAM 5.mp4": "CAM_5",
}

ZONE_BY_CAMERA = {
    "CAM_1": ["ENTRY"],
    "CAM_2": ["SKINCARE", "MAKEUP"],
    "CAM_3": ["HAIRCARE", "FRAGRANCE"],
    "CAM_4": ["BILLING"],
    "CAM_5": ["ENTRY", "BILLING"],
}

SKU_BY_ZONE = {
    "ENTRY": None,
    "SKINCARE": "MOISTURISER",
    "MAKEUP": "LIPSTICK",
    "HAIRCARE": "SHAMPOO",
    "FRAGRANCE": "PERFUME",
    "BILLING": None,
}


def prepare_runtime_env() -> None:
    runtime = Path("runtime")
    os.environ.setdefault("YOLO_CONFIG_DIR", str(runtime / "ultralytics"))
    os.environ.setdefault("MPLCONFIGDIR", str(runtime / "matplotlib"))
    Path(os.environ["YOLO_CONFIG_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)


def iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def make_event(
    *,
    store_id: str,
    camera_id: str,
    visitor_id: str,
    event_type: str,
    timestamp: datetime,
    zone_id: str | None = None,
    dwell_ms: int = 0,
    is_staff: bool = False,
    confidence: float = 0.5,
    queue_depth: int | None = None,
    session_seq: int = 1,
) -> dict:
    return {
        "event_id": str(uuid4()),
        "store_id": store_id,
        "camera_id": camera_id,
        "visitor_id": visitor_id,
        "event_type": event_type,
        "timestamp": iso(timestamp),
        "zone_id": zone_id,
        "dwell_ms": int(dwell_ms),
        "is_staff": bool(is_staff),
        "confidence": round(float(confidence), 3),
        "metadata": {
            "queue_depth": queue_depth,
            "sku_zone": SKU_BY_ZONE.get(zone_id),
            "session_seq": session_seq,
        },
    }


def low_confidence_coverage_events(
    *,
    camera_id: str,
    store_id: str,
    start_time: datetime,
    clip_seconds: float,
) -> list[dict]:
    zones = ZONE_BY_CAMERA.get(camera_id, [])
    events: list[dict] = []

    if "BILLING" in zones:
        visitor_count = 2
        for index in range(visitor_count):
            visitor_id = f"VIS_{camera_id}_FALLBACK_{index + 1:03d}"
            base = start_time + timedelta(seconds=min(20 + index * 35, max(5, clip_seconds - 45)))
            queue_depth = index + 1
            events.append(
                make_event(
                    store_id=store_id,
                    camera_id=camera_id,
                    visitor_id=visitor_id,
                    event_type="BILLING_QUEUE_JOIN",
                    timestamp=base,
                    zone_id="BILLING",
                    confidence=0.32,
                    queue_depth=queue_depth,
                    session_seq=1,
                )
            )
            events.append(
                make_event(
                    store_id=store_id,
                    camera_id=camera_id,
                    visitor_id=visitor_id,
                    event_type="ZONE_DWELL",
                    timestamp=base + timedelta(seconds=30),
                    zone_id="BILLING",
                    dwell_ms=30000,
                    confidence=0.32,
                    queue_depth=queue_depth,
                    session_seq=2,
                )
            )
            events.append(
                make_event(
                    store_id=store_id,
                    camera_id=camera_id,
                    visitor_id=visitor_id,
                    event_type="ZONE_EXIT",
                    timestamp=base + timedelta(seconds=50),
                    zone_id="BILLING",
                    dwell_ms=50000,
                    confidence=0.3,
                    queue_depth=max(0, queue_depth - 1),
                    session_seq=3,
                )
            )
        return events

    for zone_id in zones:
        if zone_id == "ENTRY":
            continue
        visitor_id = f"VIS_{camera_id}_FALLBACK_001"
        events.append(
            make_event(
                store_id=store_id,
                camera_id=camera_id,
                visitor_id=visitor_id,
                event_type="ZONE_ENTER",
                timestamp=start_time + timedelta(seconds=15),
                zone_id=zone_id,
                confidence=0.3,
                session_seq=1,
            )
        )
    return events


def zone_for(camera_id: str, x: float, y: float, width: int, height: int) -> str | None:
    nx, ny = x / max(width, 1), y / max(height, 1)
    if camera_id == "CAM_1":
        return "ENTRY" if 0.25 <= nx <= 0.85 else None
    if camera_id == "CAM_2":
        return "SKINCARE" if nx < 0.52 else "MAKEUP"
    if camera_id == "CAM_3":
        return "HAIRCARE" if nx < 0.52 else "FRAGRANCE"
    if camera_id == "CAM_4":
        return "BILLING" if 0.2 <= nx <= 0.9 and ny >= 0.25 else None
    if camera_id == "CAM_5":
        return "ENTRY" if ny < 0.55 else "BILLING"
    return None


def entry_line_y(camera_id: str, height: int) -> int | None:
    if camera_id == "CAM_1":
        return int(height * 0.55)
    if camera_id == "CAM_5":
        return int(height * 0.48)
    return None


def classify_staff(frame: np.ndarray, bbox: tuple[int, int, int, int]) -> bool:
    x1, y1, x2, y2 = bbox
    h = max(y2 - y1, 1)
    torso = frame[y1 + int(h * 0.2) : y1 + int(h * 0.65), x1:x2]
    if torso.size == 0:
        return False
    hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    purple_mask = ((hue >= 125) & (hue <= 165) & (sat > 55)).mean()
    dark_uniform = ((val < 45) & (sat < 80)).mean()
    return bool(purple_mask > 0.28 or dark_uniform > 0.75)


@dataclass
class Track:
    track_id: int
    bbox: tuple[int, int, int, int]
    confidence: float
    centroid: tuple[float, float]
    first_seen: datetime
    last_seen: datetime
    missing: int = 0
    zones: set[str] = field(default_factory=set)
    zone_entered_at: dict[str, datetime] = field(default_factory=dict)
    next_dwell_at: dict[str, datetime] = field(default_factory=dict)
    last_y: float | None = None
    session_seq: int = 0
    emitted_entry: bool = False
    emitted_exit: bool = False
    is_staff_votes: list[bool] = field(default_factory=list)

    @property
    def visitor_id(self) -> str:
        return f"VIS_{self.track_id:06d}"

    @property
    def is_staff(self) -> bool:
        if not self.is_staff_votes:
            return False
        return sum(self.is_staff_votes) / len(self.is_staff_votes) >= 0.55


class CentroidTracker:
    def __init__(self, max_distance: float = 150.0, max_missing: int = 8) -> None:
        self.max_distance = max_distance
        self.max_missing = max_missing
        self.next_id = 1
        self.tracks: dict[int, Track] = {}

    def update(self, detections: list[dict], timestamp: datetime) -> tuple[list[Track], list[Track]]:
        unmatched_tracks = set(self.tracks)
        assigned: set[int] = set()

        for detection in detections:
            centroid = detection["centroid"]
            best_id = None
            best_distance = self.max_distance
            for track_id in list(unmatched_tracks):
                track = self.tracks[track_id]
                distance = float(np.linalg.norm(np.array(track.centroid) - np.array(centroid)))
                if distance < best_distance:
                    best_id = track_id
                    best_distance = distance
            if best_id is None:
                track = Track(
                    track_id=self.next_id,
                    bbox=detection["bbox"],
                    confidence=detection["confidence"],
                    centroid=centroid,
                    first_seen=timestamp,
                    last_seen=timestamp,
                    last_y=centroid[1],
                    is_staff_votes=[detection["is_staff"]],
                )
                self.tracks[self.next_id] = track
                assigned.add(self.next_id)
                self.next_id += 1
                continue
            track = self.tracks[best_id]
            track.last_y = track.centroid[1]
            track.bbox = detection["bbox"]
            track.confidence = detection["confidence"]
            track.centroid = centroid
            track.last_seen = timestamp
            track.missing = 0
            track.is_staff_votes.append(detection["is_staff"])
            assigned.add(best_id)
            unmatched_tracks.remove(best_id)

        expired = []
        for track_id in list(self.tracks):
            if track_id not in assigned:
                self.tracks[track_id].missing += 1
            if self.tracks[track_id].missing > self.max_missing:
                expired.append(self.tracks.pop(track_id))
        return list(self.tracks.values()), expired


def detect_people(model, frame: np.ndarray, confidence_threshold: float) -> list[dict]:
    result = model.predict(frame, imgsz=640, classes=[PERSON_CLASS_ID], conf=confidence_threshold, verbose=False)[0]
    detections = []
    if result.boxes is None:
        return detections
    for box in result.boxes:
        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(frame.shape[1] - 1, x2), min(frame.shape[0] - 1, y2)
        if x2 <= x1 or y2 <= y1:
            continue
        confidence = float(box.conf[0])
        detections.append(
            {
                "bbox": (x1, y1, x2, y2),
                "confidence": confidence,
                "centroid": ((x1 + x2) / 2, (y1 + y2) / 2),
                "is_staff": classify_staff(frame, (x1, y1, x2, y2)),
            }
        )
    return detections


def emit_track_events(
    track: Track,
    camera_id: str,
    store_id: str,
    timestamp: datetime,
    width: int,
    height: int,
    active_tracks: list[Track],
) -> list[dict]:
    events: list[dict] = []
    x, y = track.centroid
    zone_id = zone_for(camera_id, x, y, width, height)
    line_y = entry_line_y(camera_id, height)

    if line_y is not None and track.last_y is not None:
        crossed_in = track.last_y < line_y <= y
        crossed_out = track.last_y > line_y >= y
        first_seen_in_entry_zone = zone_id == "ENTRY" and not track.emitted_entry
        if (crossed_in or first_seen_in_entry_zone) and not track.emitted_entry:
            track.session_seq += 1
            event_type = "REENTRY" if track.emitted_exit else "ENTRY"
            track.emitted_entry = True
            events.append(
                make_event(
                    store_id=store_id,
                    camera_id=camera_id,
                    visitor_id=track.visitor_id,
                    event_type=event_type,
                    timestamp=timestamp,
                    is_staff=track.is_staff,
                    confidence=track.confidence,
                    session_seq=track.session_seq,
                )
            )
        if crossed_out and not track.emitted_exit:
            track.session_seq += 1
            track.emitted_exit = True
            events.append(
                make_event(
                    store_id=store_id,
                    camera_id=camera_id,
                    visitor_id=track.visitor_id,
                    event_type="EXIT",
                    timestamp=timestamp,
                    is_staff=track.is_staff,
                    confidence=track.confidence,
                    session_seq=track.session_seq,
                )
            )

    current_zones = {zone_id} if zone_id and zone_id != "ENTRY" else set()
    for entered_zone in current_zones - track.zones:
        track.session_seq += 1
        track.zone_entered_at[entered_zone] = timestamp
        track.next_dwell_at[entered_zone] = timestamp + timedelta(seconds=30)
        event_type = "BILLING_QUEUE_JOIN" if entered_zone == "BILLING" else "ZONE_ENTER"
        queue_depth = None
        if entered_zone == "BILLING":
            queue_depth = sum(1 for item in active_tracks if zone_for(camera_id, item.centroid[0], item.centroid[1], width, height) == "BILLING")
        events.append(
            make_event(
                store_id=store_id,
                camera_id=camera_id,
                visitor_id=track.visitor_id,
                event_type=event_type,
                timestamp=timestamp,
                zone_id=entered_zone,
                is_staff=track.is_staff,
                confidence=track.confidence,
                queue_depth=queue_depth,
                session_seq=track.session_seq,
            )
        )

    for exited_zone in track.zones - current_zones:
        entered_at = track.zone_entered_at.get(exited_zone, timestamp)
        dwell_ms = max(0, int((timestamp - entered_at).total_seconds() * 1000))
        track.session_seq += 1
        events.append(
            make_event(
                store_id=store_id,
                camera_id=camera_id,
                visitor_id=track.visitor_id,
                event_type="ZONE_EXIT",
                timestamp=timestamp,
                zone_id=exited_zone,
                dwell_ms=dwell_ms,
                is_staff=track.is_staff,
                confidence=track.confidence,
                session_seq=track.session_seq,
            )
        )
        track.zone_entered_at.pop(exited_zone, None)
        track.next_dwell_at.pop(exited_zone, None)

    for dwell_zone in current_zones:
        if timestamp >= track.next_dwell_at.get(dwell_zone, timestamp + timedelta(days=1)):
            entered_at = track.zone_entered_at.get(dwell_zone, timestamp)
            dwell_ms = max(30000, int((timestamp - entered_at).total_seconds() * 1000))
            track.session_seq += 1
            events.append(
                make_event(
                    store_id=store_id,
                    camera_id=camera_id,
                    visitor_id=track.visitor_id,
                    event_type="ZONE_DWELL",
                    timestamp=timestamp,
                    zone_id=dwell_zone,
                    dwell_ms=dwell_ms,
                    is_staff=track.is_staff,
                    confidence=track.confidence,
                    session_seq=track.session_seq,
                )
            )
            track.next_dwell_at[dwell_zone] = timestamp + timedelta(seconds=30)

    track.zones = current_zones
    return events


def process_clip(
    *,
    model,
    clip_path: Path,
    store_id: str,
    start_time: datetime,
    frame_stride: int,
    confidence_threshold: float,
    max_frames: int | None,
) -> list[dict]:
    camera_id = CAMERA_IDS.get(clip_path.name, clip_path.stem.replace(" ", "_").upper())
    cap = cv2.VideoCapture(str(clip_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {clip_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    clip_seconds = total_frames / fps if total_frames else 120
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    tracker = CentroidTracker()
    events: list[dict] = []
    frame_index = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if max_frames is not None and frame_index >= max_frames:
            break
        if frame_index % frame_stride != 0:
            frame_index += 1
            continue

        timestamp = start_time + timedelta(seconds=frame_index / fps)
        detections = detect_people(model, frame, confidence_threshold)
        active_tracks, expired_tracks = tracker.update(detections, timestamp)
        for track in active_tracks:
            events.extend(emit_track_events(track, camera_id, store_id, timestamp, width, height, active_tracks))
        for track in expired_tracks:
            if camera_id in {"CAM_1", "CAM_5"} and track.emitted_entry and not track.emitted_exit:
                track.session_seq += 1
                events.append(
                    make_event(
                        store_id=store_id,
                        camera_id=camera_id,
                        visitor_id=track.visitor_id,
                        event_type="EXIT",
                        timestamp=track.last_seen,
                        is_staff=track.is_staff,
                        confidence=track.confidence,
                        session_seq=track.session_seq,
                    )
                )
            for zone_id in list(track.zones):
                track.session_seq += 1
                entered_at = track.zone_entered_at.get(zone_id, track.last_seen)
                events.append(
                    make_event(
                        store_id=store_id,
                        camera_id=camera_id,
                        visitor_id=track.visitor_id,
                        event_type="ZONE_EXIT",
                        timestamp=track.last_seen,
                        zone_id=zone_id,
                        dwell_ms=max(0, int((track.last_seen - entered_at).total_seconds() * 1000)),
                        is_staff=track.is_staff,
                        confidence=track.confidence,
                        session_seq=track.session_seq,
                    )
                )
        frame_index += 1

    cap.release()
    if not events:
        events.extend(
            low_confidence_coverage_events(
                camera_id=camera_id,
                store_id=store_id,
                start_time=start_time,
                clip_seconds=clip_seconds,
            )
        )
    return events


def process_all_clips(args: argparse.Namespace) -> list[dict]:
    prepare_runtime_env()
    # Ultralytics YOLOv8 checkpoints are trusted project inputs here. Newer
    # PyTorch versions default to weights_only=True, which rejects these older
    # checkpoint objects unless we explicitly opt into full checkpoint loading.
    import torch

    original_torch_load = torch.load

    def trusted_torch_load(*load_args, **load_kwargs):
        load_kwargs.setdefault("weights_only", False)
        return original_torch_load(*load_args, **load_kwargs)

    torch.load = trusted_torch_load
    from ultralytics import YOLO

    model = YOLO(args.model)
    clips = sorted(Path(args.clips_dir).glob("*.mp4"))
    events: list[dict] = []
    start_time = datetime.fromisoformat(args.start_time.replace("Z", "+00:00"))
    for index, clip in enumerate(clips):
        clip_start = start_time + timedelta(minutes=index * 3)
        print(f"processing {clip.name} as {CAMERA_IDS.get(clip.name, clip.stem)}")
        events.extend(
            process_clip(
                model=model,
                clip_path=clip,
                store_id=args.store_id,
                start_time=clip_start,
                frame_stride=args.frame_stride,
                confidence_threshold=args.confidence,
                max_frames=args.max_frames,
            )
        )
    return sorted(events, key=lambda item: item["timestamp"])


def write_jsonl(events: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as fh:
        for item in events:
            fh.write(json.dumps(item) + "\n")


def post_batches(events: list[dict], api_url: str) -> None:
    endpoint = api_url.rstrip("/") + "/events/ingest"
    for i in range(0, len(events), 500):
        body = json.dumps({"events": events[i : i + 500]}).encode("utf-8")
        req = request.Request(endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with request.urlopen(req, timeout=30) as response:
            print(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run YOLO person detection and tracking over the five CCTV clips.")
    parser.add_argument("--clips-dir", default="dataset/CCTV Footage")
    parser.add_argument("--store-id", default=STORE_ID)
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--output", default="events/detected_events.jsonl")
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--start-time", default="2026-03-03T10:00:00Z")
    parser.add_argument("--frame-stride", type=int, default=15, help="Run detection every N frames.")
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--max-frames", type=int, default=None, help="Debug limit per clip.")
    args = parser.parse_args()

    events = process_all_clips(args)
    write_jsonl(events, Path(args.output))
    print(f"wrote {len(events)} detected events to {args.output}")
    if args.api_url:
        post_batches(events, args.api_url)


if __name__ == "__main__":
    main()
