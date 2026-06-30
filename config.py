"""
Medical Image Dataset Monitoring Agent — Configuration
"""
import os
from dotenv import load_dotenv

# Load .env file if present (local development)
load_dotenv()

# ──────────────────────────────────────────────
#  API Credentials (from environment / secrets)
# ──────────────────────────────────────────────
KAGGLE_API_TOKEN = os.getenv("KAGGLE_API_TOKEN", "")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# ──────────────────────────────────────────────
#  Database
# ──────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets_state.db")

# ──────────────────────────────────────────────
#  Search Keywords (all medical imaging modalities)
# ──────────────────────────────────────────────
TARGET_KEYWORDS = [
    "medical image",
    "MRI",
    "fMRI",
    "CT scan",
    "PET scan",
    "X-ray",
    "ultrasound",
    "OCT",
    "histopathology",
    "mammography",
    "endoscopy",
    "angiography",
    "dermoscopy",
    "radiograph",
    "DICOM",
    "WSI",
    "microscopy",
]

# ──────────────────────────────────────────────
#  Time Window
# ──────────────────────────────────────────────
FIRST_RUN_LOOKBACK_DAYS = 60  # ~2 months on first run

# ──────────────────────────────────────────────
#  Per-platform result caps
# ──────────────────────────────────────────────
MAX_RESULTS_PER_KEYWORD = 20
