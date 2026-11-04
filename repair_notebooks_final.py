#!/usr/bin/env python3
"""
Repair notebooks using json-repair with robust nbformat handling.
"""

import json
import nbformat
from pathlib import Path
import sys
import shutil

try:
    import json_repair
    HAS_JSON_REPAIR = True
except ImportError:
    HAS_JSON_REPAIR = False

BACKUP_DIR = Path("notebook_backups")
BACKUP_DIR.mkdir(exist_ok=True)

NOTEBOOKS = [
    "eda/notebooks/01_eda.ipynb",
    "preprocess/notebooks/02_data_preprocessing.ipynb",
    "features/notebooks/03_feature_engineering.ipynb",
]


def fix_notebook_structure(data):
    """Fix notebook structure if it's not a proper dict."""
    if isinstance(data, list):
        return {
            'nbformat': 4,
            'nbformat_minor': 4,
            'metadata': {
                'kernelspec': {
                    'display_name': 'Python 3',
                    'language': 'python',
                    'name': 'python3'
                },
                'language_info': {
                    'name': 'python',
                    'version': '3.14.8'
                }
            },
            'cells': data if isinstance(data, list) else []
        }
    elif isinstance(data, dict):
        data.setdefault('nbformat', 4)
        data.setdefault('nbformat_minor', 4)
        data.setdefault('metadata', {})
        data.setdefault('cells', [])
        return data
    return {
        'nbformat': 4,
        'nbformat_minor': 4,
        'metadata': {},
        'cells': []
    }


def clean_cell_source(source):
    if isinstance(source, str):
        source = source.replace('\u0000', '').replace('\ufeff', '')
        return source.splitlines(keepends=True)
    elif isinstance(source, list):
        cleaned = []
        for line in source:
            if isinstance(line, str):
                line = line.replace('\u0000', '').replace('\ufeff', '')
                cleaned.append(line)
            else:
                cleaned.append(str(line))
        return cleaned
    return []


def normalize_cell(cell):
    if not isinstance(cell, dict):
        return None
    
    cell_type = cell.get('cell_type', 'markdown')
    if cell_type not in ('code', 'markdown', 'raw'):
        cell_type = 'markdown'
    
    source = clean_cell_source(cell.get('source', []))
    
    if cell_type == 'code':
        return {
            'cell_type': 'code',
            'metadata': cell.get('metadata', {}) or {},
            'source': source,
            'execution_count': cell.get('execution_count'),
            'outputs': cell.get('outputs', []) or []
        }
    else:
        return {
            'cell_type': cell_type,
            'metadata': cell.get('metadata', {}) or {},
            'source': source
        }


