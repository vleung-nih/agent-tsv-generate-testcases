# src/filters_utils.py
from typing import Dict, List, Any

# Map UI-ish labels to backend/API keys
NORMALIZATION_MAP = {
    "Diagnosis": "Diagnosis.disease_term",
    "Stage of Disease": "Diagnosis.stage_of_disease",
    # Pass-through examples (listed explicitly for clarity; they’ll also fall through)
    "Breed": "Breed",
    "Sex": "Sex",
}

def normalize_filters(raw_filters: Dict[str, List[Any]]) -> Dict[str, List[Any]]:
    out: Dict[str, List[Any]] = {}
    for k, v in (raw_filters or {}).items():
        norm_k = NORMALIZATION_MAP.get(k, k)
        out[norm_k] = v
    return out
