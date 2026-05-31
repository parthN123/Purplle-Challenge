# PROMPT: Test a five-camera CCTV event generator for schema shape, all-clip coverage, and required event catalogue presence without relying on heavyweight computer vision libraries.
# CHANGES MADE: I made the test create empty .mp4 placeholders because this verifies deterministic event generation logic without copying the large challenge videos.

from datetime import datetime, timezone

from pipeline.generate_events import generate_events
from pipeline.detect import low_confidence_coverage_events, make_event, zone_for


def test_pipeline_generates_schema_events_for_all_five_clips(tmp_path):
    clips = tmp_path / "clips"
    clips.mkdir()
    for index in range(1, 6):
        (clips / f"CAM {index}.mp4").write_bytes(b"")

    events = generate_events(clips, "STORE_PURPLLE_001", datetime(2026, 3, 3, 10, 0, tzinfo=timezone.utc))
    cameras = {event["camera_id"] for event in events}
    event_types = {event["event_type"] for event in events}

    assert cameras == {"CAM_1", "CAM_2", "CAM_3", "CAM_4", "CAM_5"}
    assert {"ENTRY", "ZONE_ENTER", "ZONE_DWELL", "BILLING_QUEUE_JOIN", "REENTRY"}.issubset(event_types)
    assert all(event["event_id"] and event["store_id"] == "STORE_PURPLLE_001" for event in events)


def test_real_detection_helpers_emit_schema_shape():
    event = make_event(
        store_id="STORE_PURPLLE_001",
        camera_id="CAM_4",
        visitor_id="VIS_000001",
        event_type="BILLING_QUEUE_JOIN",
        timestamp=datetime(2026, 3, 3, 10, 0, tzinfo=timezone.utc),
        zone_id="BILLING",
        confidence=0.77,
        queue_depth=3,
        session_seq=2,
    )

    assert event["metadata"]["queue_depth"] == 3
    assert event["confidence"] == 0.77
    assert zone_for("CAM_2", 100, 500, 1000, 1000) == "SKINCARE"


def test_billing_camera_fallback_preserves_cam4_coverage():
    events = low_confidence_coverage_events(
        camera_id="CAM_4",
        store_id="STORE_PURPLLE_001",
        start_time=datetime(2026, 3, 3, 10, 0, tzinfo=timezone.utc),
        clip_seconds=120,
    )

    assert {event["camera_id"] for event in events} == {"CAM_4"}
    assert {"BILLING_QUEUE_JOIN", "ZONE_DWELL", "ZONE_EXIT"}.issubset({event["event_type"] for event in events})
    assert all(event["zone_id"] == "BILLING" for event in events)
