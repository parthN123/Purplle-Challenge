# PROMPT: Generate focused tests for a FastAPI retail intelligence ingest endpoint, covering schema validation, idempotency, and partial success for malformed events.
# CHANGES MADE: I kept the test data small, pinned it to the Purplle 5-clip event schema, and asserted response semantics instead of implementation details.

from datetime import datetime, timezone

from app.ingestion import ingest_payload


def sample_event(event_id: str = "evt_0001") -> dict:
    return {
        "event_id": event_id,
        "store_id": "STORE_PURPLLE_001",
        "camera_id": "CAM_1",
        "visitor_id": "VIS_001",
        "event_type": "ENTRY",
        "timestamp": datetime(2026, 3, 3, 10, 0, tzinfo=timezone.utc).isoformat(),
        "zone_id": None,
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.91,
        "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1},
    }


def test_ingest_accepts_event_and_deduplicates(tmp_path, monkeypatch):
    import app.storage as storage

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")
    import app.ingestion as ingestion

    monkeypatch.setattr(ingestion, "init_db", lambda: storage.init_db(storage.DB_PATH))
    monkeypatch.setattr(ingestion, "connect", lambda: storage.connect(storage.DB_PATH))

    first = ingest_payload({"events": [sample_event()]})
    second = ingest_payload({"events": [sample_event()]})

    assert first.accepted == 1
    assert second.accepted == 0
    assert second.duplicates == 1


def test_ingest_returns_partial_success_for_bad_event(tmp_path, monkeypatch):
    import app.storage as storage

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")
    import app.ingestion as ingestion

    monkeypatch.setattr(ingestion, "init_db", lambda: storage.init_db(storage.DB_PATH))
    monkeypatch.setattr(ingestion, "connect", lambda: storage.connect(storage.DB_PATH))

    bad = sample_event("evt_bad")
    bad["confidence"] = 2.0
    result = ingest_payload({"events": [sample_event("evt_good"), bad]})

    assert result.accepted == 1
    assert result.rejected == 1
    assert result.errors[0].event_id == "evt_bad"
