"""Tkinter desktop application for PROJECT_CONTROL."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from tkinter import TclError
import tkinter as tk
from tkinter import scrolledtext, ttk

from project_control.presentation.adapters import (
    PresentationResult,
    present_dead,
    present_ghost,
    present_graph_report,
    present_graph_trace,
    present_overview,
    present_report_registry,
    present_scan,
    present_ui_verification,
    present_vfx_audit,
)
from project_control.services.report_service import list_all_reports
from project_control.ui.state import AppState, load_state, save_state


THEME = {
    "bg": "#13061E",
    "bg_soft": "#1D0F2D",
    "panel": "#2A1840",
    "panel_alt": "#341D52",
    "text": "#F6F1FF",
    "text_soft": "#D5C7F0",
    "border": "#4C2F77",
    "accent": "#1FD1C2",
    "accent_dark": "#12A89B",
    "danger": "#FF6B8A",
}


@dataclass
class BackgroundEvent:
    """Event emitted by the background runner."""

    kind: str
    workflow: str
    payload: object


class BackgroundRunner:
    """Run one background workflow at a time and emit events via queue."""

    def __init__(self) -> None:
        self.events: queue.Queue[BackgroundEvent] = queue.Queue()
        self._thread: threading.Thread | None = None

    def is_busy(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def submit(self, workflow: str, func, /, *args, **kwargs) -> None:
        if self.is_busy():
            raise RuntimeError("Another workflow is already running.")

        def worker() -> None:
            try:
                result = func(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - exercised through queue handling tests
                self.events.put(BackgroundEvent("error", workflow, exc))
                return
            self.events.put(BackgroundEvent("result", workflow, result))

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    def poll(self) -> list[BackgroundEvent]:
        items: list[BackgroundEvent] = []
        while True:
            try:
                items.append(self.events.get_nowait())
            except queue.Empty:
                return items


class GUIController:
    """Owns project state and dispatches normalized workflows."""

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.state = load_state(self.project_root)
        self.workflow_handlers = {
            "overview": self.get_overview,
            "scan": self.run_scan,
            "ghost": self.run_ghost,
            "dead": self.run_dead,
            "graph_report": self.run_graph_report,
            "graph_trace": self.run_graph_trace,
            "reports": self.get_reports,
            "vfx_audit": self.run_vfx_audit,
            "ui_verification": self.run_ui_verification,
        }

    def dispatch(self, workflow: str, **kwargs) -> PresentationResult:
        handler = self.workflow_handlers.get(workflow)
        if handler is None:
            raise KeyError(f"Unknown workflow: {workflow}")
        return handler(**kwargs)

    def refresh_state(self) -> AppState:
        self.state = load_state(self.project_root)
        return self.state

    def save_settings(
        self,
        *,
        project_mode: str,
        graph_profile: str,
        trace_depth: int,
        trace_all_paths: bool,
        ui_verification_headless: bool,
    ) -> AppState:
        self.state = AppState(
            project_mode=project_mode,
            graph_profile=graph_profile,
            trace_direction=self.state.trace_direction,
            trace_depth=trace_depth,
            trace_all_paths=trace_all_paths,
            ui_verification_headless=ui_verification_headless,
            favorites=self.state.favorites,
            history=self.state.history,
            onboarding_seen=self.state.onboarding_seen,
            last_ui_verification_profile=self.state.last_ui_verification_profile,
        )
        save_state(self.project_root, self.state)
        return self.state

    def update_trace_direction(self, direction: str) -> AppState:
        self.state.trace_direction = direction
        save_state(self.project_root, self.state)
        return self.state

    def get_overview(self) -> PresentationResult:
        return present_overview(self.project_root, self.refresh_state())

    def get_reports(self) -> PresentationResult:
        return present_report_registry(self.project_root)

    def run_scan(self) -> PresentationResult:
        return present_scan(self.project_root)

    def run_ghost(self, *, mode: str = "pragmatic", tree: bool = True) -> PresentationResult:
        return present_ghost(self.project_root, mode=mode, tree=tree)

    def run_dead(self, *, threshold: int = 2) -> PresentationResult:
        return present_dead(self.project_root, threshold=threshold)

    def run_graph_report(self) -> PresentationResult:
        return present_graph_report(self.project_root, self.refresh_state())

    def run_graph_trace(self, *, target: str, direction: str = "both") -> PresentationResult:
        self.update_trace_direction(direction)
        return present_graph_trace(
            self.project_root,
            self.refresh_state(),
            target=target,
            direction=direction,
        )

    def run_vfx_audit(self) -> PresentationResult:
        return present_vfx_audit(self.project_root)

    def run_ui_verification(self, *, profile_name: str | None = None) -> PresentationResult:
        result = present_ui_verification(
            self.project_root,
            profile_name=profile_name or None,
            headless=self.refresh_state().ui_verification_headless,
            include_html=True,
        )
        if profile_name:
            self.state.last_ui_verification_profile = profile_name
            save_state(self.project_root, self.state)
        elif result.summary.get("profile"):
            self.state.last_ui_verification_profile = str(result.summary["profile"])
            save_state(self.project_root, self.state)
        return result


class ProjectControlGUI:
    """Minimal desktop GUI shell around existing services."""

    workflow_tabs = {
        "overview": "overview",
        "scan": "overview",
        "ghost": "ghost_dead",
        "dead": "ghost_dead",
        "graph_report": "graph",
        "graph_trace": "graph",
        "reports": "reports",
        "vfx_audit": "audits",
        "ui_verification": "audits",
        "settings": "settings",
    }

    def __init__(
        self,
        project_root: Path,
        *,
        controller: GUIController | None = None,
        root: tk.Tk | None = None,
    ):
        self.project_root = project_root.resolve()
        self.controller = controller or GUIController(self.project_root)
        self.runner = BackgroundRunner()
        self.root = root or self.create_root()
        self.root.title(f"PROJECT CONTROL GUI - {self.project_root.name}")
        self.root.geometry("1360x900")
        self.root.minsize(1180, 760)
        self.root.configure(bg=THEME["bg"])

        self.status_var = tk.StringVar(value="Ready")
        self.header_var = tk.StringVar(value=f"Project: {self.project_root.name}")
        self.sidebar_actions: dict[str, tk.Button] = {}
        self.tab_frames: dict[str, ttk.Frame] = {}
        self.tab_text_widgets: dict[str, scrolledtext.ScrolledText] = {}
        self.tab_summary_vars: dict[str, list[tuple[tk.StringVar, tk.StringVar]]] = {}
        self.tab_paths_var: dict[str, tk.StringVar] = {}
        self.report_paths_cache: dict[str, Path] = {}
        self.report_listbox: tk.Listbox | None = None
        self.report_preview: scrolledtext.ScrolledText | None = None

        self.ghost_mode_var = tk.StringVar(value="pragmatic")
        self.ghost_tree_var = tk.BooleanVar(value=True)
        self.dead_threshold_var = tk.IntVar(value=2)
        self.trace_target_var = tk.StringVar()
        self.trace_direction_var = tk.StringVar(value=self.controller.state.trace_direction)
        self.ui_profile_var = tk.StringVar(value=self.controller.state.last_ui_verification_profile or "")
        self.settings_mode_var = tk.StringVar(value=self.controller.state.project_mode)
        self.settings_profile_var = tk.StringVar(value=self.controller.state.graph_profile)
        self.settings_trace_depth_var = tk.IntVar(value=self.controller.state.trace_depth)
        self.settings_all_paths_var = tk.BooleanVar(value=self.controller.state.trace_all_paths)
        self.settings_headless_var = tk.BooleanVar(value=self.controller.state.ui_verification_headless)

        self._configure_styles()
        self._build_layout()
        self._refresh_overview()
        self._refresh_reports(select_tab=False)
        self.root.after(100, self._poll_background_events)

    @staticmethod
    def create_root() -> tk.Tk:
        """Create a Tk root so tests can smoke it independently."""
        return tk.Tk()

    def run(self) -> None:
        self.root.mainloop()

    def destroy(self) -> None:
        self.root.destroy()

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except TclError:
            pass
        style.configure("PC.TFrame", background=THEME["bg"])
        style.configure("Panel.TFrame", background=THEME["panel"])
        style.configure("PanelAlt.TFrame", background=THEME["panel_alt"])
        style.configure("PC.TLabel", background=THEME["bg"], foreground=THEME["text"])
        style.configure("Panel.TLabel", background=THEME["panel"], foreground=THEME["text"])
        style.configure("Accent.TButton", background=THEME["accent"], foreground=THEME["bg"])
        style.configure("PC.TNotebook", background=THEME["bg"], borderwidth=0)
        style.configure("PC.TNotebook.Tab", background=THEME["panel"], foreground=THEME["text_soft"], padding=(12, 8))
        style.map("PC.TNotebook.Tab", background=[("selected", THEME["accent_dark"])], foreground=[("selected", THEME["text"])])
        style.configure("PC.TCombobox", fieldbackground=THEME["panel_alt"], background=THEME["panel_alt"], foreground=THEME["text"])

    def _build_layout(self) -> None:
        outer = tk.Frame(self.root, bg=THEME["bg"])
        outer.pack(fill=tk.BOTH, expand=True)

        sidebar = tk.Frame(outer, bg=THEME["bg_soft"], width=240, bd=0, highlightthickness=1, highlightbackground=THEME["border"])
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        content = tk.Frame(outer, bg=THEME["bg"])
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        header = tk.Frame(content, bg=THEME["panel"], height=72, highlightthickness=1, highlightbackground=THEME["border"])
        header.pack(fill=tk.X, padx=10, pady=(10, 6))
        header.pack_propagate(False)
        tk.Label(header, text="PROJECT CONTROL", bg=THEME["panel"], fg=THEME["text"], font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=16, pady=(10, 0))
        tk.Label(header, textvariable=self.header_var, bg=THEME["panel"], fg=THEME["text_soft"], font=("Segoe UI", 10)).pack(anchor="w", padx=16)

        notebook_holder = tk.Frame(content, bg=THEME["bg"])
        notebook_holder.pack(fill=tk.BOTH, expand=True, padx=10)
        self.notebook = ttk.Notebook(notebook_holder, style="PC.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True)

        bottom = tk.Frame(content, bg=THEME["panel"], highlightthickness=1, highlightbackground=THEME["border"])
        bottom.pack(fill=tk.X, padx=10, pady=(6, 10))
        tk.Label(bottom, textvariable=self.status_var, bg=THEME["panel"], fg=THEME["text"], anchor="w").pack(fill=tk.X, padx=12, pady=(8, 4))
        self.log_widget = scrolledtext.ScrolledText(
            bottom,
            height=5,
            wrap=tk.WORD,
            bg=THEME["bg_soft"],
            fg=THEME["text_soft"],
            insertbackground=THEME["text"],
            relief=tk.FLAT,
        )
        self.log_widget.pack(fill=tk.X, padx=12, pady=(0, 10))

        self._build_sidebar(sidebar)
        self._build_tabs()

    def _build_sidebar(self, parent: tk.Frame) -> None:
        tk.Label(parent, text="Workflows", bg=THEME["bg_soft"], fg=THEME["text"], font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=16, pady=(18, 8))
        button_specs = [
            ("overview", "Overview", lambda: self._select_tab("overview")),
            ("scan", "Run Scan", lambda: self._submit("scan")),
            ("ghost", "Run Ghost", lambda: self._submit("ghost", mode=self.ghost_mode_var.get(), tree=self.ghost_tree_var.get())),
            ("dead", "Run Dead", lambda: self._submit("dead", threshold=self.dead_threshold_var.get())),
            ("graph_report", "Graph Report", lambda: self._submit("graph_report")),
            ("graph_trace", "Graph Trace", self._submit_graph_trace),
            ("vfx_audit", "VFX Audit", lambda: self._submit("vfx_audit")),
            ("ui_verification", "UI Verify", self._submit_ui_verify),
            ("reports", "Reports", lambda: self._refresh_reports(select_tab=True)),
            ("settings", "Settings", lambda: self._select_tab("settings")),
        ]
        for key, label, callback in button_specs:
            button = tk.Button(
                parent,
                text=label,
                command=callback,
                bg=THEME["panel"],
                fg=THEME["text"],
                activebackground=THEME["accent_dark"],
                activeforeground=THEME["text"],
                relief=tk.FLAT,
                anchor="w",
                padx=14,
                pady=8,
            )
            button.pack(fill=tk.X, padx=12, pady=4)
            self.sidebar_actions[key] = button

        tk.Label(
            parent,
            text="Theme: Violet / Dark Violet / White Violet / Teal",
            bg=THEME["bg_soft"],
            fg=THEME["text_soft"],
            wraplength=200,
            justify=tk.LEFT,
        ).pack(anchor="w", padx=16, pady=(18, 0))

    def _build_tabs(self) -> None:
        self._build_result_tab("overview", "Overview")
        self._build_ghost_dead_tab()
        self._build_graph_tab()
        self._build_reports_tab()
        self._build_audits_tab()
        self._build_settings_tab()

    def _build_result_tab(self, key: str, title: str) -> ttk.Frame:
        frame = ttk.Frame(self.notebook, style="PC.TFrame")
        self.notebook.add(frame, text=title)
        self.tab_frames[key] = frame

        summary_frame = tk.Frame(frame, bg=THEME["bg"])
        summary_frame.pack(fill=tk.X, padx=10, pady=(10, 6))
        summary_pairs: list[tuple[tk.StringVar, tk.StringVar]] = []
        for _ in range(4):
            card = tk.Frame(summary_frame, bg=THEME["panel"], highlightthickness=1, highlightbackground=THEME["border"])
            card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
            title_var = tk.StringVar(value="—")
            value_var = tk.StringVar(value="—")
            tk.Label(card, textvariable=title_var, bg=THEME["panel"], fg=THEME["text_soft"], font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(8, 2))
            tk.Label(card, textvariable=value_var, bg=THEME["panel"], fg=THEME["text"], font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=(0, 8))
            summary_pairs.append((title_var, value_var))
        self.tab_summary_vars[key] = summary_pairs

        paths_var = tk.StringVar(value="")
        self.tab_paths_var[key] = paths_var
        tk.Label(frame, textvariable=paths_var, bg=THEME["bg"], fg=THEME["text_soft"], justify=tk.LEFT, anchor="w").pack(fill=tk.X, padx=14, pady=(0, 6))

        text = scrolledtext.ScrolledText(
            frame,
            wrap=tk.WORD,
            bg=THEME["bg_soft"],
            fg=THEME["text"],
            insertbackground=THEME["text"],
            relief=tk.FLAT,
        )
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.tab_text_widgets[key] = text
        return frame

    def _build_ghost_dead_tab(self) -> None:
        frame = self._build_result_tab("ghost_dead", "Ghost / Dead")
        form = tk.Frame(frame, bg=THEME["bg"])
        form.pack(fill=tk.X, padx=10, pady=(10, 6), before=self.tab_text_widgets["ghost_dead"])

        tk.Label(form, text="Ghost mode", bg=THEME["bg"], fg=THEME["text"]).grid(row=0, column=0, sticky="w")
        ttk.Combobox(form, textvariable=self.ghost_mode_var, values=("pragmatic", "strict"), width=14, state="readonly").grid(row=0, column=1, padx=8, sticky="w")
        tk.Checkbutton(
            form,
            text="ASCII tree export",
            variable=self.ghost_tree_var,
            bg=THEME["bg"],
            fg=THEME["text"],
            selectcolor=THEME["panel_alt"],
            activebackground=THEME["bg"],
        ).grid(row=0, column=2, padx=8, sticky="w")
        tk.Button(form, text="Run Ghost", command=lambda: self._submit("ghost", mode=self.ghost_mode_var.get(), tree=self.ghost_tree_var.get()), bg=THEME["accent"], fg=THEME["bg"], relief=tk.FLAT).grid(row=0, column=3, padx=8)

        tk.Label(form, text="Dead threshold", bg=THEME["bg"], fg=THEME["text"]).grid(row=1, column=0, sticky="w", pady=(8, 0))
        tk.Spinbox(form, from_=1, to=20, textvariable=self.dead_threshold_var, width=6, bg=THEME["panel_alt"], fg=THEME["text"]).grid(row=1, column=1, sticky="w", padx=8, pady=(8, 0))
        tk.Button(form, text="Run Dead", command=lambda: self._submit("dead", threshold=self.dead_threshold_var.get()), bg=THEME["accent"], fg=THEME["bg"], relief=tk.FLAT).grid(row=1, column=3, padx=8, pady=(8, 0))

    def _build_graph_tab(self) -> None:
        frame = self._build_result_tab("graph", "Graph")
        form = tk.Frame(frame, bg=THEME["bg"])
        form.pack(fill=tk.X, padx=10, pady=(10, 6), before=self.tab_text_widgets["graph"])

        tk.Button(form, text="Run Graph Report", command=lambda: self._submit("graph_report"), bg=THEME["accent"], fg=THEME["bg"], relief=tk.FLAT).grid(row=0, column=0, padx=(0, 8), sticky="w")
        tk.Label(form, text="Trace target", bg=THEME["bg"], fg=THEME["text"]).grid(row=1, column=0, sticky="w", pady=(10, 0))
        tk.Entry(form, textvariable=self.trace_target_var, width=48, bg=THEME["panel_alt"], fg=THEME["text"], insertbackground=THEME["text"]).grid(row=1, column=1, padx=8, pady=(10, 0), sticky="w")
        ttk.Combobox(form, textvariable=self.trace_direction_var, values=("inbound", "outbound", "both"), width=10, state="readonly").grid(row=1, column=2, padx=8, pady=(10, 0), sticky="w")
        tk.Button(form, text="Run Trace", command=self._submit_graph_trace, bg=THEME["accent"], fg=THEME["bg"], relief=tk.FLAT).grid(row=1, column=3, padx=8, pady=(10, 0))

    def _build_reports_tab(self) -> None:
        frame = ttk.Frame(self.notebook, style="PC.TFrame")
        self.notebook.add(frame, text="Reports")
        self.tab_frames["reports"] = frame

        left = tk.Frame(frame, bg=THEME["panel"], width=320, highlightthickness=1, highlightbackground=THEME["border"])
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 6), pady=10)
        left.pack_propagate(False)

        right = tk.Frame(frame, bg=THEME["bg"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)

        tk.Label(left, text="Generated Reports", bg=THEME["panel"], fg=THEME["text"], font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(12, 6))
        self.report_listbox = tk.Listbox(left, bg=THEME["bg_soft"], fg=THEME["text"], selectbackground=THEME["accent_dark"], relief=tk.FLAT)
        self.report_listbox.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        self.report_listbox.bind("<<ListboxSelect>>", lambda _event: self._preview_selected_report())
        tk.Button(left, text="Refresh", command=self._refresh_reports, bg=THEME["accent"], fg=THEME["bg"], relief=tk.FLAT).pack(fill=tk.X, padx=12, pady=4)
        tk.Button(left, text="Open Selected", command=self._open_selected_report, bg=THEME["panel_alt"], fg=THEME["text"], relief=tk.FLAT).pack(fill=tk.X, padx=12, pady=(0, 12))

        self.report_preview = scrolledtext.ScrolledText(
            right,
            wrap=tk.WORD,
            bg=THEME["bg_soft"],
            fg=THEME["text"],
            insertbackground=THEME["text"],
            relief=tk.FLAT,
        )
        self.report_preview.pack(fill=tk.BOTH, expand=True)

    def _build_audits_tab(self) -> None:
        frame = self._build_result_tab("audits", "Audits")
        form = tk.Frame(frame, bg=THEME["bg"])
        form.pack(fill=tk.X, padx=10, pady=(10, 6), before=self.tab_text_widgets["audits"])

        tk.Button(form, text="Run VFX Audit", command=lambda: self._submit("vfx_audit"), bg=THEME["accent"], fg=THEME["bg"], relief=tk.FLAT).grid(row=0, column=0, padx=(0, 8), sticky="w")
        tk.Label(form, text="UI profile", bg=THEME["bg"], fg=THEME["text"]).grid(row=1, column=0, sticky="w", pady=(10, 0))
        tk.Entry(form, textvariable=self.ui_profile_var, width=32, bg=THEME["panel_alt"], fg=THEME["text"], insertbackground=THEME["text"]).grid(row=1, column=1, padx=8, pady=(10, 0), sticky="w")
        tk.Button(form, text="Run UI Verify", command=self._submit_ui_verify, bg=THEME["accent"], fg=THEME["bg"], relief=tk.FLAT).grid(row=1, column=2, padx=8, pady=(10, 0))

    def _build_settings_tab(self) -> None:
        frame = ttk.Frame(self.notebook, style="PC.TFrame")
        self.notebook.add(frame, text="Settings")
        self.tab_frames["settings"] = frame

        card = tk.Frame(frame, bg=THEME["panel"], highlightthickness=1, highlightbackground=THEME["border"])
        card.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(card, text="Settings", bg=THEME["panel"], fg=THEME["text"], font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 8))
        tk.Label(card, text="Project mode", bg=THEME["panel"], fg=THEME["text"]).grid(row=1, column=0, sticky="w", padx=12, pady=4)
        ttk.Combobox(card, textvariable=self.settings_mode_var, values=("js_ts", "python", "mixed"), width=18, state="readonly").grid(row=1, column=1, sticky="w", padx=12, pady=4)
        tk.Label(card, text="Graph profile", bg=THEME["panel"], fg=THEME["text"]).grid(row=2, column=0, sticky="w", padx=12, pady=4)
        ttk.Combobox(card, textvariable=self.settings_profile_var, values=("pragmatic", "strict"), width=18, state="readonly").grid(row=2, column=1, sticky="w", padx=12, pady=4)
        tk.Label(card, text="Trace depth", bg=THEME["panel"], fg=THEME["text"]).grid(row=3, column=0, sticky="w", padx=12, pady=4)
        tk.Spinbox(card, from_=1, to=250, textvariable=self.settings_trace_depth_var, width=8, bg=THEME["panel_alt"], fg=THEME["text"]).grid(row=3, column=1, sticky="w", padx=12, pady=4)
        tk.Checkbutton(card, text="Trace all paths", variable=self.settings_all_paths_var, bg=THEME["panel"], fg=THEME["text"], selectcolor=THEME["panel_alt"], activebackground=THEME["panel"]).grid(row=4, column=0, sticky="w", padx=12, pady=4)
        tk.Checkbutton(card, text="UI verification headless", variable=self.settings_headless_var, bg=THEME["panel"], fg=THEME["text"], selectcolor=THEME["panel_alt"], activebackground=THEME["panel"]).grid(row=4, column=1, sticky="w", padx=12, pady=4)
        tk.Button(card, text="Save Settings", command=self._save_settings, bg=THEME["accent"], fg=THEME["bg"], relief=tk.FLAT).grid(row=5, column=0, padx=12, pady=(8, 12), sticky="w")

    def _save_settings(self) -> None:
        self.controller.save_settings(
            project_mode=self.settings_mode_var.get(),
            graph_profile=self.settings_profile_var.get(),
            trace_depth=int(self.settings_trace_depth_var.get()),
            trace_all_paths=bool(self.settings_all_paths_var.get()),
            ui_verification_headless=bool(self.settings_headless_var.get()),
        )
        self.trace_direction_var.set(self.controller.state.trace_direction)
        self.status_var.set("Settings saved.")
        self._log("Settings updated.")
        self._refresh_overview()

    def _submit_graph_trace(self) -> None:
        target = self.trace_target_var.get().strip()
        if not target:
            self.status_var.set("Graph trace requires a target path or symbol.")
            return
        self._submit("graph_trace", target=target, direction=self.trace_direction_var.get())

    def _submit_ui_verify(self) -> None:
        profile_name = self.ui_profile_var.get().strip() or None
        self._submit("ui_verification", profile_name=profile_name)

    def _submit(self, workflow: str, **kwargs) -> None:
        tab_key = self.workflow_tabs.get(workflow, "overview")
        self._select_tab(tab_key)
        self.status_var.set(f"Running {workflow}...")
        self._log(f"Running {workflow} with {kwargs or 'default settings'}")
        try:
            self.runner.submit(workflow, self.controller.dispatch, workflow, **kwargs)
        except RuntimeError as exc:
            self.status_var.set(str(exc))

    def _poll_background_events(self) -> None:
        for event in self.runner.poll():
            if event.kind == "result" and isinstance(event.payload, PresentationResult):
                self._handle_result(event.payload)
            elif event.kind == "error":
                self.status_var.set(f"{event.workflow} failed")
                self._log(f"{event.workflow} failed: {event.payload}")
        self.root.after(100, self._poll_background_events)

    def _handle_result(self, result: PresentationResult) -> None:
        tab_key = self.workflow_tabs.get(result.workflow, "overview")
        self.status_var.set(f"{result.title} complete.")
        self._display_result(tab_key, result)
        self._log(f"{result.title} complete.")
        if result.workflow != "overview":
            self._refresh_overview()
            self._refresh_reports(select_tab=False)

    def _display_result(self, tab_key: str, result: PresentationResult) -> None:
        summary_items = list(result.summary.items())[:4]
        for index, (title_var, value_var) in enumerate(self.tab_summary_vars.get(tab_key, [])):
            if index < len(summary_items):
                key, value = summary_items[index]
                title_var.set(str(key).replace("_", " ").title())
                value_var.set(str(value))
            else:
                title_var.set("—")
                value_var.set("—")

        self.tab_paths_var.get(tab_key, tk.StringVar()).set(
            "\n".join(f"{name}: {path}" for name, path in result.report_paths.items())
        )
        text = self.tab_text_widgets.get(tab_key)
        if text is not None:
            text.delete("1.0", tk.END)
            text.insert(tk.END, result.primary_text)
        self._select_tab(tab_key)

    def _select_tab(self, key: str) -> None:
        frame = self.tab_frames.get(key)
        if frame is not None:
            self.notebook.select(frame)

    def _refresh_overview(self) -> None:
        result = self.controller.get_overview()
        self._display_result("overview", result)

    def _refresh_reports(self, *, select_tab: bool = True) -> None:
        result = self.controller.get_reports()
        self._display_result("reports", result)
        if select_tab:
            self._select_tab("reports")
        self.report_paths_cache.clear()
        reports = list_all_reports(self.project_root)
        if self.report_listbox is None:
            return
        self.report_listbox.delete(0, tk.END)
        for report in reports:
            label = f"{report['name']} [{'OK' if report.get('exists') else 'MISSING'}]"
            self.report_listbox.insert(tk.END, label)
            self.report_paths_cache[label] = report["path"]
        if reports:
            self.report_listbox.selection_set(0)
            self._preview_selected_report()

    def _preview_selected_report(self) -> None:
        if self.report_listbox is None or self.report_preview is None:
            return
        selected = self.report_listbox.curselection()
        if not selected:
            return
        label = self.report_listbox.get(selected[0])
        path = self.report_paths_cache.get(label)
        if path is None:
            return
        preview = f"Path: {path}\n\n"
        if path.is_file():
            try:
                preview += path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                preview += "<Binary or non-text file>"
        else:
            preview += "<Report not generated yet>"
        self.report_preview.delete("1.0", tk.END)
        self.report_preview.insert(tk.END, preview)

    def _open_selected_report(self) -> None:
        if self.report_listbox is None:
            return
        selected = self.report_listbox.curselection()
        if not selected:
            self.status_var.set("No report selected.")
            return
        label = self.report_listbox.get(selected[0])
        path = self.report_paths_cache.get(label)
        if path is None:
            self.status_var.set("Selected report is unavailable.")
            return
        if not path.exists():
            self.status_var.set("Selected report has not been generated yet.")
            return
        try:
            open_path(path)
            self.status_var.set(f"Opened {path.name}")
        except Exception as exc:  # pragma: no cover - platform-specific
            self.status_var.set(f"Failed to open report: {exc}")

    def _log(self, message: str) -> None:
        self.log_widget.insert(tk.END, f"{message}\n")
        self.log_widget.see(tk.END)


def open_path(path: Path) -> None:
    """Open a generated file in the platform default viewer."""
    if sys.platform == "win32":
        os.startfile(str(path))  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
        return
    subprocess.run(["xdg-open", str(path)], check=False)


def launch_gui(project_root: Path) -> None:
    """Launch the desktop GUI for a project root."""
    app = ProjectControlGUI(project_root)
    app.run()
