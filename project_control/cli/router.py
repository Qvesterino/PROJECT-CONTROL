"""CLI router that delegates commands to core services."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional

from project_control.config.patterns_loader import get_scan_extensions, load_patterns
from project_control.core.exit_codes import EXIT_OK, EXIT_VALIDATION_ERROR
from project_control.core.artifact_service import run_artifact_hygiene
from project_control.core.audit_retention_service import run_audit_retention
from project_control.core.ghost_service import run_ghost, write_ghost_report, write_ghost_tree_report
from project_control.core.markdown_renderer import render_writer_report
from project_control.core.snapshot_service import create_snapshot, load_snapshot, save_snapshot
from project_control.core.project_initializer import ensure_project_initialized
from project_control.core.writers import run_writers_analysis
from project_control.core.error_handler import (
    ErrorHandler,
    ErrorContext,
    FileNotFoundError as ProjectControlFileNotFoundError,
    ValidationError,
)
from project_control.core.pre_flight import require_healthy_snapshot
from project_control.utils.fs_helpers import run_rg
from project_control.cli.graph_cmd import graph_build, graph_report, graph_trace
from project_control.utils.renderers import render_unused, render_patterns, render_search
from project_control.render.dead_renderer import render_dead
from project_control.render.ui_verification_renderer import render_ui_verification_console_summary
from project_control.render.vfx_contract_renderer import render_vfx_contract_console
from project_control.analysis.dead_analyzer import analyze_dead_code
from project_control.analysis.unused_analyzer import analyze_unused_systems
from project_control.analysis.patterns_analyzer import analyze_patterns
from project_control.analysis.search_analyzer import smart_search
from project_control.analysis.vfx_contract_audit import vfx_contract_result_to_dict
from project_control.services.ui_verification_service import list_ui_verification_profiles, run_ui_verification_profile
from project_control.services.nebula_export_service import run_nebula_export
from project_control.services.patron_path_service import run_patron_path_audit
from project_control.services.ecosystem_health_service import run_ecosystem_health
from project_control.services.vfx_contract_service import run_vfx_contract_audit
import json
from project_control.cli.menu import run_menu
from project_control.graph.ensure import ensure_graph

logger = logging.getLogger(__name__)

_DEFAULT_PROJECT_DIR = Path.cwd().resolve()
_DEFAULT_CONTROL_DIR = _DEFAULT_PROJECT_DIR / ".project-control"
_DEFAULT_EXPORTS_DIR = _DEFAULT_CONTROL_DIR / "exports"

PROJECT_DIR = _DEFAULT_PROJECT_DIR
CONTROL_DIR = _DEFAULT_CONTROL_DIR
EXPORTS_DIR = _DEFAULT_EXPORTS_DIR

def _resolve_project_root(args: argparse.Namespace | None = None) -> Path:
    project_root = getattr(args, "project_root", None) if args is not None else None
    if project_root:
        return Path(project_root).resolve()
    patched_project_dir = Path(PROJECT_DIR).resolve()
    if patched_project_dir != _DEFAULT_PROJECT_DIR:
        return patched_project_dir
    return Path.cwd().resolve()


def _control_dir(project_root: Path) -> Path:
    if project_root == Path(PROJECT_DIR).resolve() and Path(CONTROL_DIR).resolve() != _DEFAULT_CONTROL_DIR:
        return Path(CONTROL_DIR).resolve()
    return project_root / ".project-control"


def _exports_dir(project_root: Path) -> Path:
    if project_root == Path(PROJECT_DIR).resolve() and Path(EXPORTS_DIR).resolve() != _DEFAULT_EXPORTS_DIR:
        return Path(EXPORTS_DIR).resolve()
    return _control_dir(project_root) / "exports"


def _load_existing_snapshot() -> Optional[dict]:
    try:
        return load_snapshot(_resolve_project_root())
    except ProjectControlFileNotFoundError:
        print("Run 'pc scan' first.")
        return None


def cmd_init(args: argparse.Namespace) -> int:
    project_root = _resolve_project_root(args)
    initialization = ensure_project_initialized(project_root)
    if initialization.updated_gitignore:
        print("  Added '.project-control/' to .gitignore")
    print("PROJECT CONTROL initialized.")
    return EXIT_OK


def cmd_scan(args: argparse.Namespace) -> int:
    """Scan project and create snapshot with error handling."""
    try:
        with ErrorContext("Scanning project"):
            run_scan(_resolve_project_root(args))
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "Scan command")


def cmd_checklist(args: argparse.Namespace) -> int:
    """Generate checklist from snapshot with error handling."""
    try:
        with ErrorContext("Generating checklist"):
            project_root = _resolve_project_root(args)
            require_healthy_snapshot(project_root, operation="checklist generation")
            snapshot = load_snapshot(project_root)

            ensure_project_initialized(project_root)

            output = ["# PROJECT CHECKLIST\n"]
            for file in snapshot["files"]:
                output.append(f"- [ ] {file['path']}")

            checklist_path = _exports_dir(project_root) / "checklist.md"
            checklist_path.parent.mkdir(parents=True, exist_ok=True)
            checklist_path.write_text("\n".join(output), encoding="utf-8")

            print(f"Checklist generated: {checklist_path}")
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "Checklist command")


def cmd_quick(args: argparse.Namespace) -> int:
    """Quick analysis - scan, find issues, and build dependencies."""
    try:
        with ErrorContext("Quick analysis"):
            project_root = _resolve_project_root(args)
            ensure_project_initialized(project_root)
            
            # Get flags
            health_only = getattr(args, "health", False)
            orphans_only = getattr(args, "orphans", False)
            tree_export = getattr(args, "tree", False)
            
            # Step 1: Scan
            print("\n📂 Scanning project...")
            run_scan(project_root)
            
            snapshot = load_snapshot(project_root)
            if snapshot is None:
                print("Error: Failed to load snapshot")
                return EXIT_VALIDATION_ERROR
            
            print(f"   ✓ Found {len(snapshot.get('files', []))} files")
            
            # Step 2: Run ghost analysis
            if not health_only:
                print("\n👻 Running ghost analysis...")
                
                # Create args for ghost
                ghost_args = argparse.Namespace(
                    mode="pragmatic",
                    max_high=-1,
                    max_medium=-1,
                    max_low=-1,
                    max_info=-1,
                    tree=tree_export
                )
                
                ghost_data = run_ghost(ghost_args, project_root)
                if ghost_data:
                    result = ghost_data["result"]
                    counts = ghost_data["counts"]
                    
                    # Write reports
                    write_ghost_report(result, project_root)
                    if tree_export:
                        write_ghost_tree_report(result, project_root)
                    
                    print(f"   ✓ Orphans: {counts.get('orphans', 0)}")
                    print(f"   ✓ Legacy: {counts.get('legacy', 0)}")
                    print(f"   ✓ Sessions: {counts.get('sessions', 0)}")
                    print(f"   ✓ Duplicates: {counts.get('duplicates', 0)}")
                    print(f"   ✓ Semantic: {counts.get('semantic', 0)}")
                    
                    if tree_export:
                        print(f"\n   📄 Tree reports saved to .project-control/")
            
            # Step 3: Build graph (if not orphans_only)
            if not orphans_only:
                print("\n🔗 Building dependency graph...")
                try:
                    graph_path, metrics_path, report_path = ensure_graph(project_root)
                    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
                    totals = metrics.get("totals", {})
                    print(f"   ✓ Graph built with {totals.get('nodeCount', 0)} nodes")
                    print(f"   ✓ Metrics: {metrics_path.name}")
                    print(f"   ✓ Report:  {report_path.name}")
                except Exception as e:
                    print(f"   ⚠️  Graph build skipped: {e}")
            
            # Step 4: Health check
            if health_only or orphans_only:
                print("\n✅ Quick analysis complete!")
                return EXIT_OK
            
            # Full analysis summary
            print("\n" + "="*60)
            print("  QUICK ANALYSIS COMPLETE")
            print("="*60)
            print("\nReports saved to .project-control/:")
            print("  • exports/ghost_candidates.md")
            if tree_export:
                print("  • exports/ghost_*_tree.txt")
            print("  • out/graph.report.md")
            print("\nNext steps:")
            print("  • Run 'pc ghost' to see detailed results")
            print("  • Run 'pc graph report' to analyze dependencies")
            print("  • Run 'pc graph trace <file>' to trace imports")
            
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "Quick analysis")


def cmd_find(args: argparse.Namespace) -> int:
    """Find symbol usage with error handling."""
    if not args.symbol:
        print("Provide symbol to search.")
        return EXIT_VALIDATION_ERROR

    try:
        with ErrorContext("Searching for symbol"):
            project_root = _resolve_project_root(args)
            ensure_project_initialized(project_root)

            result = run_rg(args.symbol)
            output_path = _exports_dir(project_root) / f"find_{args.symbol}.md"

            output_path.write_text(
                f"# Usage of: {args.symbol}\n\n{result or 'No matches found.'}",
                encoding="utf-8",
            )

            print(f"Search results saved: {output_path}")
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "Find command")


def cmd_ghost(args: argparse.Namespace) -> int:
    """Run shallow ghost analysis using canonical ghost core with error handling."""
    try:
        with ErrorContext("Running ghost analysis"):
            project_root = _resolve_project_root(args)
            ghost_data = run_ghost(args, project_root)
            if ghost_data is None:
                return EXIT_OK

            result = ghost_data["result"]
            counts = ghost_data["counts"]

            # Write markdown report
            write_ghost_report(result, project_root)

            # Write ASCII tree report if --tree flag is set
            if getattr(args, "tree", False):
                write_ghost_tree_report(result, project_root)

            # Print summary
            print("\nGhost Results")
            print("-------------")
            print(f"Orphans:   {counts.get('orphans', 0)}")
            print(f"Legacy:    {counts.get('legacy', 0)}")
            print(f"Sessions:  {counts.get('sessions', 0)}")
            print(f"Duplicates: {counts.get('duplicates', 0)}")
            print(f"Semantic:  {counts.get('semantic', 0)}")

            if getattr(args, "tree", False):
                print("\n📄 Tree reports saved to:")
                for key in ["orphans", "legacy", "sessions", "duplicates", "semantic"]:
                    if counts.get(key, 0) > 0:
                        print(f"   - ghost_{key}_tree.txt")

            if ghost_data.get("limit_violation"):
                print(f"\n⚠️  {ghost_data['limit_violation']['message']}")
                return ghost_data["limit_violation"]["exit_code"]

        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "Ghost command")

    return EXIT_OK


def cmd_writers(args: argparse.Namespace) -> int:
    project_root = _resolve_project_root(args)
    ensure_project_initialized(project_root)

    results = run_writers_analysis(project_root)
    output_path = _exports_dir(project_root) / "writers_report.md"
    render_writer_report(results, str(output_path))

    print(f"Writers report saved: {output_path}")
    return EXIT_OK


def cmd_artifacts(args: argparse.Namespace) -> int:
    """Artifact Hygiene Engine - report suspicious visual artifacts without deleting anything."""
    try:
        with ErrorContext("Running artifact hygiene analysis"):
            project_root = _resolve_project_root(args)
            artifact_data = run_artifact_hygiene(args, project_root)
            result = artifact_data["result"]
            summary = result.get("summary", {})
            paths = artifact_data["paths"]

            if getattr(args, "json", False):
                print(paths["json"].read_text(encoding="utf-8"))
                return EXIT_OK

            if getattr(args, "delete_list", False):
                delete_candidates = result.get("delete_candidates", [])
                print("\n".join(delete_candidates))
                return EXIT_OK

            print("\nArtifact Hygiene Results")
            print("------------------------")
            print(f"Assets scanned: {summary.get('total_assets_scanned', 0)}")
            print(f"Report candidates: {summary.get('report_candidates', 0)}")
            print(f"Safe to delete now: {summary.get('safe_to_delete', 0)}")
            print(f"Reclaimable MB: {summary.get('safe_to_delete_mb', 0)}")
            print(f"High confidence: {summary.get('high_confidence_cleanup_candidates', 0)}")
            print(f"Review candidates: {summary.get('review_candidates', 0)}")
            print(f"Duplicate groups: {summary.get('duplicate_groups', 0)}")
            print(f"Delete candidates: {summary.get('delete_candidates', 0)}")

            if getattr(args, "by_resolution", False):
                print("\nBy Resolution")
                for group in result.get("grouped_by_resolution", []):
                    print(f"  {group['resolution']}: {group['count']}")

            print(f"\nMarkdown report: {paths['markdown']}")
            print(f"JSON data:       {paths['json']}")
            print(f"Delete list:     {paths['delete_list']}")
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "Artifacts command")


def cmd_audit_retention(args: argparse.Namespace) -> int:
    """Audit Retention Engine - report stale generated audits and exports without deleting anything."""
    try:
        with ErrorContext("Running audit retention analysis"):
            project_root = _resolve_project_root(args)
            retention_data = run_audit_retention(args, project_root)
            result = retention_data["result"]
            summary = result.get("summary", {})
            paths = retention_data["paths"]

            if getattr(args, "json", False):
                print(paths["json"].read_text(encoding="utf-8"))
                return EXIT_OK

            if getattr(args, "delete_list", False):
                delete_candidates = result.get("delete_candidates", [])
                print("\n".join(delete_candidates))
                return EXIT_OK

            print("\nAudit Retention Results")
            print("-----------------------")
            print(f"Reports scanned: {summary.get('total_reports_scanned', 0)}")
            print(f"Report candidates: {summary.get('report_candidates', 0)}")
            print(f"Safe to delete now: {summary.get('safe_to_delete', 0)}")
            print(f"Reclaimable MB: {summary.get('safe_to_delete_mb', 0)}")
            print(f"High confidence: {summary.get('high_confidence_cleanup_candidates', 0)}")
            print(f"Review candidates: {summary.get('review_candidates', 0)}")
            print(f"Duplicate groups: {summary.get('duplicate_groups', 0)}")
            print(f"Families detected: {summary.get('families_detected', 0)}")
            print(f"Delete candidates: {summary.get('delete_candidates', 0)}")

            if getattr(args, "by_family", False):
                print("\nBy Family")
                for group in result.get("grouped_by_family", []):
                    print(f"  {group['report_family']}: {group['count']}")

            print(f"\nMarkdown report: {paths['markdown']}")
            print(f"JSON data:       {paths['json']}")
            print(f"Delete list:     {paths['delete_list']}")
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "Audit retention command")


def cmd_dead(args: argparse.Namespace) -> int:
    """Dead Code Radar - finds files with zero or minimal usage."""
    try:
        with ErrorContext("Running dead code analysis"):
            project_root = _resolve_project_root(args)
            threshold = getattr(args, "threshold", 2)
            json_output = getattr(args, "json", False)
            require_healthy_snapshot(project_root, operation="dead code analysis")
            snapshot = load_snapshot(project_root)
            files = [f.get("path") for f in snapshot.get("files", [])]
            result = analyze_dead_code(files, low_usage_threshold=threshold)

            if json_output:
                print(json.dumps(result, indent=2))
            else:
                output = render_dead(result)
                _safe_print(output)
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "Dead code analysis")


def cmd_unused(args: argparse.Namespace) -> int:
    """Unused System Scan - finds systems that exist but aren't used."""
    try:
        with ErrorContext("Running unused systems analysis"):
            project_root = _resolve_project_root(args)
            json_output = getattr(args, "json", False)
            no_color = getattr(args, "no_color", False)
            result = analyze_unused_systems(project_root)

            if json_output:
                print(json.dumps(result, indent=2))
            else:
                output = render_unused(result, colored=not no_color)
                _safe_print(output)
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "Unused systems analysis")


