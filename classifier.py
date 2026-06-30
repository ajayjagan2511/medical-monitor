"""
Intelligence layer — modality detection & relevance scoring.

This module adds "smarts" beyond simple keyword matching:
  1. Modality Detection: Identifies the imaging type (MRI, CT, X-ray, etc.)
     from the dataset title/description.
  2. Relevance Scoring: Scores how likely a result is an actual medical
     imaging *dataset* vs. an unrelated match.
"""
import re
from dataclasses import dataclass
from typing import Optional

# ──────────────────────────────────────────────
#  Modality Detection
# ──────────────────────────────────────────────
# Ordered by specificity (most specific first so "fMRI" matches before "MRI")
MODALITY_PATTERNS: list[tuple[str, str]] = [
    (r"\bfMRI\b", "fMRI"),
    (r"\bMRI\b|\bmagnetic\s*resonance\b", "MRI"),
    (r"\bCT\s*scan\b|\bcomputed\s*tomography\b|\bCT\b", "CT Scan"),
    (r"\bPET\s*scan\b|\bpositron\s*emission\b|\bPET[/-]CT\b", "PET Scan"),
    (r"\bX[-\s]?ray\b|\bradiograph\b", "X-ray"),
    (r"\bultrasound\b|\bsonograph\b|\bechocardiograph\b", "Ultrasound"),
    (r"\bOCT\b|\boptical\s*coherence\b", "OCT"),
    (r"\bhistopath\b|\bpathology\b|\bH\s*&\s*E\b|\bWSI\b|\bwhole\s*slide\b", "Histopathology"),
    (r"\bmammogra\b|\bbreast\s*imag\b", "Mammography"),
    (r"\bendoscop\b|\bcolonoscop\b|\bgastroscop\b", "Endoscopy"),
    (r"\bangiograph\b|\bvessel\b", "Angiography"),
    (r"\bdermoscop\b|\bskin\s*lesion\b|\bmelanoma\b", "Dermoscopy"),
    (r"\bDICOM\b", "DICOM"),
    (r"\bmicroscop\b|\bcell\s*imag\b", "Microscopy"),
    (r"\bretina\b|\bfundus\b|\boptic\s*disc\b", "Retinal Imaging"),
    (r"\bdental\b|\bpanoramic\b|\bcephalometr\b", "Dental Imaging"),
]

# ──────────────────────────────────────────────
#  Relevance Scoring
# ──────────────────────────────────────────────
# Keywords that strongly suggest this is a *dataset* (not just a paper)
DATASET_SIGNALS = [
    r"\bdataset\b",
    r"\bdata\s*set\b",
    r"\bcollection\b",
    r"\bbenchmark\b",
    r"\bcorpus\b",
    r"\bannotated\b",
    r"\blabeled\b",
    r"\blabelled\b",
    r"\bsegmentation\b",
    r"\bclassification\b",
    r"\bdetection\b",
    r"\btraining\s*data\b",
    r"\bground\s*truth\b",
    r"\bimage[s]?\b",
    r"\bscan[s]?\b",
]

# Keywords that indicate medical relevance
MEDICAL_SIGNALS = [
    r"\bmedical\b",
    r"\bclinical\b",
    r"\bdiagnos\b",
    r"\bpatient\b",
    r"\btumor\b|\btumour\b",
    r"\bcancer\b",
    r"\blesion\b",
    r"\borgan\b",
    r"\banatom\b",
    r"\bradiol\b",
    r"\bpatholog\b",
    r"\bbiomedic\b",
    r"\bhealthcare\b",
]

# Minimum relevance score to include in alerts (0-100)
RELEVANCE_THRESHOLD = 15


@dataclass
class ClassificationResult:
    modality: str           # e.g. "MRI", "CT Scan", "Unknown"
    relevance_score: int    # 0-100
    is_relevant: bool       # score >= threshold


def detect_modality(text: str) -> str:
    """
    Detect the imaging modality from a text string (title or description).
    Returns the most specific matching modality, or "Medical Imaging" as fallback.
    """
    for pattern, label in MODALITY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return label
    return "Medical Imaging"


def compute_relevance(title: str, platform: str = "") -> int:
    """
    Score how relevant a result is as a medical imaging dataset (0-100).

    Scoring:
      - Each modality keyword found:      +20 (capped at 40)
      - Each dataset signal keyword:       +10 (capped at 30)
      - Each medical signal keyword:       +8  (capped at 24)
      - PubMed platform bonus:             +6  (these are always medical)
    """
    score = 0
    text = title.lower()

    # Modality matches (strong signal)
    modality_hits = sum(
        1 for pattern, _ in MODALITY_PATTERNS
        if re.search(pattern, text, re.IGNORECASE)
    )
    score += min(modality_hits * 20, 40)

    # Dataset signal matches
    dataset_hits = sum(
        1 for pattern in DATASET_SIGNALS
        if re.search(pattern, text, re.IGNORECASE)
    )
    score += min(dataset_hits * 10, 30)

    # Medical signal matches
    medical_hits = sum(
        1 for pattern in MEDICAL_SIGNALS
        if re.search(pattern, text, re.IGNORECASE)
    )
    score += min(medical_hits * 8, 24)

    # Platform bonus (PubMed results are inherently medical)
    if platform.lower() in ("pubmed", "pmc"):
        score += 6

    return min(score, 100)


def classify(title: str, platform: str = "") -> ClassificationResult:
    """
    Full classification: detect modality + compute relevance.
    """
    modality = detect_modality(title)
    relevance = compute_relevance(title, platform)

    return ClassificationResult(
        modality=modality,
        relevance_score=relevance,
        is_relevant=relevance >= RELEVANCE_THRESHOLD,
    )
