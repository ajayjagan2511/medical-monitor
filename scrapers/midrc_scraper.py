import os
import logging
import requests
from datetime import datetime
from typing import List, Optional

from scrapers.base import BaseScraper, DatasetResult
from classifier import classify

logger = logging.getLogger(__name__)

class MIDRCScraper(BaseScraper):
    PLATFORM_NAME = "MIDRC"
    BASE_URL = "https://data.midrc.org/api/v0/submission/graphql"

    def fetch(self, since_date: Optional[datetime] = None) -> List[DatasetResult]:
        results: List[DatasetResult] = []
        
        midrc_token = os.getenv("MIDRC_AUTH_TOKEN")
        if not midrc_token:
            logger.warning(
                "MIDRC_AUTH_TOKEN not set. Skipping MIDRC scraper. "
                "Requires a Gen3 API Key."
            )
            return results

        try:
            # Exchange API Key for an Access Token
            token_url = "https://data.midrc.org/user/credentials/cdis/access_token"
            token_resp = requests.post(token_url, json={"api_key": midrc_token}, timeout=15)
            token_resp.raise_for_status()
            access_token = token_resp.json().get("access_token")
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Query the dataset node in Gen3 Graph
            query = """
            {
              dataset(first: 50, order_by_desc: "created_datetime") {
                id
                submitter_id
                project_id
                created_datetime
              }
            }
            """
            payload = {"query": query}
            resp = requests.post(self.BASE_URL, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            
            data = resp.json().get("data", {})
            datasets = data.get("dataset", [])
            
            for ds in datasets:
                ds_id = ds.get("submitter_id", ds.get("id", ""))
                project_id = ds.get("project_id", "")
                created = ds.get("created_datetime", "")
                
                title = f"{project_id} - {ds_id}"
                url = f"https://data.midrc.org/explorer"  # MIDRC doesn't have a direct dataset page usually, it's explored via the data commons
                
                upload_date_str = ""
                if created:
                    try:
                        # "2021-03-22T14:42:00.321151+00:00"
                        dt = datetime.fromisoformat(created)
                        upload_date_str = dt.strftime("%b %d, %Y")
                        if since_date and dt.replace(tzinfo=None) < since_date:
                            continue
                    except Exception:
                        pass
                
                cl = classify(title, self.PLATFORM_NAME)
                
                results.append(
                    DatasetResult(
                        platform=self.PLATFORM_NAME,
                        dataset_id=f"midrc:{ds_id}",
                        title=title,
                        url=url,
                        upload_date=upload_date_str,
                        data_type=cl.modality,
                        relevance_score=cl.relevance_score,
                    )
                )
                
        except requests.RequestException as e:
            logger.warning(f"{self.PLATFORM_NAME} request failed: {e}")
        except Exception as e:
            logger.warning(f"{self.PLATFORM_NAME} unexpected error: {e}")
            
        return self._deduplicate(results)
