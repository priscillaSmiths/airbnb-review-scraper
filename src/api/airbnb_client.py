from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

log = logging.getLogger(__name__)

@dataclass
class AirbnbConfig:
    base_url: str
    operation_name: str = "PdpReviews"
    locale: str = "en"
    currency: str = "USD"
    headers: Optional[Dict[str, str]] = None
    timeout_seconds: int = 20
    max_retries: int = 3
    retry_backoff_seconds: int = 2

class AirbnbClient:
    """
    Thin wrapper around Airbnb's public PdpReviews endpoint (as used by the web app).
    WARNING: This is an unofficial interface and may change.
    """

    def __init__(self, cfg: AirbnbConfig):
        self.cfg = cfg
        self.session = requests.Session()
        if cfg.headers:
            self.session.headers.update(cfg.headers)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.RequestException,)),
    )
    def fetch_reviews(self, room_id: str, limit: int = 20, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch a page of reviews for a given listing.
        Returns the JSON payload from Airbnb.
        """
        # GraphQL-like query variables used by Airbnb's web app (shape observed; may evolve).
        variables = {
            "request": {
                "fieldSelector": "for_p3",
                "limit": limit,
                "listingId": str(room_id),
                "offset": 0,
                "showingTranslationButton": True,
                "numberOfStars": 0,
                "cursor": cursor,
                "searchType": "PAGINATION",
                "isOrderByMostRelevant": False,
                "language": self.cfg.locale,
            }
        }
        params = {
            "operationName": self.cfg.operation_name,
            "locale": self.cfg.locale,
            "currency": self.cfg.currency,
            "variables": json.dumps(variables, separators=(",", ":")),
        }

        log.debug("Requesting reviews for %s", room_id)
        resp = self.session.get(self.cfg.base_url, params=params, timeout=self.cfg.timeout_seconds)
        resp.raise_for_status()
        return resp.json()