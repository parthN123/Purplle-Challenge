# PROMPT: Create tests for store metrics, funnel, and heatmap calculations using customer, staff, billing, and re-entry events.
# CHANGES MADE: I removed broad fixtures and wrote direct event dictionaries so the expected business calculations are visible in the test.

from app.analytics import funnel_for, heatmap_for, metrics_for


def event(visitor_id, event_type, zone_id=None, dwell_ms=0, is_staff=False, queue_depth=None):
    return {
        "event_id": f"{visitor_id}_{event_type}_{zone_id}",
        "store_id": "STORE_PURPLLE_001",
        "camera_id": "CAM_1",
        "visitor_id": visitor_id,
        "event_type": event_type,
        "timestamp": "2026-03-03T10:00:00+00:00",
        "zone_id": zone_id,
        "dwell_ms": dwell_ms,
        "is_staff": is_staff,
        "confidence": 0.9,
        "metadata": {"queue_depth": queue_depth, "sku_zone": None, "session_seq": 1},
    }


def test_metrics_exclude_staff_and_compute_conversion():
    events = [
        event("VIS_1", "ENTRY"),
        event("VIS_1", "ZONE_DWELL", "SKINCARE", 30000),
        event("VIS_1", "BILLING_QUEUE_JOIN", "BILLING", queue_depth=3),
        event("VIS_2", "ENTRY"),
        event("STAFF_1", "ENTRY", is_staff=True),
        event("STAFF_1", "BILLING_QUEUE_JOIN", "BILLING", is_staff=True, queue_depth=9),
    ]

    metrics = metrics_for(events)

    assert metrics["unique_visitors"] == 2
    assert metrics["converted_visitors"] == 1
    assert metrics["conversion_rate"] == 0.5
    assert metrics["queue_depth"] == 3
    assert metrics["avg_dwell_ms_per_zone"]["SKINCARE"] == 30000


def test_funnel_counts_reentry_once_per_session_token():
    events = [
        event("VIS_1", "ENTRY"),
        event("VIS_1", "REENTRY"),
        event("VIS_1", "ZONE_ENTER", "SKINCARE"),
        event("VIS_1", "BILLING_QUEUE_JOIN", "BILLING", queue_depth=1),
    ]

    funnel = funnel_for(events)

    assert funnel["stages"][0]["count"] == 1
    assert funnel["stages"][3]["count"] == 1


def test_heatmap_marks_low_confidence_when_sessions_are_few():
    heatmap = heatmap_for([event("VIS_1", "ZONE_ENTER", "MAKEUP"), event("VIS_1", "ZONE_DWELL", "MAKEUP", 45000)])

    assert heatmap["data_confidence"] == "LOW"
    assert heatmap["zones"][0]["intensity"] == 100

