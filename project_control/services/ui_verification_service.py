"""Reusable Playwright-driven UI verification service."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Optional

from project_control.config.ui_verification_config import (
    UILifecycleStep,
    UIVerificationConfig,
    UIVerificationProfileInfo,
    find_ui_verification_profile as _find_ui_verification_profile,
    get_default_ui_verification_config_path as _get_default_ui_verification_config_path,
    inspect_ui_verification_profile,
    list_ui_verification_profiles as _list_ui_verification_profiles,
    load_ui_verification_config,
)


DEFAULT_UI_VERIFICATION_CONFIG = Path(".project-control/ui-verification.yaml")


@dataclass
class UIElement:
    """Result model for a single discovered UI element."""

    id: str
    tag: str
    type: Optional[str]
    selector: str
    category: str
    section: str
    present: bool = False
    visible: bool = False
    clickable: bool = False
    interacted: bool = False
    state_changed: bool = False
    visibility_state: str = "unknown"
    enabled_state: str = "unknown"
    state_change_verified: bool = False
    runtime_effect_verified: bool = False
    criticality: str = "coverage"
    mode_context: str = "imported"
    proof_type: str = "presence-only"
    source_path: Optional[str] = None
    test_result: str = "pending"
    error: Optional[str] = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        source_path = data.pop("source_path", None)
        if source_path:
            data["sourcePath"] = source_path
        return data


@dataclass
class VerificationReport:
    """Structured report emitted after a UI verification run."""

    timestamp: str
    app_name: str
    profile_name: str
    url: str
    browser: str
    html_path: str
    manifest_path: Optional[str]
    total: int = 0
    passed: int = 0
    failed: int = 0
    hidden_by_context: int = 0
    not_applicable: int = 0
    warned: int = 0
    elements: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


def discover_elements_from_html(html_path: Path, config: UIVerificationConfig) -> list[UIElement]:
    """Parse HTML and discover interactive elements using generic patterns."""

    html = html_path.read_text(encoding="utf-8")
    elements: list[UIElement] = []

    button_pattern = re.compile(r'<button\s+[^>]*id="([^"]+)"', re.IGNORECASE)
    for match in button_pattern.finditer(html):
        element_id = match.group(1)
        elements.append(
            UIElement(
                id=element_id,
                tag="button",
                type=None,
                selector=f"#{element_id}",
                category="button",
                section=guess_section(element_id, config),
            )
        )

    input_pattern = re.compile(
        r'<input\s+[^>]*id="([^"]+)"(?:\s+[^>]*type="([^"]+)")?',
        re.IGNORECASE,
    )
    for match in input_pattern.finditer(html):
        element_id = match.group(1)
        input_type = match.group(2)
        elements.append(
            UIElement(
                id=element_id,
                tag="input",
                type=input_type,
                selector=f"#{element_id}",
                category=_input_category(input_type),
                section=guess_section(element_id, config),
            )
        )

    select_pattern = re.compile(r'<select\s+[^>]*id="([^"]+)"', re.IGNORECASE)
    for match in select_pattern.finditer(html):
        element_id = match.group(1)
        elements.append(
            UIElement(
                id=element_id,
                tag="select",
                type=None,
                selector=f"#{element_id}",
                category="select",
                section=guess_section(element_id, config),
            )
        )

    return _deduplicate_elements(elements)


def guess_section(element_id: str, config: UIVerificationConfig) -> str:
    """Assign an element to a configured logical section."""

    for rule in config.sections:
        if re.search(rule.pattern, element_id, re.IGNORECASE):
            return rule.name
    return "other"


def load_verification_manifest(manifest_path: Optional[Path]) -> dict[str, dict[str, Any]]:
    """Load manifest metadata used to enrich per-element expectations."""

    if manifest_path is None or not manifest_path.exists():
        return {}
    try:
        payload = manifest_path.read_text(encoding="utf-8")
        manifest = __import__("json").loads(payload)
    except Exception:
        return {}
    return {
        entry["id"]: entry
        for entry in manifest
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }


def summarize_verification(
    config: UIVerificationConfig,
    url: str,
    elements: list[UIElement],
) -> VerificationReport:
    """Build the final structured report from collected element results."""

    passed = sum(1 for element in elements if element.test_result == "pass")
    failed = sum(1 for element in elements if element.test_result == "fail")
    hidden_by_context = sum(1 for element in elements if element.test_result == "hidden-by-context")
    not_applicable = sum(1 for element in elements if element.test_result == "not-applicable")
    warned = sum(1 for element in elements if element.test_result == "warn")

    report = VerificationReport(
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        app_name=config.app_name,
        profile_name=config.profile_name,
        url=url,
        browser=config.browser,
        html_path=str(config.html_path),
        manifest_path=str(config.manifest_path) if config.manifest_path else None,
        total=len(elements),
        passed=passed,
        failed=failed,
        hidden_by_context=hidden_by_context,
        not_applicable=not_applicable,
        warned=warned,
        elements=[element.to_dict() for element in elements],
    )
    report.summary = {
        "total": report.total,
        "passed": passed,
        "failed": failed,
        "hidden_by_context": hidden_by_context,
        "not_applicable": not_applicable,
        "warned": warned,
        "pass_rate": round(passed / max(report.total - hidden_by_context - not_applicable, 1) * 100, 1),
        "by_section": _summary_by_key(elements, "section"),
        "by_category": _summary_by_key(elements, "category"),
    }
    return report


def run_ui_verification(
    config: UIVerificationConfig,
    *,
    url: Optional[str] = None,
    image_path: Optional[Path] = None,
    screenshots_dir: Optional[Path] = None,
    headless: bool = True,
) -> VerificationReport:
    """Run browser-based UI verification using the provided profile."""

    sync_playwright, timeout_error = _load_playwright_runtime()
    target_url = url or config.base_url
    target_image = (image_path or config.image_path).resolve()

    with sync_playwright() as playwright:
        browser_launcher = getattr(playwright, config.browser, None)
        if browser_launcher is None:
            raise RuntimeError(f"Unsupported browser '{config.browser}' in UI verification profile.")

        browser = browser_launcher.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": config.viewport.width, "height": config.viewport.height}
        )
        page = context.new_page()

        runner = UIVerificationRunner(
            page=page,
            config=config,
            url=target_url,
            image_path=target_image,
            screenshots_dir=screenshots_dir,
            timeout_error=timeout_error,
        )
        try:
            return runner.run()
        finally:
            browser.close()


def get_default_ui_verification_config_path(project_root: Path) -> Path:
    """Return the default project-scoped UI verification profile path."""

    return _get_default_ui_verification_config_path(project_root)


def list_ui_verification_profiles(project_root: Path) -> tuple[UIVerificationProfileInfo, ...]:
    """Return all discovered UI verification profiles for the project."""

    return _list_ui_verification_profiles(project_root)


def resolve_ui_verification_config_path(
    project_root: Path,
    config_path: Optional[Path | str] = None,
    profile_name: Optional[str] = None,
) -> Path:
    """Resolve a verification profile path relative to the project root."""

    resolved_project_root = project_root.resolve()

    if config_path is not None:
        candidate = Path(config_path)
        resolved_path = candidate.resolve() if candidate.is_absolute() else (resolved_project_root / candidate).resolve()
        profile_info = inspect_ui_verification_profile(resolved_path)
        if not resolved_path.is_file():
            return resolved_path
        if not profile_info.is_valid:
            raise RuntimeError(f"UI verification profile is invalid: {resolved_path} ({profile_info.error})")
        return resolved_path

    profiles = list_ui_verification_profiles(resolved_project_root)

    if profile_name:
        profile = _find_ui_verification_profile(resolved_project_root, profile_name)
        if profile is None:
            available_profiles = ", ".join(sorted(p.name for p in profiles if p.is_valid)) or "none"
            raise RuntimeError(
                f"UI verification profile '{profile_name}' not found. Available profiles: {available_profiles}"
            )
        if not profile.is_valid:
            raise RuntimeError(f"UI verification profile '{profile.name}' is invalid: {profile.error}")
        return profile.path

    default_profile = next((profile for profile in profiles if profile.is_default), None)
    if default_profile is not None:
        if not default_profile.is_valid:
            raise RuntimeError(
                f"Default UI verification profile is invalid: {default_profile.path} ({default_profile.error})"
            )
        return default_profile.path

    valid_profiles = [profile for profile in profiles if profile.is_valid]
    if len(valid_profiles) == 1:
        return valid_profiles[0].path
    if len(valid_profiles) > 1:
        available_profiles = ", ".join(sorted(profile.name for profile in valid_profiles))
        raise RuntimeError(
            f"Multiple UI verification profiles found. Use --profile <name> or --config <path>. Available profiles: {available_profiles}"
        )

    if profiles:
        invalid_profiles = "; ".join(
            f"{profile.name}: {profile.error}"
            for profile in profiles
            if not profile.is_valid
        )
        raise RuntimeError(f"No valid UI verification profiles found. Invalid profiles: {invalid_profiles}")

    return get_default_ui_verification_config_path(resolved_project_root).resolve()


def run_ui_verification_profile(
    project_root: Path,
    *,
    config_path: Optional[Path | str] = None,
    profile_name: Optional[str] = None,
    url: Optional[str] = None,
    image_path: Optional[Path | str] = None,
    screenshots_dir: Optional[Path | str] = None,
    headless: bool = True,
    output_dir: Optional[Path | str] = None,
    include_html: bool = False,
) -> tuple[VerificationReport, Path, Path, Path, Optional[Path]]:
    """Run a project-scoped UI verification profile and persist standard outputs."""

    resolved_project_root = project_root.resolve()
    resolved_config_path = resolve_ui_verification_config_path(
        resolved_project_root,
        config_path=config_path,
        profile_name=profile_name,
    )

    if not resolved_config_path.is_file():
        default_path = get_default_ui_verification_config_path(resolved_project_root)
        template_path = _get_ui_verification_template_path()
        hint = f" Create {default_path} or pass --config."
        if template_path is not None:
            hint += f" Template: {template_path}"
        raise RuntimeError(f"UI verification profile not found: {resolved_config_path}.{hint}")

    config = load_ui_verification_config(resolved_config_path)
    if not config.html_path.exists():
        raise RuntimeError(f"UI verification HTML source not found: {config.html_path}")

    resolved_image_path = _resolve_optional_path(resolved_project_root, image_path)
    target_image_path = resolved_image_path or config.image_path
    if _profile_uses_image_path(config) and not target_image_path.exists():
        raise RuntimeError(f"UI verification image asset not found: {target_image_path}")

    resolved_screenshots_dir = _resolve_optional_path(resolved_project_root, screenshots_dir)
    target_output_dir = _resolve_optional_path(resolved_project_root, output_dir) or (
        resolved_project_root / ".project-control" / "exports"
    )

    report = run_ui_verification(
        config,
        url=url,
        image_path=target_image_path,
        screenshots_dir=resolved_screenshots_dir,
        headless=headless,
    )

    from project_control.render.ui_verification_renderer import write_ui_verification_outputs

    markdown_path, json_path, html_path = write_ui_verification_outputs(
        report,
        target_output_dir,
        include_html=include_html,
    )
    return report, resolved_config_path, markdown_path, json_path, html_path


class UIVerificationRunner:
    """Config-driven verifier that runs a UI profile inside a Playwright page."""

    def __init__(
        self,
        *,
        page: Any,
        config: UIVerificationConfig,
        url: str,
        image_path: Path,
        screenshots_dir: Optional[Path],
        timeout_error: type[Exception],
    ):
        self.page = page
        self.config = config
        self.url = url
        self.image_path = image_path
        self.screenshots_dir = screenshots_dir
        self.timeout_error = timeout_error
        self.elements: list[UIElement] = []
        self.manifest_by_id = load_verification_manifest(config.manifest_path)

    def run(self) -> VerificationReport:
        self.page.goto(self.url, wait_until="networkidle", timeout=self.config.default_timeout_ms)
        self._maybe_screenshot("01-initial-load")

        self.elements = discover_elements_from_html(self.config.html_path, self.config)

        self._run_lifecycle_steps(self.config.import_steps)
        self._maybe_screenshot("02-after-import")

        for element in self.elements:
            self._test_element(element)

        if self.config.preview_setup_steps:
            self._run_lifecycle_steps(self.config.preview_setup_steps)
            self._maybe_screenshot("03-preview-mode")
            self._retest_sections(self.config.preview_retest_sections)

        if self.config.preview_teardown_steps:
            self._run_lifecycle_steps(self.config.preview_teardown_steps)
            self._maybe_screenshot("04-after-preview")

        return summarize_verification(self.config, self.url, self.elements)

    def _run_lifecycle_steps(self, steps: tuple[UILifecycleStep, ...]) -> None:
        for step in steps:
            try:
                self._run_lifecycle_step(step)
            except Exception:
                if not step.optional:
                    raise

    def _run_lifecycle_step(self, step: UILifecycleStep) -> None:
        timeout = step.timeout_ms or self.config.default_timeout_ms
        if step.action == "wait_for":
            if step.selector is None:
                return
            self.page.wait_for_selector(step.selector, state=step.state or "visible", timeout=timeout)
            return

        if step.action == "set_input_files":
            if step.selector is None:
                return
            locator = self.page.locator(step.selector)
            locator.set_input_files(self._resolve_step_value(step))
            return

        if step.action == "click":
            if step.selector is None:
                return
            locator = self.page.locator(step.selector)
            locator.scroll_into_view_if_needed(timeout=timeout)
            locator.click(timeout=timeout)
            return

        if step.action == "click_if_visible":
            if step.selector is None:
                return
            locator = self.page.locator(step.selector)
            if locator.count() and locator.is_visible() and not _locator_is_disabled(locator):
                locator.scroll_into_view_if_needed(timeout=timeout)
                locator.click(timeout=timeout)
            return

        if step.action == "press_key":
            if step.key:
                self.page.keyboard.press(step.key)
            return

        if step.action == "sleep":
            self.page.wait_for_timeout(step.wait_ms or 0)

    def _resolve_step_value(self, step: UILifecycleStep) -> str:
        if step.value_from == "image_path":
            return str(self.image_path)
        return step.value or ""

    def _retest_sections(self, sections: tuple[str, ...]) -> None:
        if not sections:
            return
        targets = [element for element in self.elements if element.section in sections]
        for element in targets:
            element.present = False
            element.visible = False
            element.clickable = False
            element.interacted = False
            element.state_changed = False
            element.mode_context = "preview"
            element.test_result = "pending"
            element.error = None
            element.notes = []
            self._test_element(element)

    def _maybe_screenshot(self, name: str) -> None:
        if self.screenshots_dir is None:
            return
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = self.screenshots_dir / f"{name}.png"
        self.page.screenshot(path=str(screenshot_path), full_page=True)

    def _test_element(self, element: UIElement) -> None:
        locator = self.page.locator(element.selector)
        manifest_entry = self.manifest_by_id.get(element.id)
        if manifest_entry:
            element.criticality = manifest_entry.get("criticality", element.criticality)
            element.proof_type = manifest_entry.get("proofType", element.proof_type)
            source_path = manifest_entry.get("sourcePath") or manifest_entry.get("source_path")
            if isinstance(source_path, str) and source_path.strip():
                element.source_path = source_path.strip()

        count = locator.count()
        if count == 0:
            element.test_result = "hidden-by-context"
            element.visibility_state = "missing-from-dom"
            element.notes.append("Element not found in DOM")
            return

        element.present = True

        try:
            element.visible = locator.is_visible()
        except Exception as error:
            element.visible = False
            element.notes.append(f"Visibility check error: {error}")
        element.visibility_state = "visible" if element.visible else "hidden-by-context"

        try:
            if element.category == "button":
                self._test_button(element, locator)
            elif element.category == "slider":
                self._test_slider(element, locator)
            elif element.category == "toggle":
                self._test_toggle(element, locator)
            elif element.category == "select":
                self._test_select(element, locator)
            elif element.category == "color":
                self._test_color(element, locator)
            elif element.category == "text":
                self._test_text(element, locator)
            elif element.category == "file":
                self._test_file(element)
            else:
                element.test_result = "skip"
                element.notes.append(f"Unknown category '{element.category}' — no generic test logic")
        except Exception as error:
            element.test_result = "fail"
            element.error = str(error)
            element.notes.append(f"Interaction error: {error}")

    def _test_button(self, element: UIElement, locator: Any) -> None:
        if not element.visible:
            element.test_result = "hidden-by-context"
            element.notes.append("Button not visible (context-dependent)")
            return

        disabled = _locator_is_disabled(locator)
        element.enabled_state = "disabled" if disabled else "enabled"
        if disabled:
            reason = _disable_reason(locator)
            element.test_result = "not-applicable" if reason or element.proof_type == "disabled-reason" else "warn"
            element.notes.append(f"Button is disabled{' — ' + reason if reason else ''}")
            return

        element.clickable = True
        try:
            locator.scroll_into_view_if_needed(timeout=self.config.interaction_timeout_ms)
            locator.click(timeout=self.config.interaction_timeout_ms)
            element.interacted = True
            if element.proof_type == "presence-only":
                element.test_result = "pass"
                element.notes.append("Clicked successfully")
            else:
                element.test_result = "warn"
                element.notes.append("Clicked successfully; state change not independently verified")
        except self.timeout_error:
            self._dom_click_fallback(element, locator, "pointer timeout")
        except Exception as error:
            self._dom_click_fallback(element, locator, f"pointer error: {error}")

    def _dom_click_fallback(self, element: UIElement, locator: Any, reason: str) -> None:
        try:
            locator.evaluate("(node) => node.click()")
            element.interacted = True
            element.test_result = "warn" if element.proof_type != "presence-only" else "pass"
            element.notes.append(f"DOM click fallback succeeded after {reason}")
        except Exception as fallback_error:
            element.test_result = "warn"
            element.error = f"Click fallback failed after {reason}: {fallback_error}"

    def _test_slider(self, element: UIElement, locator: Any) -> None:
        if not element.visible:
            element.test_result = "hidden-by-context"
            element.notes.append("Slider not visible (context-dependent)")
            return
        if _locator_is_disabled(locator):
            reason = _disable_reason(locator)
            element.enabled_state = "disabled"
            element.test_result = "not-applicable" if reason or element.proof_type == "disabled-reason" else "warn"
            element.notes.append(f"Slider is disabled{' — ' + reason if reason else ''}")
            return

        element.enabled_state = "enabled"
        current = locator.input_value()
        min_value = locator.get_attribute("min") or "0"
        max_value = locator.get_attribute("max") or "1"
        step_value = locator.get_attribute("step") or "1"
        mid = (float(min_value) + float(max_value)) / 2
        if step_value and float(step_value) > 0:
            mid = round(mid / float(step_value)) * float(step_value)

        self.page.evaluate(
            """({ selector, value }) => {
                const element = document.querySelector(selector);
                if (element) {
                    element.value = value;
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }""",
            {"selector": element.selector, "value": str(mid)},
        )

        new_value = locator.input_value()
        element.interacted = True
        element.state_changed = new_value != current
        element.state_change_verified = element.state_changed
        element.test_result = "pass" if element.state_changed else "fail"
        element.notes.append(
            f"Changed from {current} to {new_value} (min={min_value}, max={max_value})"
        )

    def _test_toggle(self, element: UIElement, locator: Any) -> None:
        if not element.visible:
            element.test_result = "hidden-by-context"
            element.notes.append("Toggle not visible (context-dependent)")
            return
        if _locator_is_disabled(locator):
            reason = _disable_reason(locator)
            element.enabled_state = "disabled"
            element.test_result = "not-applicable" if reason or element.proof_type == "disabled-reason" else "warn"
            element.notes.append(f"Toggle is disabled{' — ' + reason if reason else ''}")
            return

        element.enabled_state = "enabled"
        before = locator.is_checked()
        try:
            locator.scroll_into_view_if_needed(timeout=self.config.interaction_timeout_ms)
            locator.click(timeout=self.config.interaction_timeout_ms)
        except self.timeout_error:
            locator.evaluate("(node) => node.click()")
        after = locator.is_checked()
        element.interacted = True
        element.state_changed = before != after
        element.state_change_verified = element.state_changed
        element.test_result = "pass" if element.state_changed else "fail"
        element.notes.append(f"Toggled from {before} to {after}")

    def _test_select(self, element: UIElement, locator: Any) -> None:
        if not element.visible:
            element.test_result = "hidden-by-context"
            element.notes.append("Select not visible (context-dependent)")
            return
        if _locator_is_disabled(locator):
            reason = _disable_reason(locator)
            element.enabled_state = "disabled"
            element.test_result = "not-applicable" if reason or element.proof_type == "disabled-reason" else "warn"
            element.notes.append(f"Select is disabled{' — ' + reason if reason else ''}")
            return

        element.enabled_state = "enabled"
        options = locator.locator("option").all_inner_texts()
        if len(options) <= self.config.test_values.select_index:
            element.test_result = "warn"
            element.notes.append(f"Only {len(options)} option(s) — may be dynamic")
            return

        before = locator.input_value()
        locator.select_option(index=self.config.test_values.select_index, timeout=self.config.interaction_timeout_ms)
        after = locator.input_value()
        element.interacted = True
        element.state_changed = before != after
        element.state_change_verified = element.state_changed
        element.test_result = "pass" if element.state_changed else "fail"
        element.notes.append(
            f"Selected option index {self.config.test_values.select_index} (was '{before}', now '{after}')"
        )

    def _test_color(self, element: UIElement, locator: Any) -> None:
        if not element.visible:
            element.test_result = "hidden-by-context"
            element.notes.append("Color input not visible")
            return
        if _locator_is_disabled(locator):
            reason = _disable_reason(locator)
            element.enabled_state = "disabled"
            element.test_result = "not-applicable" if reason or element.proof_type == "disabled-reason" else "warn"
            element.notes.append(f"Color input is disabled{' — ' + reason if reason else ''}")
            return

        before = locator.input_value()
        locator.evaluate(
            "(node, value) => { node.value = value; node.dispatchEvent(new Event('input', { bubbles: true })); }",
            self.config.test_values.color,
        )
        after = locator.input_value()
        element.interacted = True
        element.state_changed = before != after
        element.state_change_verified = element.state_changed
        element.test_result = "pass" if element.state_changed else "fail"
        element.notes.append(f"Changed color from {before} to {after}")

    def _test_text(self, element: UIElement, locator: Any) -> None:
        if not element.visible:
            element.test_result = "hidden-by-context"
            element.notes.append("Text input not visible")
            return
        if _locator_is_disabled(locator):
            reason = _disable_reason(locator)
            element.enabled_state = "disabled"
            element.test_result = "not-applicable" if reason or element.proof_type == "disabled-reason" else "warn"
            element.notes.append(f"Text input is disabled{' — ' + reason if reason else ''}")
            return

        before = locator.input_value()
        locator.fill(self.config.test_values.text, timeout=self.config.interaction_timeout_ms)
        after = locator.input_value()
        element.interacted = True
        element.state_changed = before != after
        element.state_change_verified = element.state_changed
        element.test_result = "pass" if element.state_changed else "fail"
        element.notes.append(f"Filled text input (was '{before}', now '{after}')")

    def _test_file(self, element: UIElement) -> None:
        element.test_result = "not-applicable"
        element.enabled_state = "enabled"
        element.notes.append("File input — tested during configured import flow")


def _summary_by_key(elements: list[UIElement], attribute: str) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for element in elements:
        key = getattr(element, attribute)
        bucket = summary.setdefault(
            key,
            {"total": 0, "pass": 0, "fail": 0, "warn": 0, "not-applicable": 0, "hidden-by-context": 0},
        )
        bucket["total"] += 1
        bucket[element.test_result] = bucket.get(element.test_result, 0) + 1
    return summary


def _resolve_optional_path(project_root: Path, raw_path: Optional[Path | str]) -> Optional[Path]:
    if raw_path is None:
        return None
    candidate = Path(raw_path)
    return candidate.resolve() if candidate.is_absolute() else (project_root / candidate).resolve()


def _profile_uses_image_path(config: UIVerificationConfig) -> bool:
    lifecycle_steps = config.import_steps + config.preview_setup_steps + config.preview_teardown_steps
    return any(step.value_from == "image_path" for step in lifecycle_steps)


def _deduplicate_elements(elements: list[UIElement]) -> list[UIElement]:
    seen: set[str] = set()
    unique: list[UIElement] = []
    for element in elements:
        if element.id in seen:
            continue
        seen.add(element.id)
        unique.append(element)
    return unique


def _input_category(input_type: Optional[str]) -> str:
    if input_type == "range":
        return "slider"
    if input_type == "checkbox":
        return "toggle"
    if input_type == "file":
        return "file"
    if input_type == "color":
        return "color"
    if input_type == "text":
        return "text"
    return "input"


def _disable_reason(locator: Any) -> str:
    for attribute in ("title", "aria-label", "data-disabled-reason"):
        try:
            value = locator.get_attribute(attribute)
        except Exception:
            value = None
        if value and value.strip():
            return value.strip()
    return ""


def _locator_is_disabled(locator: Any) -> bool:
    try:
        if hasattr(locator, "is_disabled"):
            return bool(locator.is_disabled())
    except Exception:
        return False
    return False


def _load_playwright_runtime() -> tuple[Any, type[Exception]]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError(
            "Playwright Python package is not installed. Run: pip install playwright; then: playwright install chromium"
        ) from error
    return sync_playwright, PlaywrightTimeoutError


def _get_ui_verification_template_path() -> Optional[Path]:
    candidate = Path(__file__).resolve().parents[2] / "examples" / "new" / "ui_verification.flowra.yaml"
    return candidate if candidate.exists() else None
