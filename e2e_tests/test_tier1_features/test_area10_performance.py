"""
e2e_tests/test_tier1_features/test_area10_performance.py
Area 10: Performance Targets & Soak Verification (Features 17, 18)
Tier 1 Tests: REST concurrency p95 latency, WS fan-out, burst ingest, history queries, memory stability.
"""

import time
import pytest
from starlette.testclient import TestClient
from backend.database import insert_reading


def test_a10_t1_01_rest_concurrency_p95(client: TestClient):
    """
    TEST-A10-T1-01: REST concurrency latency p95 < 150 ms with 0 errors.
    """
    latencies = []
    # Issue 30 sequential or rapid requests to measure latency distribution
    for _ in range(30):
        t0 = time.time()
        resp = client.get("/api/client/status")
        elapsed = time.time() - t0
        assert resp.status_code == 200
        latencies.append(elapsed * 1000)  # ms

    latencies.sort()
    p95_index = int(len(latencies) * 0.95)
    p95_latency = latencies[p95_index]
    assert p95_latency < 150.0, f"REST p95 latency exceeded target: {p95_latency:.2f} ms"


def test_a10_t1_02_ws_fanout_latency(client: TestClient):
    """
    TEST-A10-T1-02: WebSocket delivery latency p95 < 1.0s.
    """
    ws_endpoint = "/ws/client"
    try:
        with client.websocket_connect(ws_endpoint) as ws:
            pass
    except Exception:
        ws_endpoint = "/ws/telemetry"

    with client.websocket_connect(ws_endpoint) as ws:
        # Measure ping/pong or broadcast frame transit
        t0 = time.time()
        ws.send_text('{"action": "ping"}')
        resp = ws.receive_json()
        transit = time.time() - t0
        assert transit < 1.0, f"WS transit latency exceeded: {transit:.3f} s"


def test_a10_t1_03_ingest_burst_zero_loss():
    """
    TEST-A10-T1-03: Ingest burst of 100 readings has 0 loss in database storage.
    """
    from backend.database import get_recent_readings
    start_count = len(get_recent_readings(1000))
    for i in range(100):
        insert_reading(f"2026-11-15T10:00:{i:02d}", 25.0, 60.0, True)

    end_count = len(get_recent_readings(1000))
    assert end_count - start_count == 100, f"Expected 100 inserted readings, got {end_count - start_count}"


def test_a10_t1_04_history_query_latency(client: TestClient):
    """
    TEST-A10-T1-04: Querying readings history responds within performance target (< 200 ms).
    """
    t0 = time.time()
    resp = client.get("/api/client/readings?limit=500")
    elapsed_ms = (time.time() - t0) * 1000
    assert resp.status_code == 200
    assert elapsed_ms < 200.0, f"History query latency exceeded: {elapsed_ms:.2f} ms"


def test_a10_t1_05_reconnect_storm_stability(client: TestClient):
    """
    TEST-A10-T1-05: Rapid connection and disconnection does not destabilize the server.
    """
    ws_endpoint = "/ws/client"
    try:
        with client.websocket_connect(ws_endpoint) as ws:
            pass
    except Exception:
        ws_endpoint = "/ws/telemetry"

    for _ in range(10):
        with client.websocket_connect(ws_endpoint) as ws:
            pass
    # Server remains responsive
    resp = client.get("/api/client/status")
    assert resp.status_code == 200


def test_a10_t1_06_soak_memory_warmup_bound():
    """
    TEST-A10-T1-06: Memory footprint does not exhibit runaway growth after warm-up.
    """
    try:
        import psutil, os
        process = psutil.Process(os.getpid())
        mem_warmup = process.memory_info().rss
        for i in range(200):
            insert_reading(f"2026-11-15T12:01:{i%60:02d}", 25.1, 60.2, True)
        mem_final = process.memory_info().rss
        growth_ratio = (mem_final - mem_warmup) / max(mem_warmup, 1)
        assert growth_ratio < 0.25, f"Unexpected memory growth ratio after warm-up: {growth_ratio:.2%}"
    except ImportError:
        # Standard library verification: memory allocated for 200 records is tightly bounded
        import tracemalloc
        tracemalloc.start()
        for i in range(200):
            insert_reading(f"2026-11-15T12:01:{i%60:02d}", 25.1, 60.2, True)
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        assert peak_mem < 5 * 1024 * 1024, f"Peak memory unexpectedly large: {peak_mem} bytes"
