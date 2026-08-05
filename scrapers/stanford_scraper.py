import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Optional

from scrapers.base import BaseScraper, DatasetResult
from classifier import classify

logger = logging.getLogger(__name__)

class StanfordScraper(BaseScraper):
    PLATFORM_NAME = "Stanford AIMI"
    BASE_URL = "https://stanford.redivis.com/datasets/"

    def fetch(self, since_date: Optional[datetime] = None) -> List[DatasetResult]:
        results: List[DatasetResult] = []
        
        try:
            # We will scrape the Stanford Redivis portal where AIMI hosts datasets
            url = "https://aimi.stanford.edu/shared-datasets"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                if 'stanford.redivis.com/datasets/' in href:
                    title = link.get_text(strip=True)
                    if not title or title.lower() == 'dataset':
                        continue
                        
                    # Extract the unique ID from the URL (e.g., https://stanford.redivis.com/datasets/5yyj-1a9f6ap0x)
                    ds_id = href.split('/datasets/')[-1].split('?')[0]
                    
                    # Since it's a static HTML page, we don't have exact upload dates readily available in this list.
                    # We will rely on deduplication in the database to prevent duplicate alerts.
                    
                    cl = classify(title, self.PLATFORM_NAME)
                    
                    results.append(
                        DatasetResult(
                            platform=self.PLATFORM_NAME,
                            dataset_id=f"stanford:{ds_id}",
                            title=title,
                            url=href,
                            upload_date="", # Date not available in simple HTML listing
                            data_type=cl.modality,
                            relevance_score=cl.relevance_score,
                        )
                    )
        except requests.RequestException as e:
            logger.warning(f"{self.PLATFORM_NAME} request failed: {e}")
        except Exception as e:
            logger.warning(f"{self.PLATFORM_NAME} unexpected error: {e}")
            
        return self._deduplicate(results)
