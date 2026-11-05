#!/usr/bin/env python3
"""
Repair notebooks using lenient JSON parsers (json5, demjson) then re-serialize with nbformat.
"""

import json
import nbformat
from pathlib import Path
import sys
import subprocess

NOTEBOOKS = [
    "eda/notebooks/01_eda.ipynb",
    "preprocess/notebooks/02_data_preprocessing.ipynb",
    "features/notebooks/03_feature_engineering.ipynb",
]

BACKUP_DIR = Path("notebook_backups")
BACKUP_DIR.mkdir(exist_ok=True)


def try_parse_with_json5(content: str):
    """Try parsing with json5 library."""
    try:
        import json5
        return json5.loads(content)
    except Exception as e:
        return None, f"json5: {e}"


def try_parse_with_demjson(content: str):
    """Try parsing with demjson library."""
    try:
        import demjson3 as demjson
        return demjson.decode(content)
    except ImportError:
        try:
            import demjson
            return demjson.decode(content)
        except ImportError:
            return None, "demjson not available"
        except Exception as e:
            return None, f"demjson: {e}"


def try_parse_with_standard_json(content: str):
    """Try standard json parser."""
    try:
        return json.loads(content)
    except Exception as e:
        return None, f"json: {e}"


def repair_notebook(nb_path: Path) -> tuple[bool, str]:
    print(f"\n{'='*60}")
    print(f"Repairing: {nb_path}")
    print(f"{'='*60}")
    
    try:
        # Backup
        import shutil
        backup_path = BACKUP_DIR / nb_path.name
        shutil.copy2(nb_path, backup_path)
        print(f"  Backed up to: {backup_path}")
        
        # Read content
        with open(nb_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"  File size: {len(content)} chars")
        
        # Try multiple parsers in order of leniency
        data = None
        errors = []
        
        # 1. Try json5
        data, err = try_parse_with_json5(content)
        if data:
            print("  Parsed with json5!")
        else:
            errors.append(err)
            print(f"  json5 failed: {err}")
        
        # 2. Try demjson
        if data is None:
            data, err = try_parse_with_demjson(content)
            if data:
                print("  Parsed with demjson!")
            else:
                errors.append(err)
                print(f"  demjson failed: {err}")
        
        # 3. Try standard json
        if data is None:
            data, err = try_parse_with_standard_json(content)
            if data:
                print("  Parsed with standard json!")
            else:
                errors.append(err)
                print(f"  standard json failed: {err}")
        
        if data is None:
            return False, f"All parsers failed: {errors}"
        
        # Convert to notebook
        nb = nbformat.from_dict(data)
        
        # Validate
        try:
            nbformat.validate(nb)
            print("  Validation: OK")
        except nbformat.ValidationError as e:
            print(f"  Validation warning: {e}")
        
        # Write back
        nbformat.write(nb, str(nb_path), version=4)
        print(f"  Written to {nb_path}")
        
        # Verify
        with open(nb_path, 'r', encoding='utf-8') as f:
            verify = f.read()
        json.loads(verify)
        nbformat.validate(nbformat.reads(verify, as_version=4))
        print("  Verification: OK")
        
        return True, "Successfully repaired"
        
    except Exception as e:
        return False, f"Error: {type(e).__name__}: {e}"


def main():
    print("=" * 60)
    print("JUPYTER NOTEBOOK REPAIR - LENIENT PARSERS")
    print("=" * 60)
    
    # Install required libraries
    print("Installing lenient JSON parsers...")
    for pkg in ['json5', 'demjson3']:
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', pkg], 
                         capture_output=True, check=True)
            print(f"  Installed {pkg}")
        except subprocess.CalledProcessError:
            print(f"  Could not install {pkg} (may already exist)")
    
    results = {}
    
    for nb_rel_path in [
        "eda/notebooks/01_eda.ipynb",
        "preprocess/notebooks/02_data_preprocessing.ipynb",
        "features/notebooks/03_feature_engineering.ipynb",
    ]:
        nb_path = Path(nb_rel_path)
        
        if not nb_path.exists():
            print(f"\nSKIP: {nb_rel_path} - NOT FOUND")
            results[nb_rel_path] = "NOT FOUND"
            continue
        
        success, message = repair_notebook(nb_path)
        results[str(nb_rel_path)] = message if success else f"FAILED: {message}"
    
    # Summary
    print("\n" + "=" * 60)
    print("REPAIR SUMMARY")
    print("=" * 60)
    
    for path, result in results.items():
        status = "PASS" if "Successfully" in result else "FAIL"
        print(f"  {status} {path}: {result}")
    
    # Generate report
    with open("notebook_validation_report.md", "w", encoding='utf-8') as f:
        f.write("# Notebook Validation Report\n\n")
        f.write(f"Generated: {__import__('datetime').datetime.now()}\n\n")
        f.write("## Summary\n\n")
        for path, result in results.items():
            status = "OK" if "Successfully" in result else "FAIL"
            f.write(f"- {status} {path}: {result}\n")
        f.write("\n## Root Cause\n\n")
        f.write("Notebooks were generated by manually constructing JSON strings ")
        f.write("with f-strings, which failed to escape special characters in ")
        f.write("Markdown content (pipes in tables, checkmarks, headers, etc.).\n\n")
        f.write("## Solution\n\n")
        f.write("Repaired using lenient JSON parsers (json5, demjson) then ")
        f.write("re-serialized with nbformat for proper escaping.\n")


if __name__ == "__main__":
    main()