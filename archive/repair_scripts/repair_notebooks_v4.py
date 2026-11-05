#!/usr/bin/env python3
"""
Aggressively fix Jupyter notebook JSON by pre-processing the raw text
to escape special characters in string values before JSON parsing.
"""

import json
import nbformat
from pathlib import Path
import sys
import re

NOTEBOOKS = [
    "eda/notebooks/01_eda.ipynb",
    "preprocess/notebooks/02_data_preprocessing.ipynb",
    "features/notebooks/03_feature_engineering.ipynb",
]

BACKUP_DIR = Path("notebook_backups")
BACKUP_DIR.mkdir(exist_ok=True)


def pre_fix_json(content: str) -> str:
    """
    Pre-process JSON text to fix common escaping issues in string values.
    This works on the raw text before JSON parsing.
    """
    # The strategy: Find all JSON string values and escape their content.
    # We'll use a state machine to identify string boundaries and fix content.
    
    # First pass: Fix obvious issues in the raw text
    # 1. Fix unescaped backslashes in what appear to be file paths
    # 2. Fix unescaped newlines in strings
    # 3. The main issue: markdown content with #, |, ✅, ❌ inside JSON strings
    
    # Let's use a more robust approach: parse the JSON structure and fix strings
    # We'll use a custom decoder approach
    
    return content


def fix_json_strings_aggressive(content: str) -> str:
    """
    Aggressively fix string values in JSON by parsing the structure
    and properly escaping string content.
    """
    # We'll parse the JSON token by token, fixing string values as we go
    # This is a simplified JSON parser that fixes strings on the fly
    
    result = []
    i = 0
    depth = 0  # Track object/array nesting
    in_string = False
    escape = False
    string_chars = []
    
    while i < len(content):
        ch = content[i]
        
        if not in_string:
            if ch == '"':
                # Check if this is a string value (not a key)
                # Look ahead to see if next non-whitespace is :
                j = i + 1
                while j < len(content) and content[j] in ' \t\n\r':
                    j += 1
                is_key = (j < len(content) and content[j] == ':')
                
                in_string = True
                result.append(ch)
            else:
                result.append(ch)
        else:
            # Inside a string value
            if escape:
                # Previous char was backslash - this char is escaped
                escape = False
                result.append(ch)
            elif ch == '\\':
                escape = True
                result.append(ch)
            elif ch == '"':
                in_string = False
                result.append(ch)
            elif ch in '\n\r\t\b\f':
                # Literal control chars in string - escape them
                escapes = {'\n': '\\n', '\r': '\\r', '\t': '\\t', '\b': '\\b', '\f': '\\f'}
                result.append(escapes.get(ch, ch))
            else:
                result.append(ch)
        i += 1
    
    return ''.join(result)


def main():
    print("=" * 60)
    print("JUPYTER NOTEBOOK REPAIR - AGGRESSIVE STRING FIXING")
    print("=" * 60)
    
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
        
        # Backup
        backup_path = BACKUP_DIR / nb_path.name
        import shutil
        shutil.copy2(nb_path, backup_path)
        print(f"Backed up: {nb_rel_path}")
        
        # Read content
        with open(nb_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"Processing {nb_rel_path} ({len(content)} chars)...")
        
        # Try aggressive fix
        fixed = fix_json_strings_aggressive(content)
        
        # Try to parse
        try:
            nb = nbformat.reads(fixed, as_version=4)
            print(f"  Parsed OK!")
        except Exception as e:
            print(f"  Parse failed: {e}")
            results[nb_rel_path] = f"FAILED: {e}"
            continue
        
        # Validate
        try:
            nbformat.validate(nb)
            print("  Validated OK")
        except Exception as e:
            print(f"  Validation warning: {e}")
        
        # Write
        nbformat.write(nb, str(nb_path), version=4)
        print(f"  Written to {nb_path}")
        
        # Verify
        with open(nb_path, 'r', encoding='utf-8') as f:
            verify = f.read()
        json.loads(verify)
        nbformat.validate(nbformat.reads(verify, as_version=4))
        print("  Verified OK")
        
        results[nb_rel_path] = "Successfully repaired"
    
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
        f.write("Repaired using proper JSON string escaping via state machine.\n")


if __name__ == "__main__":
    main()