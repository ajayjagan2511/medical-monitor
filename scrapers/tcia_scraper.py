"""
TCIA (The Cancer Imaging Archive) scraper — Collection Manager REST API v2.

No authentication required for public collections.
Endpoint: https://cancerimagingarchive.net/api/v2/collections/
Supports ?search= for keyword-based filtering (case-insensitive, scans title,
summary, abstract, and programme fields).
"""
import logging
import requests
from datetime import datetime
from typing import List, Optional

from scrapers.base import BaseScraper, DatasetResult
from classifier import classify

logger = logging.getLogger(__name__)

TCIA_API_URL = "https://cancerimagingarchive.net/api/v2/collections/"


class TCIAScraper(BaseScraper):
    PLATFORM_NAME = "TCIA"

    def fetch(self, since_date: Optional[datetime] = None) -> List[DatasetResult]:
        results: List[DatasetResult] = []

        for keyword in self.keywords:
            try:
                # The TCIA v2 Collection Manager supports a ?search= parameter
                params = {
                    "search": keyword,
                    "format": "json",
                }

                resp = requests.get(TCIA_API_URL, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()

                # API returns a list directly or {"results": [...]} depending on version
                collections = data if isinstance(data, list) else data.get("results", [])

                for col in collections:
                    col_id = str(col.get("id", ""))
                    slug = col.get("slug", col_id)
                    title = col.get("collection_title") or col.get("collection_short_title") or slug
                    url = col.get("url", f"https://www.cancerimagingarchive.net/collection/{slug}/")
                    date_updated_str = col.get("date_updated", "")
                    upload_date = ""

                    # Date filter + extract human-readable date
                    if date_updated_str:
                        try:
                            # TCIA dates are "YYYY-MM-DD"
                            updated_dt = datetime.strptime(date_updated_str, "%Y-%m-%d")
                            upload_date = updated_dt.strftime("%b %d, %Y")
                            if since_date and updated_dt < since_date:
                                continue
                        except (ValueError, TypeError):
                            upload_date = date_updated_str

                    # Build a richer description for the classifier using data types
                    data_types = col.get("data_types", [])
                    classify_text = title
                    if data_types and isinstance(data_types, list):
                        classify_text = f"{title} {' '.join(data_types)}"

                    cl = classify(classify_text, self.PLATFORM_NAME)

                    results.append(
                        DatasetResult(
                            platform=self.PLATFORM_NAME,
                            dataset_id=f"tcia:{slug}",
                            title=title,
                            url=url,
                            upload_date=upload_date,
                            data_type=cl.modality,
                            relevance_score=cl.relevance_score,
                        )
                    )

            except requests.RequestException as e:
                logger.warning(f"TCIA keyword '{keyword}' failed: {e}")
                continue
            except Exception as e:
                logger.warning(f"TCIA unexpected error for '{keyword}': {e}")
                continue

        return self._deduplicate(results)
