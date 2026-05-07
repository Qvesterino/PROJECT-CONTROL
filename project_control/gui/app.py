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
    present_artifacts,
    present_audit_retention,
    present_dead,
    present_graph_report,
    present_graph_status,
    present_graph_trace,
    present_overview,
    present_report_registry,
    present_scan,
    present_ui_verification,
    present_vfx_audit,
    present_workflow_status,
)
from project_control.services.report_service import list_all_reports
from project_control.ui.state import AppState, load_state, save_state


THEME = {
    "bg": "#12071E",
    "bg_alt": "#170A26",
    "bg_soft": "#1E1030",
    "glass": "#24143B",
    "glass_alt": "#2B1944",
    "glass_high": "#331F52",
    "glass_card": "#2A1844",
    "glass_deep": "#1B0F2C",
    "text": "#F7F1FF",
    "text_soft": "#D9C9F4",
    "text_muted": "#AE9CCA",
    "text_faint": "#8C79AA",
    "border": "#4E2F78",
    "border_soft": "#3B235C",
    "border_glow": "#6E46A3",
    "accent": "#2CE6D5",
    "accent_dark": "#17B7A9",
    "accent_glow": "#7CF8EC",
    "success": "#31D686",
    "warning": "#FFCB6B",
    "danger": "#FF6B8A",
    "info": "#73B8FF",
    "shadow": "#0B0413",
}

STATE_TONES = {
    "ready": {"bg": THEME["glass"], "border": THEME["border"], "accent": THEME["info"], "text": THEME["text"]},
    "empty": {"bg": THEME["glass"], "border": THEME["border_soft"], "accent": THEME["warning"], "text": THEME["text"]},
    "running": {"bg": THEME["glass_high"], "border": THEME["accent"], "accent": THEME["accent_glow"], "text": THEME["text"]},
    "complete": {"bg": THEME["glass"], "border": THEME["success"], "accent": THEME["success"], "text": THEME["text"]},
    "error": {"bg": THEME["glass"], "border": THEME["danger"], "accent": THEME["danger"], "text": THEME["text"]},
}

SUMMARY_ICONS = {
    "status": "◉",
    "setup": "⌁",
    "snapshot": "◌",
    "graph": "◎",
    "file_count": "▣",
    "total_files": "▣",
    "dead_files": "✕",
    "low_usage_files": "⋯",
    "safe_to_delete": "⌫",
    "reclaimable_mb": "◫",
    "duplicate_groups": "⧉",
    "high_confidence": "▲",
    "families_detected": "◍",
    "nodes": "◈",
    "edges": "⇄",
    "cycles": "↺",
    "orphans": "◔",
    "target": "⌖",
    "inbound_paths": "↘",
    "outbound_paths": "↗",
}


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _mix(color_a: str, color_b: str, ratio: float) -> str:
    ratio = max(0.0, min(1.0, ratio))
    rgb_a = _hex_to_rgb(color_a)
    rgb_b = _hex_to_rgb(color_b)
    mixed = tuple(int((1 - ratio) * a + ratio * b) for a, b in zip(rgb_a, rgb_b))
    return _rgb_to_hex(mixed)


