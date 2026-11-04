#!/usr/bin/env python3
"""
Environment verification script for IoT Anomaly Detection.

Checks Python version, dependencies, config, and data availability.
"""
import sys
import subprocess
from pathlib import Path
from importlib.metadata import version, PackageNotFoundError


def check_python_version() -> bool:
    """Verify Python version >= 3.10."""
    version_info = sys.version_info
    print(f"Python version: {version_info.major}.{version_info.minor}.{version_info.micro}")
    if version_info.major == 3 and version_info.minor >= 10:
        print("  [OK] Python >= 3.10")
        return True
    print("  [FAIL] Python >= 3.10 required")
    return False


def check_dependencies() -> bool:
    """Verify required packages are installed."""
    required = [
        "pyserial",
        "pandas",
        "numpy",
        "scikit-learn",
        "scipy",
        "joblib",
        "yaml",  # pyyaml
    ]
    
    all_ok = True
    for pkg in required:
        try:
            ver = version(pkg if pkg != "yaml" else "pyyaml")
            print(f"  [OK] {pkg}=={ver}")
        except PackageNotFoundError:
            print(f"  [FAIL] {pkg} NOT INSTALLED")
            all_ok = False
    return all_ok


def check_config() -> bool:
    """Verify config.yaml exists and loads correctly."""
    config_path = Path("config.yaml")
    if not config_path.exists():
        print("  ✗ config.yaml not found")
        return False
    
    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        required_sections = ["serial", "data", "features", "model", "model_paths", "detection"]
        for section in required_sections:
            if section not in data:
                print(f"  [FAIL] Missing config section: {section}")
                return False
        print("  [OK] config.yaml valid")
        return True
    except Exception as e:
        print(f"  [FAIL] config.yaml parse error: {e}")
        return False


def check_data_files() -> bool:
    """Verify raw data files exist."""
    raw_dir = Path("data/raw")
    required_files = [
        "normal_data.csv",
        "pilot_data.csv",
        "test.csv",
        "test_labels.csv",
    ]
    
    all_ok = True
    for fname in required_files:
        fpath = raw_dir / fname
        if fpath.exists():
            lines = fpath.read_text(encoding="utf-8").strip().splitlines()
            print(f"  [OK] {fname} ({len(lines)} lines)")
        else:
            print(f"  [FAIL] {fname} NOT FOUND")
            all_ok = False
    return all_ok


def check_project_structure() -> bool:
    """Verify expected directories exist."""
    required_dirs = [
        "firmware",
        "collect",
        "data/raw",
        "data/processed",
        "data/splits",
        "preprocess",
        "eda/notebooks",
        "eda/reports",
        "features",
        "train",
        "evaluate",
        "models",
        "detect",
        "dashboard/components",
        "tests/unit",
        "tests/integration",
        "tests/fixtures",
        "docs/runbooks",
        ".github/workflows",
    ]
    
    all_ok = True
    for d in required_dirs:
        p = Path(d)
        if p.exists() and p.is_dir():
            print(f"  [OK] {d}/")
        else:
            print(f"  [FAIL] {d}/ MISSING")
            all_ok = False
    return all_ok


def check_config_module() -> bool:
    """Verify config.py loads correctly."""
    try:
        from config import config
        print(f"  [OK] config.py loads")
        print(f"    serial.port = {config.serial_port}")
        print(f"    baudrate = {config.baudrate}")
        print(f"    sampling_interval_ms = {config.sampling_interval_ms}")
        print(f"    raw_dir = {config.raw_dir}")
        return True
    except Exception as e:
        print(f"  [FAIL] config.py error: {e}")
        return False


def main() -> int:
    """Run all verification checks."""
    print("=" * 60)
    print("IoT Anomaly Detection - Environment Verification")
    print("=" * 60)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Configuration", check_config),
        ("Config Module", check_config_module),
        ("Data Files", check_data_files),
        ("Project Structure", check_project_structure),
    ]
    
    results = {}
    for name, check_fn in checks:
        print(f"\n{name}:")
        results[name] = check_fn()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_passed = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n[OK] All checks passed. Environment ready.")
        return 0
    else:
        print("\n[FAIL] Some checks failed. Fix issues before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())