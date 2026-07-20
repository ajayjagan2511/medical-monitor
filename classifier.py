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
    # MRI & Subtypes
    (r"\bfMRI\b|\bfunctional\s*mri\b", "fMRI"),
    (r"\bsMRI\b|\bstructural\s*mri\b", "sMRI"),
    (r"\bdMRI\b|\bdiffusion\s*mri\b", "dMRI"),
    (r"\bDTI\b|\bdiffusion\s*tensor\b", "DTI"),
    (r"\bMR\s*Angiograph", "MR Angiography"),
    (r"\bMRI\b|\bmagnetic\s*resonance\b", "MRI"),
    
    # CT & Subtypes
    (r"\bCBCT\b|\bcone\s*beam\b", "CBCT"),
    (r"\bmicro[-]?CT\b", "Micro-CT"),
    (r"\bCT\s*scan\b|\bcomputed\s*tomography\b|\bCAT\s*scan\b|\bCT\b", "CT"),
    
    # PET & Subtypes
    (r"\bFDG[-]?PET\b", "FDG-PET"),
    (r"\bPET[-/]?CT\b", "PET-CT"),
    (r"\bPET[-/]?MRI\b", "PET-MRI"),
    (r"\bPET\s*scan\b|\bpositron\s*emission\b|\bPET\b", "PET"),
    
    # X-Ray & Subtypes
    (r"\bmammogra\b|\bbreast\s*imag", "Mammography"),
    (r"\bDEXA\b|\bbone\s*densitom", "DEXA"),
    (r"\bfluoroscop", "Fluoroscopy"),
    (r"\bX[-\s]?ray\b|\bradiograph", "X-ray"),
    
    # Ultrasound & Subtypes
    (r"\bechocardiograph|\becho\b", "Echocardiography"),
    (r"\bdoppler\b", "Doppler Ultrasound"),
    (r"\bPOCUS\b|\bpoint[- ]of[- ]care", "POCUS"),
    (r"\bIVUS\b|\bintravascular", "IVUS"),
    (r"\bultrasound\b|\bsonograph", "Ultrasound"),
    
    # OCT & Subtypes
    (r"\bOCTA\b|\boct\s*angiograph", "OCTA"),
    (r"\bSD[-]?OCT\b|\bspectral\s*domain", "SD-OCT"),
    (r"\bSS[-]?OCT\b|\bswept\s*source", "SS-OCT"),
    (r"\bOCT\b|\boptical\s*coherence\b", "OCT"),
    
    # Endoscopy & Subtypes
    (r"\bcolonoscop", "Colonoscopy"),
    (r"\bgastroscop", "Gastroscopy"),
    (r"\blaparoscop", "Laparoscopy"),
    (r"\bbronchoscop", "Bronchoscopy"),
    (r"\bcystoscop", "Cystoscopy"),
    (r"\brhinoscop", "Rhinoscopy"),
    (r"\benteroscop", "Enteroscopy"),
    (r"\bendoscop", "Endoscopy"),
    
    # Retinal & Eye Imaging
    (r"\bfluorescein\s*angiograph|\bFA\b", "Fluorescein Angiography"),
    (r"\bultra[- ]?widefield", "Ultra-widefield Fundus"),
    (r"\bcolor\s*fundus", "Color Fundus"),
    (r"\bfundus", "Fundus"),
    (r"\bretina", "Retinal Image"),
    
    # Microscopy
    (r"\belectron\s*microscop|\bSEM\b|\bTEM\b", "Electron Microscopy"),
    (r"\bconfocal", "Confocal Microscopy"),
    (r"\bfluorescent\s*microscop", "Fluorescent Microscopy"),
    (r"\bmicroscop|\bcell\s*imag", "Microscopy"),
    
    # Pathology & Subtypes
    (r"\bhistopath", "Histopathology"),
    (r"\bcytopath", "Cytopathology"),
    (r"\bdigital\s*patholog", "Digital Pathology"),
    (r"\bWSI\b|\bwhole\s*slide", "Whole Slide Imaging"),
    (r"\bH\s*&\s*E\b|\bhematoxylin", "H&E"),
    (r"\bIHC\b|\bimmunohistochem", "Immunohistochemistry"),
    (r"\bpatholog", "Pathology"),
    
    # Dermoscopy
    (r"\bepiluminescence", "Epiluminescence Microscopy"),
    (r"\bdermoscop|\bdermatoscop|\bskin\s*lesion|\bmelanoma\b", "Dermoscopy"),
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
      
    Strict Filtering:
      - A dataset signal is REQUIRED. If 0 dataset keywords are found, the
        maximum possible score is capped below RELEVANCE_THRESHOLD.
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
        
    # Strict Dataset Requirement Filter
    if dataset_hits == 0:
        return min(score, RELEVANCE_THRESHOLD - 1)

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
