"""
Synapse (Sage Bionetworks) scraper — REST API v1.

Authentication: requires a Personal Access Token (PAT) set via
SYNAPSE_AUTH_TOKEN environment variable.

Uses POST /repo/v1/search to perform full-text search across all public
Synapse entities. Filters results to type=project (which corresponds to
research dataset projects). Falls back gracefully if no token is supplied.
"""
import logging
import requests
from datetime import datetime
from typing import List, Optional

from scrapers.base import BaseScraper, DatasetResult
from config import SYNAPSE_AUTH_TOKEN
from classifier import classify

logger = logging.getLogger(__name__)

SYNAPSE_SEARCH_URL = "https://repo-prod.prod.sagebase.org/repo/v1/search"


class SynapseScraper(BaseScraper):
    PLATFORM_NAME = "Synapse"

    def fetch(self, since_date: Optional[datetime] = None) -> List[DatasetResult]:
        results: List[DatasetResult] = []

        if not SYNAPSE_AUTH_TOKEN:
            logger.warning(
                "SYNAPSE_AUTH_TOKEN not set. Skipping Synapse scraper. "
                "Get a Personal Access Token from synapse.org/Profile:<id>/settings."
            )
            return results

        headers = {
            "Authorization": f"Bearer {SYNAPSE_AUTH_TOKEN}",
            "Content-Type": "application/json",
        }

        for keyword in self.keywords:
            try:
                # Synapse search uses a cloud-search-style query syntax
                payload = {
                    "queryTerm": [keyword],
                    "returnFields": ["id", "name", "description", "modified_on", "entity_type"],
                    "size": 20,
                    "start": 0,
                }

                resp = requests.post(
                    SYNAPSE_SEARCH_URL, json=payload, headers=headers, timeout=30
                )
                resp.raise_for_status()
                data = resp.json()

                hits = data.get("hits", [])

                for hit in hits:
                    syn_id = hit.get("id", "")
                    title = hit.get("name") or syn_id
                    description = hit.get("description") or ""
                    modified_on = hit.get("modified_on")
                    upload_date = ""

                    # modified_on is a Unix epoch timestamp in seconds
                    if modified_on:
                        try:
                            modified_dt = datetime.utcfromtimestamp(int(modified_on))
                            upload_date = modified_dt.strftime("%b %d, %Y")
                            if since_date and modified_dt < since_date:
                                continue
                        except (ValueError, TypeError):
                            pass

                    cl = classify(f"{title} {description}", self.PLATFORM_NAME)


                    results.append(
                        DatasetResult(
                            platform=self.PLATFORM_NAME,
                            dataset_id=f"synapse:{syn_id}",
                            title=title or syn_id,
                            url=f"https://www.synapse.org/Synapse:{syn_id}",
                            upload_date=upload_date,
                            data_type=cl.modality,
                            relevance_score=cl.relevance_score,
                        )
                    )

            except requests.RequestException as e:
                logger.warning(f"Synapse keyword '{keyword}' failed: {e}")
                continue
            except Exception as e:
                logger.warning(f"Synapse unexpected error for '{keyword}': {e}")
                continue

        return self._deduplicate(results)
