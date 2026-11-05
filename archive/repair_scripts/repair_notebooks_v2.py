#!/usr/bin/env python3
"""
Aggressively repair Jupyter notebooks by fixing JSON syntax errors at the character level.
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

def find_and_fix_json_errors(content: str) -> str:
    """
    Attempt to fix JSON syntax errors by iteratively trying to parse
    and fixing errors at the reported position.
    """
    # We'll try to parse and when it fails, fix the specific error
    max_attempts = 10
    attempt = 0
    
    while attempt < max_attempts:
        try:
            json.loads(content)
            return content  # Success!
        except json.JSONDecodeError as e:
            attempt += 1
            print(f"  Attempt {attempt}: JSON error at pos {e.pos} (line {e.lineno}, col {e.colno}): {e.msg}")
            
            # Show context
            start = max(0, e.pos - 80)
            end = min(len(content), e.pos + 80)
            context = content[start:end]
            print(f"  Context: ...{repr(context)}...")
            
            # Apply specific fixes based on error type
            if "Expecting property name enclosed in double quotes" in e.msg:
                # Missing quote before property name
                # This often happens when there's a missing comma or unescaped quote
                content = fix_missing_quote(content, e.pos)
            elif "Expecting ',' delimiter" in e.msg:
                # Missing comma between object members or array elements
                content = fix_missing_comma(content, e.pos)
            elif "Expecting value" in e.msg:
                # Missing value (could be trailing comma, or missing quote)
                content = fix_missing_value(content, e.pos)
            elif "Unterminated string" in e.msg:
                content = fix_unterminated_string(content, e.pos)
            elif "Invalid control character" in e.msg:
                content = fix_control_chars(content, e.pos)
            else:
                # Generic: try to remove/replace problematic character
                content = remove_problematic_char(content, e.pos)
            
            if attempt >= max_attempts:
                print(f"  Failed after {max_attempts} attempts")
                return content
    
    # Final attempt
    try:
        json.loads(content)
        return content
    except json.JSONDecodeError as e:
        print(f"  Final parse failed: {e}")
        return content


def fix_missing_quote(content: str, pos: int) -> str:
    """Try to fix missing quote at position."""
    # Look around the position for the issue
    # Often it's a missing quote before a property name
    # We'll try to insert a quote at the right place
    before = content[:pos]
    after = content[pos:]
    
    # Look for the pattern: , "key": or { "key":
    # The error is usually that a quote is missing before a key
    # Let's try to find where the key starts and add a quote
    
    # Simple heuristic: look backwards for { or , then forward for word
    # This is very heuristic - better to use a proper JSON repair lib
    # For now, just return original
    return content


def fix_missing_comma(content: str, pos: int) -> str:
    """Try to fix missing comma."""
    # The error is usually between } and " or ] and "
    # We'll try to insert a comma at the right position
    return content


def fix_missing_value(content: str, pos: int) -> str:
    """Try to fix missing value."""
    return content


def fix_unterminated_string(content: str, pos: int) -> str:
    """Try to fix unterminated string."""
    return content


def fix_control_chars(content: str, pos: int) -> str:
    """Fix control characters in strings."""
    # Replace literal newlines/tabs in strings with escaped versions
    # This is complex - we'd need to parse the JSON structure
    return content


def remove_problematic_char(content: str, pos: int) -> str:
    """Remove the character at the error position."""
    return content[:pos] + content[pos+1:]


def aggressive_json_fix(content: str) -> str:
    """
    More aggressive fix: rebuild JSON by tokenizing and reconstructing.
    This is a last resort for severely malformed JSON.
    """
    # Strategy: Use a streaming JSON parser approach
    # We'll try to parse incrementally and fix errors on the fly
    
    # For now, let's try a different approach:
    # Use the `json5` library concept - be more lenient
    # But since we don't have json5, let's try manual fixes
    
    # The most common issues in these notebooks:
    # 1. Markdown tables with | characters inside JSON strings
    # 2. Check marks (✅/❌) and emoji
    # 3. Backslashes in file paths
    # 4. Unescaped newlines in string values
    
    # Let's try a different approach: parse the JSON with a custom decoder
    # that's more lenient
    
    return content


def extract_cells_from_raw_json(content: str):
    """
    Last resort: Extract cells from the raw JSON text by parsing
    the structure manually, then rebuild with nbformat.
    """
    # Find the "cells" array
    cells_match = re.search(r'"cells"\s*:\s*\[', content)
    if not cells_match:
        return None
    
    # This is very complex. Let's try a different approach.
    return None


def main():
    print("=" * 60)
    print("JUPYTER NOTEBOOK AGGRESSIVE REPAIR")
    print("=" * 60)
    
    BACKUP_DIR = Path("notebook_backups")
    BACKUP_DIR.mkdir(exist_ok=True)
    
    NOTEBOOKS = [
        "eda/notebooks/01_eda.ipynb",
        "preprocess/notebooks/02_data_preprocessing.ipynb",
        "features/notebooks/03_feature_engineering.ipynb",
    ]
    
    for nb_rel_path in NOTEBOOKS:
        nb_path = Path(nb_rel_path)
        
        if not nb_path.exists():
            print(f"\nSKIP: {nb_rel_path} - NOT FOUND")
            continue
        
        print(f"\n{'='*60}")
        print(f"Repairing: {nb_rel_path}")
        print(f"{'='*60}")
        
        # Backup
        backup_path = BACKUP_DIR / nb_path.name
        import shutil
        shutil.copy2(nb_path, backup_path)
        print(f"Backed up to: {backup_path}")
        
        # Read content
        with open(nb_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"  File size: {len(content)} chars")
        
        # Try to fix JSON syntax
        print("  Attempting JSON syntax repair...")
        fixed_content = fix_json_syntax(content)
        
        # Try to parse the fixed content
        try:
            nb = nbformat.reads(fixed_content, as_version=4)
            print("  Parsed successfully with nbformat!")
            
            # Validate
            nbformat.validate(nb)
            print("  Validation: OK")
            
            # Write back
            nbformat.write(nb, str(nb_path), version=4)
            print(f"  Written to {nb_path}")
            
            # Verify
            with open(nb_path, 'r', encoding='utf-8') as f:
                verify = f.read()
            json.loads(verify)
            nbformat.validate(nbformat.reads(verify, as_version=4))
            print("  Verification: OK")
            print("  ✓ SUCCESS")
            
        except Exception as e:
            print(f"  ✗ FAILED: {type(e).__name__}: {e}")

if __name__ == "__main__":
    main()