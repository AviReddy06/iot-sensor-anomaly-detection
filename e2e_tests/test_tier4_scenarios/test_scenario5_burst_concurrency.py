"""
e2e_tests/test_tier4_scenarios/test_scenario5_burst_concurrency.py
Tier 4 Scenario 5: High-Concurrency Burst Streaming with Simultaneous Polling & Public Clients
Simulates crisis telemetry burst while concurrent REST clients poll endpoints without database lock.
"""

import concurrent.futures
import time
import pytest
from starlette.testclient import TestClient
from backend.database import insert_reading


def test_scenario_05_burst_concurrency_storm(client: TestClient):
    """
    Scenario 5: High-concurrency storm under rapid ingestion.
    1. Continuous stream of readings ingested by background writer thread.
    2. Concurrent REST queries to /api/client/status, /api/client/readings, /api/client/events.
    3. Assert 0 database lock errors, 100% 200 OK responses, and p95 latency < 250ms.
    """
    latencies = []

    def writer_worker():
        for i in range(30):
            insert_reading(f"2026-11-15T10:00:{i:02d}", 25.0 + (i * 0.05), 60.0, True)
            time.sleep(0.005)

    def reader_worker():
        t0 = time.time()
        resp_status = client.get("/api/client/status")
        resp_readings = client.get("/api/client/readings?limit=20")
        resp_events = client.get("/api/client/events")
        elapsed = (time.time() - t0) * 1000

        assert resp_status.status_code == 200
        assert resp_readings.status_code == 200
        assert resp_events.status_code == 200
        return elapsed

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        writer_future = executor.submit(writer_worker)
        reader_futures = [executor.submit(reader_worker) for _ in range(25)]

        for f in concurrent.futures.as_completed(reader_futures):
            latencies.append(f.result())
        writer_future.result()

    assert len(latencies) == 25
    p95 = sorted(latencies)[int(len(latencies) * 0.95)]
    assert p95 < 250.0, f"p95 latency during concurrent burst exceeded target: {p95:.2f} ms"
