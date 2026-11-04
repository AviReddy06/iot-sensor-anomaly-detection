#!/usr/bin/env python3
"""
Repair notebooks using json-repair library with robust normalization.
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
        
        # Debug: Print structure
        print(f"  Data keys: {list(data.keys()) if isinstance(data, dict) else 'NOT A DICT'}")
        if isinstance(data, dict) and 'cells' in data:
            print(f"  Number of cells: {len(data['cells'])}")
            if data['cells']:
                print(f"  First cell keys: {list(data['cells'][0].keys()) if isinstance(data['cells'][0], dict) else 'NOT A DICT'}")
        
        # Normalize and create notebook
        nb = normalize_notebook_dict(data)
        if nb is None:
            return False, "Failed to normalize notebook"
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
        import traceback
        traceback.print_exc()
        return False, f"Error: {type(e).__name__}: {e}"


def normalize_notebook_dict(data: dict):
    """
    Normalize a notebook dict to match nbformat v4 schema.
    """
    # Ensure top-level structure
    if not isinstance(data, dict):
        return None
    
    # Ensure required fields
    data.setdefault('nbformat', 4)
    data.setdefault('nbformat_minor', 4)
    data.setdefault('metadata', {})
    data.setdefault('cells', [])
    
    # Ensure metadata
    metadata = data['metadata']
    metadata.setdefault('kernelspec', {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3"
    })
    metadata.setdefault('language_info', {
        "name": "python",
        "version": "3.14.8"
    })
    
    # Normalize cells
    normalized_cells = []
    cells = data.get('cells', [])
    
    for i, cell in enumerate(cells):
        if not isinstance(cell, dict):
            print(f"  Warning: Cell {i} is not a dict, skipping")
            continue
        
        cell_type = cell.get('cell_type')
        if cell_type not in ('code', 'markdown', 'raw'):
            print(f"  Warning: Cell {i} has invalid cell_type: {cell_type}, defaulting to markdown")
            cell_type = 'markdown'
        
        # Get source
        source = cell.get('source', [])
        if isinstance(source, str):
            # Split string into lines, preserving newlines
            source_list = source.splitlines(keepends=True)
        elif isinstance(source, list):
            # Ensure all elements are strings
            source_list = [str(s) for s in source]
        else:
            source_list = []
        
        # Build normalized cell
        norm_cell = {
            'cell_type': cell_type,
            'metadata': cell.get('metadata', {}),
            'source': source_list
        }
        
        if cell_type == 'code':
            norm_cell['execution_count'] = cell.get('execution_count', None)
            norm_cell['outputs'] = cell.get('outputs', [])
        else:
            # markdown/raw cells shouldn't have execution_count or outputs
            pass
        
        normalized_cells.append(norm_cell)
    
    # Create notebook using nbformat v4
    nb = nbformat.v4.new_notebook()
    nb.metadata = data.get('metadata', {})
    nb.cells = normalized_cells
    
    # Ensure metadata has required fields
    nb.metadata.setdefault('kernelspec', {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3"
    })
    nb.metadata.setdefault('language_info', {
        "name": "python",
        "version": "3.14.8"
    })
    
    return nb


def main():
    print("=" * 60)
    print("JUPYTER NOTEBOOK REPAIR - JSON-REPAIR + ROBUST NORMALIZATION")
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
        
        success, message = repair_notebook(Path(nb_rel_path))
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