def cmd_patterns(args: argparse.Namespace) -> int:
    """Suspicious Patterns - detects forbidden code patterns."""
    try:
        with ErrorContext("Running suspicious patterns analysis"):
            project_root = _resolve_project_root(args)
            patterns_file = getattr(args, "file", None)
            json_output = getattr(args, "json", False)
            no_color = getattr(args, "no_color", False)
            result = analyze_patterns(project_root, patterns_file=patterns_file)

            if json_output:
                print(json.dumps(result, indent=2))
            else:
                output = render_patterns(result, colored=not no_color)
                _safe_print(output)
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "Suspicious patterns analysis")


def cmd_nebula_export(args: argparse.Namespace) -> int:
    """Export the locked Codebase Nebula bridge artifact."""
    try:
        with ErrorContext("Exporting Codebase Nebula bridge"):
            project_root = _resolve_project_root(args)
            payload, output_path = run_nebula_export(project_root)
            summary = payload.get("summary", {})
            by_kind = summary.get("byKind", {})

            print("\nNebula Bridge Export")
            print("--------------------")
            print(f"Artifact: {output_path}")
            print(f"Findings: {summary.get('findingCount', 0)}")
            print(f"Ghost: {by_kind.get('ghost', 0)}")
            print(f"Dead: {by_kind.get('dead', 0)}")
            print(f"Unused systems: {by_kind.get('unused_system', 0)}")
            print(f"Suspicious patterns: {by_kind.get('suspicious_pattern', 0)}")
            print(f"Artifact hygiene: {by_kind.get('artifact_hygiene', 0)}")
            print(f"Audit retention: {by_kind.get('audit_retention', 0)}")
            print(f"VFX contract: {by_kind.get('vfx_contract', 0)}")
            print(f"UI audit: {by_kind.get('ui_audit', 0)}")
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "Nebula export")


