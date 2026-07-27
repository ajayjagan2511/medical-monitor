"""
Grand Challenge scraper — public REST API v1.

No authentication required for listing public challenges.
Endpoint: https://grand-challenge.org/api/v1/challenges/
Returns paginated results; filters by keyword in title/description client-side
since the API does not support a server-side search parameter.

Rate note: fetches a single paginated batch per run (up to 100 records)
sorted by most-recently modified to surface new challenges quickly.
"""
import logging
import requests
from datetime import datetime
from typing import List, Optional

from scrapers.base import BaseScraper, DatasetResult
from classifier import classify

logger = logging.getLogger(__name__)

GRANDCHALLENGE_API_URL = "https://grand-challenge.org/api/v1/challenges/"

# Maximum challenges to retrieve per run (API max per page is 100)
_PAGE_SIZE = 100


class GrandChallengeScraper(BaseScraper):
    PLATFORM_NAME = "Grand Challenge"

    def fetch(self, since_date: Optional[datetime] = None) -> List[DatasetResult]:
        results: List[DatasetResult] = []
        keywords_lower = [kw.lower() for kw in self.keywords]

        # Build a lowercase keyword set for fast membership testing
        keyword_set = set(keywords_lower)

        try:
            params = {
                "format": "json",
                "limit": _PAGE_SIZE,
                "offset": 0,
            }

            resp = requests.get(GRANDCHALLENGE_API_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            challenges = data.get("results", [])

            for challenge in challenges:
                slug = challenge.get("slug", "")
                title = challenge.get("title", "") or slug
                description = challenge.get("description", "") or ""
                url = challenge.get("url", f"https://{slug.lower()}.grand-challenge.org/")
                created_str = challenge.get("created", "")
                modified_str = challenge.get("modified", "")
                upload_date = ""

                # Use the more recent of created / modified for date display
                date_str = modified_str or created_str
                if date_str:
                    try:
                        date_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        upload_date = date_dt.strftime("%b %d, %Y")

                        # Date filter — check against since_date
                        naive_dt = date_dt.replace(tzinfo=None)
                        if since_date and naive_dt < since_date:
                            continue
                    except (ValueError, TypeError):
                        pass

                # Client-side keyword filtering on title + description
                combined_text = f"{title} {description}".lower()
                if not any(kw in combined_text for kw in keywords_lower):
                    continue

                cl = classify(f"{title} {description}", self.PLATFORM_NAME)

                results.append(
                    DatasetResult(
                        platform=self.PLATFORM_NAME,
                        dataset_id=f"gc:{slug}",
                        title=title or description[:80],
                        url=url,
                        upload_date=upload_date,
                        data_type=cl.modality,
                        relevance_score=cl.relevance_score,
                    )
                )

        except requests.RequestException as e:
            logger.warning(f"Grand Challenge fetch failed: {e}")
        except Exception as e:
            logger.warning(f"Grand Challenge unexpected error: {e}")

        return self._deduplicate(results)
