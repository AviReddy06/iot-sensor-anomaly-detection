#!/usr/bin/env python3
"""
Repair notebooks using json-repair library, with proper nbformat conversion.
"""

import json
import nbformat
from pathlib import Path
import sys

try:
    import json_repair
    HAS_JSON_REPAIR = True
except ImportError:
    HAS_JSON_REPAIR = False

NOTEBOOKS = [
    "eda/notebooks/01_eda.ipynb",
    "preprocess/notebooks/02_data_preprocessing.ipynb",
    "features/notebooks/03_feature_engineering.ipynb",
]

BACKUP_DIR = Path("notebook_backups")
BACKUP_DIR.mkdir(exist_ok=True)


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
        
        # Try json-repair
        if not HAS_JSON_REPAIR:
            return False, "json-repair not available"
        
        print("  Attempting json-repair...")
        try:
            fixed_content = json_repair.repair_json(content, skip_json_loads=True)
            print("  json-repair succeeded!")
        except Exception as e:
            print(f"  json-repair failed: {e}")
            return False, f"json-repair failed: {e}"
        
        # Try to parse repaired content
        try:
            data = json.loads(fixed_content)
            print("  JSON parsed successfully!")
        except json.JSONDecodeError as e:
            print(f"  JSON parse failed after repair: {e}")
            return False, f"JSON parse failed: {e}"
        
        # Convert to notebook using nbformat v4 schema
        # The repaired data might have minor schema differences, so we normalize
        try:
            nb = nbformat.from_dict(data)
            print("  Converted to notebook!")
        except Exception as e:
            print(f"  nbformat.from_dict failed: {e}")
            # Try manual construction
            nb = normalize_notebook_dict(data)
            if nb is None:
                return False, f"Failed to normalize: {e}"
            print("  Normalized notebook structure!")
        
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


def normalize_notebook_dict(data: dict):
    """
    Normalize a notebook dict to match nbformat v4 schema.
    Fixes common issues from json-repair output.
    """
    # Ensure required top-level fields
    if 'nbformat' not in data:
        data['nbformat'] = 4
    if 'nbformat_minor' not in data:
        data['nbformat_minor'] = 4
    if 'metadata' not in data:
        data['metadata'] = {}
    if 'cells' not in data:
        data['cells'] = []
    
    # Ensure metadata has kernelspec
    if 'kernelspec' not in data['metadata']:
        data['metadata']['kernelspec'] = {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        }
    if 'language_info' not in data['metadata']:
        data['metadata']['language_info'] = {
            "name": "python",
            "version": "3.14.8"
        }
    
    # Normalize cells
    normalized_cells = []
    for cell in data.get('cells', []):
        # Ensure cell has required fields
        if 'cell_type' not in cell:
            continue  # Skip invalid cells
        
        normalized_cell = {
            'cell_type': cell['cell_type'],
            'metadata': cell.get('metadata', {}),
            'source': cell.get('source', [])
        }
        
        # Ensure source is a list of strings
        source = cell.get('source', [])
        if isinstance(source, str):
            # Split string into lines
            normalized_cell['source'] = source.splitlines(keepends=True)
        elif isinstance(source, list):
            # Ensure all elements are strings
            normalized_cell['source'] = [str(s) for s in source]
        else:
            normalized_cell['source'] = []
        
        # Add execution fields for code cells
        if cell['cell_type'] == 'code':
            normalized_cell['execution_count'] = cell.get('execution_count', None)
            normalized_cell['outputs'] = cell.get('outputs', [])
        elif cell['cell_type'] == 'markdown':
            # Markdown cells shouldn't have execution_count or outputs
            normalized_cell.pop('execution_count', None)
            normalized_cell.pop('outputs', None)
        
        normalized_cells.append(normalized_cell)
    
    data['cells'] = normalized_cells
    
    return nbformat.from_dict(data)


def main():
    print("=" * 60)
    print("JUPYTER NOTEBOOK REPAIR - JSON-REPAIR + NORMALIZATION")
    print("=" * 60)
    
    if not HAS_JSON_REPAIR:
        print("json-repair library not available!")
        return
    
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
        f.write("Repaired using json-repair library for automatic JSON fixing, ")
        f.write("then normalized to nbformat v4 schema.\n")


if __name__ == "__main__":
    main()