def cmd_search(args: argparse.Namespace) -> int:
    """Smart Search - power-user code search."""
    try:
        with ErrorContext("Running smart search"):
            project_root = _resolve_project_root(args)
            patterns = getattr(args, "pattern", [])
            invert = getattr(args, "invert", False)
            files_only = getattr(args, "files_only", False)
            json_output = getattr(args, "json", False)
            no_color = getattr(args, "no_color", False)

            if not patterns:
                print("Error: At least one pattern is required")
                return EXIT_VALIDATION_ERROR

            result = smart_search(patterns, project_root, invert=invert, files_only=files_only)

            if json_output:
                print(json.dumps(result, indent=2))
            else:
                output = render_search(result, colored=not no_color)
                _safe_print(output)
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "Smart search")


def cmd_audit_vfx(args: argparse.Namespace) -> int:
    """VFX contract audit for FX-oriented JavaScript files."""
    try:
        with ErrorContext("Running VFX contract audit"):
            project_root = Path(getattr(args, "project_root", ".")).resolve()
            json_output = getattr(args, "json", False)
            output_dir = getattr(args, "output", None)
            require_healthy_snapshot(project_root, operation="VFX contract audit")

            target_dir = Path(output_dir).resolve() if output_dir else project_root / ".project-control" / "exports"
            result, markdown_path, json_path = run_vfx_contract_audit(project_root, target_dir)

            if json_output:
                print(json.dumps(vfx_contract_result_to_dict(result), indent=2, ensure_ascii=False))
            else:
                _safe_print(render_vfx_contract_console(result))

            if not json_output:
                print(f"VFX audit report saved: {markdown_path}")
                print(f"VFX audit data saved:   {json_path}")
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "VFX contract audit")


