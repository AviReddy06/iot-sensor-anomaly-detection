#!/usr/bin/env python3
import json
import nbformat
import shutil
from pathlib import Path
import sys

try:
    import json_repair
except ImportError:
    print("json-repair not available!")
    sys.exit(1)

BACKUP_DIR = Path("notebook_backups")
BACKUP_DIR.mkdir(exist_ok=True)

def clean_source(src):
    if isinstance(src, str):
        src = src.replace('\u0000', '').replace('\ufeff', '')
        return src.splitlines(keepends=True)
    elif isinstance(src, list):
        out = []
        for line in src:
            if isinstance(line, str):
                line = line.replace('\u0000', '').replace('\ufeff', '')
                out.append(line)
            else:
                out.append(str(line))
        return out
    return []

def normalize_cell(cell):
    if not isinstance(cell, dict):
        return None
    ct = cell.get('cell_type', 'markdown')
    if ct not in ('code', 'markdown', 'raw'):
        ct = 'markdown'
    src = cell.get('source', [])
    if isinstance(src, str):
        src = src.replace('\u0000', '').replace('\ufeff', '')
        src_list = src.splitlines(keepends=True)
    elif isinstance(src, list):
        src_list = []
        for line in src:
            if isinstance(line, str):
                line = line.replace('\u0000', '').replace('\ufeff', '')
                src_list.append(line)
            else:
                src_list.append(str(line))
        else:
            src_list = []
    if cell.get('cell_type') == 'code':
        return {
            'cell_type': 'code',
            'metadata': cell.get('metadata', {}) or {},
            'source': src_list,
            'execution_count': cell.get('execution_count'),
            'outputs': cell.get('outputs', []) or []
        }
    else:
        return {
            'cell_type': ct,
            'metadata': cell.get('metadata', {}) or {},
            'source': src_list
        }

def main():
    print("=" * 60)
    print("JUPYTER NOTEBOOK REPAIR - FINAL")
    print("=" * 60)
    
    results = {}
    notebooks = [
        "eda/notebooks/01_eda.ipynb",
        "preprocess/notebooks/02_data_preprocessing.ipynb",
        "features/notebooks/03_feature_engineering.ipynb",
    ]
    
    for nb_rel_path in [
        "eda/notebooks/01_eda.ipynb",
        "preprocess/notebooks/02_data_preprocessing.ipynb",
        "features/notebooks/03_feature_engineering.ipynb",
    ]:
        nb_path = Path(nb_rel_path)
        if not nb_path.exists():
            print(f"SKIP: {nb_rel_path} - NOT FOUND")
            continue
        
        backup_path = Path("notebook_backups") / nb_path.name
        shutil.copy2(nb_path, backup_path)
        print(f"Backed up: {nb_rel_path}")
        
        with open(nb_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"Processing {nb_rel_path} ({len(content)} chars)...")
        
        try:
            fixed = json_repair.repair_json(content, skip_json_loads=True)
            data = json.loads(fixed)
        except Exception as e:
            print(f"  Failed to repair/parse: {e}")
            continue
        
        if isinstance(data, list):
            data = {'nbformat': 4, 'nbformat_minor': 4, 'metadata': {}, 'cells': data}
        elif not isinstance(data, dict):
            data = {'nbformat': 4, 'nbformat_minor': 4, 'metadata': {}, 'cells': []}
        
        data.setdefault('nbformat', 4)
        data.setdefault('nbformat_minor', 4)
        data.setdefault('metadata', {})
        data.setdefault('cells', [])
        data['metadata'].setdefault('kernelspec', {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'})
        data['metadata'].setdefault('language_info', {'name': 'python', 'version': '3.14.8'})
        
        norm_cells = []
        for cell in data.get('cells', []):
            if not isinstance(cell, dict):
                continue
            ct = cell.get('cell_type', 'markdown')
            if ct not in ('code', 'markdown', 'raw'):
                ct = 'markdown'
            src = cell.get('source', [])
            if isinstance(src, str):
                src = src.replace('\u0000', '').replace('\ufeff', '')
                src_list = src.splitlines(keepends=True)
            elif isinstance(src, list):
                src_list = []
                for line in src:
                    if isinstance(line, str):
                        line = line.replace('\u0000', '').replace('\ufeff', '')
                        src_list.append(line)
                    else:
                        src_list.append(str(line))
            else:
                src_list = []
            if cell.get('cell_type') == 'code':
                norm = {
                    'cell_type': 'code',
                    'metadata': cell.get('metadata', {}) or {},
                    'source': src_list,
                    'execution_count': cell.get('execution_count'),
                    'outputs': cell.get('outputs', []) or []
                }
            else:
                norm = {
                    'cell_type': ct,
                    'metadata': cell.get('metadata', {}) or {},
                    'source': src_list
                }
            norm_cells.append(norm)
        
        data['cells'] = norm_cells
        data.setdefault('nbformat', 4)
        data.setdefault('nbformat_minor', 4)
        data.setdefault('metadata', {})
        data['metadata'].setdefault('kernelspec', {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'})
        data['metadata'].setdefault('language_info', {'name': 'python', 'version': '3.14.8'})
        
        try:
            nb = nbformat.from_dict(data)
        except Exception as e:
            print(f"  from_dict failed: {e}")
            continue
        
        try:
            nbformat.validate(nb)
        except Exception as e:
            print(f"  Validation warning: {e}")
        
        nbformat.write(nb, str(nb_path), version=4)
        
        with open(nb_path, 'r', encoding='utf-8') as f:
            verify = f.read()
        json.loads(verify)
        nbformat.validate(nbformat.reads(verify, as_version=4))
        
        print(f"  Successfully repaired: {nb_path}")
    
    print("\n" + "=" * 60)
    print("REPAIR COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()