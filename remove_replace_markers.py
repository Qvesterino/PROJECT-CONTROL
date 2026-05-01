#!/usr/bin/env python
"""Remove ++++++++ REPLACE markers from menu.py"""

# Read the file
with open('project_control/cli/menu.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Filter out lines containing ++++++++ REPLACE
filtered = [line for line in lines if '+++++++ REPLACE' not in line]

# Write to a temp file first
with open('project_control/cli/menu.py.tmp', 'w', encoding='utf-8') as f:
    f.writelines(filtered)

# Replace original
import os
os.replace('project_control/cli/menu.py.tmp', 'project_control/cli/menu.py')

print(f'Processed: {len(lines)} lines -> {len(filtered)} lines')
print(f'Removed: {len(lines) - len(filtered)} lines with ++++++++ REPLACE')