def cmd_audit_patron(args: argparse.Namespace) -> int:
    """Patron's Path integration contract audit."""
    try:
        with ErrorContext("Running Patron's Path audit"):
            project_root = Path(getattr(args, "project_root", ".")).resolve()
            json_output = getattr(args, "json", False)
            output_dir = getattr(args, "output", None)
            result, markdown_path, json_path = run_patron_path_audit(
                project_root,
                Path(output_dir).resolve() if output_dir else None,
            )

            if json_output:
                print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
            else:
                print("\nPatron's Path Integration Contract")
                print("----------------------------------")
                print(f"Project root: {result.project_root}")
                print(f"Contract file: {result.contract_path}")
                print(f"Overall status: {result.summary['overallStatus']}")
                print(f"OK: {result.summary['okCount']}")
                print(f"Warnings: {result.summary['warningCount']}")
                print(f"Errors: {result.summary['errorCount']}")
                print(f"Report saved: {markdown_path}")
                print(f"Data saved:   {json_path}")
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "Patron's Path audit")


def cmd_ecosystem_health(args: argparse.Namespace) -> int:
    """Cross-project ecosystem health check."""
    try:
        with ErrorContext("Running ecosystem health check"):
            project_root = Path(getattr(args, "project_root", ".")).resolve()
            json_output = getattr(args, "json", False)
            output_dir = getattr(args, "output", None)
            result, markdown_path, json_path = run_ecosystem_health(
                project_root,
                Path(output_dir).resolve() if output_dir else None,
            )

            if json_output:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print("\nEcosystem Health")
                print("----------------")
                print(f"Project root: {result['projectRoot']}")
                print(f"Overall status: {result['summary']['overallStatus']}")
                print(f"Project Control: {result['summary']['projectControlStatus']}")
                print(f"Nebula bridge:  {result['summary']['nebulaBridgeStatus']}")
                print(f"Downstream:     {result['summary']['downstreamStatus']}")
                print(f"Report saved:   {markdown_path}")
                print(f"Data saved:     {json_path}")
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "Ecosystem health")


