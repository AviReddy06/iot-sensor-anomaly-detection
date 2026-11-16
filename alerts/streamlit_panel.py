"""
alerts/streamlit_panel.py
Shared Streamlit sidebar controls and live status rendering for building-wide employee alerts.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional

import pandas as pd
import streamlit as st

from alerts.notifier import AlertManager, load_alert_settings


def get_alert_manager() -> AlertManager:
    """Return shared AlertManager preserved across Streamlit reruns and page switches."""
    if "alert_manager" not in st.session_state or st.session_state.alert_manager is None:
        st.session_state.alert_manager = AlertManager(load_alert_settings())
    return st.session_state.alert_manager


def render_alert_sidebar(
    page_id: str,
    default_temp: float = 26.0,
    default_hum: float = 58.0,
) -> AlertManager:
    """Render sidebar controls for live employee notifications and return shared AlertManager."""
    mgr = get_alert_manager()
    curr = mgr.settings

    with st.sidebar:
        with st.expander("🔔 Employee Alerts (Live Only)", expanded=False):
            enabled = st.checkbox(
                "Enable Broadcast Alerts",
                value=curr.enabled,
                key=f"alert_en_{page_id}",
                help="Sends push/webhook/email alerts only during live ESP32 streaming (never during Demo/CSV playback).",
            )
            zone = st.text_input(
                "Building / Room Zone",
                value=curr.building_zone,
                key=f"alert_zone_{page_id}",
            )
            ntfy_topic = st.text_input(
                "ntfy.sh Topic",
                value=curr.ntfy_topic,
                key=f"alert_ntfy_{page_id}",
                placeholder="e.g. avi-office-climate-alerts",
                help="Employees open ntfy app or https://ntfy.sh/<topic> to receive live building push alerts.",
            )
            sev_options = ["Medium", "High", "Low"]
            sev_idx = sev_options.index(curr.min_severity) if curr.min_severity in sev_options else 0
            min_severity = st.selectbox(
                "Broadcast Minimum Severity",
                sev_options,
                index=sev_idx,
                key=f"alert_sev_{page_id}",
            )
            comfort_enabled = st.checkbox(
                "AC / Building Comfort Guardrails",
                value=curr.comfort_enabled,
                key=f"alert_comfort_{page_id}",
                help="Alert even on slow HVAC/AC drift outside comfort range.",
            )
            c_t_min, c_t_max = curr.comfort_temp_min, curr.comfort_temp_max
            if comfort_enabled:
                col_a, col_b = st.columns(2)
                c_t_min = col_a.number_input("Min °C", value=float(curr.comfort_temp_min), step=0.5, key=f"alert_tmin_{page_id}")
                c_t_max = col_b.number_input("Max °C", value=float(curr.comfort_temp_max), step=0.5, key=f"alert_tmax_{page_id}")

            updated = replace(
                curr,
                enabled=bool(enabled),
                building_zone=zone.strip() or curr.building_zone,
                ntfy_topic=ntfy_topic.strip(),
                min_severity=min_severity,
                comfort_enabled=bool(comfort_enabled),
                comfort_temp_min=float(c_t_min),
                comfort_temp_max=float(c_t_max),
            )
            mgr.update_settings(updated)

            channels = updated.active_channels()
            if updated.ntfy_topic:
                subscribe_url = f"{updated.ntfy_server.rstrip('/')}/{updated.ntfy_topic.strip('/')}"
                st.caption(f"Subscribe link: [{subscribe_url}]({subscribe_url})")
            st.caption(f"Active channels: `{', '.join(channels) if channels else 'local log only'}`")

            if st.button("📢 Send Test Alert", key=f"alert_test_{page_id}", width="stretch"):
                results = mgr.send_test_alert(temperature=default_temp, humidity=default_hum)
                if not results:
                    st.info("Test alert written to local log (`logs/alert_history.csv`). Enter an ntfy topic or configure `.env` to push remotely.")
                elif all(r.ok for r in results):
                    st.success(f"Test alert delivered via {', '.join(r.channel for r in results)}!")
                else:
                    errs = "; ".join(f"{r.channel}: {r.detail}" for r in results if not r.ok)
                    st.warning(f"Partial/failed delivery: {errs}")

            st.caption(f"Status: {mgr.state.last_status_message}")

    return mgr


def load_recent_alert_log(limit: int = 30) -> Optional[pd.DataFrame]:
    """Load recent logged employee alerts from disk if available."""
    mgr = get_alert_manager()
    path = mgr.settings.log_file
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
        return df.tail(limit).iloc[::-1].reset_index(drop=True)
    except Exception:
        return None
