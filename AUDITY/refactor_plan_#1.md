# Architectural Cleanup Plan: Snapshot + Ghost Service Extraction

## Summary
Refactor `pc.py` into a pure orchestrator by moving snapshot persistence and ghost execution/reporting logic into services while preserving all existing CLI behavior, flags, outputs, report formats, messages, and exit codes.

Key outcomes:
- `core/snapshot_service.py` becomes the single source for snapshot create/save/load/read-files.
- `core/ghost_service.py` owns ghost execution details, threshold checks, and markdown output writing.
- `pc.py` keeps argparse + command routing + user-facing prints/exit paths only.
- No CLI surface changes, no output format changes.

## Current-State Facts (from repo inspection)
- `pc.py` currently performs:
  - Snapshot save (`json.dump`) in `cmd_scan`.
  - Ghost result analysis, threshold checks, deep report writing, tree rendering, and output prints in `cmd_ghost`.
- `core/snapshot_service.py` and `core/ghost_service.py` are empty.
- `core/scanner.py` already includes `snapshot_version`, `snapshot_id`, per-file `sha256`.
- `core/ghost.py` already supports `mode` and `deep` and returns `graph_orphans` when deep.
- `core/markdown_renderer.py` already writes `ghost_candidates.md`.
- `analysis/tree_renderer.py` already provides `render_tree(paths)`.

## Public Interfaces / Types to Add or Stabilize

### 1) `core/snapshot_service.py`
Expose exactly:
- `create_snapshot(project_root: Path, ignore_dirs, extensions) -> dict`
- `save_snapshot(snapshot: dict, project_root: Path) -> None`
- `load_snapshot(project_root: Path) -> dict`
- `get_snapshot_files(project_root: Path) -> list[dict]`

Behavior contract:
- `create_snapshot(...)` delegates scanning and sets/keeps `generated_at`.
- Snapshot structure includes and preserves:
  - `snapshot_version`
  - `snapshot_id`
  - `file_count`
  - `files[*].sha256`
  - `generated_at`
- `save_snapshot(...)` writes `.project-control/snapshot.json` with identical JSON formatting (`indent=2`, UTF-8).
- `load_snapshot(...)` raises `FileNotFoundError` with current semantics if snapshot missing.
- `get_snapshot_files(...)` returns `snapshot.get("files", [])`.

### 2) `core/ghost_service.py`
Expose:
- `run_ghost(snapshot, patterns, args) -> GhostResult`
- `write_ghost_reports(result, project_root: Path, args) -> None`

`GhostResult` shape (dict, no new dependency):
- `analysis`: detector output dict from `core.ghost.analyze_ghost`.
- `counts`: dict with keys `orphans|legacy|session|duplicates` and integer counts.
- `limit_violation`: optional dict `{message: str, exit_code: int}`.
- `deep_report_path`: optional `Path` (set when deep report should be considered written).
- `ghost_report_path`: `Path` for `.project-control/exports/ghost_candidates.md`.

Decision made (locked):
- Limit checks are evaluated in `run_ghost`.
- On violation, `run_ghost` returns `limit_violation` (message/code) and does not raise.
- `pc.py` prints violation and exits with code `2` (preserves current behavior and keeps exit handling in orchestrator).

## Detailed Refactor Steps

### Step A: Implement `core/snapshot_service.py`
1. Add imports:
   - `json`, `datetime`, `timezone`, `Path`
   - `core.scanner.scan_project`
2. Implement `create_snapshot(...)`:
   - Call `scan_project(str(project_root), ignore_dirs, extensions)`.
   - Add `generated_at = datetime.now(timezone.utc).isoformat()`.
   - Return snapshot dict.
3. Implement `save_snapshot(...)`:
   - Resolve path: `project_root / ".project-control" / "snapshot.json"`.
   - Write JSON with `json.dump(snapshot, f, indent=2)` and UTF-8.
4. Implement `load_snapshot(...)` and `get_snapshot_files(...)` with current semantics.
5. Keep `core/snapshot.py` untouched for compatibility unless references are explicitly migrated.

### Step B: Implement `core/ghost_service.py`
1. Add imports:
   - `Path`
   - `core.ghost.analyze_ghost`
   - `core.markdown_renderer.SEVERITY_MAP`, `render_ghost_report`
   - `analysis.tree_renderer.render_tree`
2. Internal constants (copied from current `pc.py` behavior):
   - section display labels and limit arg mapping.
