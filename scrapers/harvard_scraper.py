import logging
import requests
from datetime import datetime, timezone
from typing import List, Optional

from scrapers.base import BaseScraper, DatasetResult
from classifier import classify

logger = logging.getLogger(__name__)

class HarvardScraper(BaseScraper):
    PLATFORM_NAME = "Harvard Dataverse"
    BASE_URL = "https://dataverse.harvard.edu/api/search"

    def fetch(self, since_date: Optional[datetime] = None) -> List[DatasetResult]:
        results: List[DatasetResult] = []
        
        for keyword in self.keywords:
            try:
                params = {
                    "q": keyword,
                    "type": "dataset",
                    "per_page": 20
                }
                resp = requests.get(self.BASE_URL, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json().get("data", {})
                items = data.get("items", [])
                
                for item in items:
                    ds_id = item.get("global_id", "")
                    title = item.get("name", ds_id)
                    description = item.get("description", "")
                    url = item.get("url", f"https://dataverse.harvard.edu/dataset.xhtml?persistentId={ds_id}")
                    published_at = item.get("published_at", "")
                    
                    upload_date_str = ""
                    if published_at:
                        try:
                            # Usually ISO format ending in Z, e.g., "2024-01-01T00:00:00Z"
                            pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                            upload_date_str = pub_dt.strftime("%b %d, %Y")
                            if since_date and pub_dt.replace(tzinfo=None) < since_date:
                                continue
                        except Exception:
                            pass
                            
                    cl = classify(f"{title} {description}", self.PLATFORM_NAME)
                    
                    results.append(
                        DatasetResult(
                            platform=self.PLATFORM_NAME,
                            dataset_id=f"harvard:{ds_id}",
                            title=title,
                            url=url,
                            upload_date=upload_date_str,
                            data_type=cl.modality,
                            relevance_score=cl.relevance_score,
                        )
                    )
            except requests.RequestException as e:
                logger.warning(f"{self.PLATFORM_NAME} keyword '{keyword}' failed: {e}")
            except Exception as e:
                logger.warning(f"{self.PLATFORM_NAME} unexpected error for '{keyword}': {e}")
                
        return self._deduplicate(results)