def cmd_ui_verify(args: argparse.Namespace) -> int:
    """Run configurable browser-based UI verification."""
    try:
        project_root = Path(getattr(args, "project_root", ".")).resolve()
        json_output = getattr(args, "json", False)
        include_html = getattr(args, "html", False)
        if getattr(args, "list_profiles", False):
            profiles = list_ui_verification_profiles(project_root)

            if json_output:
                print(
                    json.dumps(
                        [
                            {
                                "name": profile.name,
                                "app_name": profile.app_name,
                                "path": str(profile.path),
                                "source": profile.source,
                                "is_default": profile.is_default,
                                "is_valid": profile.is_valid,
                                "error": profile.error,
                            }
                            for profile in profiles
                        ],
                        indent=2,
                        ensure_ascii=False,
                    )
                )
            else:
                print("UI VERIFICATION PROFILES")
                print("=" * 70)
                if not profiles:
                    print("No UI verification profiles found.")
                for profile in profiles:
                    flags: list[str] = []
                    if profile.is_default:
                        flags.append("default")
                    if not profile.is_valid:
                        flags.append("invalid")
                    suffix = f" [{' | '.join(flags)}]" if flags else ""
                    print(f"- {profile.name}{suffix}")
                    print(f"  App:    {profile.app_name}")
                    print(f"  Source: {profile.source}")
                    print(f"  Path:   {profile.path}")
                    if profile.error:
                        print(f"  Error:  {profile.error}")
            return EXIT_OK

        report, config_path, markdown_path, json_path, html_path = run_ui_verification_profile(
            project_root,
            config_path=getattr(args, "config", None),
            profile_name=getattr(args, "profile", None),
            url=getattr(args, "url", None),
            image_path=getattr(args, "image", None),
            screenshots_dir=getattr(args, "screenshots", None),
            headless=getattr(args, "headless", True),
            output_dir=getattr(args, "output", None),
            include_html=include_html,
        )

        if json_output:
            print(json_path.read_text(encoding="utf-8"))
        else:
            _safe_print(render_ui_verification_console_summary(report))
            print(f"UI verification profile: {config_path}")
            print(f"UI verification report:  {markdown_path}")
            print(f"UI verification data:    {json_path}")
            if html_path is not None:
                print(f"UI verification html:    {html_path}")

        return EXIT_OK
    except Exception as e:
        return ErrorHandler.handle(e, "UI verification")


