"""Integration tests for end-to-end inference and all 6 Streamlit dashboards."""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest


def test_eval_suite_end_to_end_performance_bounds(project_root: Path):
    import json
    summary = json.loads((project_root / "models" / "evaluation_summary.json").read_text(encoding="utf-8"))
    eval_hyb = summary["datasets"]["eval_suite"]["Hybrid (IF + EWMA-Z)"]
    pilot_hyb = summary["datasets"]["pilot"]["Hybrid (IF + EWMA-Z)"]
    live_fp = summary["eval_suite_breakdown"]["live_dht11_normal"]["hybrid_fp"]

    assert eval_hyb["f1"] >= 0.90
    assert eval_hyb["events_caught"] == eval_hyb["events_total"]
    assert pilot_hyb["f1"] >= 0.90
    assert pilot_hyb["events_caught"] == pilot_hyb["events_total"]
    assert live_fp == 0


@pytest.mark.parametrize(
    "rel_app",
    [
        "dashboard/Home.py",
        "dashboard/pages/1_Analyse.py",
        "dashboard/pages/2_Results.py",
        "dashboard/pages/3_Model_Metrics.py",
        "dashboard/user_app.py",
        "dashboard/admin_app.py",
    ],
)
def test_streamlit_dashboards_render_without_exception(project_root: Path, rel_app: str):
    app_path = project_root / rel_app
    at = AppTest.from_file(str(app_path), default_timeout=25)
    at.run()
    assert not at.exception, f"Exception in {rel_app}: {at.exception}"
    assert not at.error, f"Error alert in {rel_app}: {at.error}"


def test_analyse_and_results_interactive_flow(project_root: Path):
    at_an = AppTest.from_file(str(project_root / "dashboard" / "pages" / "1_Analyse.py"), default_timeout=25).run()
    assert not at_an.exception
    if at_an.radio:
        at_an.radio[0].set_value("Demo data").run()
    for choice in [
        "Pilot Session Annotated (3,087 rows)",
        "Legacy Test Set (56 rows)",
        "Unseen Multi-Fault + Live Suite (1,950 rows)",
    ]:
        at_an.selectbox[0].set_value(choice).run()
        at_an.button[0].click().run()
        assert not at_an.exception, f"Exception loading {choice}: {at_an.exception}"
        assert not at_an.error, f"Error loading {choice}: {at_an.error}"
        assert at_an.session_state["processed_df"] is not None

    at_res = AppTest.from_file(str(project_root / "dashboard" / "pages" / "2_Results.py"), default_timeout=25)
    at_res.session_state["processed_df"] = at_an.session_state["processed_df"]
    at_res.run()
    assert not at_res.exception
    assert not at_res.error
    if at_res.sidebar.selectbox:
        at_res.sidebar.selectbox[0].set_value("Low (0.1th %ile)").run()
        assert not at_res.exception

    # Verify live buffer schema compatibility between 2_Results.py & 1_Analyse.py without infinite rerun
    from features.feature_engine import MODEL_FEATURE_COLS, apply_gated_persistence, build_features, compute_adaptive_ewma_z
    import joblib, json
    live_sample = pd.DataFrame([
        {"timestamp": f"2026-11-10T17:00:{i*2:02d}", "temperature": 29.5, "humidity": 53.7}
        for i in range(6)
    ])
    feat_live = build_features(live_sample)
    iso = joblib.load(project_root / "models" / "iforest.joblib")
    scaler = joblib.load(project_root / "models" / "scaler.joblib")
    th = json.loads((project_root / "models" / "thresholds.json").read_text(encoding="utf-8"))
    scores = iso.decision_function(scaler.transform(feat_live[MODEL_FEATURE_COLS]))
    if_raw = scores < th["iforest_threshold"]
    if_flg = apply_gated_persistence(if_raw, feat_live["session_id"].to_numpy(), features_df=feat_live)
    ez = compute_adaptive_ewma_z(feat_live, th["ewma_temp_std"], th["ewma_hum_std"])
    ez_flg = ez > th["ewma_zscore_threshold"]
    feat_live["iforest_score"] = scores
    feat_live["iforest_raw_anomaly"] = if_raw
    feat_live["iforest_anomaly"] = if_flg
    feat_live["ewma_z_score"] = ez
    feat_live["ewma_z_anomaly"] = ez_flg
    feat_live["zscore_anomaly"] = False
    feat_live["hybrid_anomaly"] = if_flg | ez_flg
    feat_live["source"] = "live"

    at_back = AppTest.from_file(str(project_root / "dashboard" / "pages" / "1_Analyse.py"), default_timeout=25)
    at_back.session_state["processed_df"] = feat_live
    at_back.run()
    assert not at_back.exception
    assert not at_back.error
