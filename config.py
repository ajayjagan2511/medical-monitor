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
    # MRI & Subtypes
    "MRI", "Magnetic Resonance Imaging", "fMRI", "sMRI", "dMRI", "DTI", "Diffusion Tensor", "MR Angiography",
    
    # CT & Subtypes
    "CT scan", "Computed Tomography", "CAT scan", "CBCT", "Micro-CT",
    
    # PET & Subtypes
    "PET scan", "Positron Emission Tomography", "FDG-PET", "PET-CT", "PET-MRI",
    
    # X-Ray & Subtypes
    "X-Ray", "Radiograph", "Radiography", "Fluoroscopy", "Mammography", "DEXA",
    
    # Ultrasound & Subtypes
    "Ultrasound", "Sonography", "Echocardiography", "Doppler Ultrasound", "POCUS", "IVUS",
    
    # OCT & Subtypes
    "OCT", "Optical Coherence Tomography", "SD-OCT", "SS-OCT", "OCTA",
    
    # Endoscopy & Subtypes
    "Endoscopy", "Colonoscopy", "Gastroscopy", "Laparoscopy", "Bronchoscopy", "Cystoscopy", "Rhinoscopy", "Enteroscopy",
    
    # Retinal & Eye Imaging
    "Fundus photography", "Retinal image", "Fluorescein Angiography", "Ultra-widefield fundus", "Color fundus",
    
    # Microscopy
    "Microscopy", "Electron Microscopy", "Confocal Microscopy", "Fluorescent Microscopy",
    
    # Pathology & Subtypes
    "Pathology", "Histopathology", "Cytopathology", "Digital Pathology", "WSI", "Whole Slide Imaging", "Hematoxylin and Eosin", "Immunohistochemistry",
    
    # Dermoscopy
    "Dermoscopy", "Dermatoscopy", "Epiluminescence Microscopy", "Skin lesion",
]

# ──────────────────────────────────────────────
#  Time Window
# ──────────────────────────────────────────────
FIRST_RUN_LOOKBACK_DAYS = 60  # ~2 months on first run

# ──────────────────────────────────────────────
#  Per-platform result caps
# ──────────────────────────────────────────────
MAX_RESULTS_PER_KEYWORD = 20
