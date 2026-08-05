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
    body_part: str = ""
    anatomical_area: str = ""
    broad_modality: str = ""
    dataset_size: str = ""


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


# ──────────────────────────────────────────────
#  Metadata Extraction Heuristics
# ──────────────────────────────────────────────

BODY_PARTS = {
    "Brain": [r"\bbrain", r"\bcerebral", r"\bhead", r"\bcranial"],
    "Chest/Lung": [r"\bchest", r"\blung", r"\bpulmonary", r"\bthorax", r"\bthoracic"],
    "Heart": [r"\bheart", r"\bcardiac", r"\bcoronary", r"\becho\b"],
    "Liver": [r"\bliver", r"\bhepatic"],
    "Kidney": [r"\bkidney", r"\brenal"],
    "Skin": [r"\bskin", r"\bmelanoma", r"\bderm", r"\blesion", r"\bnevus"],
    "Eye": [r"\beye", r"\bretina", r"\bfundus", r"\bmacula", r"\bocular", r"\bglaucoma"],
    "Bone/Joint": [r"\bbone", r"\bknee", r"\bspine", r"\bjoint", r"\bmsk", r"\bskeletal", r"\bmusculoskeletal", r"\bortho"],
    "Breast": [r"\bbreast", r"\bmamm"],
    "Prostate": [r"\bprostate"],
    "Pelvis": [r"\bpelvi"],
    "Abdomen": [r"\babdomen", r"\babdominal", r"\bgastro", r"\bbowel", r"\bcolon"]
}

ANATOMICAL_AREAS = {
    "Head and Neck": [r"\bbrain", r"\bhead", r"\bcranial", r"\bneck", r"\bthyroid", r"\beye", r"\bretina", r"\bfundus", r"\bmacula"],
    "Thorax": [r"\bchest", r"\blung", r"\bthorax", r"\bthoracic", r"\bpulmonary", r"\bheart", r"\bcardiac", r"\bbreast", r"\bmamm"],
    "Abdomen": [r"\bliver", r"\bkidney", r"\brenal", r"\babdomen", r"\babdominal", r"\bgastro", r"\bbowel", r"\bcolon", r"\bhepatic"],
    "Pelvis": [r"\bpelvi", r"\bprostate"],
    "Limbs/Joints": [r"\bknee", r"\bjoint", r"\barm", r"\bleg", r"\bfoot", r"\bhand"],
    "Skin": [r"\bskin", r"\bmelanoma", r"\bderm"]
}

BROAD_MODALITIES_LIST = [
    "CT", "Dermoscopy", "Endoscopy", "Fundus", "Microscopy", 
    "MRI", "OCT", "OCTA", "Ultrasound", "X-Ray"
]

def extract_broad_modality(text: str) -> str:
    found = []
    text_lower = text.lower()
    
    # Simple heuristic checks
    if "mri" in text_lower or "magnetic resonance" in text_lower:
        found.append("MRI")
    if "ct" in text_lower.split() or "tomography" in text_lower or "cbct" in text_lower:
        found.append("CT")
    if "x-ray" in text_lower or "xray" in text_lower or "radiograph" in text_lower or "dexa" in text_lower or "mammogra" in text_lower or "fluoroscop" in text_lower:
        found.append("X-Ray")
    if "ultrasound" in text_lower or "echo" in text_lower.split() or "sonograph" in text_lower or "pocus" in text_lower:
        found.append("Ultrasound")
    if "dermoscop" in text_lower or "dermatoscop" in text_lower or "epiluminescence" in text_lower:
        found.append("Dermoscopy")
    if "endoscop" in text_lower or "colonoscop" in text_lower or "gastroscop" in text_lower or "bronchoscop" in text_lower or "rhinoscop" in text_lower:
        found.append("Endoscopy")
    if "fundus" in text_lower or "retina" in text_lower or "macula" in text_lower:
        found.append("Fundus")
    if "microscop" in text_lower or "wsi" in text_lower or "slide" in text_lower or "patholog" in text_lower or "histopatholog" in text_lower:
        found.append("Microscopy")
    if "oct" in text_lower.split() or "optical coherence" in text_lower:
        found.append("OCT")
    if "octa" in text_lower.split() or "oct angiography" in text_lower:
        found.append("OCTA")
        
    return ", ".join(list(dict.fromkeys(found)))

def extract_size(text: str) -> str:
    # e.g., "10,000 images", "500 scans", "300 patients"
    match = re.search(r"(\d+(?:,\d+)*)\s*(images|scans|videos|cases|patients|studies|slices|volumes)", text, re.IGNORECASE)
    if match:
        return match.group(0)
    return ""

def extract_body_part(text: str) -> str:
    for part, patterns in BODY_PARTS.items():
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                return part
    return ""

def extract_anatomical_area(text: str) -> str:
    for area, patterns in ANATOMICAL_AREAS.items():
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                return area
    return ""


def classify(title: str, platform: str = "") -> ClassificationResult:
    """
    Full classification: detect modality, compute relevance, and extract metadata.
    """
    modality = detect_modality(title)
    relevance = compute_relevance(title, platform)
    
    return ClassificationResult(
        modality=modality,
        relevance_score=relevance,
        is_relevant=relevance >= RELEVANCE_THRESHOLD,
        body_part=extract_body_part(title),
        anatomical_area=extract_anatomical_area(title),
        broad_modality=extract_broad_modality(title),
        dataset_size=extract_size(title)
    )
