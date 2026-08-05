import logging
import requests
from datetime import datetime
from typing import List, Optional

from scrapers.base import BaseScraper, DatasetResult
from classifier import classify

logger = logging.getLogger(__name__)

class OpenIScraper(BaseScraper):
    PLATFORM_NAME = "Open-I"
    BASE_URL = "https://openi.nlm.nih.gov/api/search"

    def fetch(self, since_date: Optional[datetime] = None) -> List[DatasetResult]:
        results: List[DatasetResult] = []
        
        for keyword in self.keywords:
            try:
                params = {
                    "query": keyword,
                    "m": 1,
                    "n": 20
                }
                resp = requests.get(self.BASE_URL, params=params, timeout=30)
                resp.raise_for_status()
                items = resp.json().get("list", [])
                
                for item in items:
                    ds_id = item.get("uid", "")
                    title = item.get("title", ds_id)
                    description = item.get("abstract", "")
                    url = f"https://openi.nlm.nih.gov/detailedresult?img={item.get('imgLarge', '')}&req=4"
                    
                    journal_date = item.get("journal_date", {})
                    year = journal_date.get("year", "")
                    month = journal_date.get("month", "01")
                    day = journal_date.get("day", "01")
                    
                    upload_date_str = f"{year}-{month}-{day}"
                    
                    if year and month and day:
                        try:
                            pub_dt = datetime(int(year), int(month), int(day))
                            upload_date_str = pub_dt.strftime("%b %d, %Y")
                            if since_date and pub_dt < since_date:
                                continue
                        except Exception:
                            pass
                            
                    cl = classify(f"{title} {description}", self.PLATFORM_NAME)
                    
                    results.append(
                        DatasetResult(
                            platform=self.PLATFORM_NAME,
                            dataset_id=f"openi:{ds_id}",
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