def _rounded_points(x1: float, y1: float, x2: float, y2: float, radius: float) -> list[float]:
    radius = max(4.0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    return [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]


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
            except Exception as exc:  # pragma: no cover - exercised by queue handling tests
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


class GlassButton(tk.Canvas):
    """Rounded faux-glass button with hover glow and pulse feedback."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        text: str,
        command,
        tone: str = "primary",
        width: int = 168,
        height: int = 42,
        anchor: str = "center",
    ) -> None:
        super().__init__(
            master,
            width=width,
            height=height,
            bg=master.cget("bg"),
            highlightthickness=0,
            bd=0,
            relief=tk.FLAT,
        )
        self.command = command
        self.label = text
        self.anchor = anchor
        self.enabled = True
        self.hovered = False
        self.pressed = False
        self.selected = False
        self.running = False
        self.tone = tone
        self._pulse_after: str | None = None
        self._button_shape: int | None = None
        self._glow_shape: int | None = None
        self._text_item: int | None = None
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>", lambda _event: self._draw())

    def set_disabled(self, disabled: bool) -> None:
        self.enabled = not disabled
        if disabled:
            self.hovered = False
            self.pressed = False
        self._draw()

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self._draw()

    def set_running(self, running: bool) -> None:
        self.running = running
        self._draw()

    def pulse(self, accent: str | None = None) -> None:
        if self._pulse_after is not None:
            try:
                self.after_cancel(self._pulse_after)
            except TclError:
                pass
            self._pulse_after = None
        base_selected = self.selected
        self.selected = True
        self._draw(force_accent=accent or THEME["accent_glow"])

        def restore() -> None:
            self.selected = base_selected
            self._draw()
            self._pulse_after = None

        self._pulse_after = self.after(160, restore)

    def invoke(self) -> None:
        if self.enabled and callable(self.command):
            self.command()

    def _palette(self) -> tuple[str, str, str]:
        if self.tone == "secondary":
            base_fill = THEME["glass_alt"]
            base_border = THEME["border"]
            text = THEME["text"]
        elif self.tone == "tab":
            base_fill = THEME["glass_card"]
            base_border = THEME["border_soft"]
            text = THEME["text_soft"]
        else:
            base_fill = _mix(THEME["accent"], THEME["glass_high"], 0.75)
            base_border = _mix(THEME["accent_glow"], THEME["accent"], 0.35)
            text = THEME["text"]

        if not self.enabled:
            return _mix(base_fill, THEME["bg"], 0.35), _mix(base_border, THEME["bg"], 0.45), THEME["text_muted"]
        if self.tone == "tab" and self.selected:
            return _mix(base_fill, THEME["accent"], 0.12), _mix(THEME["accent_glow"], THEME["border_glow"], 0.35), THEME["text"]
        if self.running:
            return _mix(base_fill, THEME["accent"], 0.2), THEME["accent_glow"], text
        if self.pressed:
            return _mix(base_fill, THEME["accent"], 0.28), THEME["accent_glow"], text
        if self.hovered or self.selected:
            return _mix(base_fill, THEME["accent_glow"], 0.12), _mix(base_border, THEME["accent_glow"], 0.35), text
        return base_fill, base_border, text

    def _draw(self, *, force_accent: str | None = None) -> None:
        self.delete("all")
        width = max(60, self.winfo_width() or int(self.cget("width")))
        height = max(30, self.winfo_height() or int(self.cget("height")))
        points = _rounded_points(4, 4, width - 4, height - 4, 14)
        fill, border, text_color = self._palette()
        glow = force_accent or (THEME["accent_glow"] if (self.hovered or self.selected or self.running) and self.enabled else THEME["shadow"])
        glow_border = _mix(glow, fill, 0.55)
        self._glow_shape = self.create_polygon(
            _rounded_points(2, 2, width - 2, height - 2, 16),
            smooth=True,
            fill="",
            outline=glow_border,
            width=2,
        )
        self._button_shape = self.create_polygon(points, smooth=True, fill=fill, outline=border, width=1.5)
        text_x = width / 2 if self.anchor == "center" else 16
        self._text_item = self.create_text(
            text_x,
            height / 2,
            text=self.label,
            fill=text_color,
            font=("Segoe UI", 10 if self.tone != "tab" else 9, "bold"),
            anchor=self.anchor,
        )

    def _on_enter(self, _event: tk.Event) -> None:
        if not self.enabled:
            return
        self.hovered = True
        self._draw()

    def _on_leave(self, _event: tk.Event) -> None:
        self.hovered = False
        self.pressed = False
        self._draw()

    def _on_press(self, _event: tk.Event) -> None:
        if not self.enabled:
            return
        self.pressed = True
        self._draw()

    def _on_release(self, event: tk.Event) -> None:
        if not self.enabled:
            return
        inside = 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        self.pressed = False
        self._draw()
        if inside:
            self.pulse()
            self.invoke()


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
            "artifacts": self.run_artifacts,
            "audit_retention": self.run_audit_retention,
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
        return present_scan(self.project_root, interactive=True)

    def run_ghost(self, *, mode: str = "pragmatic", tree: bool = True) -> PresentationResult:
        return present_ghost(self.project_root, mode=mode, tree=tree)

    def run_dead(self, *, threshold: int = 2) -> PresentationResult:
        return present_dead(self.project_root, threshold=threshold)

    def run_artifacts(self) -> PresentationResult:
        return present_artifacts(self.project_root)

    def run_audit_retention(self) -> PresentationResult:
        return present_audit_retention(self.project_root)

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
    """Polished desktop GUI shell around the existing workflow adapters."""

    workflow_tabs = {
        "overview": "overview",
        "scan": "overview",
        "ghost": "ghost_dead",
        "dead": "ghost_dead",
        "artifacts": "audits",
        "audit_retention": "audits",
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
    ) -> None:
        self.project_root = project_root.resolve()
        self.controller = controller or GUIController(self.project_root)
        self.runner = BackgroundRunner()
        self.root = root or self.create_root()
        self.root.title(f"PROJECT CONTROL GUI - {self.project_root.name}")
        self.root.geometry("1380x920")
        self.root.minsize(1200, 780)
        self.root.configure(bg=THEME["bg"])

        self.status_var = tk.StringVar(value="Ready")
        self.status_detail_var = tk.StringVar(value="Choose a workflow to start.")
        self.header_var = tk.StringVar(value=f"Project: {self.project_root.name}")
        self.sidebar_actions: dict[str, GlassButton] = {}
        self.tab_frames: dict[str, tk.Frame] = {}
        self.tab_order: list[str] = []
        self.tab_buttons: dict[str, GlassButton] = {}
        self.tab_text_widgets: dict[str, scrolledtext.ScrolledText] = {}
        self.tab_summary_vars: dict[str, list[tuple[tk.StringVar, tk.StringVar]]] = {}
        self.tab_summary_frames: dict[str, list[tk.Frame]] = {}
        self.tab_summary_badges: dict[str, list[tk.Label]] = {}
        self.tab_summary_badge_vars: dict[str, list[tk.StringVar]] = {}
        self.tab_summary_icon_vars: dict[str, list[tk.StringVar]] = {}
        self.tab_paths_var: dict[str, tk.StringVar] = {}
        self.tab_banner_vars: dict[str, dict[str, tk.StringVar]] = {}
        self.tab_banner_frames: dict[str, tk.Frame] = {}
        self.report_paths_cache: dict[str, Path] = {}
        self.report_listbox: tk.Listbox | None = None
        self.report_preview: scrolledtext.ScrolledText | None = None
        self.report_summary_var = tk.StringVar(value="Reports refresh automatically after successful workflows.")
        self.log_widget: scrolledtext.ScrolledText | None = None
        self.header_frame: tk.Frame | None = None
        self.footer_frame: tk.Frame | None = None
        self.footer_pill: tk.Frame | None = None
        self.footer_status_label: tk.Label | None = None
        self.footer_detail_label: tk.Label | None = None
        self.tab_bar_card: tk.Frame | None = None
        self.tab_content_stack: tk.Frame | None = None
        self.action_buttons: list[GlassButton] = []
        self.active_workflow: str | None = None
        self.selected_tab: str = "overview"
        self.busy = False

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
        self._seed_workflow_onboarding()
        self._refresh_reports(select_tab=False)
        self.root.after(100, self._poll_background_events)

    @staticmethod
    def create_root() -> tk.Tk:
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
        style.configure(
            "PC.TCombobox",
            fieldbackground=THEME["glass_alt"],
            background=THEME["glass_alt"],
            foreground=THEME["text"],
            bordercolor=THEME["border"],
            lightcolor=THEME["border"],
            darkcolor=THEME["border"],
            arrowcolor=THEME["accent_glow"],
        )

    def _build_layout(self) -> None:
        outer = tk.Frame(self.root, bg=THEME["bg"])
        outer.pack(fill=tk.BOTH, expand=True)

        sidebar = self._glass_frame(outer, bg=THEME["bg_soft"], border=THEME["border_soft"])
        sidebar.configure(width=256)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 8), pady=10)
        sidebar.pack_propagate(False)

        content = tk.Frame(outer, bg=THEME["bg"])
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)

        self.header_frame = self._glass_frame(content, bg=THEME["glass"], border=THEME["border"])
        self.header_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(
            self.header_frame,
            text="PROJECT CONTROL",
            bg=THEME["glass"],
            fg=THEME["text"],
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w", padx=20, pady=(16, 2))
        tk.Label(
            self.header_frame,
            textvariable=self.header_var,
            bg=THEME["glass"],
            fg=THEME["text_soft"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=20, pady=(0, 16))

        workspace = tk.Frame(content, bg=THEME["bg"])
        workspace.pack(fill=tk.BOTH, expand=True)

        self.tab_bar_card = self._glass_frame(workspace, bg=THEME["glass"], border=THEME["border_soft"])
        self.tab_bar_card.pack(fill=tk.X, pady=(0, 10))

        tab_row = tk.Frame(self.tab_bar_card, bg=THEME["glass"])
        tab_row.pack(fill=tk.X, padx=14, pady=12)
        self._build_top_tabs(tab_row)

        self.tab_content_stack = tk.Frame(workspace, bg=THEME["bg"])
        self.tab_content_stack.pack(fill=tk.BOTH, expand=True)

        self.footer_frame = self._glass_frame(content, bg=THEME["glass"], border=THEME["border_soft"])
        self.footer_frame.pack(fill=tk.X, pady=(10, 0))
        footer_top = tk.Frame(self.footer_frame, bg=THEME["glass"])
        footer_top.pack(fill=tk.X, padx=14, pady=(12, 8))
        self.footer_pill = tk.Frame(footer_top, bg=STATE_TONES["ready"]["accent"], height=10, width=10)
        self.footer_pill.pack(side=tk.LEFT, padx=(0, 10))
        self.footer_status_label = tk.Label(
            footer_top,
            textvariable=self.status_var,
            bg=THEME["glass"],
            fg=THEME["text"],
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        )
        self.footer_status_label.pack(side=tk.LEFT)
        self.footer_detail_label = tk.Label(
            self.footer_frame,
            textvariable=self.status_detail_var,
            bg=THEME["glass"],
            fg=THEME["text_soft"],
            anchor="w",
            justify=tk.LEFT,
            wraplength=1000,
        )
        self.footer_detail_label.pack(fill=tk.X, padx=14)
        self.log_widget = scrolledtext.ScrolledText(
            self.footer_frame,
            height=5,
            wrap=tk.WORD,
            bg=THEME["bg_alt"],
            fg=THEME["text_muted"],
            insertbackground=THEME["text"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=THEME["border_soft"],
        )
        self.log_widget.pack(fill=tk.X, padx=14, pady=(8, 14))

        self._build_sidebar(sidebar)
        self._build_tabs()
        self._select_tab("overview")
        self._set_footer_state("ready", "Ready", "Choose a workflow to start.")

    def _build_sidebar(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="Workflows",
            bg=THEME["bg_soft"],
            fg=THEME["text"],
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", padx=18, pady=(18, 10))

        button_specs = [
            ("overview", "Overview", lambda: self._select_tab("overview")),
            ("scan", "Run Scan", lambda: self._submit("scan")),
            ("ghost", "Run Ghost", lambda: self._submit("ghost", mode=self.ghost_mode_var.get(), tree=self.ghost_tree_var.get())),
            ("dead", "Run Dead", lambda: self._submit("dead", threshold=self.dead_threshold_var.get())),
            ("artifacts", "Run Artifacts", lambda: self._submit("artifacts")),
            ("audit_retention", "Run Audit Retention", lambda: self._submit("audit_retention")),
            ("graph_report", "Graph Report", lambda: self._submit("graph_report")),
            ("graph_trace", "Graph Trace", self._submit_graph_trace),
            ("vfx_audit", "VFX Audit", lambda: self._submit("vfx_audit")),
            ("ui_verification", "UI Verify", self._submit_ui_verify),
            ("reports", "Reports", lambda: self._refresh_reports(select_tab=True)),
            ("settings", "Settings", lambda: self._select_tab("settings")),
        ]
        for key, label, callback in button_specs:
            button = GlassButton(parent, text=label, command=callback, tone="secondary", width=216, anchor="w")
            button.pack(fill=tk.X, padx=14, pady=5)
            self.sidebar_actions[key] = button

        helper = self._glass_frame(parent, bg=THEME["glass_alt"], border=THEME["border_soft"])
        helper.pack(fill=tk.X, padx=14, pady=(16, 12))
        tk.Label(
            helper,
            text="Visual Mode",
            bg=THEME["glass_alt"],
            fg=THEME["text"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 4))
        tk.Label(
            helper,
            text="Glass panels, state banners, hover glow, and faster workflow feedback.",
            bg=THEME["glass_alt"],
            fg=THEME["text_muted"],
            justify=tk.LEFT,
            wraplength=190,
        ).pack(anchor="w", padx=12, pady=(0, 10))

    def _build_top_tabs(self, parent: tk.Frame) -> None:
        tab_specs = [
            ("overview", "Overview"),
            ("ghost_dead", "Ghost / Dead"),
            ("graph", "Graph"),
            ("reports", "Reports"),
            ("audits", "Audits"),
            ("settings", "Settings"),
        ]
        self.tab_order = [key for key, _label in tab_specs]
        for key, label in tab_specs:
            button = GlassButton(parent, text=label, command=lambda current=key: self._select_tab(current), tone="tab", width=118, height=40)
            button.pack(side=tk.LEFT, padx=(0, 8))
            self.tab_buttons[key] = button

    def _build_tabs(self) -> None:
        self._build_overview_tab()
        self._build_ghost_dead_tab()
        self._build_graph_tab()
        self._build_reports_tab()
        self._build_audits_tab()
        self._build_settings_tab()

    def _build_result_tab(self, key: str, title: str) -> tk.Frame:
        parent = self.tab_content_stack if self.tab_content_stack is not None else self.root
        frame = tk.Frame(parent, bg=THEME["bg"])
        self.tab_frames[key] = frame

        banner_card = self._glass_frame(frame, bg=THEME["glass"], border=THEME["border_soft"])
        banner_card.pack(fill=tk.X, padx=10, pady=(0, 10))
        banner_head = tk.Frame(banner_card, bg=THEME["glass"])
        banner_head.pack(fill=tk.X, padx=16, pady=(14, 6))
        badge_var = tk.StringVar(value="READY")
        title_var = tk.StringVar(value=title)
        body_var = tk.StringVar(value="")
        badge = tk.Label(
            banner_head,
            textvariable=badge_var,
            bg=THEME["info"],
            fg=THEME["bg"],
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
        )
        badge.pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(
            banner_head,
            textvariable=title_var,
            bg=THEME["glass"],
            fg=THEME["text"],
            font=("Segoe UI", 13, "bold"),
        ).pack(side=tk.LEFT)
        tk.Label(
            banner_card,
            textvariable=body_var,
            bg=THEME["glass"],
            fg=THEME["text_soft"],
            justify=tk.LEFT,
            wraplength=920,
            font=("Segoe UI", 10),
        ).pack(fill=tk.X, padx=16, pady=(0, 14))
        self.tab_banner_frames[key] = banner_card
        self.tab_banner_vars[key] = {"badge": badge_var, "title": title_var, "body": body_var}

        summary_frame = tk.Frame(frame, bg=THEME["bg"])
        summary_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        summary_pairs: list[tuple[tk.StringVar, tk.StringVar]] = []
        summary_frames: list[tk.Frame] = []
        summary_badges: list[tk.Label] = []
        summary_badge_vars: list[tk.StringVar] = []
        summary_icon_vars: list[tk.StringVar] = []
        for _ in range(4):
            card = self._glass_frame(summary_frame, bg=THEME["glass_card"], border=THEME["border_soft"])
            card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
            header = tk.Frame(card, bg=THEME["glass_card"])
            header.pack(fill=tk.X, padx=12, pady=(10, 2))
            badge_var = tk.StringVar(value="INFO")
            icon_var = tk.StringVar(value="◌")
            badge = tk.Label(
                header,
                textvariable=badge_var,
                bg=THEME["info"],
                fg=THEME["bg"],
                font=("Segoe UI", 8, "bold"),
                padx=7,
                pady=2,
            )
            badge.pack(side=tk.LEFT)
            tk.Label(
                header,
                textvariable=icon_var,
                bg=THEME["glass_card"],
                fg=THEME["accent_glow"],
                font=("Segoe UI", 11, "bold"),
            ).pack(side=tk.RIGHT)
            title_var = tk.StringVar(value="—")
            value_var = tk.StringVar(value="—")
            tk.Label(card, textvariable=title_var, bg=THEME["glass_card"], fg=THEME["text_faint"], font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(2, 3))
            tk.Label(card, textvariable=value_var, bg=THEME["glass_card"], fg=THEME["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=12, pady=(0, 12))
            summary_pairs.append((title_var, value_var))
            summary_frames.append(card)
            summary_badges.append(badge)
            summary_badge_vars.append(badge_var)
            summary_icon_vars.append(icon_var)
        self.tab_summary_vars[key] = summary_pairs
        self.tab_summary_frames[key] = summary_frames
        self.tab_summary_badges[key] = summary_badges
        self.tab_summary_badge_vars[key] = summary_badge_vars
        self.tab_summary_icon_vars[key] = summary_icon_vars

        paths_card = self._glass_frame(frame, bg=THEME["glass_alt"], border=THEME["border_soft"])
        paths_card.pack(fill=tk.X, padx=10, pady=(0, 10))
        paths_var = tk.StringVar(value="")
        self.tab_paths_var[key] = paths_var
        tk.Label(paths_card, textvariable=paths_var, bg=THEME["glass_alt"], fg=THEME["text_muted"], justify=tk.LEFT, anchor="w", wraplength=920, font=("Segoe UI", 9)).pack(fill=tk.X, padx=16, pady=12)

        text_card = self._glass_frame(frame, bg=THEME["glass"], border=THEME["border"])
        text_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        text = scrolledtext.ScrolledText(
            text_card,
            wrap=tk.WORD,
            bg=THEME["glass_deep"],
            fg=THEME["text"],
            insertbackground=THEME["text"],
            relief=tk.FLAT,
            highlightthickness=0,
            padx=12,
            pady=12,
            font=("Cascadia Mono", 10),
        )
        text.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.tab_text_widgets[key] = text
        return frame

    def _build_overview_tab(self) -> None:
        self._build_result_tab("overview", "Overview")

    def _build_ghost_dead_tab(self) -> None:
        frame = self._build_result_tab("ghost_dead", "Ghost / Dead")
        controls = self._glass_frame(frame, bg=THEME["glass_alt"], border=THEME["border_soft"])
        controls.pack(fill=tk.X, padx=10, pady=(0, 10), before=self.tab_banner_frames["ghost_dead"])
        grid = tk.Frame(controls, bg=THEME["glass_alt"])
        grid.pack(fill=tk.X, padx=14, pady=14)

        tk.Label(grid, text="Ghost mode", bg=THEME["glass_alt"], fg=THEME["text_soft"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Combobox(grid, textvariable=self.ghost_mode_var, values=("pragmatic", "strict"), width=16, state="readonly").grid(row=0, column=1, padx=(12, 14), sticky="w")
        tk.Checkbutton(
            grid,
            text="ASCII tree export",
            variable=self.ghost_tree_var,
            bg=THEME["glass_alt"],
            fg=THEME["text"],
            selectcolor=THEME["glass_high"],
            activebackground=THEME["glass_alt"],
            activeforeground=THEME["text"],
        ).grid(row=0, column=2, sticky="w", padx=(0, 12))
        self._add_action_button(grid, "Run Ghost", lambda: self._submit("ghost", mode=self.ghost_mode_var.get(), tree=self.ghost_tree_var.get()), row=0, column=3)

        tk.Label(grid, text="Dead threshold", bg=THEME["glass_alt"], fg=THEME["text_soft"], font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(14, 0))
        tk.Spinbox(
            grid,
            from_=1,
            to=20,
            textvariable=self.dead_threshold_var,
            width=7,
            bg=THEME["glass_high"],
            fg=THEME["text"],
            insertbackground=THEME["text"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=THEME["border"],
        ).grid(row=1, column=1, sticky="w", padx=(10, 12), pady=(12, 0))
        self._add_action_button(grid, "Run Dead", lambda: self._submit("dead", threshold=self.dead_threshold_var.get()), row=1, column=3, pady=(12, 0))

    def _build_graph_tab(self) -> None:
        frame = self._build_result_tab("graph", "Graph")
        controls = self._glass_frame(frame, bg=THEME["glass_alt"], border=THEME["border_soft"])
        controls.pack(fill=tk.X, padx=10, pady=(0, 10), before=self.tab_banner_frames["graph"])
        grid = tk.Frame(controls, bg=THEME["glass_alt"])
        grid.pack(fill=tk.X, padx=14, pady=14)
        self._add_action_button(grid, "Run Graph Report", lambda: self._submit("graph_report"), row=0, column=0)
        tk.Label(grid, text="Trace target", bg=THEME["glass_alt"], fg=THEME["text_soft"], font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(14, 0))
        tk.Entry(
            grid,
            textvariable=self.trace_target_var,
            width=48,
            bg=THEME["glass_high"],
            fg=THEME["text"],
            insertbackground=THEME["text"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=THEME["border"],
        ).grid(row=1, column=1, padx=10, pady=(12, 0), sticky="w")
        ttk.Combobox(grid, textvariable=self.trace_direction_var, values=("inbound", "outbound", "both"), width=12, state="readonly").grid(row=1, column=2, padx=10, pady=(14, 0), sticky="w")
        self._add_action_button(grid, "Run Trace", self._submit_graph_trace, row=1, column=3, pady=(12, 0))

    def _build_reports_tab(self) -> None:
        parent = self.tab_content_stack if self.tab_content_stack is not None else self.root
        frame = tk.Frame(parent, bg=THEME["bg"])
        self.tab_frames["reports"] = frame

        header = self._glass_frame(frame, bg=THEME["glass"], border=THEME["border_soft"])
        header.pack(fill=tk.X, padx=10, pady=(0, 10))
        tk.Label(header, text="Reports Workspace", bg=THEME["glass"], fg=THEME["text"], font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Label(header, textvariable=self.report_summary_var, bg=THEME["glass"], fg=THEME["text_soft"], justify=tk.LEFT, wraplength=920, font=("Segoe UI", 10)).pack(fill=tk.X, padx=16, pady=(0, 14))

        body = tk.Frame(frame, bg=THEME["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        left = self._glass_frame(body, bg=THEME["glass"], border=THEME["border"])
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        left.configure(width=340)
        left.pack_propagate(False)

        right = self._glass_frame(body, bg=THEME["glass"], border=THEME["border"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="Generated Reports", bg=THEME["glass"], fg=THEME["text"], font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(14, 6))
        list_shell = self._glass_frame(left, bg=THEME["glass_card"], border=THEME["border_soft"])
        list_shell.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 10))
        self.report_listbox = tk.Listbox(
            list_shell,
            bg=THEME["glass_deep"],
            fg=THEME["text"],
            selectbackground=THEME["accent_dark"],
            selectforeground=THEME["text"],
            relief=tk.FLAT,
            highlightthickness=0,
            activestyle="none",
            font=("Segoe UI", 10),
        )
        self.report_listbox.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.report_listbox.bind("<<ListboxSelect>>", lambda _event: self._preview_selected_report())

        left_actions = tk.Frame(left, bg=THEME["glass"])
        left_actions.pack(fill=tk.X, padx=14, pady=(0, 14))
        refresh_button = GlassButton(left_actions, text="Refresh", command=self._refresh_reports, width=130)
        refresh_button.pack(side=tk.LEFT, padx=(0, 8))
        open_button = GlassButton(left_actions, text="Open Selected", command=self._open_selected_report, tone="secondary", width=160)
        open_button.pack(side=tk.LEFT)
        self.action_buttons.extend([refresh_button, open_button])

        tk.Label(right, text="Preview", bg=THEME["glass"], fg=THEME["text"], font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(14, 6))
        preview_shell = self._glass_frame(right, bg=THEME["glass_card"], border=THEME["border_soft"])
        preview_shell.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 14))
        self.report_preview = scrolledtext.ScrolledText(
            preview_shell,
            wrap=tk.WORD,
            bg=THEME["glass_deep"],
            fg=THEME["text"],
            insertbackground=THEME["text"],
            relief=tk.FLAT,
            highlightthickness=0,
            padx=12,
            pady=12,
            font=("Cascadia Mono", 10),
        )
        self.report_preview.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

    def _build_audits_tab(self) -> None:
        frame = self._build_result_tab("audits", "Audits")
        controls = self._glass_frame(frame, bg=THEME["glass_alt"], border=THEME["border_soft"])
        controls.pack(fill=tk.X, padx=10, pady=(0, 10), before=self.tab_banner_frames["audits"])
        grid = tk.Frame(controls, bg=THEME["glass_alt"])
        grid.pack(fill=tk.X, padx=14, pady=14)
        self._add_action_button(grid, "Run Artifacts", lambda: self._submit("artifacts"), row=0, column=0)
        self._add_action_button(grid, "Run Audit Retention", lambda: self._submit("audit_retention"), row=0, column=1)
        self._add_action_button(grid, "Run VFX Audit", lambda: self._submit("vfx_audit"), row=0, column=2)

        tk.Label(grid, text="UI profile", bg=THEME["glass_alt"], fg=THEME["text_soft"], font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(14, 0))
        tk.Entry(
            grid,
            textvariable=self.ui_profile_var,
            width=34,
            bg=THEME["glass_high"],
            fg=THEME["text"],
            insertbackground=THEME["text"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=THEME["border"],
        ).grid(row=1, column=1, padx=10, pady=(12, 0), sticky="w")
        self._add_action_button(grid, "Run UI Verify", self._submit_ui_verify, row=1, column=2, pady=(12, 0))

    def _build_settings_tab(self) -> None:
        parent = self.tab_content_stack if self.tab_content_stack is not None else self.root
        frame = tk.Frame(parent, bg=THEME["bg"])
        self.tab_frames["settings"] = frame

        shell = tk.Frame(frame, bg=THEME["bg"])
        shell.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        settings_card = self._glass_frame(shell, bg=THEME["glass"], border=THEME["border"])
        settings_card.pack(fill=tk.X)
        tk.Label(settings_card, text="Settings", bg=THEME["glass"], fg=THEME["text"], font=("Segoe UI", 13, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 8))
        self._settings_row(settings_card, 1, "Project mode", ttk.Combobox(settings_card, textvariable=self.settings_mode_var, values=("js_ts", "python", "mixed"), width=18, state="readonly"))
        self._settings_row(settings_card, 2, "Graph profile", ttk.Combobox(settings_card, textvariable=self.settings_profile_var, values=("pragmatic", "strict"), width=18, state="readonly"))
        self._settings_row(
            settings_card,
            3,
            "Trace depth",
            tk.Spinbox(
                settings_card,
                from_=1,
                to=250,
                textvariable=self.settings_trace_depth_var,
                width=8,
                bg=THEME["glass_high"],
                fg=THEME["text"],
                insertbackground=THEME["text"],
                relief=tk.FLAT,
                highlightthickness=1,
                highlightbackground=THEME["border"],
            ),
        )
        tk.Checkbutton(
            settings_card,
            text="Trace all paths",
            variable=self.settings_all_paths_var,
            bg=THEME["glass"],
            fg=THEME["text"],
            selectcolor=THEME["glass_high"],
            activebackground=THEME["glass"],
            activeforeground=THEME["text"],
        ).grid(row=4, column=0, sticky="w", padx=14, pady=6)
        tk.Checkbutton(
            settings_card,
            text="UI verification headless",
            variable=self.settings_headless_var,
            bg=THEME["glass"],
            fg=THEME["text"],
            selectcolor=THEME["glass_high"],
            activebackground=THEME["glass"],
            activeforeground=THEME["text"],
        ).grid(row=4, column=1, sticky="w", padx=14, pady=6)
        save_button = GlassButton(settings_card, text="Save Settings", command=self._save_settings, width=150)
        save_button.grid(row=5, column=0, padx=14, pady=(10, 14), sticky="w")
        self.action_buttons.append(save_button)

        helper = self._glass_frame(shell, bg=THEME["glass_alt"], border=THEME["border_soft"])
        helper.pack(fill=tk.X, pady=(10, 0))
        tk.Label(helper, text="State", bg=THEME["glass_alt"], fg=THEME["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(12, 4))
        tk.Label(
            helper,
            text="Settings affect graph defaults, trace depth, and the remembered UI verification behavior for this project.",
            bg=THEME["glass_alt"],
            fg=THEME["text_muted"],
            justify=tk.LEFT,
            wraplength=920,
        ).pack(fill=tk.X, padx=16, pady=(0, 14))

    def _settings_row(self, parent: tk.Frame, row: int, label: str, widget: tk.Widget) -> None:
        tk.Label(parent, text=label, bg=THEME["glass"], fg=THEME["text_soft"], font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w", padx=16, pady=7)
        widget.grid(row=row, column=1, sticky="w", padx=16, pady=7)

    def _glass_frame(self, parent: tk.Misc, *, bg: str, border: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=bg, bd=0, relief=tk.FLAT, highlightthickness=1, highlightbackground=border)
        return frame

    def _add_action_button(
        self,
        parent: tk.Misc,
        text: str,
        command,
        *,
        row: int,
        column: int,
        pady: tuple[int, int] | int = 0,
        tone: str = "primary",
    ) -> GlassButton:
        button = GlassButton(parent, text=text, command=command, tone=tone, width=160)
        button.grid(row=row, column=column, padx=(0, 10), pady=pady, sticky="w")
        self.action_buttons.append(button)
        return button

    def _save_settings(self) -> None:
        self.controller.save_settings(
            project_mode=self.settings_mode_var.get(),
            graph_profile=self.settings_profile_var.get(),
            trace_depth=int(self.settings_trace_depth_var.get()),
            trace_all_paths=bool(self.settings_all_paths_var.get()),
            ui_verification_headless=bool(self.settings_headless_var.get()),
        )
        self.trace_direction_var.set(self.controller.state.trace_direction)
        self._set_footer_state("complete", "Settings saved", "Project settings were updated.")
        self._log("Settings updated.")
        self._refresh_overview()
        self._pulse_header()

    def _submit_graph_trace(self) -> None:
        target = self.trace_target_var.get().strip()
        if not target:
            self._set_footer_state("error", "Graph trace requires a target", "Enter a project path or symbol before running Graph Trace.")
            return
        self._submit("graph_trace", target=target, direction=self.trace_direction_var.get())

    def _submit_ui_verify(self) -> None:
        profile_name = self.ui_profile_var.get().strip() or None
        self._submit("ui_verification", profile_name=profile_name)

    def _submit(self, workflow: str, **kwargs) -> None:
        tab_key = self.workflow_tabs.get(workflow, "overview")
        self._select_tab(tab_key)
        if workflow == "scan":
            detail = "Initializing PROJECT CONTROL if needed, then scanning project files."
            self._log(detail)
            self._set_visual_state("running", workflow, detail)
        else:
            detail = f"Running {workflow} with {kwargs or 'default settings'}"
            self._log(detail)
            self._set_visual_state("running", workflow, detail)
        try:
            self.runner.submit(workflow, self.controller.dispatch, workflow, **kwargs)
        except RuntimeError as exc:
            self._set_footer_state("error", "Busy", str(exc))

    def _poll_background_events(self) -> None:
        for event in self.runner.poll():
            if event.kind == "result" and isinstance(event.payload, PresentationResult):
                self._handle_result(event.payload)
            elif event.kind == "error":
                self._handle_error(event.workflow, event.payload)
        self.root.after(100, self._poll_background_events)

    def _handle_result(self, result: PresentationResult) -> None:
        tab_key = self.workflow_tabs.get(result.workflow, "overview")
        self._display_result(tab_key, result, visual_state="complete")
        self._log(f"{result.title} complete.")
        self._set_visual_state("complete", result.workflow, f"{result.title} complete.")
        self._pulse_summary(tab_key)
        self._pulse_header()
        if result.workflow != "overview":
            self._refresh_overview()
            self._refresh_reports(select_tab=False)

    def _handle_error(self, workflow: str, error: object) -> None:
        message = self._format_workflow_error(workflow, error)
        tab_key = self.workflow_tabs.get(workflow, "overview")
        title = workflow.replace("_", " ").title()
        result = PresentationResult(
            workflow=workflow,
            title=title,
            summary={"status": "Error", "workflow": workflow.replace("_", " "), "state": "Blocked", "next_step": "Check message"},
            primary_text=message,
        )
        self._display_result(tab_key, result, visual_state="error")
        self._set_visual_state("error", workflow, message)
        self._log(message)

    def _display_result(self, tab_key: str, result: PresentationResult, *, visual_state: str | None = None) -> None:
        summary_items = list(result.summary.items())[:4]
        state = visual_state or self._derive_visual_state(result)
        for index, (title_var, value_var) in enumerate(self.tab_summary_vars.get(tab_key, [])):
            if index < len(summary_items):
                key, value = summary_items[index]
                title_var.set(str(key).replace("_", " ").title())
                value_var.set(str(value))
                self.tab_summary_badge_vars.get(tab_key, [])[index].set(self._summary_badge_for(state, key))
                self.tab_summary_icon_vars.get(tab_key, [])[index].set(self._summary_icon_for(key))
            else:
                title_var.set("—")
                value_var.set("—")
                self.tab_summary_badge_vars.get(tab_key, [])[index].set("INFO")
                self.tab_summary_icon_vars.get(tab_key, [])[index].set("◌")

        self._apply_banner_state(tab_key, result, state)
        self.tab_paths_var.get(tab_key, tk.StringVar()).set(
            "\n".join(f"{name}: {path}" for name, path in result.report_paths.items())
        )
        text = self.tab_text_widgets.get(tab_key)
        if text is not None:
            text.delete("1.0", tk.END)
            text.insert(tk.END, result.primary_text)
        self._select_tab(tab_key)

    def _derive_visual_state(self, result: PresentationResult) -> str:
        status = str(result.summary.get("status", "")).lower()
        if status == "ready":
            return "ready"
        if status in {"setup required", "scan required", "graph required", "not ready"}:
            return "empty"
        if status == "error":
            return "error"
        return "ready"

    def _apply_banner_state(self, tab_key: str, result: PresentationResult, state: str) -> None:
        tone = STATE_TONES[state]
        banner = self.tab_banner_frames.get(tab_key)
        vars_map = self.tab_banner_vars.get(tab_key)
        if banner is None or vars_map is None:
            return
        banner.configure(bg=tone["bg"], highlightbackground=tone["border"])
        vars_map["badge"].set(state.upper())
        vars_map["title"].set(result.title)
        lines = [line.strip() for line in result.primary_text.splitlines() if line.strip()]
        vars_map["body"].set(lines[1] if len(lines) > 1 else (lines[0] if lines else ""))
        for child in banner.winfo_children():
            if isinstance(child, tk.Frame):
                child.configure(bg=tone["bg"])
                for nested in child.winfo_children():
                    if isinstance(nested, tk.Label):
                        if nested.cget("textvariable") == str(vars_map["badge"]):
                            nested.configure(bg=tone["accent"], fg=THEME["bg"])
                        else:
                            nested.configure(bg=tone["bg"], fg=tone["text"])
            elif isinstance(child, tk.Label):
                child.configure(bg=tone["bg"], fg=THEME["text_soft"])

        for frame in self.tab_summary_frames.get(tab_key, []):
            border = tone["border"] if state in {"running", "complete", "error"} else THEME["border_soft"]
            frame.configure(highlightbackground=border)
        for badge in self.tab_summary_badges.get(tab_key, []):
            badge.configure(bg=tone["accent"], fg=THEME["bg"])

    def _select_tab(self, key: str) -> None:
        frame = self.tab_frames.get(key)
        if frame is not None:
            for current_key, current in self.tab_frames.items():
                if current_key == key:
                    current.pack(fill=tk.BOTH, expand=True)
                else:
                    current.pack_forget()
            self.selected_tab = key
        self._highlight_top_tabs(key)
        self._highlight_sidebar(key)

    def _highlight_top_tabs(self, selected_key: str) -> None:
        for key, button in self.tab_buttons.items():
            button.set_selected(key == selected_key)

    def _highlight_sidebar(self, selected_key: str | None) -> None:
        for key, button in self.sidebar_actions.items():
            button.set_selected(key == selected_key or (selected_key == "overview" and key == "overview"))

    def _refresh_overview(self) -> None:
        result = self.controller.get_overview()
        self._display_result("overview", result)

    def _seed_workflow_onboarding(self) -> None:
        self._display_result("ghost_dead", present_workflow_status(self.project_root, workflow="ghost", title="Ghost / Dead"))
        self._display_result("graph", present_graph_status(self.project_root, self.controller.refresh_state()))
        self._display_result("audits", present_workflow_status(self.project_root, workflow="artifacts", title="Audits"))

    def _refresh_reports(self, *, select_tab: bool = True) -> None:
        result = self.controller.get_reports()
        self._display_result("reports", result)
        if select_tab:
            self._select_tab("reports")
        self.report_paths_cache.clear()
        reports = list_all_reports(self.project_root)
        available = sum(1 for report in reports if report.get("exists"))
        if available == 0:
            self.report_summary_var.set("No reports are generated yet. Run Scan, Graph, Ghost, or the audit workflows to populate this workspace.")
        else:
            self.report_summary_var.set(f"{available} of {len(reports)} report artifacts are available for preview right now.")
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

    def _summary_badge_for(self, state: str, key: object) -> str:
        if state == "error":
            return "BLOCKED"
        if state == "running":
            return "LIVE"
        if state == "complete":
            return "DONE"
        if str(key).lower() in {"setup", "snapshot", "graph"}:
            return "CHECK"
        return "READY" if state == "ready" else "INFO"

    def _summary_icon_for(self, key: object) -> str:
        return SUMMARY_ICONS.get(str(key).lower(), "◌")

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
            preview += "This report is not generated yet.\n\nRun the related workflow first, then refresh this workspace."
        self.report_preview.delete("1.0", tk.END)
        self.report_preview.insert(tk.END, preview)

    def _open_selected_report(self) -> None:
        if self.report_listbox is None:
            return
        selected = self.report_listbox.curselection()
        if not selected:
            self._set_footer_state("error", "No report selected", "Pick a generated report from the list first.")
            return
        label = self.report_listbox.get(selected[0])
        path = self.report_paths_cache.get(label)
        if path is None:
            self._set_footer_state("error", "Selected report unavailable", "This report path is missing from the registry.")
            return
        if not path.exists():
            self._set_footer_state("empty", "Report not generated yet", "Run the related workflow first, then refresh Reports.")
            return
        try:
            open_path(path)
            self._set_footer_state("complete", f"Opened {path.name}", f"Opened report in the platform default viewer: {path}")
        except Exception as exc:  # pragma: no cover - platform-specific
            self._set_footer_state("error", "Failed to open report", str(exc))

    def _set_visual_state(self, state: str, workflow: str | None, detail: str) -> None:
        self.busy = state == "running"
        self.active_workflow = workflow if self.busy else None
        selected_tab = self.workflow_tabs.get(workflow, self.selected_tab if workflow is None else workflow)
        for key, button in self.sidebar_actions.items():
            button.set_disabled(self.busy and key != workflow)
            button.set_running(self.busy and key == workflow)
            button.set_selected((not self.busy) and key == selected_tab)
        for button in self.action_buttons:
            button.set_disabled(self.busy)
            button.set_running(False)
        self._highlight_top_tabs(selected_tab)
        self._set_footer_state(state, self._status_title_for(workflow, state), detail)

    def _status_title_for(self, workflow: str | None, state: str) -> str:
        if workflow is None:
            return "Ready"
        label = workflow.replace("_", " ").title()
        if state == "running":
            return f"Running {label}"
        if state == "complete":
            return f"{label} complete"
        if state == "error":
            return f"{label} failed"
        return label

    def _set_footer_state(self, state: str, title: str, detail: str) -> None:
        tone = STATE_TONES[state]
        self.status_var.set(title)
        self.status_detail_var.set(detail)
        if self.footer_frame is not None:
            self.footer_frame.configure(highlightbackground=tone["border"])
        if self.footer_pill is not None:
            self.footer_pill.configure(bg=tone["accent"])
        if self.footer_status_label is not None:
            self.footer_status_label.configure(bg=THEME["glass"], fg=tone["text"])
        if self.footer_detail_label is not None:
            self.footer_detail_label.configure(bg=THEME["glass"], fg=THEME["text_soft"])

    def _pulse_header(self) -> None:
        if self.header_frame is None:
            return
        original = self.header_frame.cget("highlightbackground")
        self.header_frame.configure(highlightbackground=THEME["accent_glow"])
        self.root.after(180, lambda: self.header_frame.configure(highlightbackground=original))

    def _pulse_summary(self, tab_key: str) -> None:
        for frame in self.tab_summary_frames.get(tab_key, []):
            original = frame.cget("highlightbackground")
            frame.configure(highlightbackground=THEME["accent_glow"])
            self.root.after(180, lambda current=frame, base=original: current.configure(highlightbackground=base))

    def _log(self, message: str) -> None:
        if self.log_widget is None:
            return
        self.log_widget.insert(tk.END, f"{message}\n")
        self.log_widget.see(tk.END)

    def _format_workflow_error(self, workflow: str, error: object) -> str:
        message = str(error)
        if workflow == "scan" and "not initialized" in message.lower():
            return (
                "Scan could not start. This project is not set up yet. "
                "Check write permissions, then run Scan again. The terminal fallback is 'pc init' followed by 'pc scan'."
            )
        if "snapshot file not found" in message.lower() or "snapshot not found" in message.lower():
            return f"{workflow.replace('_', ' ').title()} is not ready yet. Run Scan first to create a snapshot."
        if "graph" in message.lower() and "not found" in message.lower():
            return f"{workflow.replace('_', ' ').title()} is not ready yet. Run Graph Report first to build the dependency graph."
        return f"{workflow.replace('_', ' ').title()} failed: {message}"


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
