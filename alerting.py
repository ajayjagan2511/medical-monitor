"""
Slack Alerting Module — Table-formatted notifications.

Sends a single consolidated message per run with datasets displayed
in a clean table-like format: clickable name, data type, upload date.
Falls back to console output if SLACK_WEBHOOK_URL is not configured.
"""
import logging
import requests
from datetime import datetime, timezone
from typing import List

from scrapers.base import DatasetResult
from config import SLACK_WEBHOOK_URL

logger = logging.getLogger(__name__)

# Emoji mapping for visual flair
PLATFORM_ICONS = {
    "Kaggle": "📊",
    "Hugging Face": "🤗",
    "Zenodo": "🔬",
    "PubMed": "📄",
}

MODALITY_ICONS = {
    "MRI": "🧠",
    "fMRI": "🧠",
    "CT Scan": "🫁",
    "PET Scan": "☢️",
    "X-ray": "🦴",
    "Ultrasound": "📡",
    "OCT": "👁️",
    "Histopathology": "🔬",
    "Mammography": "🩺",
    "Endoscopy": "🔍",
    "Angiography": "❤️",
    "Dermoscopy": "🩹",
    "DICOM": "💾",
    "Microscopy": "🔬",
    "Retinal Imaging": "👁️",
    "Dental Imaging": "🦷",
    "Medical Imaging": "🏥",
}


class SlackAlerter:
    """Dispatches batched Slack alerts with a table-like layout."""

    def __init__(self, webhook_url: str = SLACK_WEBHOOK_URL):
        self.webhook_url = webhook_url

    # ── public API ────────────────────────────

    def send_batch(self, datasets: List[DatasetResult]) -> bool:
        """
        Send a single consolidated Slack message for all new datasets.
        Returns True on success, False on failure.
        """
        if not datasets:
            return True

        if not self.webhook_url:
            logger.warning(
                "SLACK_WEBHOOK_URL not configured. Printing to console instead."
            )
            self._print_to_console(datasets)
            return False

        payload = self._build_payload(datasets)

        try:
            resp = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            resp.raise_for_status()
            logger.info(f"✓ Slack alert sent ({len(datasets)} datasets)")
            return True
        except requests.RequestException as e:
            logger.error(f"✗ Failed to send Slack alert: {e}")
            self._print_to_console(datasets)
            return False

    # ── payload builder ───────────────────────

    def _build_payload(self, datasets: List[DatasetResult]) -> dict:
        """Construct a Slack Block Kit payload with table-like layout."""

        # Group datasets by platform
        by_platform: dict[str, List[DatasetResult]] = {}
        for ds in datasets:
            by_platform.setdefault(ds.platform, []).append(ds)

        count = len(datasets)
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": (
                        f"🏥 {count} New Medical Image "
                        f"Dataset{'s' if count != 1 else ''} Found"
                    ),
                    "emoji": True,
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"📅 Scan completed at "
                            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
                        ),
                    }
                ],
            },
            {"type": "divider"},
        ]

        for platform, items in by_platform.items():
            icon = PLATFORM_ICONS.get(platform, "📁")
            n = len(items)

            # Platform header
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{icon} {platform}* — {n} dataset{'s' if n != 1 else ''}",
                },
            })

            # Table header
            blocks.append({
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": "📋 *Dataset*  ·  🏷️ *Type*  ·  📅 *Uploaded*",
                }],
            })

            # Dataset rows (group them to avoid hitting Slack's 50 block limit)
            chunk_text = ""
            for ds in items[:30]:  # we can comfortably show 30 if grouped
                mod_icon = MODALITY_ICONS.get(ds.data_type, "🏥")
                truncated = ds.title[:70] + "…" if len(ds.title) > 70 else ds.title
                date_str = ds.upload_date if ds.upload_date else "—"

                row_text = (
                    f"• <{ds.url}|{truncated}>\n"
                    f"    {mod_icon} `{ds.data_type}`  ·  📅 {date_str}\n\n"
                )
                
                # Slack text limit is 3000, we split at 2500 to be safe
                if len(chunk_text) + len(row_text) > 2500:
                    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": chunk_text.strip()}})
                    chunk_text = row_text
                else:
                    chunk_text += row_text
                    
            if chunk_text:
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": chunk_text.strip()}})

            if n > 30:
                blocks.append({
                    "type": "context",
                    "elements": [{
                        "type": "mrkdwn",
                        "text": f"_…and {n - 30} more from {platform}_",
                    }],
                })

            blocks.append({"type": "divider"})

        return {"blocks": blocks}

    # ── fallback ──────────────────────────────

    @staticmethod
    def _print_to_console(datasets: List[DatasetResult]):
        """Pretty-print results in table format when Slack is unavailable."""
        print()
        print("=" * 90)
        print(f"🏥  {len(datasets)} New Medical Image Dataset(s) Found")
        print("=" * 90)
        print(f"  {'Dataset':<45} {'Type':<18} {'Date':<12} {'Source'}")
        print(f"  {'─' * 44}  {'─' * 17}  {'─' * 11}  {'─' * 12}")

        for ds in datasets:
            title = ds.title[:42] + "…" if len(ds.title) > 42 else ds.title
            dtype = ds.data_type[:16] if ds.data_type else "—"
            date = ds.upload_date[:10] if ds.upload_date else "—"
            print(f"  {title:<45} {dtype:<18} {date:<12} {ds.platform}")

        print("=" * 90)
        print(f"  🔗 URLs printed above for reference. Set SLACK_WEBHOOK_URL for Slack alerts.")
        print("=" * 90)
        print()
