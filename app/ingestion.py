import sqlite3

from pydantic import ValidationError

from app.models import EventError, IngestResponse, StoreEvent
from app.storage import connect, init_db, insert_event


def ingest_payload(payload: dict) -> IngestResponse:
    init_db()
    raw_events = payload.get("events", [])
    if not isinstance(raw_events, list):
        return IngestResponse(
            accepted=0,
            duplicates=0,
            rejected=1,
            errors=[EventError(index=-1, error="payload.events must be a list")],
        )

    accepted = 0
    duplicates = 0
    errors: list[EventError] = []

    with connect() as conn:
        for index, raw in enumerate(raw_events[:500]):
            try:
                event = StoreEvent.model_validate(raw)
            except ValidationError as exc:
                event_id = raw.get("event_id") if isinstance(raw, dict) else None
                errors.append(EventError(index=index, event_id=event_id, error=str(exc.errors()[0]["msg"])))
                continue
            try:
                if insert_event(conn, event):
                    accepted += 1
                else:
                    duplicates += 1
            except sqlite3.Error as exc:
                errors.append(EventError(index=index, event_id=event.event_id, error=str(exc)))

    overflow = max(0, len(raw_events) - 500)
    for index in range(500, 500 + overflow):
        errors.append(EventError(index=index, error="batch limit is 500 events"))

    return IngestResponse(
        accepted=accepted,
        duplicates=duplicates,
        rejected=len(errors),
        errors=errors,
    )

