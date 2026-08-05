import logging
import requests
from datetime import datetime
from typing import List, Optional

from scrapers.base import BaseScraper, DatasetResult
from classifier import classify

logger = logging.getLogger(__name__)

class ISICScraper(BaseScraper):
    PLATFORM_NAME = "ISIC Archive"
    BASE_URL = "https://api.isic-archive.com/api/v2/collections/"

    def fetch(self, since_date: Optional[datetime] = None) -> List[DatasetResult]:
        results: List[DatasetResult] = []
        
        try:
            resp = requests.get(self.BASE_URL, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            collections = data.get("results", [])
            
            for coll in collections:
                # ISIC collections usually contain melanoma/dermoscopy datasets
                ds_id = str(coll.get("id", ""))
                title = coll.get("name", ds_id)
                description = coll.get("description", "")
                url = f"https://api.isic-archive.com/collections/{ds_id}"
                
                created_str = coll.get("created", "")
                upload_date_str = ""
                if created_str:
                    try:
                        # "2020-08-11T16:21:46.331566Z"
                        dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                        upload_date_str = dt.strftime("%b %d, %Y")
                        if since_date and dt.replace(tzinfo=None) < since_date:
                            continue
                    except Exception:
                        pass
                
                # We can do a keyword check on title/description to make sure it matches user's targets
                combined_text = (title + " " + description).lower()
                matched = any(kw.lower() in combined_text for kw in self.keywords)
                # ISIC is specifically dermoscopy, so it's inherently relevant if keywords include skin/dermoscopy
                # But we'll just classify it directly.
                
                cl = classify(f"{title} {description}", self.PLATFORM_NAME)
                
                results.append(
                    DatasetResult(
                        platform=self.PLATFORM_NAME,
                        dataset_id=f"isic:{ds_id}",
                        title=title,
                        url=url,
                        upload_date=upload_date_str,
                        data_type="Dermoscopy" if cl.modality == "Medical Imaging" else cl.modality,
                        relevance_score=cl.relevance_score,
                    )
                )
        except requests.RequestException as e:
            logger.warning(f"{self.PLATFORM_NAME} failed: {e}")
        except Exception as e:
            logger.warning(f"{self.PLATFORM_NAME} unexpected error: {e}")
            
        return self._deduplicate(results)
