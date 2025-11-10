from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

def _parse_dt(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    # Try multiple formats; return ISO 8601 Z.
    fmts = (
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    )
    for fmt in fmts:
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            continue
    # Fallback: leave as-is
    return value

def sanitize_review(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a single review dict to the required contract.
    """
    reviewer = raw.get("reviewer", {}) or {}
    reviewee = raw.get("reviewee", {}) or {}
    return {
        "comments": (raw.get("comments") or "").strip(),
        "id": str(raw.get("id") or ""),
        "language": raw.get("language") or raw.get("localizedLanguage") or None,
        "createdAt": _parse_dt(raw.get("createdAt") or raw.get("created_at")),
        "reviewee": {
            "firstName": reviewee.get("firstName") or reviewee.get("hostName"),
            "hostName": reviewee.get("hostName") or reviewee.get("firstName"),
            "pictureUrl": reviewee.get("pictureUrl"),
        },
        "reviewer": {
            "firstName": reviewer.get("firstName") or reviewer.get("name"),
            "pictureUrl": reviewer.get("pictureUrl") or reviewer.get("avatarUrl"),
            "localizedReviewerLocation": reviewer.get("localizedReviewerLocation")
            or reviewer.get("location"),
        },
        "rating": raw.get("rating") or raw.get("overallRating"),
        "localizedDate": raw.get("localizedDate"),
    }