def dispatch(args: argparse.Namespace) -> int:
    if args.command == "init":
        return cmd_init(args)
    if args.command == "scan":
        return cmd_scan(args)
    if args.command == "checklist":
        return cmd_checklist(args)
    if args.command == "quick":
        return cmd_quick(args)
    if args.command == "find":
        return cmd_find(args)
    if args.command == "ghost":
        return cmd_ghost(args)
    if args.command == "artifacts":
        return cmd_artifacts(args)
    if args.command == "writers":
        return cmd_writers(args)
    if args.command == "dead":
        return cmd_dead(args)
    if args.command == "unused":
        return cmd_unused(args)
    if args.command == "patterns":
        return cmd_patterns(args)
    if args.command == "nebula":
        if getattr(args, "nebula_cmd", None) == "export":
            return cmd_nebula_export(args)
        print("Unknown nebula command.")
        return EXIT_VALIDATION_ERROR
    if args.command == "search":
        return cmd_search(args)
    if args.command == "audit":
        if getattr(args, "audit_cmd", None) == "vfx":
            return cmd_audit_vfx(args)
        if getattr(args, "audit_cmd", None) == "patron":
            return cmd_audit_patron(args)
        print("Unknown audit command.")
        return EXIT_VALIDATION_ERROR
    if args.command == "ecosystem":
        if getattr(args, "ecosystem_cmd", None) == "health":
            return cmd_ecosystem_health(args)
        print("Unknown ecosystem command.")
        return EXIT_VALIDATION_ERROR
    if args.command == "audits":
        if getattr(args, "audits_cmd", None) == "retention":
            return cmd_audit_retention(args)
        print("Unknown audits command.")
        return EXIT_VALIDATION_ERROR
    if args.command == "tui":
        tui_cmd = getattr(args, "tui_cmd", None)
        if tui_cmd in (None, "menu"):
            run_menu(_resolve_project_root(args))
            return EXIT_OK
        if tui_cmd == "verify":
            return cmd_ui_verify(args)
        print("Unknown tui command.")
        return EXIT_VALIDATION_ERROR
    if args.command == "ui":
        ui_cmd = getattr(args, "ui_cmd", None)
        if ui_cmd == "verify":
            return cmd_ui_verify(args)
        print("Usage: pc ui verify [options]")
        print("Try 'pc ui verify --help' for available options.")
        return EXIT_VALIDATION_ERROR
    if args.command == "gui":
        return _handle_gui_command(args)
    if args.command == "graph":
        project_root = Path(getattr(args, "project_root", ".")).resolve()
        config_path = Path(args.config).resolve() if getattr(args, "config", None) else None
        if getattr(args, "graph_cmd", None) == "build":
            return graph_build(project_root, config_path)
        if getattr(args, "graph_cmd", None) == "report":
            return graph_report(project_root, config_path)
        if getattr(args, "graph_cmd", None) == "trace":
            direction = getattr(args, "direction", "both")
            max_depth = None if getattr(args, "no_limits", False) or getattr(args, "all", False) else getattr(args, "max_depth", None)
            max_paths = None if getattr(args, "no_limits", False) or getattr(args, "all", False) else getattr(args, "max_paths", None)
            return graph_trace(
                project_root,
                config_path,
                getattr(args, "target", ""),
                direction,
                max_depth,
                max_paths,
                getattr(args, "line", False),
            )
    if args.command == "embed":
        try:
            from project_control.embedding.index_builder import build_index
            from project_control.embedding.config import EmbedConfig
            from project_control.embedding.search_engine import SearchEngine
        except ImportError as e:
            print("❌ Embedding dependencies not installed.")
            print("   Install with: pip install -e '.[embedding]'")
            print(f"   Error: {e}")
            return EXIT_VALIDATION_ERROR

        root = Path(getattr(args, "path", ".")).resolve()
        cfg = EmbedConfig()

        if getattr(args, "embed_cmd", None) == "build":
            try:
                files, chunks, dim = build_index(root, cfg, overwrite=False)
                print(f"Embedding build complete. Files: {files}, Chunks: {chunks}, Dim: {dim}")
                print(f"Index: {cfg.index_path}")
                return EXIT_OK
            except Exception as e:
                print(f"❌ Embedding build failed: {e}")
                print("   Ensure Ollama is running: ollama serve")
                print(f"   Download model: ollama pull {cfg.model}")
                return EXIT_VALIDATION_ERROR
        if getattr(args, "embed_cmd", None) == "rebuild":
            try:
                files, chunks, dim = build_index(root, cfg, overwrite=True)
                print(f"Embedding rebuild complete. Files: {files}, Chunks: {chunks}, Dim: {dim}")
                return EXIT_OK
            except Exception as e:
                print(f"❌ Embedding rebuild failed: {e}")
                return EXIT_VALIDATION_ERROR
        if getattr(args, "embed_cmd", None) == "search":
            try:
                engine = SearchEngine(cfg)
                hits = engine.search(getattr(args, "query", ""), top_k=getattr(args, "top_k", 5))
                for rank, hit in enumerate(hits, 1):
                    print(f"  {rank}. {hit['path']} (score={hit['score']:.4f})")
                return EXIT_OK
            except Exception as e:
                print(f"❌ Embedding search failed: {e}")
                return EXIT_VALIDATION_ERROR

    # Preset commands
    if args.command == "preset":
        return _handle_preset_command(args)

    # Export commands
    if args.command == "export":
        return _handle_export_command(args)

    # Import commands
    if args.command == "import":
        return _handle_import_command(args)

    # Explore command
    if args.command == "explore":
        return _handle_explore_command(args)
    
    # Wizard command
    if args.command == "wizard":
        return _handle_wizard_command(args)

    print(f"Unknown command: {args.command}")
    return EXIT_VALIDATION_ERROR


