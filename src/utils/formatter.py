from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

def to_pretty_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)

def write_json_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(to_pretty_json(data))

def read_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def validate_inputs(obj: Dict[str, Any]) -> Dict[str, Any]:
    if "roomids" not in obj or not isinstance(obj["roomids"], list) or not obj["roomids"]:
        raise ValueError("Input JSON must contain non-empty 'roomids' array")
    if "limit_per_listing" in obj:
        try:
            obj["limit_per_listing"] = int(obj["limit_per_listing"])
        except Exception:
            obj["limit_per_listing"] = 20
    else:
        obj["limit_per_listing"] = 20
    return obj

def aggregate_results(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Already normalized by extractor; just return.
    return items