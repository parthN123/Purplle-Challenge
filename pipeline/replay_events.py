import argparse
import json
import time
from pathlib import Path
from urllib import request


def post_batch(api_url: str, events: list[dict]) -> None:
    endpoint = api_url.rstrip("/") + "/events/ingest"
    body = json.dumps({"events": events}).encode("utf-8")
    req = request.Request(endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=10) as response:
        print(response.read().decode("utf-8"))


def replay_events(input_path: Path, api_url: str, delay_seconds: float, batch_size: int) -> None:
    batch: list[dict] = []
    with input_path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            batch.append(json.loads(line))
            if len(batch) >= batch_size:
                post_batch(api_url, batch)
                batch = []
                time.sleep(delay_seconds)
        if batch:
            post_batch(api_url, batch)


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay JSONL events into the API for live dashboard demos.")
    parser.add_argument("--input", default="events/detected_events.jsonl")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between batches in seconds.")
    parser.add_argument("--batch-size", type=int, default=10)
    args = parser.parse_args()

    replay_events(Path(args.input), args.api_url, args.delay, args.batch_size)


if __name__ == "__main__":
    main()
