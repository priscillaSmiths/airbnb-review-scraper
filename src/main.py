from __future__ import annotations

import argparse
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table
from rich.progress import track

from utils.formatter import read_json_file, write_json_file, validate_inputs, aggregate_results
from parser.review_extractor import extract_from_airbnb_graphql, extract_from_mock
from api.airbnb_client import AirbnbClient, AirbnbConfig

console = Console()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("airbnb-review-scraper")

def load_settings(path: Path) -> Dict[str, Any]:
    if not path.exists():
        log.warning("Settings file %s not found. Using defaults (mock mode).", path)
        return {}
    try:
        return read_json_file(path)
    except Exception as e:
        log.error("Failed to parse settings: %s", e)
        return {}

def build_client(cfg_dict: Dict[str, Any]) -> Optional[AirbnbClient]:
    airbnb_cfg = cfg_dict.get("airbnb", {}) if cfg_dict else {}
    cfg = AirbnbConfig(
        base_url=airbnb_cfg.get("base_url", "https://www.airbnb.com/api/v3/PdpReviews"),
        operation_name=airbnb_cfg.get("operation_name", "PdpReviews"),
        locale=airbnb_cfg.get("locale", "en"),
        currency=airbnb_cfg.get("currency", "USD"),
        headers=airbnb_cfg.get("headers"),
        timeout_seconds=int(cfg_dict.get("request_timeout_seconds", 20) if cfg_dict else 20),
        max_retries=int(cfg_dict.get("max_retries", 3) if cfg_dict else 3),
        retry_backoff_seconds=int(cfg_dict.get("retry_backoff_seconds", 2) if cfg_dict else 2),
    )
    return AirbnbClient(cfg)

def run_live(room_id: str, limit: int, client: AirbnbClient) -> Dict[str, Any]:
    payload = client.fetch_reviews(room_id, limit=limit)
    return extract_from_airbnb_graphql(room_id, payload)

def run_mock(room_id: str, _limit: int, sample_path: Path) -> Dict[str, Any]:
    try:
        payload = read_json_file(sample_path)
    except Exception:
        payload = []
    return extract_from_mock(room_id, payload)

def render_summary_table(results: List[Dict[str, Any]]) -> None:
    table = Table(title="Airbnb Review Scraper — Summary")
    table.add_column("Room ID", style="cyan", no_wrap=True)
    table.add_column("Review Count", justify="right", style="magenta")
    for item in results:
        table.add_row(str(item["roomid"]), str(item.get("count", 0)))
    console.print(table)

def main() -> None:
    parser = argparse.ArgumentParser(description="Airbnb Review Scraper (unofficial).")
    parser.add_argument(
        "--input",
        type=str,
        default=str(Path(__file__).resolve().parents[1] / "data" / "inputs.sample.json"),
        help="Path to input JSON containing {'roomids': [...], 'limit_per_listing': 20}",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(Path.cwd() / "output.json"),
        help="Where to write the aggregated JSON output.",
    )
    parser.add_argument(
        "--settings",
        type=str,
        default=str(Path(__file__).resolve().parents[0] / "config" / "settings.example.json"),
        help="Path to settings JSON (see settings.example.json).",
    )
    parser.add_argument(
        "--mode",
        choices=["live", "mock"],
        default=None,
        help="Override mode (live or mock). Defaults to settings.mode or 'mock'.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    settings_path = Path(args.settings)

    inputs = validate_inputs(read_json_file(input_path))
    settings = load_settings(settings_path)

    mode = args.mode or settings.get("mode") or "mock"
    concurrency = int(settings.get("concurrency", 5))

    log.info("Mode: %s | Concurrency: %s", mode, concurrency)

    client: Optional[AirbnbClient] = None
    if mode == "live":
        client = build_client(settings)

    tasks = []
    results: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for rid in inputs["roomids"]:
            if mode == "live" and client:
                fut = pool.submit(run_live, rid, inputs["limit_per_listing"], client)
            else:
                sample_path = Path(__file__).resolve().parents[1] / "data" / "sample_output.json"
                fut = pool.submit(run_mock, rid, inputs["limit_per_listing"], sample_path)
            tasks.append(fut)

        for fut in track(as_completed(tasks), total=len(tasks), description="Collecting reviews"):
            try:
                result = fut.result()
                results.append(result)
            except Exception as e:
                log.error("Task failed: %s", e)

    final = aggregate_results(results)
    write_json_file(Path(output_path), final)
    render_summary_table(final)
    console.print(f"[green]Wrote {len(final)} record(s) to[/green] [bold]{output_path}[/bold]")

if __name__ == "__main__":
    main()