"""
Kaggle scraper — uses the official `kaggle` Python library (SDK v2+).

Authentication is handled via the KAGGLE_API_TOKEN env var
(the library reads this automatically on authenticate()).
"""
import logging
import os
from datetime import datetime
from typing import List, Optional

from scrapers.base import BaseScraper, DatasetResult
from config import MAX_RESULTS_PER_KEYWORD, KAGGLE_API_TOKEN
from classifier import classify

logger = logging.getLogger(__name__)


class KaggleScraper(BaseScraper):
    PLATFORM_NAME = "Kaggle"

    def fetch(self, since_date: Optional[datetime] = None) -> List[DatasetResult]:
        results: List[DatasetResult] = []

        if not KAGGLE_API_TOKEN:
            logger.warning("KAGGLE_API_TOKEN not set. Skipping Kaggle scraper.")
            return results

        # Ensure the token is in the environment for the Kaggle SDK
        os.environ["KAGGLE_API_TOKEN"] = KAGGLE_API_TOKEN

        try:
            from kaggle.api.kaggle_api_extended import KaggleApi

            api = KaggleApi()
            api.authenticate()
        except ImportError:
            logger.error(
                "kaggle library not installed — run `pip install kaggle`. "
                "Skipping Kaggle scraper."
            )
            return results
        except (Exception, SystemExit) as e:
            logger.error(f"Kaggle authentication failed: {e}")
            return results

        for keyword in self.keywords:
            try:
                datasets = api.dataset_list(
                    search=keyword,
                    sort_by="updated",
                    file_type="all",
                )

                for ds in datasets[:MAX_RESULTS_PER_KEYWORD]:
                    ref = str(ds.ref) if hasattr(ds, "ref") else str(ds)
                    title = str(ds.title) if hasattr(ds, "title") else ref

                    # Extract upload/update date
                    upload_date = ""
                    if hasattr(ds, "lastUpdated") and ds.lastUpdated:
                        last_updated = ds.lastUpdated
                        # Date filter — skip datasets older than since_date
                        if since_date and last_updated < since_date:
                            continue
                        try:
                            upload_date = last_updated.strftime("%b %d, %Y")
                        except (AttributeError, ValueError):
                            upload_date = str(last_updated)[:10]

                    # Classify
                    cl = classify(title, self.PLATFORM_NAME)

                    results.append(
                        DatasetResult(
                            platform=self.PLATFORM_NAME,
                            dataset_id=f"kaggle:{ref}",
                            title=title,
                            url=f"https://www.kaggle.com/datasets/{ref}",
                            upload_date=upload_date,
                            data_type=cl.modality,
                            relevance_score=cl.relevance_score,
                        )
                    )

            except Exception as e:
                logger.warning(f"Kaggle keyword '{keyword}' failed: {e}")
                continue

        return self._deduplicate(results)
