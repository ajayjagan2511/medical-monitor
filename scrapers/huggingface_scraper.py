"""
Hugging Face scraper — REST API, no auth required for public datasets.
"""
import logging
import requests
from datetime import datetime
from typing import List, Optional

from scrapers.base import BaseScraper, DatasetResult
from config import MAX_RESULTS_PER_KEYWORD
from classifier import classify

logger = logging.getLogger(__name__)

HF_API_URL = "https://huggingface.co/api/datasets"


class HuggingFaceScraper(BaseScraper):
    PLATFORM_NAME = "Hugging Face"

    def fetch(self, since_date: Optional[datetime] = None) -> List[DatasetResult]:
        results: List[DatasetResult] = []

        for keyword in self.keywords:
            try:
                params = {
                    "search": keyword,
                    "sort": "createdAt",
                    "direction": "-1",
                    "limit": MAX_RESULTS_PER_KEYWORD,
                }

                resp = requests.get(HF_API_URL, params=params, timeout=30)
                resp.raise_for_status()
                datasets = resp.json()

                for ds in datasets:
                    ds_id = ds.get("id", "")
                    created_str = ds.get("createdAt", "")
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
                            pass  # Can't parse → include it to be safe

                    # Classify
                    cl = classify(ds_id, self.PLATFORM_NAME)

                    results.append(
                        DatasetResult(
                            platform=self.PLATFORM_NAME,
                            dataset_id=f"hf:{ds_id}",
                            title=ds_id,
                            url=f"https://huggingface.co/datasets/{ds_id}",
                            upload_date=upload_date,
                            data_type=cl.modality,
                            relevance_score=cl.relevance_score,
                        )
                    )

            except requests.RequestException as e:
                logger.warning(f"HuggingFace keyword '{keyword}' failed: {e}")
                continue
            except Exception as e:
                logger.warning(f"HuggingFace unexpected error for '{keyword}': {e}")
                continue

        return self._deduplicate(results)
