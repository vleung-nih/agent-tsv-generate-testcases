# src/wire_expected.py
import json, re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
from .expected_results_client import ExpectedResultsClient

# ---- Filter extraction helpers ---------------------------------------------

def _from_context(tc: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Preferred: test case already carries a structured context."""
    ctx = tc.get("context") or {}
    study = ctx.get("study")
    filters = ctx.get("expected_filters") or ctx.get("filters")
    if study and isinstance(filters, dict):
        return study, filters
    return None

_FILTER_KEYS = [
    "Breed",
    "Diagnosis.disease_term",
    "Sex",
    # add common keys you expect here; the regex fallback helps too
]

def _parse_filters_from_text(txt: str) -> Dict[str, Any]:
    """
    Fallback: parse a step like:
    'Apply filters: Breed=Greyhound; Diagnosis.disease_term=Osteosarcoma; Sex=Male,Female'
    """
    filters: Dict[str, Any] = {}
    # Split on ; or , then look for key=value
    parts = re.split(r"[;]", txt)
    for raw in parts:
        m = re.search(r"\s*([A-Za-z0-9._-]+)\s*=\s*([A-Za-z0-9 _\-/,.]+)\s*$", raw)
        if not m:
            continue
        key, val = m.group(1).strip(), m.group(2).strip()
        # Convert comma lists -> arrays
        if "," in val:
            vals = [v.strip() for v in val.split(",") if v.strip()]
        else:
            vals = [val]
        filters[key] = vals
    return filters

def _from_steps(tc: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Heuristic: find a step mentioning a study and filters.
    Customize this for your generator’s step style.
    """
    steps = tc.get("steps") or []
    study = None
    filters: Dict[str, Any] = {}
    for s in steps:
        s_text = s if isinstance(s, str) else str(s)
        # study inference
        m_study = re.search(r"\bStudy\s+([A-Za-z0-9_-]+)\b", s_text)
        if m_study:
            study = m_study.group(1)
        # filter inference
        if "Apply filters:" in s_text or "Filters:" in s_text:
            parsed = _parse_filters_from_text(s_text)
            filters.update(parsed)
    if study and filters:
        return study, filters
    return None

def extract_study_filters(tc: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Strategy:
      1) Prefer structured context.
      2) Fall back to parsing steps.
      3) Direct extraction from test case structure.
    """
    # First try direct extraction from test case structure
    study = tc.get("study")
    filters = tc.get("filters", {})
    if study and isinstance(filters, dict):
        # Map filter names for API compatibility
        mapped_filters = {}
        for key, value in filters.items():
            if key == "Diagnosis":
                mapped_filters["Diagnosis.disease_term"] = value
            else:
                mapped_filters[key] = value
        return study, mapped_filters
    
    return _from_context(tc) or _from_steps(tc)

# ---- Main wiring -----------------------------------------------------------

def wire_expected_for_run(run_dir: Path) -> Dict[str, Any]:
    """
    Reads test_cases.json and fetches expected results for each case that has study+filters.
    Writes expected_results.json and also augments test_cases.json with an 'expected' block.
    Returns the aggregated expected_results payload for convenience.
    """
    tc_path = run_dir / "test_cases.json"
    if not tc_path.exists():
        raise FileNotFoundError(f"Missing test_cases.json at: {tc_path}")

    with open(tc_path, "r") as f:
        test_cases: List[Dict[str, Any]] = json.load(f)

    client = ExpectedResultsClient()
    aggregated: Dict[str, Any] = {"test_cases": []}

    for tc in test_cases:
        study_filters = extract_study_filters(tc)
        if not study_filters:
            tc["expected"] = {"available": False, "reason": "no study/filters found"}
            aggregated["test_cases"].append(
                {"id": tc.get("id"), "available": False, "reason": "no study/filters found"}
            )
            continue

        study, filters = study_filters
        try:
            expected = client.get_expected_with_retry(study, filters)
            # store on tc for later phases
            tc["expected"] = {
                "available": True,
                "study": study,
                "filters": filters,
                "data": expected,   # raw API response
            }
            aggregated["test_cases"].append(
                {
                    "id": tc.get("id"),
                    "available": True,
                    "study": study,
                    "filters": filters,
                    "data": expected,
                }
            )
        except Exception as e:
            tc["expected"] = {"available": False, "reason": str(e)}
            aggregated["test_cases"].append(
                {"id": tc.get("id"), "available": False, "reason": str(e)}
            )

    # Write back augmented test cases (non-destructive—just adds 'expected')
    with open(tc_path, "w") as f:
        json.dump(test_cases, f, indent=2)

    # Write a separate expected_results.json
    er_path = run_dir / "expected_results.json"
    with open(er_path, "w") as f:
        json.dump(aggregated, f, indent=2)

    # Also print to console
    print("\n=== EXPECTED RESULTS (aggregated) ===")
    print(json.dumps(aggregated, indent=2))
    print("=== END EXPECTED RESULTS ===\n")

    return aggregated