# Backward compat — used by cmd_scan
def run_scan(project_root: Path) -> None:
    """Run scan with configuration."""
    patterns = load_patterns(project_root)
    snapshot = create_snapshot(project_root, patterns.get("ignore_dirs", []), get_scan_extensions(patterns))
    save_snapshot(snapshot, project_root)
    print(f"Scan complete. {len(snapshot.get('files', []))} files indexed.")


# ── Preset Commands ───────────────────────────────────────────────────────

def _handle_preset_command(args: argparse.Namespace) -> int:
    """Handle preset subcommands."""
    from project_control.config.presets import PresetManager

    try:
        project_root = Path(getattr(args, "project_root", ".")).resolve()
        manager = PresetManager(project_root)
        preset_cmd = getattr(args, "preset_cmd", None)

        if preset_cmd == "list":
            presets = manager.list_presets()
            print("Available Presets:")
            print("=" * 60)
            for preset in presets:
                category_mark = " [builtin]" if preset["category"] == "builtin" else " [custom]"
                print(f"  • {preset['name']}{category_mark}")
                print(f"    {preset['description']}")
            print()

            current = manager.get_current_preset_name()
            if current:
                print(f"Current preset: {current}")
            else:
                print("Current configuration doesn't match any preset")
            return EXIT_OK

        if preset_cmd == "apply":
            name = getattr(args, "name", None)
            if not name:
                raise ValidationError("Preset name is required")

            backup = not getattr(args, "no_backup", False)
            if not manager.apply_preset(name, backup=backup):
                raise ValidationError(f"Preset not found: {name}")

            print(f"[OK] Applied preset: {name}")
            if backup:
                print("  (Backup created in .project-control/backups/)")
            return EXIT_OK

        if preset_cmd == "save":
            name = getattr(args, "name", None)
            if not name:
                raise ValidationError("Preset name is required")

            description = getattr(args, "description", "") or f"Custom preset: {name}"
            if not manager.save_custom_preset(name, description):
                raise ValidationError(f"Failed to save preset: {name}")

            print(f"[OK] Saved custom preset: {name}")
            print(f"  Description: {description}")
            return EXIT_OK

        if preset_cmd == "delete":
            name = getattr(args, "name", None)
            if not name:
                raise ValidationError("Preset name is required")

            if not manager.delete_custom_preset(name):
                raise ValidationError(f"Cannot delete preset '{name}' (not found or is built-in)")

            print(f"[OK] Deleted custom preset: {name}")
            return EXIT_OK

        raise ValidationError(
            "No preset subcommand specified",
            details="Use: pc preset {list|apply|save|delete}",
        )
    except Exception as e:
        return ErrorHandler.handle(e, "Preset command")


# ── Export Commands ───────────────────────────────────────────────────────

def _handle_export_command(args: argparse.Namespace) -> int:
    """Handle export subcommands."""
    from project_control.persistence.state_manager import StateManager

    try:
        project_root = Path(getattr(args, "project_root", ".")).resolve()
        manager = StateManager(project_root)

        if getattr(args, "export_cmd", None) != "state":
            raise ValidationError(
                "No export subcommand specified",
                details="Use: pc export {state}",
            )

        export_path = getattr(args, "path", None)
        if export_path:
            export_path = Path(export_path).resolve()

        include_metadata = not getattr(args, "no_metadata", False)
        result_path = manager.export_state(export_path, include_metadata=include_metadata)
        print(f"[OK] State exported to: {result_path.resolve()}")
        return EXIT_OK
    except Exception as e:
        return ErrorHandler.handle(e, "Export command")


# ── Import Commands ───────────────────────────────────────────────────────

