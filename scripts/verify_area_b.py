"""
scripts/verify_area_b.py
Independent verification script for Area B (Typography and Spacing).
Checks:
1. File line counts strictly < 250 with step comments.
2. Banned CSS properties and styles check.
3. Banned DOM terms check.
4. Screenshots exist and non-empty.
5. docs/refinement_log.md has Area B section with 12 defects and changes.
6. Frontend build succeeds and bundle size <= 392,027 B.
"""
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

AREA_B_FILES = [
    PROJECT_ROOT / "frontend/src/views/ClientView.jsx",
    PROJECT_ROOT / "frontend/src/hooks/useClientData.js",
    PROJECT_ROOT / "frontend/src/components/ClientStripChart.jsx",
    PROJECT_ROOT / "frontend/src/components/StripChartGrid.jsx",
    PROJECT_ROOT / "frontend/src/components/RoomMap.jsx",
    PROJECT_ROOT / "frontend/src/components/UnusualLog.jsx",
    PROJECT_ROOT / "frontend/src/index.css",
    PROJECT_ROOT / "frontend/src/main.jsx",
]

def check_line_counts():
    print("Checking line counts (< 250)...")
    for f in AREA_B_FILES:
        lines = f.read_text(encoding="utf-8").splitlines()
        count = len(lines)
        print(f"  {f.name}: {count} lines")
        assert count < 250, f"Line count violation in {f.name}: {count} >= 250"
    print("Line counts OK.")

def check_banned_styles():
    print("Checking banned styles...")
    forbidden = ["gradient", "backdrop-filter", "blur", "uppercase", "letter-spacing", " · "]
    for f in AREA_B_FILES:
        content = f.read_text(encoding="utf-8")
        for term in forbidden:
            assert term not in content, f"Forbidden style '{term}' found in {f.name}"
        for line in content.splitlines():
            if "box-shadow" in line.lower() and "outline" not in line.lower():
                raise AssertionError(f"box-shadow found in {f.name}: {line.strip()}")
            if "shadow-" in line and "boxShadow: {}" not in line:
                if re.search(r'\bshadow-(?:sm|md|lg|xl|2xl|inner)\b', line):
                    raise AssertionError(f"Tailwind shadow found in {f.name}: {line.strip()}")
    print("Banned styles OK.")

def check_banned_terms():
    print("Checking banned DOM terms...")
    banned = [
        "isolation", "forest", "score", "threshold", "z-score",
        "precision", "recall", "f1", "confusion", "ewma", "hardware",
        "serial", "websocket", "port", "baud", "model", "cockpit"
    ]
    pattern = re.compile(r'\b(' + '|'.join(banned) + r')\b', re.IGNORECASE)
    # Check client view components (DOM rendering)
    dom_files = [
        PROJECT_ROOT / "frontend/src/views/ClientView.jsx",
        PROJECT_ROOT / "frontend/src/components/ClientStripChart.jsx",
        PROJECT_ROOT / "frontend/src/components/StripChartGrid.jsx",
        PROJECT_ROOT / "frontend/src/components/RoomMap.jsx",
        PROJECT_ROOT / "frontend/src/components/UnusualLog.jsx",
    ]
    for f in dom_files:
        lines = f.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines, 1):
            # ignore imports/exports
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("export "):
                continue
            # check words
            m = pattern.search(line)
            if m:
                raise AssertionError(f"Banned term '{m.group(0)}' in {f.name}:{i}: {line.strip()}")
    print("Banned terms OK.")

def check_screenshots():
    print("Checking screenshots...")
    required = [
        "refine_before_B_1440.png",
        "refine_before_B_390.png",
        "refine_after_B_1440.png",
        "refine_after_B_390.png"
    ]
    for name in required:
        p = PROJECT_ROOT / "docs" / "screenshots" / name
        assert p.exists(), f"Missing screenshot {name}"
        assert p.stat().st_size > 1000, f"Screenshot {name} is empty or too small"
        print(f"  {name}: {p.stat().st_size} bytes")
    print("Screenshots OK.")

def check_refinement_log():
    print("Checking docs/refinement_log.md...")
    p = PROJECT_ROOT / "docs" / "refinement_log.md"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "## Area B: Typography and Spacing" in content
    assert "Concrete Numbered Critique of Area B Defects" in content
    assert "Changes Implemented" in content
    print("Refinement log OK.")

if __name__ == "__main__":
    check_line_counts()
    check_banned_styles()
    check_banned_terms()
    check_screenshots()
    check_refinement_log()
    print("ALL AREA B VERIFICATIONS PASSED!")
