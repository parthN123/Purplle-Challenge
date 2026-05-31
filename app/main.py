import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse

from app.analytics import anomalies_for, funnel_for, health_for, heatmap_for, metrics_for
from app.ingestion import ingest_payload
from app.storage import connect, fetch_events, fetch_recent_events, init_db


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("store-intelligence")

app = FastAPI(title="Store Intelligence API", version="1.0.0")


DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Store Intelligence Live Dashboard</title>
  <style>
    :root {
      color-scheme: light;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f7f3f8;
      color: #241824;
    }
    body { margin: 0; }
    header {
      background: #72246c;
      color: white;
      padding: 22px 32px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }
    h1 { margin: 0; font-size: 24px; }
    main { max-width: 1180px; margin: 0 auto; padding: 24px; }
    .grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
    .panel {
      background: white;
      border: 1px solid #e6dce7;
      border-radius: 8px;
      padding: 16px;
      box-shadow: 0 8px 24px rgba(80, 35, 76, 0.08);
    }
    .label { color: #6f6070; font-size: 13px; margin-bottom: 6px; }
    .value { font-size: 30px; font-weight: 750; }
    .wide { grid-column: span 2; }
    .full { grid-column: 1 / -1; }
    .bar { height: 10px; border-radius: 999px; background: #eadfea; overflow: hidden; margin-top: 8px; }
    .fill { height: 100%; background: #8c2c83; width: 0%; transition: width .25s ease; }
    table { width: 100%; border-collapse: collapse; font-size: 14px; }
    th, td { text-align: left; padding: 9px 8px; border-bottom: 1px solid #eee5ef; }
    th { color: #6f6070; font-weight: 650; }
    .status { font-size: 13px; opacity: .9; }
    .pill { display: inline-block; border-radius: 999px; padding: 4px 8px; background: #f0e3f0; color: #72246c; }
    @media (max-width: 860px) {
      header { align-items: flex-start; flex-direction: column; padding: 18px; }
      main { padding: 16px; }
      .grid { grid-template-columns: 1fr; }
      .wide, .full { grid-column: auto; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Store Intelligence Live Dashboard</h1>
      <div class="status">STORE_PURPLLE_001 · refreshes every 2 seconds</div>
    </div>
    <div id="lastUpdated" class="status">Waiting for events...</div>
  </header>
  <main>
    <section class="grid">
      <div class="panel"><div class="label">Unique visitors</div><div id="visitors" class="value">0</div></div>
      <div class="panel"><div class="label">Conversion rate</div><div id="conversion" class="value">0%</div></div>
      <div class="panel"><div class="label">Queue depth</div><div id="queue" class="value">0</div></div>
      <div class="panel"><div class="label">Abandonment</div><div id="abandonment" class="value">0%</div></div>
      <div class="panel wide">
        <div class="label">Funnel</div>
        <div id="funnel"></div>
      </div>
      <div class="panel wide">
        <div class="label">Heatmap zones</div>
        <div id="heatmap"></div>
      </div>
      <div class="panel full">
        <div class="label">Recent event stream</div>
        <table>
          <thead><tr><th>Received</th><th>Camera</th><th>Visitor</th><th>Type</th><th>Zone</th><th>Confidence</th></tr></thead>
          <tbody id="events"></tbody>
        </table>
      </div>
    </section>
  </main>
  <script>
    const storeId = "STORE_PURPLLE_001";
    const pct = value => `${Math.round((value || 0) * 100)}%`;

    function renderBars(target, rows, labelKey, valueKey) {
      target.innerHTML = rows.map(row => {
        const label = row[labelKey];
        const value = Number(row[valueKey] || 0);
        return `<div style="margin:10px 0"><span class="pill">${label}</span> ${value}<div class="bar"><div class="fill" style="width:${Math.min(100, value)}%"></div></div></div>`;
      }).join("") || "<p>No zone data yet.</p>";
    }

    async function refresh() {
      const res = await fetch(`/stores/${storeId}/live`);
      const data = await res.json();
      const m = data.metrics;
      document.getElementById("visitors").textContent = m.unique_visitors;
      document.getElementById("conversion").textContent = pct(m.conversion_rate);
      document.getElementById("queue").textContent = m.queue_depth;
      document.getElementById("abandonment").textContent = pct(m.abandonment_rate);
      document.getElementById("lastUpdated").textContent = `Last update ${new Date().toLocaleTimeString()}`;
      renderBars(document.getElementById("funnel"), data.funnel.stages, "stage", "count");
      renderBars(document.getElementById("heatmap"), data.heatmap.zones, "zone_id", "intensity");
      document.getElementById("events").innerHTML = data.recent_events.map(event => `
        <tr>
          <td>${new Date(event.received_at).toLocaleTimeString()}</td>
          <td>${event.camera_id}</td>
          <td>${event.visitor_id}</td>
          <td>${event.event_type}</td>
          <td>${event.zone_id || ""}</td>
          <td>${Number(event.confidence).toFixed(2)}</td>
        </tr>
      `).join("");
    }

    refresh();
    setInterval(refresh, 2000);
  </script>
</body>
</html>
"""


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.middleware("http")
async def structured_logging(request: Request, call_next):
    trace_id = request.headers.get("x-trace-id", str(uuid4()))
    start = time.perf_counter()
    status_code = 500
    try:
        response: Response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            {
                "trace_id": trace_id,
                "store_id": request.path_params.get("store_id"),
                "endpoint": request.url.path,
                "method": request.method,
                "latency_ms": latency_ms,
                "event_count": getattr(request.state, "event_count", None),
                "status_code": status_code,
            }
        )


@app.post("/events/ingest")
async def ingest(request: Request):
    payload = await request.json()
    raw_events = payload.get("events", []) if isinstance(payload, dict) else []
    request.state.event_count = len(raw_events) if isinstance(raw_events, list) else None
    try:
        return ingest_payload(payload)
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"error": "STORE_UNAVAILABLE", "message": "Unable to persist events right now."},
        )


@app.get("/stores/{store_id}/metrics")
def store_metrics(store_id: str):
    with connect() as conn:
        return metrics_for(fetch_events(conn, store_id))


@app.get("/stores/{store_id}/funnel")
def store_funnel(store_id: str):
    with connect() as conn:
        return funnel_for(fetch_events(conn, store_id))


@app.get("/stores/{store_id}/heatmap")
def store_heatmap(store_id: str):
    with connect() as conn:
        return heatmap_for(fetch_events(conn, store_id))


@app.get("/stores/{store_id}/anomalies")
def store_anomalies(store_id: str):
    with connect() as conn:
        return {"anomalies": anomalies_for(fetch_events(conn, store_id))}


@app.get("/stores/{store_id}/live")
def store_live_snapshot(store_id: str):
    with connect() as conn:
        events = fetch_events(conn, store_id)
        recent = fetch_recent_events(conn, store_id, limit=15)
    return {
        "store_id": store_id,
        "metrics": metrics_for(events),
        "funnel": funnel_for(events),
        "heatmap": heatmap_for(events),
        "anomalies": anomalies_for(events),
        "recent_events": recent,
    }


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return DASHBOARD_HTML


@app.get("/health")
def health():
    with connect() as conn:
        rows = conn.execute("SELECT DISTINCT store_id FROM events").fetchall()
        by_store = {row["store_id"]: fetch_events(conn, row["store_id"]) for row in rows}
    return health_for(by_store)
