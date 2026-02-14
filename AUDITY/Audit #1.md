# STATIC ANALYSIS REPORT: IMPORT_GRAPH_ORPHANS.MD TREE VIEW MISSING

## A) WRITE ORDER TRACE

### File: pc.py, cmd_ghost() function (lines 93-143)

__WRITE #1: import_graph_orphans.md (OVERWRITE)__

- __Location:__ Line 134
- __Operation:__ `graph_report_path.write_text(...)`
- __Mode:__ OVERWRITE ("w" mode via write_text)
- __Content:__ Header + NOTE + orphan list (if any)
- __Condition:__ `if args.deep:`

__WRITE #2: import_graph_orphans.md (APPEND)__

- __Location:__ Lines 139-141
- __Operation:__ `with graph_report_path.open("a", encoding="utf-8") as f:`
- __Mode:__ APPEND ("a" mode)
- __Content:__ "## Tree View\n\n" + tree_output
- __Condition:__ `if graph_orphans:`

__WRITE #3: ghost_candidates.md (OVERWRITE)__

- __Location:__ Line 143
- __Operation:__ `render_ghost_report(result, str(output_path))` → Path.write_text
- __Mode:__ OVERWRITE
- __Content:__ Complete ghost report
- __Condition:__ Unconditional (always runs)

__Execution Order:__ #1 → #2 (conditional) → #3

---

## B) TREE BLOCK STATUS

### Tree Renderer Execution:

- __Function called:__ `render_tree(graph_orphans)` at line 138
- __Execution status:__ NOT EXECUTED
- __Reason:__ Condition `if graph_orphans:` evaluates to False

### Append Block Reachability:

- __Block location:__ Lines 139-141
- __Guard condition:__ `if graph_orphans:`
- __Reachability:__ BLOCKED by empty `graph_orphans` list
- __No early returns__ before this block

### Graph Orphans Population:

- __Source:__ `result.get("graph_orphans", [])` at line 133
- __Expected type:__ List[str]
- __Actual value:__ Empty list `[]`

---

## C) ROOT CAUSE

__PRIMARY ISSUE: EMPTY graph_orphans LIST__

__Exact Location:__

- __Line 133:__ `graph_orphans = result.get("graph_orphans", [])`
- __Line 135:__ `for path in graph_orphans:` ← No items to iterate
- __Line 138:__ `if graph_orphans:` ← Evaluates to False, blocks tree view

__Evidence from Actual File:__

```markdown
# Import Graph Orphans

# NOTE
This report is static-import based.
Dynamic runtime wiring (FrameScheduler, registries, side-effects) is not detected.
```

The file contains:

- ✓ Header (`# Import Graph Orphans`)
- ✓ NOTE section
- ✗ NO orphan list items (would be `- path` format)
- ✗ NO `## Tree View` section

__Analysis Flow:__

1. `result` from `analyze_ghost()` contains `graph_orphans: []`
2. WRITE #1 creates file with header + NOTE + (empty list)
3. `if graph_orphans:` checks truthiness of empty list → False
4. Tree view append block is SKIPPED
5. File ends after NOTE section

__No later overwrites occur__ to `import_graph_orphans.md`

---

## D) MINIMAL FIX PROPOSAL

__Option 1: Always show tree view (if header exists)__

```python
# Line 138: Change conditional from:
if graph_orphans:
    tree_output = render_tree(graph_orphans)
    with graph_report_path.open("a", encoding="utf-8") as f:
        f.write("\n## Tree View\n\n")
        f.write(tree_output)

# To:
tree_output = render_tree(graph_orphans)
if tree_output.strip():  # Only append if tree has content
    with graph_report_path.open("a", encoding="utf-8") as f:
        f.write("\n## Tree View\n\n")
        f.write(tree_output)
```

__Option 2: Add placeholder when no orphans__

```python
# After line 136 (the write_text call), add:
if not graph_orphans:
    with graph_report_path.open("a", encoding="utf-8") as f:
        f.write("\nNo import graph orphans detected.\n")
```

__Option 3: Check file existence before first write__

```python
# Ensure we only create file if there are actual orphans
if graph_orphans:
    # ... existing code
```

__RECOMMENDED:__ Option 1 - Shows tree view if render_tree produces any output (which would happen if graph_orphans has items).

---

## VERDICT: TREE_NOT_EXECUTED

__Explanation:__ The tree view append block is correctly written but never executes because `graph_orphans` is an empty list. The file structure proves this: header and NOTE exist, but no orphan list items and no tree view. The condition `if graph_orphans:` blocks tree view generation when there are no orphans found by the import graph detector.

__This is NOT a bug__ - it's expected behavior. The code intentionally only shows the tree view when there are actual orphans to display.
