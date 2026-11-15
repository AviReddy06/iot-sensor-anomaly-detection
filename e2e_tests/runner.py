"""
e2e_tests/runner.py
Standalone test runner and orchestrator for E2E Testing Track.
Executes test tiers, collects metrics, and generates formatted reports.
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any
import pytest

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

E2E_DIR = PROJECT_ROOT / "e2e_tests"

TIER_MAP = {
    1: E2E_DIR / "test_tier1_features",
    2: E2E_DIR / "test_tier2_boundaries",
    3: E2E_DIR / "test_tier3_cross_features",
    4: E2E_DIR / "test_tier4_scenarios",
}


class E2ETestResultCollector:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = 0
        self.tests: List[Dict[str, Any]] = []

    def pytest_runtest_logreport(self, report):
        if report.when == "call":
            item = {
                "nodeid": report.nodeid,
                "outcome": report.outcome,
                "duration": report.duration,
            }
            if report.passed:
                self.passed += 1
            elif report.failed:
                self.failed += 1
                item["error"] = str(report.longrepr)
            elif report.skipped:
                self.skipped += 1
            self.tests.append(item)
        elif report.when == "setup" and report.failed:
            self.errors += 1
            self.tests.append({
                "nodeid": report.nodeid,
                "outcome": "error",
                "duration": report.duration,
                "error": str(report.longrepr),
            })


def run_tier(tier: int, run_slow: bool = False, verbose: bool = False) -> Dict[str, Any]:
    tier_path = TIER_MAP.get(tier)
    if not tier_path or not tier_path.exists():
        return {
            "tier": tier,
            "status": "NOT_FOUND",
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "duration": 0.0,
            "tests": [],
        }

    collector = E2ETestResultCollector()
    pytest_args = [str(tier_path)]
    if not run_slow:
        pytest_args.extend(["-m", "not slow"])
    if verbose:
        pytest_args.append("-v")
    else:
        pytest_args.append("-q")

    start_time = time.time()
    exit_code = pytest.main(pytest_args, plugins=[collector])
    elapsed = time.time() - start_time

    return {
        "tier": tier,
        "path": str(tier_path),
        "exit_code": int(exit_code),
        "status": "PASSED" if collector.failed == 0 and collector.errors == 0 else "FAILED",
        "passed": collector.passed,
        "failed": collector.failed,
        "skipped": collector.skipped,
        "errors": collector.errors,
        "total": collector.passed + collector.failed + collector.skipped + collector.errors,
        "duration": round(elapsed, 2),
        "tests": collector.tests,
    }


def main():
    parser = argparse.ArgumentParser(description="E2E Test Suite Runner for IoT Anomaly Detection")
    parser.add_argument(
        "--tier",
        type=str,
        default="1,2,3,4",
        help="Comma-separated tiers to run (e.g. 1, 1,2, 1,2,3,4). Default: 1,2,3,4",
    )
    parser.add_argument(
        "--json",
        type=str,
        default=None,
        help="Path to write JSON execution report",
    )
    parser.add_argument(
        "--run-slow",
        action="store_true",
        help="Include tests marked with @pytest.mark.slow (e.g. long soak)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose test execution output",
    )

    args = parser.parse_args()

    try:
        tiers = [int(t.strip()) for t in args.tier.split(",") if t.strip()]
    except ValueError:
        print(f"Error: Invalid tier specification '{args.tier}'. Must be numbers like 1,2,3,4.")
        sys.exit(2)

    print("=" * 70)
    print("AI-Based IoT Sensor Anomaly Detection — E2E Test Suite")
    print(f"Selected Tiers: {tiers} | Run Slow: {args.run_slow}")
    print("=" * 70)

    all_results = []
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_errors = 0
    total_duration = 0.0

    for tier in tiers:
        print(f"\n>>> Running Tier {tier} ({TIER_MAP.get(tier, 'Unknown')})...")
        res = run_tier(tier, run_slow=args.run_slow, verbose=args.verbose)
        all_results.append(res)

        total_passed += res["passed"]
        total_failed += res["failed"]
        total_skipped += res["skipped"]
        total_errors += res["errors"]
        total_duration += res["duration"]

        print(
            f"Tier {tier} Results: {res['status']} | Passed: {res['passed']} | "
            f"Failed: {res['failed']} | Skipped: {res['skipped']} | Duration: {res['duration']}s"
        )

    print("\n" + "=" * 70)
    print("E2E Test Execution Summary")
    print("=" * 70)
    print(f"{'Tier':<10} | {'Status':<10} | {'Passed':<8} | {'Failed':<8} | {'Skipped':<8} | {'Duration':<10}")
    print("-" * 70)
    for res in all_results:
        print(
            f"Tier {res['tier']:<8} | {res['status']:<10} | {res['passed']:<8} | "
            f"{res['failed']:<8} | {res['skipped']:<8} | {res['duration']:<10}s"
        )
    print("-" * 70)
    total_tests = total_passed + total_failed + total_skipped + total_errors
    print(
        f"TOTAL: {total_tests} tests | Passed: {total_passed} | Failed: {total_failed} | "
        f"Skipped: {total_skipped} | Time: {round(total_duration, 2)}s"
    )
    print("=" * 70)

    if args.json:
        report_data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "skipped": total_skipped,
            "errors": total_errors,
            "duration": round(total_duration, 2),
            "tiers": all_results,
        }
        json_path = Path(args.json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        print(f"\nJSON report written to: {json_path}")

    # Return non-zero exit code if any test failed
    sys.exit(1 if (total_failed > 0 or total_errors > 0) else 0)


if __name__ == "__main__":
    main()