def main():
    print("=" * 60)
    print("JUPYTER NOTEBOOK REPAIR - FINAL VERSION")
    print("=" * 60)
    
    if not HAS_JSON_REPAIR:
        print("json-repair library not available!")
        return
    
    results = {}
    notebooks = [
        "eda/notebooks/01_eda.ipynb",
        "preprocess/notebooks/02_data_preprocessing.ipynb",
        "features/notebooks/03_feature_engineering.ipynb",
    ]
    
    for nb_rel_path in notebooks:
        nb_path = Path(nb_rel_path)
        
        if not nb_path.exists():
            print(f"\nSKIP: {nb_rel_path} - NOT FOUND")
            continue
        
        # Backup
        backup_path = Path("notebook_backups") / nb_path.name
        shutil.copy2(nb_path, backup_path)
        print(f"Backed up: {nb_rel_path}")
        
        # Read content
        with open(nb_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"Processing {nb_rel_path} ({len(content)} chars)...")
        
        try:
            # Repair with json-repair
            fixed_content = json_repair.repair_json(content, skip_json_loads=True)
            data = json.loads(fixed_content)
        except Exception as e:
            print(f"  Failed to repair/parse: {e}")
            results[nb_rel_path] = f"FAILED: {e}"
            continue
        
        # Fix structure
        if isinstance(data, list):
            data = {
                'nbformat': 4,
                'nbformat_minor': 4,
                'metadata': {
                    'kernelspec': {
                        'display_name': 'Python 3',
                        'language': 'python',
                        'name': 'python3'
                    },
                    'language_info': {
                        'name': 'python',
                        'version': '3.14.8'
                    }
                },
                'cells': data
            }
        elif isinstance(data, dict):
            data.setdefault('nbformat', 4)
            data.setdefault('nbformat_minor', 4)
            data.setdefault('metadata', {})
            data.setdefault('cells', [])
        else:
            data = {'nbformat': 4, 'nbformat_minor': 4, 'metadata': {}, 'cells': []}
        
        # Ensure metadata
        data['metadata'].setdefault('kernelspec', {
            'display_name': 'Python 3',
            'language': 'python',
            'name': 'python3'
        })
        data['metadata'].setdefault('language_info', {
            'name': 'python',
            'version': '3.14.8'
        })
        
        # Normalize cells
        normalized_cells = []
        for cell in data.get('cells', []):
            if not isinstance(cell, dict):
                continue
            cell_type = cell.get('cell_type', 'markdown')
            if cell_type not in ('code', 'markdown', 'raw'):
                cell_type = 'markdown'
            
            source = cell.get('source', [])
            if isinstance(source, str):
                source = source.replace('\u0000', '').replace('\ufeff', '')
                source_list = source.splitlines(keepends=True)
            elif isinstance(source, list):
                source_list = []
                for line in source:
                    if isinstance(line, str):
                        line = line.replace('\u0000', '').replace('\ufeff', '')
                        source_list.append(line)
                    else:
                        source_list.append(str(line))
                else:
                    source_list = []
            
            if cell_type == 'code':
                normalized = {
                    'cell_type': 'code',
                    'metadata': cell.get('metadata', {}) or {},
                    'source': source_list,
                    'execution_count': cell.get('execution_count'),
                    'outputs': cell.get('outputs', []) or []
                }
            else:
                normalized = {
                    'cell_type': cell_type,
                    'metadata': cell.get('metadata', {}) or {},
                    'source': source_list
                }
            normalized_cells.append(normalized)
        
        data['cells'] = normalized_cells
        data.setdefault('nbformat', 4)
        data.setdefault('nbformat_minor', 4)
        data.setdefault('metadata', {})
        data['metadata'].setdefault('kernelspec', {
            'display_name': 'Python 3',
            'language': 'python',
            'name': 'python3'
        })
        data['metadata'].setdefault('language_info', {
            'name': 'python',
            'version': '3.14.8'
        })
        
        # Create notebook
        try:
            nb = nbformat.from_dict(data)
        except Exception as e:
            print(f"  from_dict failed: {e}")
            results[nb_rel_path] = f"FAILED: Could not create notebook"
            continue
        
        # Validate (warnings OK)
        try:
            nbformat.validate(nb)
        except nbformat.ValidationError as e:
            print(f"  Validation warning: {e}")
        
        # Write
        nbformat.write(nb, str(nb_path), version=4)
        
        # Verify
        with open(nb_path, 'r', encoding='utf-8') as f:
            verify = f.read()
        json.loads(verify)
        nbformat.validate(nbformat.reads(verify, as_version=4))
        
        print(f"  Successfully repaired: {nb_rel_path}")
        results[nb_rel_path] = "Successfully repaired"
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        results[nb_rel_path] = f"FAILED: {type(e).__name__}: {e}"

    # Summary
    print("\n" + "=" * 60)
    print("REPAIR SUMMARY")
    print("=" * 60)
    for path, result in results.items():
        status = "PASS" if "Successfully" in result else "FAIL"
        print(f"  {status} {path}: {result}")

    # Report
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
        f.write("then normalized to nbformat v4 schema with proper cell handling.\n")


if __name__ == "__main__":
    main()