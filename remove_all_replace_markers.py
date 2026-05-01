#!/usr/bin/env python
"""Remove ++++++++ REPLACE markers from all Python files"""

import os
from pathlib import Path

# Find all Python files in project_control
project_dir = Path('project_control')
python_files = list(project_dir.rglob('*.py'))

total_removed = 0
files_modified = 0

for py_file in python_files:
    # Read the file
    with open(py_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Filter out lines containing ++++++++ REPLACE
    filtered = [line for line in lines if '+++++++ REPLACE' not in line]
    
    removed = len(lines) - len(filtered)
    if removed > 0:
        # Write to a temp file first
        with open(str(py_file) + '.tmp', 'w', encoding='utf-8') as f:
            f.writelines(filtered)
        
        # Replace original
        os.replace(str(py_file) + '.tmp', str(py_file))
        
        print(f'{py_file}: Removed {removed} lines')
        total_removed += removed
        files_modified += 1

print(f'\nTotal: Removed {total_removed} lines from {files_modified} files')