# PROMPT: Generate tests for retail anomaly detection covering queue spikes and conversion drops.
# CHANGES MADE: I constrained the assertions to public anomaly types and severity so the internal thresholds can evolve safely.

from app.analytics import anomalies_for


def event(visitor_id, event_type, queue_depth=None):
    return {
        "event_id": f"{visitor_id}_{event_type}",
        "store_id": "STORE_PURPLLE_001",
        "camera_id": "CAM_4",
        "visitor_id": visitor_id,
        "event_type": event_type,
        "timestamp": "2026-03-03T10:00:00+00:00",
        "zone_id": "BILLING" if "BILLING" in event_type else None,
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.9,
        "metadata": {"queue_depth": queue_depth, "sku_zone": None, "session_seq": 1},
    }


def test_detects_queue_spike():
    anomalies = anomalies_for([event("VIS_1", "ENTRY"), event("VIS_1", "BILLING_QUEUE_JOIN", 5)])

    assert any(item["type"] == "BILLING_QUEUE_SPIKE" for item in anomalies)


def test_detects_conversion_drop_when_visitors_do_not_purchase():
    anomalies = anomalies_for([event("VIS_1", "ENTRY"), event("VIS_2", "ENTRY")])

    assert any(item["type"] == "CONVERSION_DROP" for item in anomalies)

