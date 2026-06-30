"""
Base scraper interface & shared DatasetResult model.

Every platform scraper inherits from BaseScraper and implements fetch().
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class DatasetResult:
    """Uniform representation of a discovered dataset regardless of source."""

    platform: str
    dataset_id: str          # globally unique: "kaggle:<ref>" / "hf:<id>" / …
    title: str
    url: str
    upload_date: str = ""            # human-readable date string (e.g. "Jun 28, 2026")
    data_type: str = "Medical Imaging"  # detected modality (e.g. "MRI", "CT Scan")
    relevance_score: int = 0         # 0-100, from classifier
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseScraper(ABC):
    """
    Abstract base class for all platform scrapers.

    Subclasses must set PLATFORM_NAME and implement fetch().
    """

    PLATFORM_NAME: str = "Unknown"

    def __init__(self, keywords: List[str]):
        self.keywords = keywords

    @abstractmethod
    def fetch(self, since_date: Optional[datetime] = None) -> List[DatasetResult]:
        """
        Query the platform for datasets matching self.keywords.

        Args:
            since_date: If provided, only return datasets created/updated
                        after this datetime.  On the very first run this will
                        be ~60 days ago; on subsequent runs it will be the
                        timestamp of the previous run.

        Returns:
            A de-duplicated list of DatasetResult objects.
        """
        ...

    # ── helpers ───────────────────────────────

    def _deduplicate(self, results: List[DatasetResult]) -> List[DatasetResult]:
        """Remove results with the same dataset_id (keeps first occurrence)."""
        seen_ids: set[str] = set()
        unique: List[DatasetResult] = []
        for r in results:
            if r.dataset_id not in seen_ids:
                seen_ids.add(r.dataset_id)
                unique.append(r)
        return unique
