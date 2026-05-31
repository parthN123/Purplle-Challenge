from collections import Counter, defaultdict
from datetime import datetime, timezone


def customer_events(events: list[dict]) -> list[dict]:
    return [event for event in events if not event["is_staff"]]


def unique_visitors(events: list[dict]) -> set[str]:
    return {event["visitor_id"] for event in customer_events(events)}


def converted_visitors(events: list[dict]) -> set[str]:
    converted: set[str] = set()
    for event in customer_events(events):
        if event["event_type"] == "BILLING_QUEUE_JOIN":
            converted.add(event["visitor_id"])
        if event["event_type"] == "BILLING_QUEUE_ABANDON":
            converted.discard(event["visitor_id"])
    return converted


def metrics_for(events: list[dict]) -> dict:
    customers = customer_events(events)
    visitors = unique_visitors(events)
    converted = converted_visitors(events)
    dwell_by_zone: dict[str, list[int]] = defaultdict(list)
    queue_depth = 0
    abandons = 0
    joins = 0

    for event in customers:
        zone_id = event["zone_id"]
        if event["event_type"] == "ZONE_DWELL" and zone_id:
            dwell_by_zone[zone_id].append(event["dwell_ms"])
        if event["event_type"] == "BILLING_QUEUE_JOIN":
            joins += 1
            queue_depth = max(queue_depth, event["metadata"].get("queue_depth") or 0)
        if event["event_type"] == "BILLING_QUEUE_ABANDON":
            abandons += 1

    avg_dwell = {
        zone: round(sum(values) / len(values), 2)
        for zone, values in sorted(dwell_by_zone.items())
        if values
    }
    return {
        "unique_visitors": len(visitors),
        "converted_visitors": len(converted),
        "conversion_rate": round(len(converted) / len(visitors), 4) if visitors else 0.0,
        "avg_dwell_ms_per_zone": avg_dwell,
        "queue_depth": queue_depth,
        "abandonment_rate": round(abandons / joins, 4) if joins else 0.0,
    }


def funnel_for(events: list[dict]) -> dict:
    stages = {
        "entry": unique_visitors(events),
        "zone_visit": set(),
        "billing_queue": set(),
        "purchase": converted_visitors(events),
    }
    for event in customer_events(events):
        visitor_id = event["visitor_id"]
        if event["event_type"] in {"ENTRY", "REENTRY"}:
            stages["entry"].add(visitor_id)
        if event["event_type"] in {"ZONE_ENTER", "ZONE_DWELL"}:
            stages["zone_visit"].add(visitor_id)
        if event["event_type"] == "BILLING_QUEUE_JOIN":
            stages["billing_queue"].add(visitor_id)

    ordered = ["entry", "zone_visit", "billing_queue", "purchase"]
    previous = None
    result = []
    for name in ordered:
        count = len(stages[name])
        dropoff = 0.0 if previous in (None, 0) else round((previous - count) / previous, 4)
        result.append({"stage": name, "count": count, "dropoff_from_previous": dropoff})
        previous = count
    return {"unit": "visitor_session", "stages": result}


def heatmap_for(events: list[dict]) -> dict:
    visits = Counter()
    dwell: dict[str, list[int]] = defaultdict(list)
    sessions = unique_visitors(events)
    for event in customer_events(events):
        zone_id = event["zone_id"]
        if not zone_id:
            continue
        if event["event_type"] == "ZONE_ENTER":
            visits[zone_id] += 1
        if event["event_type"] == "ZONE_DWELL":
            dwell[zone_id].append(event["dwell_ms"])

    max_visits = max(visits.values(), default=1)
    zones = sorted(set(visits) | set(dwell))
    return {
        "data_confidence": "LOW" if len(sessions) < 20 else "HIGH",
        "zones": [
            {
                "zone_id": zone,
                "visit_count": visits[zone],
                "avg_dwell_ms": round(sum(dwell[zone]) / len(dwell[zone]), 2) if dwell[zone] else 0,
                "intensity": round((visits[zone] / max_visits) * 100, 2),
            }
            for zone in zones
        ],
    }


def anomalies_for(events: list[dict]) -> list[dict]:
    current_metrics = metrics_for(events)
    anomalies = []
    if current_metrics["queue_depth"] >= 4:
        anomalies.append(
            {
                "type": "BILLING_QUEUE_SPIKE",
                "severity": "WARN" if current_metrics["queue_depth"] < 6 else "CRITICAL",
                "suggested_action": "Open another billing counter or move staff to checkout.",
            }
        )
    if current_metrics["unique_visitors"] > 0 and current_metrics["conversion_rate"] < 0.15:
        anomalies.append(
            {
                "type": "CONVERSION_DROP",
                "severity": "WARN",
                "suggested_action": "Check billing wait time and whether staff are engaging high-dwell zones.",
            }
        )
    heatmap = heatmap_for(events)
    for zone in heatmap["zones"]:
        if zone["visit_count"] == 0:
            anomalies.append(
                {
                    "type": "DEAD_ZONE",
                    "severity": "INFO",
                    "suggested_action": f"Review merchandising or camera coverage for {zone['zone_id']}.",
                }
            )
    return anomalies


def health_for(events_by_store: dict[str, list[dict]]) -> dict:
    now = datetime.now(timezone.utc)
    stores = {}
    for store_id, events in events_by_store.items():
        last_ts = max((datetime.fromisoformat(e["timestamp"]) for e in events), default=None)
        lag_seconds = (now - last_ts).total_seconds() if last_ts else None
        stores[store_id] = {
            "last_event_timestamp": last_ts.isoformat() if last_ts else None,
            "status": "STALE_FEED" if lag_seconds is None or lag_seconds > 600 else "OK",
            "lag_seconds": lag_seconds,
        }
    return {"service": "ok", "stores": stores}
