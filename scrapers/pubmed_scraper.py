"""
PubMed (PMC) scraper — NCBI E-Utilities REST API.

Uses esearch to find article IDs, then esummary to fetch titles.
Filters by publication date when since_date is provided.
"""
import logging
import time
import requests
from datetime import datetime
from typing import List, Optional

from scrapers.base import BaseScraper, DatasetResult
from classifier import classify

logger = logging.getLogger(__name__)

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


class PubMedScraper(BaseScraper):
    PLATFORM_NAME = "PubMed"

    def fetch(self, since_date: Optional[datetime] = None) -> List[DatasetResult]:
        results: List[DatasetResult] = []

        # Build compound query
        keyword_parts = " OR ".join(
            [f'"{kw}"[Title/Abstract]' for kw in self.keywords]
        )
        query = f"({keyword_parts}) AND dataset[Title/Abstract]"

        try:
            params = {
                "db": "pmc",
                "term": query,
                "retmode": "json",
                "sort": "date",
                "retmax": 50,
            }

            # Date range filter
            if since_date:
                params["datetype"] = "pdat"
                params["mindate"] = since_date.strftime("%Y/%m/%d")
                params["maxdate"] = datetime.utcnow().strftime("%Y/%m/%d")

            resp = requests.get(ESEARCH_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            id_list = data.get("esearchresult", {}).get("idlist", [])

            if not id_list:
                logger.info("PubMed: no matching articles found.")
                return results

            logger.info(f"PubMed: {len(id_list)} article IDs found, fetching summaries…")

            # NCBI rate limit: 3 requests/sec without API key
            time.sleep(0.4)

            # Fetch summaries in one call
            summary_params = {
                "db": "pmc",
                "id": ",".join(id_list),
                "retmode": "json",
            }
            summary_resp = requests.get(
                ESUMMARY_URL, params=summary_params, timeout=30
            )
            summary_resp.raise_for_status()
            summary_data = summary_resp.json()

            for pmcid in id_list:
                article = summary_data.get("result", {}).get(pmcid, {})
                title = article.get("title", f"PMC Article {pmcid}")
                url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/"

                # Extract publication date
                upload_date = ""
                pub_date = article.get("pubdate", "")
                if pub_date:
                    try:
                        # PubMed dates come as "2026 Jun 28" or "2026 Jun"
                        parts = pub_date.split()
                        if len(parts) >= 2:
                            upload_date = f"{parts[1]} {parts[2] + ',' if len(parts) > 2 else ''} {parts[0]}".strip()
                        else:
                            upload_date = pub_date
                    except (IndexError, ValueError):
                        upload_date = pub_date

                # Classify
                cl = classify(title, self.PLATFORM_NAME)

                results.append(
                    DatasetResult(
                        platform=self.PLATFORM_NAME,
                        dataset_id=f"pmc:{pmcid}",
                        title=title,
                        url=url,
                        upload_date=upload_date,
                        data_type=cl.modality,
                        relevance_score=cl.relevance_score,
                    )
                )

        except requests.RequestException as e:
            logger.error(f"PubMed scraper failed: {e}")
        except Exception as e:
            logger.error(f"PubMed unexpected error: {e}")

        return self._deduplicate(results)
