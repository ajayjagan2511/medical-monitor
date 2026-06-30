#!/usr/bin/env python3
"""
Medical Image Dataset Monitoring Agent
=======================================
Entry point. Orchestrates the full pipeline:

  1. Load config & connect to SQLite
  2. Determine lookback window (first run → 2 months, else since last run)
  3. Query all platforms via scrapers
  4. Deduplicate against the database
  5. Send a batched Slack alert for any new finds
  6. Log the run and close the database
"""

import logging
import sys
from datetime import datetime, timedelta, timezone

from config import TARGET_KEYWORDS, FIRST_RUN_LOOKBACK_DAYS
from database import DatabaseManager
from alerting import SlackAlerter
from classifier import RELEVANCE_THRESHOLD
from scrapers import KaggleScraper, HuggingFaceScraper, ZenodoScraper, PubMedScraper

# ── Logging ───────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("monitor")


def main():
    logger.info("=" * 55)
    logger.info("  Medical Image Dataset Monitor — Starting run")
    logger.info("=" * 55)

    # 1 ── Database
    db = DatabaseManager()
    db.connect()

    try:
        # 2 ── Lookback window
        last_run = db.get_last_run_time()

        if last_run:
            since_date = datetime.fromisoformat(last_run)
            logger.info(
                f"Previous run: {last_run}. "
                f"Fetching datasets updated since then."
            )
        else:
            since_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=FIRST_RUN_LOOKBACK_DAYS)
            logger.info(
                f"First run detected → looking back {FIRST_RUN_LOOKBACK_DAYS} days "
                f"to {since_date.strftime('%Y-%m-%d')}."
            )

        # 3 ── Scrapers
        scrapers = [
            KaggleScraper(keywords=TARGET_KEYWORDS),
            HuggingFaceScraper(keywords=TARGET_KEYWORDS),
            ZenodoScraper(keywords=TARGET_KEYWORDS),
            PubMedScraper(keywords=TARGET_KEYWORDS),
        ]

        # 4 ── Fetch → deduplicate → collect new
        new_datasets = []

        for scraper in scrapers:
            logger.info(f"Querying {scraper.PLATFORM_NAME}…")
            try:
                results = scraper.fetch(since_date=since_date)
                logger.info(
                    f"  → {len(results)} candidate(s) from {scraper.PLATFORM_NAME}"
                )

                for ds in results:
                    if not db.is_seen(ds.dataset_id):
                        db.mark_seen(ds.platform, ds.dataset_id, ds.title, ds.url)
                        new_datasets.append(ds)

            except Exception as e:
                logger.error(f"  ✗ {scraper.PLATFORM_NAME} failed: {e}")
                continue

        # 5 ── Relevance filtering
        total_before = len(new_datasets)
        relevant_datasets = [
            ds for ds in new_datasets if ds.relevance_score >= RELEVANCE_THRESHOLD
        ]
        filtered_out = total_before - len(relevant_datasets)

        logger.info(
            f"New datasets: {total_before} total, "
            f"{len(relevant_datasets)} relevant (score ≥ {RELEVANCE_THRESHOLD}), "
            f"{filtered_out} filtered out"
        )

        # 6 ── Alert
        if relevant_datasets:
            alerter = SlackAlerter()
            alerter.send_batch(relevant_datasets)
        else:
            logger.info("No relevant datasets — no alert sent.")

        # 7 ── Log run
        db.log_run(datasets_found=len(relevant_datasets), status="success")

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        db.log_run(datasets_found=0, status=f"error: {e}")

    finally:
        # Critical: release the file lock before GitHub Actions commits the DB
        db.close()

    logger.info("=" * 55)
    logger.info("  Medical Image Dataset Monitor — Run complete")
    logger.info("=" * 55)


if __name__ == "__main__":
    main()
