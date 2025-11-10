from __future__ import annotations

from typing import Any, Dict, List

from .data_cleaner import sanitize_review

def extract_from_airbnb_graphql(room_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract reviews from Airbnb GraphQL PdpReviews response shape.

    Expected shape (simplified):
    {
      "data": {
        "merchandising": {...},
        "presentation": {
          "pdpReviews": {
            "reviews": [ { ... } ],
            "metadata": { ... }
          }
        }
      }
    }
    """
    # Traverse defensively
    presentation = (payload or {}).get("data", {}).get("presentation", {})
    pdp = presentation.get("pdpReviews") or presentation.get("pdpReviewsV2") or {}
    reviews_raw: List[Dict[str, Any]] = pdp.get("reviews") or pdp.get("sections", {}).get("reviews", []) or []
    cleaned = [sanitize_review(r) for r in reviews_raw]
    return {
        "roomid": str(room_id),
        "count": len(cleaned),
        "Reviews": {
            "reviews": cleaned,
        },
    }

def extract_from_mock(room_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Payload is already in target contract (as shipped in sample_output).
    """
    # Use the first item if payload is an array produced by our sample.
    if isinstance(payload, list) and payload:
        obj = payload[0]
        if obj.get("roomid") == str(room_id):
            return obj
    # Fallback to empty bundle
    return {"roomid": str(room_id), "count": 0, "Reviews": {"reviews": []}}