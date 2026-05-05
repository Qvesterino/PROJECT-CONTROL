"""YAML-backed configuration for reusable UI verification profiles."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Optional

import yaml


DEFAULT_BASE_URL = "http://127.0.0.1:6100"
DEFAULT_BROWSER = "chromium"
DEFAULT_TIMEOUT_MS = 15000
DEFAULT_INTERACTION_TIMEOUT_MS = 2000
DEFAULT_UI_VERIFICATION_CONFIG = Path(".project-control/ui-verification.yaml")
UI_VERIFICATION_PROFILES_DIR = Path(".project-control/ui-profiles")
ALLOWED_HOOK_ACTIONS = frozenset(
    {
        "click",
        "click_if_visible",
        "press_key",
        "set_input_files",
        "sleep",
        "wait_for",
    }
)


@dataclass(frozen=True)
class UISectionRule:
    """Maps UI element IDs to logical sections using regex patterns."""

    name: str
    pattern: str


@dataclass(frozen=True)
class UILifecycleStep:
    """Declarative step used by a UI verification lifecycle hook."""

    action: str
    selector: Optional[str] = None
    state: Optional[str] = None
    value: Optional[str] = None
    value_from: Optional[str] = None
    key: Optional[str] = None
    wait_ms: Optional[int] = None
    timeout_ms: Optional[int] = None
    optional: bool = False


@dataclass(frozen=True)
class UIViewport:
    """Viewport dimensions used for browser-based verification."""

    width: int = 1440
    height: int = 900


@dataclass(frozen=True)
class UITestValues:
    """Default interaction values used for generic input testing."""

    color: str = "#ff0000"
    text: str = "test-value"
    select_index: int = 1


@dataclass(frozen=True)
class UIVerificationConfig:
    """Fully resolved configuration for a single UI verification variant."""

    app_name: str = "UI Verification"
    profile_name: str = "default"
    base_url: str = DEFAULT_BASE_URL
    browser: str = DEFAULT_BROWSER
    html_path: Path = Path("index.html")
    image_path: Path = Path("assets/ATOMA.png")
    manifest_path: Optional[Path] = None
    default_timeout_ms: int = DEFAULT_TIMEOUT_MS
    interaction_timeout_ms: int = DEFAULT_INTERACTION_TIMEOUT_MS
    viewport: UIViewport = field(default_factory=UIViewport)
    sections: tuple[UISectionRule, ...] = ()
    import_steps: tuple[UILifecycleStep, ...] = ()
    preview_setup_steps: tuple[UILifecycleStep, ...] = ()
    preview_teardown_steps: tuple[UILifecycleStep, ...] = ()
    preview_retest_sections: tuple[str, ...] = ()
    test_values: UITestValues = field(default_factory=UITestValues)
    config_path: Optional[Path] = None


@dataclass(frozen=True)
class UIVerificationProfileInfo:
    """Strict metadata for a discovered UI verification profile."""

    name: str
    app_name: str
    path: Path
    source: str
    is_default: bool = False
    is_valid: bool = True
    error: Optional[str] = None


def default_ui_verification_config(base_dir: Optional[Path] = None) -> UIVerificationConfig:
    """Return a default config resolved against the provided base directory."""

    root = (base_dir or Path.cwd()).resolve()
    return UIVerificationConfig(
        html_path=root / "index.html",
        image_path=root / "assets" / "ATOMA.png",
        manifest_path=root / "src" / "shared" / "release-verification-manifest.json",
    )


def load_ui_verification_config(config_path: Optional[Path] = None) -> UIVerificationConfig:
    """
    Load a UI verification YAML profile.

    Missing or invalid files fall back to defaults resolved against the profile
    directory when available, otherwise against the current working directory.
    Unknown lifecycle actions are ignored rather than raising.
    """

    resolved_config_path = config_path.resolve() if config_path else None
    base_dir = resolved_config_path.parent if resolved_config_path else Path.cwd().resolve()
    defaults = default_ui_verification_config(base_dir)

    if resolved_config_path is None or not resolved_config_path.is_file():
        return defaults

    try:
        with resolved_config_path.open("r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream) or {}
    except (yaml.YAMLError, OSError):
        return defaults

    if not isinstance(data, dict):
        return defaults

    manifest_path = _resolve_optional_path(base_dir, data.get("manifest_path"), defaults.manifest_path)

    return UIVerificationConfig(
        app_name=str(data.get("app_name", defaults.app_name)),
        profile_name=str(data.get("profile_name", resolved_config_path.stem)),
        base_url=str(data.get("base_url", defaults.base_url)),
        browser=str(data.get("browser", defaults.browser)),
        html_path=_resolve_path(base_dir, data.get("html_path"), defaults.html_path),
        image_path=_resolve_path(base_dir, data.get("image_path"), defaults.image_path),
        manifest_path=manifest_path,
        default_timeout_ms=_safe_int(data.get("default_timeout_ms"), defaults.default_timeout_ms),
        interaction_timeout_ms=_safe_int(
            data.get("interaction_timeout_ms"), defaults.interaction_timeout_ms
        ),
        viewport=_parse_viewport(data.get("viewport")),
        sections=_parse_sections(data.get("sections")),
        import_steps=_parse_steps(data.get("import_steps")),
        preview_setup_steps=_parse_steps(data.get("preview_setup_steps")),
        preview_teardown_steps=_parse_steps(data.get("preview_teardown_steps")),
        preview_retest_sections=_parse_preview_sections(data.get("preview_retest_sections")),
        test_values=_parse_test_values(data.get("test_values")),
        config_path=resolved_config_path,
    )


def get_default_ui_verification_config_path(project_root: Path) -> Path:
    """Return the legacy single-profile path used as the default UI profile."""

    return project_root / DEFAULT_UI_VERIFICATION_CONFIG


def get_ui_verification_profiles_dir(project_root: Path) -> Path:
    """Return the canonical directory for multi-profile UI verification configs."""

    return project_root / UI_VERIFICATION_PROFILES_DIR


def list_ui_verification_profiles(project_root: Path) -> tuple[UIVerificationProfileInfo, ...]:
    """Discover UI verification profiles without falling back to runtime defaults."""

    resolved_project_root = project_root.resolve()
    profiles: list[UIVerificationProfileInfo] = []

    default_path = get_default_ui_verification_config_path(resolved_project_root)
    if default_path.is_file():
        profiles.append(inspect_ui_verification_profile(default_path, source="legacy", is_default=True))

    profiles_dir = get_ui_verification_profiles_dir(resolved_project_root)
    if profiles_dir.is_dir():
        for profile_path in sorted(
            [*profiles_dir.glob("*.yaml"), *profiles_dir.glob("*.yml")],
            key=lambda path: path.as_posix().lower(),
        ):
            profiles.append(inspect_ui_verification_profile(profile_path, source="project-profile"))

    return tuple(_mark_duplicate_profile_names(profiles))


def find_ui_verification_profile(project_root: Path, profile_name: str) -> Optional[UIVerificationProfileInfo]:
    """Find a discovered profile by name."""

    normalized_name = profile_name.strip().lower()
    if not normalized_name:
        return None

    for profile in list_ui_verification_profiles(project_root):
        if profile.name.lower() == normalized_name:
            return profile
    return None


def inspect_ui_verification_profile(
    profile_path: Path,
    *,
    source: str = "explicit",
    is_default: bool = False,
) -> UIVerificationProfileInfo:
    """Read strict metadata for a single UI verification profile path."""

    return _read_ui_verification_profile_info(profile_path, source=source, is_default=is_default)


def _resolve_path(base_dir: Path, raw_value: object, default_path: Path) -> Path:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return default_path
    candidate = Path(raw_value)
    return candidate.resolve() if candidate.is_absolute() else (base_dir / candidate).resolve()


def _resolve_optional_path(base_dir: Path, raw_value: object, default_path: Optional[Path]) -> Optional[Path]:
    if raw_value is None:
        return default_path
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    candidate = Path(raw_value)
    return candidate.resolve() if candidate.is_absolute() else (base_dir / candidate).resolve()


def _parse_sections(raw_sections: object) -> tuple[UISectionRule, ...]:
    if not isinstance(raw_sections, list):
        return ()
    result: list[UISectionRule] = []
    for item in raw_sections:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        pattern = item.get("pattern")
        if isinstance(name, str) and name and isinstance(pattern, str) and pattern:
            result.append(UISectionRule(name=name, pattern=pattern))
    return tuple(result)


def _parse_steps(raw_steps: object) -> tuple[UILifecycleStep, ...]:
    if not isinstance(raw_steps, list):
        return ()
    steps: list[UILifecycleStep] = []
    for item in raw_steps:
        if not isinstance(item, dict):
            continue
        action = item.get("action")
        if not isinstance(action, str) or action not in ALLOWED_HOOK_ACTIONS:
            continue
        steps.append(
            UILifecycleStep(
                action=action,
                selector=_optional_str(item.get("selector")),
                state=_optional_str(item.get("state")),
                value=_optional_str(item.get("value")),
                value_from=_optional_str(item.get("value_from")),
                key=_optional_str(item.get("key")),
                wait_ms=_optional_int(item.get("wait_ms")),
                timeout_ms=_optional_int(item.get("timeout_ms")),
                optional=bool(item.get("optional", False)),
            )
        )
    return tuple(steps)


def _parse_preview_sections(raw_sections: object) -> tuple[str, ...]:
    if not isinstance(raw_sections, list):
        return ()
    return tuple(section for section in raw_sections if isinstance(section, str) and section)


def _parse_viewport(raw_viewport: object) -> UIViewport:
    if not isinstance(raw_viewport, dict):
        return UIViewport()
    return UIViewport(
        width=_safe_int(raw_viewport.get("width"), 1440),
        height=_safe_int(raw_viewport.get("height"), 900),
    )


def _parse_test_values(raw_values: object) -> UITestValues:
    if not isinstance(raw_values, dict):
        return UITestValues()
    return UITestValues(
        color=str(raw_values.get("color", "#ff0000")),
        text=str(raw_values.get("text", "test-value")),
        select_index=_safe_int(raw_values.get("select_index"), 1),
    )


def _optional_str(value: object) -> Optional[str]:
    return value if isinstance(value, str) and value else None


def _optional_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _read_ui_verification_profile_info(
    profile_path: Path,
    *,
    source: str,
    is_default: bool = False,
) -> UIVerificationProfileInfo:
    resolved_path = profile_path.resolve()
    fallback_name = resolved_path.stem

    try:
        with resolved_path.open("r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
    except (yaml.YAMLError, OSError) as error:
        return UIVerificationProfileInfo(
            name=fallback_name,
            app_name="UI Verification",
            path=resolved_path,
            source=source,
            is_default=is_default,
            is_valid=False,
            error=str(error),
        )

    if not isinstance(data, dict):
        return UIVerificationProfileInfo(
            name=fallback_name,
            app_name="UI Verification",
            path=resolved_path,
            source=source,
            is_default=is_default,
            is_valid=False,
            error="Profile YAML must contain a mapping at the top level.",
        )

    raw_name = data.get("profile_name")
    raw_app_name = data.get("app_name")
    name = raw_name.strip() if isinstance(raw_name, str) and raw_name.strip() else fallback_name
    app_name = raw_app_name.strip() if isinstance(raw_app_name, str) and raw_app_name.strip() else "UI Verification"

    return UIVerificationProfileInfo(
        name=name,
        app_name=app_name,
        path=resolved_path,
        source=source,
        is_default=is_default,
        is_valid=True,
    )


def _mark_duplicate_profile_names(
    profiles: list[UIVerificationProfileInfo],
) -> list[UIVerificationProfileInfo]:
    counts: dict[str, int] = {}
    for profile in profiles:
        key = profile.name.lower()
        counts[key] = counts.get(key, 0) + 1

    marked_profiles: list[UIVerificationProfileInfo] = []
    for profile in profiles:
        if counts.get(profile.name.lower(), 0) > 1:
            marked_profiles.append(
                replace(
                    profile,
                    is_valid=False,
                    error=f"Duplicate UI verification profile name: {profile.name}",
                )
            )
        else:
            marked_profiles.append(profile)
    return marked_profiles