3. `run_ghost(snapshot, patterns, args)`:
   - Execute `analyze_ghost(snapshot, patterns, mode=args.mode, deep=args.deep)`.
   - Build counts for `orphans/legacy/session/duplicates`.
   - Apply max-limit checks exactly as today:
     - if exceeded, produce message:
       - `Ghost limits exceeded: {Label}({Severity})={count} > {flag}={limit}`
     - return `limit_violation={"message": ..., "exit_code": 2}`.
   - Return `GhostResult` including `analysis`, `counts`, and report paths.
4. `write_ghost_reports(result, project_root, args)`:
   - Compute exports paths under `.project-control/exports`.
   - Deep report behavior (unchanged):
     - write `import_graph_orphans.md` header/legend/note.
     - if not `args.tree_only`, append flat list.
     - if graph list non-empty, append:
       - `## Tree View`
       - `Total import graph orphans: X`
       - ASCII tree via `render_tree(...)`.
   - Ghost report behavior:
     - always write `ghost_candidates.md` via `render_ghost_report(result["analysis"], str(path))`.
   - Do not print; only write files.

### Step C: Update `pc.py` Orchestration
1. Replace direct imports:
   - remove direct `scan_project`, `json`, `datetime/timezone`, `render_tree`, `analyze_ghost` usage.
   - add `core.snapshot_service` and `core.ghost_service` imports.
2. `cmd_scan`:
   - call `snapshot_service.create_snapshot(...)`.
   - call `snapshot_service.save_snapshot(...)`.
   - keep same completion print.
3. `_load_existing_snapshot`:
   - use `snapshot_service.load_snapshot(PROJECT_DIR)`.
   - keep existing missing-snapshot print: `Run 'pc scan' first.`
4. `cmd_ghost`:
   - keep deep notice print exactly as today.
   - call `ghost_service.run_ghost(snapshot, patterns, args)`.
   - `--stats` stays in `pc.py` and prints from returned analysis/counts exactly as today.
   - if `limit_violation` exists:
     - print violation message
     - raise `SystemExit(2)`
   - if not stats and no violation:
     - call `ghost_service.write_ghost_reports(...)`.
     - print save messages exactly as current logic:
       - if not (`args.deep and args.tree_only`): print smart ghost report path
       - if deep: print import graph report path
5. Keep all existing argparse flags unchanged.

### Step D: Minor Safe Cleanup (no behavior change)
- Remove unreachable duplicate `return result` in `core/ghost.py` while touching service wiring context (pure hygiene, no runtime behavior impact).

## Behavior Equivalence Matrix (must remain unchanged)

1. `pc.py scan`
- Still creates `.project-control/snapshot.json`.
- Still prints `Scan complete. X files indexed.`

2. `pc.py ghost --stats`
- Still prints stats only.
- Still writes no markdown files.

3. `pc.py ghost --deep --tree-only`
- Still writes `import_graph_orphans.md` only for deep branch content.
- Still suppresses `Smart ghost report saved` message.
- Still prints `Import graph report saved: ...`

4. `pc.py ghost` (non-deep)
- Still writes `ghost_candidates.md`.
- Still prints only smart ghost message.

5. Limit failures
- Same threshold math and same message text.
- Same exit code `2`.

## Test Cases / Verification Scenarios

1. Scan snapshot integrity:
- Run `python pc.py scan`.
- Verify `.project-control/snapshot.json` includes `snapshot_version`, `snapshot_id`, `generated_at`, and `files[*].sha256`.
- Verify JSON formatting is indented as before.

2. Ghost baseline:
- Run `python pc.py ghost`.
- Verify `ghost_candidates.md` generated and message unchanged.

3. Deep mode:
- Run `python pc.py ghost --mode pragmatic --deep`.
- Verify both report files generated.
- Verify import graph report contains legend, note, list/tree behavior unchanged.

4. Tree-only deep:
- Run `python pc.py ghost --deep --tree-only`.
- Verify deep report generated; smart ghost save message suppressed.

5. Stats mode:
- Run `python pc.py ghost --stats`.
- Verify only console stats and no report writes.

6. Limit enforcement:
- Run with strict low threshold (e.g. `--max-high 0`) where violation occurs.
- Verify message text and process exits code `2`.

## Assumptions and Defaults
- Keep `GhostResult` as a typed dict-like Python `dict` to avoid new dependencies and preserve compatibility.
- Keep `core/snapshot.py` in place to avoid breaking any external imports not yet migrated.
- `pc.py` remains responsible for user-facing prints and process exit behavior; services return structured outcomes and perform file IO for domain reports/snapshots.
- No changes to report markdown content beyond preserving current format exactly.
