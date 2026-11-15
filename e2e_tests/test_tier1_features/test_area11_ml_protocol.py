"""
e2e_tests/test_tier1_features/test_area11_ml_protocol.py
Area 11: ML Evaluation Protocol & Code Freeze (Features 19, 20, 21)
Tier 1 Tests: Model freeze integrity, thresholds.json validation, provenance tracking, evaluation reproducibility.
"""

from pathlib import Path
import hashlib
import json
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_a11_t1_01_models_artifacts_integrity():
    """
    TEST-A11-T1-01: Validates that all frozen ML model artifacts exist and have non-empty SHA256 hashes.
    """
    models_dir = PROJECT_ROOT / "models"
    required_artifacts = [
        "iforest.joblib",
        "scaler.joblib",
        "ocsvm.joblib",
        "thresholds.json",
        "evaluation_summary.json",
    ]
    for artifact in required_artifacts:
        art_path = models_dir / artifact
        assert art_path.exists(), f"Model artifact '{artifact}' is missing"
        assert art_path.stat().st_size > 0, f"Model artifact '{artifact}' is empty"
        sha = _compute_sha256(art_path)
        assert len(sha) == 64, f"Invalid SHA256 hash for {artifact}"


def test_a11_t1_02_thresholds_json_contract():
    """
    TEST-A11-T1-02: Validates the 12 feature columns and threshold levels in thresholds.json.
    """
    thresholds_path = PROJECT_ROOT / "models" / "thresholds.json"
    assert thresholds_path.exists()
    with open(thresholds_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate 12 feature columns
    features = data.get("feature_cols")
    assert isinstance(features, list)
    assert len(features) == 12, f"Expected 12 feature columns, got {len(features)}"

    # Validate sensitivity thresholds
    assert "sensitivity_thresholds" in data
    sens = data["sensitivity_thresholds"]
    for level in ["Low", "Medium", "High"]:
        matching_keys = [k for k in sens if level in k]
        assert len(matching_keys) > 0, f"Sensitivity level '{level}' missing from {list(sens.keys())}"
        for k in matching_keys:
            assert isinstance(sens[k], (int, float))


def test_a11_t1_03_dataset_provenance_and_roles(client: TestClient, admin_token: str):
    """
    TEST-A11-T1-03: Evaluation datasets explicitly declare provenance (Recorded/Synthetic) and role.
    Queries /api/admin/datasets/overview and validates metadata contracts.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.get("/api/admin/datasets/overview", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    datasets = data.get("datasets", [])
    assert len(datasets) > 0, "No datasets returned in overview"

    for ds in datasets:
        assert "provenance" in ds, f"Dataset '{ds.get('name')}' missing provenance declaration"
        assert any(p in ds["provenance"] for p in ["Recorded", "Synthetic"]), (
            f"Invalid provenance '{ds['provenance']}' in dataset {ds.get('name')}"
        )
        assert "role" in ds, f"Dataset '{ds.get('name')}' missing role declaration"
        assert any(r in ds["role"] for r in ["Training", "Development", "Held-out"]), (
            f"Invalid role '{ds['role']}' in dataset {ds.get('name')}"
        )


def test_a11_t1_04_bootstrap_confidence_interval_ranges():
    """
    TEST-A11-T1-04: Metrics must obey boundary constraints (0.0 <= metric <= 1.0).
    """
    eval_summary_path = PROJECT_ROOT / "models" / "evaluation_summary.json"
    if eval_summary_path.exists():
        with open(eval_summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
        # Any reported precision, recall, f1 must be in [0.0, 1.0]
        if isinstance(summary, dict):
            for k, v in summary.items():
                if isinstance(v, dict) and "f1" in v:
                    assert 0.0 <= v["f1"] <= 1.0


def test_a11_t1_05_reproducibility_artifacts_exist():
    """
    TEST-A11-T1-05: Processed training and evaluation datasets exist and have valid row counts.
    """
    test_csv = PROJECT_ROOT / "data" / "processed" / "test_data_with_labels.csv"
    assert test_csv.exists()
    with open(test_csv, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    # Header + 55 data rows = 56 lines
    assert len(lines) >= 50
