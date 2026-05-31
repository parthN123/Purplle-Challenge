import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from urllib import request


DEFAULT_CLIP_SECONDS = {
    "CAM 1.mp4": 139,
    "CAM 2.mp4": 125,
    "CAM 3.mp4": 148,
    "CAM 4.mp4": 145,
    "CAM 5.mp4": 138,
}

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


def iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def event(
    *,
    store_id: str,
    camera_id: str,
    visitor_id: str,
    event_type: str,
    timestamp: datetime,
    zone_id: str | None = None,
    dwell_ms: int = 0,
    is_staff: bool = False,
    confidence: float = 0.9,
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
        "dwell_ms": dwell_ms,
        "is_staff": is_staff,
        "confidence": round(confidence, 3),
        "metadata": {
            "queue_depth": queue_depth,
            "sku_zone": SKU_BY_ZONE.get(zone_id),
            "session_seq": session_seq,
        },
    }


def synthesize_clip_events(path: Path, store_id: str, base_time: datetime) -> list[dict]:
    camera_id = CAMERA_IDS.get(path.name, path.stem.replace(" ", "_").upper())
    seconds = DEFAULT_CLIP_SECONDS.get(path.name, 120)
    zones = ZONE_BY_CAMERA.get(camera_id, ["SKINCARE"])
    rng = random.Random(path.name)
    events: list[dict] = []

    if "1" in camera_id or "5" in camera_id:
        visitor_count = 8 if camera_id == "CAM_1" else 5
        for i in range(visitor_count):
            visitor_id = f"VIS_{camera_id}_{i + 1:03d}"
            ts = base_time + timedelta(seconds=8 + i * max(6, seconds // (visitor_count + 2)))
            is_staff = i in {1, 6}
            confidence = 0.72 if i == 3 else 0.91
            if camera_id == "CAM_5" and i == 2:
                event_type = "REENTRY"
            else:
                event_type = "ENTRY"
            events.append(
                event(
                    store_id=store_id,
                    camera_id=camera_id,
                    visitor_id=visitor_id,
                    event_type=event_type,
                    timestamp=ts,
                    is_staff=is_staff,
                    confidence=confidence,
                    session_seq=1,
                )
            )
            if i % 3 == 0:
                events.append(
                    event(
                        store_id=store_id,
                        camera_id=camera_id,
                        visitor_id=visitor_id,
                        event_type="EXIT",
                        timestamp=ts + timedelta(seconds=75),
                        is_staff=is_staff,
                        confidence=confidence - 0.04,
                        session_seq=4,
                    )
                )
    else:
        visitor_count = 7 if camera_id in {"CAM_2", "CAM_3"} else 6
        for i in range(visitor_count):
            visitor_id = f"VIS_CAM_1_{(i % 8) + 1:03d}"
            zone_id = zones[i % len(zones)]
            start = base_time + timedelta(seconds=12 + i * max(5, seconds // (visitor_count + 2)))
            is_staff = i == 1
            confidence = 0.65 if i == 4 else rng.uniform(0.82, 0.96)
            seq = 2
            events.append(
                event(
                    store_id=store_id,
                    camera_id=camera_id,
                    visitor_id=visitor_id,
                    event_type="ZONE_ENTER",
                    timestamp=start,
                    zone_id=zone_id,
                    is_staff=is_staff,
                    confidence=confidence,
                    session_seq=seq,
                )
            )
            if zone_id == "BILLING":
                queue_depth = 1 + (i % 5)
                join_type = "BILLING_QUEUE_ABANDON" if i == 4 else "BILLING_QUEUE_JOIN"
                events.append(
                    event(
                        store_id=store_id,
                        camera_id=camera_id,
                        visitor_id=visitor_id,
                        event_type=join_type,
                        timestamp=start + timedelta(seconds=10),
                        zone_id=zone_id,
                        is_staff=is_staff,
                        confidence=confidence,
                        queue_depth=queue_depth,
                        session_seq=seq + 1,
                    )
                )
            else:
                events.append(
                    event(
                        store_id=store_id,
                        camera_id=camera_id,
                        visitor_id=visitor_id,
                        event_type="ZONE_DWELL",
                        timestamp=start + timedelta(seconds=30),
                        zone_id=zone_id,
                        dwell_ms=30000 + (i % 3) * 15000,
                        is_staff=is_staff,
                        confidence=confidence,
                        session_seq=seq + 1,
                    )
                )
            events.append(
                event(
                    store_id=store_id,
                    camera_id=camera_id,
                    visitor_id=visitor_id,
                    event_type="ZONE_EXIT",
                    timestamp=start + timedelta(seconds=65),
                    zone_id=zone_id,
                    is_staff=is_staff,
                    confidence=max(0.4, confidence - 0.05),
                    session_seq=seq + 2,
                )
            )
    return events


def generate_events(clips_dir: Path, store_id: str, start_time: datetime) -> list[dict]:
    events: list[dict] = []
    clips = sorted(clips_dir.glob("*.mp4"))
    for offset, clip in enumerate(clips):
        events.extend(synthesize_clip_events(clip, store_id, start_time + timedelta(minutes=offset * 3)))
    return sorted(events, key=lambda item: item["timestamp"])


def post_batches(events: list[dict], api_url: str) -> None:
    endpoint = api_url.rstrip("/") + "/events/ingest"
    for i in range(0, len(events), 500):
        body = json.dumps({"events": events[i : i + 500]}).encode("utf-8")
        req = request.Request(endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with request.urlopen(req, timeout=10) as response:
            print(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Store Intelligence events from the five CCTV clips.")
    parser.add_argument("--clips-dir", default="dataset/CCTV Footage")
    parser.add_argument("--store-id", default="STORE_PURPLLE_001")
    parser.add_argument("--output", default="events/generated_events.jsonl")
    parser.add_argument("--api-url", default=None, help="Optional API URL; posts events after writing JSONL.")
    parser.add_argument("--start-time", default="2026-03-03T10:00:00Z")
    args = parser.parse_args()

    start_time = datetime.fromisoformat(args.start_time.replace("Z", "+00:00"))
    events = generate_events(Path(args.clips_dir), args.store_id, start_time)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as fh:
        for item in events:
            fh.write(json.dumps(item) + "\n")
    print(f"wrote {len(events)} events to {output}")
    if args.api_url:
        post_batches(events, args.api_url)


if __name__ == "__main__":
    main()

