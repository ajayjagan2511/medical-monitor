"""
Zenodo scraper — REST API, no auth required for open-access records.

Uses the Zenodo search API with keyword batching to stay within
query-length limits.
"""
import logging
import requests
from datetime import datetime
from typing import List, Optional

from scrapers.base import BaseScraper, DatasetResult
from classifier import classify

logger = logging.getLogger(__name__)

ZENODO_API_URL = "https://zenodo.org/api/records"


class ZenodoScraper(BaseScraper):
    PLATFORM_NAME = "Zenodo"

    # Split keywords into smaller batches to avoid 400 errors
    _BATCH_SIZE = 5

    def fetch(self, since_date: Optional[datetime] = None) -> List[DatasetResult]:
        results: List[DatasetResult] = []

        for i in range(0, len(self.keywords), self._BATCH_SIZE):
            batch = self.keywords[i : i + self._BATCH_SIZE]
            batch_results = self._query_batch(batch, since_date)
            results.extend(batch_results)

        return self._deduplicate(results)

    def _query_batch(
        self, keywords: List[str], since_date: Optional[datetime]
    ) -> List[DatasetResult]:
        """Run a single Zenodo query for a batch of keywords."""
        results: List[DatasetResult] = []

        query_parts = [f'"{kw}"' for kw in keywords]
        query_string = " OR ".join(query_parts)

        try:
            params = {
                "q": query_string,
                "sort": "mostrecent",
                "size": 25,
                "status": "published",
                "resource_type": "dataset",
            }

            resp = requests.get(ZENODO_API_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            for record in data.get("hits", {}).get("hits", []):
                record_id = str(record.get("id", ""))
                metadata = record.get("metadata", {})
                title = metadata.get("title", "Untitled")
                url = record.get("links", {}).get(
                    "self_html",
                    record.get("links", {}).get(
                        "html", f"https://zenodo.org/records/{record_id}"
                    ),
                )
                created_str = record.get("created", "")
                upload_date = ""

                # Date filter + extract human-readable date
                if created_str:
                    try:
                        created_dt = datetime.fromisoformat(
                            created_str.replace("Z", "+00:00")
                        )
                        upload_date = created_dt.strftime("%b %d, %Y")
                        if since_date and created_dt.replace(tzinfo=None) < since_date:
                            continue
                    except (ValueError, TypeError):
                        pass

                # Classify
                cl = classify(title, self.PLATFORM_NAME)

                results.append(
                    DatasetResult(
                        platform=self.PLATFORM_NAME,
                        dataset_id=f"zenodo:{record_id}",
                        title=title,
                        url=url,
                        upload_date=upload_date,
                        data_type=cl.modality,
                        relevance_score=cl.relevance_score,
                    )
                )

        except requests.RequestException as e:
            logger.warning(f"Zenodo batch query failed: {e}")
        except Exception as e:
            logger.warning(f"Zenodo unexpected error: {e}")

        return results