def _handle_import_command(args: argparse.Namespace) -> int:
    """Handle import subcommands."""
    from project_control.persistence.state_manager import StateManager

    try:
        project_root = Path(getattr(args, "project_root", ".")).resolve()
        manager = StateManager(project_root)

        if getattr(args, "import_cmd", None) != "state":
            raise ValidationError(
                "No import subcommand specified",
                details="Use: pc import {state}",
            )

        path_value = getattr(args, "path", None)
        if not path_value:
            raise ValidationError("Import path is required")

        import_path = Path(path_value).resolve()
        if not import_path.exists():
            raise ProjectControlFileNotFoundError(f"Import file not found: {import_path}")

        merge = getattr(args, "merge", False)
        manager.import_state(import_path, merge=merge)
        mode = "merged" if merge else "imported"
        print(f"[OK] State {mode} from: {import_path}")
        return EXIT_OK
    except Exception as e:
        return ErrorHandler.handle(e, "Import command")


# ── Explore Command ───────────────────────────────────────────────────────

def _handle_explore_command(args: argparse.Namespace) -> int:
    """Handle explore command."""
    from project_control.ui.file_explorer import FileExplorer

    project_root = Path(getattr(args, "project_root", ".")).resolve()
    raw_path = Path(getattr(args, "path", "."))
    start_path = raw_path.resolve() if raw_path.is_absolute() else (project_root / raw_path).resolve()

    # Resolve start_path relative to project_root if needed
    try:
        start_path = start_path.relative_to(project_root)
    except ValueError:
        # If not relative, use as-is if it's within project_root
        if not str(start_path).startswith(str(project_root)):
            return ErrorHandler.handle(
                ValidationError(
                    "Explore path must stay within the project root",
                    details=f"Project root: {project_root}",
                ),
                "Explore command",
            )

    start_path = project_root / start_path

    try:
        explorer = FileExplorer(project_root)

        if start_path.is_dir():
            explorer.change_directory(str(start_path.relative_to(project_root)))
            output = explorer.render_file_list()
            _safe_print(output)
        elif start_path.is_file():
            rel_path = str(start_path.relative_to(project_root))
            output = explorer.render_file_details(rel_path)
            _safe_print(output)
        else:
            return ErrorHandler.handle(
                ProjectControlFileNotFoundError(
                    f"Explore path not found: {start_path}",
                    details=f"Project root: {project_root}",
                ),
                "Explore command",
            )

        return EXIT_OK
    except Exception as e:
        return ErrorHandler.handle(e, "Explore command")


def _safe_print(text: str) -> None:
    """Print text safely, handling Unicode encoding issues on Windows."""
    import sys
    try:
        print(text)
    except UnicodeEncodeError:
        stdout_encoding = sys.stdout.encoding or "utf-8"
        # Fallback for Windows console with limited encoding
        if sys.platform == "win32":
            # Encode with error replacement
            safe_text = text.encode(stdout_encoding, errors="replace").decode(stdout_encoding)
            print(safe_text)
        else:
            # For other platforms, try UTF-8
            try:
                print(text.encode("utf-8", errors="replace").decode("utf-8"))
            except Exception:
                print(text.encode("ascii", errors="replace").decode("ascii"))


# ── Wizard Command ───────────────────────────────────────────────────────

def _handle_wizard_command(args: argparse.Namespace) -> int:
    """Handle interactive setup wizard command."""
    from project_control.ui.wizard import run_wizard, mark_wizard_completed, clear_wizard_mark
    from project_control.utils.terminal import print_success, print_info, print_warning
    
    project_root = Path(getattr(args, "project_root", ".")).resolve()
    reset = getattr(args, "reset", False)
    
    try:
        # If reset flag is set, clear the wizard mark
        if reset:
            clear_wizard_mark(project_root)
            print_info("Wizard reset. Starting fresh configuration...")
        
        # Run the wizard
        config = run_wizard(project_root)
        
        if config:
            # Mark wizard as completed
            mark_wizard_completed(project_root)
            print_success("\nSetup wizard completed successfully!")
            print_info(f"\nYour project is now configured with:")
            print(f"  • Project Type: {config.get('project_mode', 'auto')}")
            print(f"  • Output Format: {config.get('output_format', 'both')}")
            print(f"  • Analysis Mode: {config.get('analysis_mode', 'pragmatic')}")
            print_info("\nNext steps:")
            print("  • Run 'pc scan' to index your project")
            print("  • Run 'pc quick' for a full analysis")
            print("  • Run 'pc tui' for the TUI text-based menu")
            return EXIT_OK
        else:
            print_warning("\nWizard was cancelled. No changes were made.")
            return EXIT_OK
            
    except KeyboardInterrupt:
        print_warning("\n\nWizard interrupted by user.")
        return EXIT_OK
    except Exception as e:
        return ErrorHandler.handle(e, "Wizard command")


def _handle_gui_command(args: argparse.Namespace) -> int:
    """Launch the desktop Tkinter GUI."""
    from project_control.gui.app import launch_gui

    project_root = Path(getattr(args, "project_root", ".")).resolve()
    try:
        launch_gui(project_root)
        return EXIT_OK
    except Exception as e:
        return ErrorHandler.handle(e, "GUI command")
