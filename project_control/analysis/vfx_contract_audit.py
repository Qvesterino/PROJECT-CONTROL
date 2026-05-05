"""VFX contract audit analyzer for FX-oriented JavaScript files."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from project_control.core.content_store import ContentStore
from project_control.core.snapshot_service import load_snapshot


EXPLICIT_FX_FILES: Set[str] = {
    "_AdaptiveGlyphRendering1_0.js",
    "_AiEmotionalFeed3_1.js",
    "_AINarrativePatterns6_0.js",
    "_AIThoughtStorms2_0.js",
    "_AmbientEntityManager.js",
    "_AmbientEntityRegistry.js",
    "_AtomaGlyphSystem4_0.js",
    "AIConsciousnessLayer.js",
    "ArchetypeShaderModes_v1.js",
    "CanonicalGeometryFamilies_v1.js",
    "CanonicalTemplate3_StressVisuals.js",
    "CascadeBurstVisual_Session147.js",
    "CascadeEventBridge_v1.js",
    "CascadeParticleSystem_Session120.js",
    "CascadeResonanceWaveVisualization_Session146.js",
    "CascadeSystemConsoleAPI.js",
    "CascadeToWaveBridge_v1.js",
    "CascadeWaveParticles.js",
    "CascadingRuptureSystem.js",
    "CinematicUpgrade.js",
    "CognitiveHorizonPlane.js",
    "ColonyVFXManager.js",
    "CompositeGlyphGenerator.js",
    "CompositeGlyphResonanceFeedback.js",
    "CoreHologramShader.js",
    "CorruptionVisualFX_v1.js",
    "CriticalNodeFailureSystem.js",
    "DistanceLODController.js",
    "DreamDepthEffectManager.js",
    "EchoRippleIntegrationPatch_Session125.js",
    "EchoRippleSystem_Session125.js",
    "EnergyVisualProfile.js",
    "EnhancedNodeModels.js",
    "EnvironmentalHazards.js",
    "EventVisualSuppression_v1.js",
    "FireLikeAuraConfig.js",
    "FresnelAuraIntegrationPatch.js",
    "FresnelRimLightAuraShader.js",
    "FXPerformanceController_v1.js",
    "FXPerformanceSmoothTransition_v1.js",
    "GlyphAnimationModulator.js",
    "GlyphFusionZone.js",
    "HarmonicAudioReactivitySystem_Session135.js",
    "HarmonicCascadeAmplification_Session145.js",
    "HarmonicHealingVisualSystem_Session134.js",
    "HarmonicHubAuraSystem_Session126.js",
    "HarmonicHubCascade.js",
    "HarmonicHubLifecycle.js",
    "HarmonicHubSync.js",
    "HarmonicInfluencePropagationSystem_Session127.js",
    "HarmonicNodeResonanceHalos.js",
    "HarmonicRecoveryVisualSystem_Session138.js",
    "HarmonicResonanceCoupling_v1.js",
    "HarmonicResonanceFeedbackSystem.js",
    "HarmonicTopologyLearningSystem.js",
    "NeuralConvergenceSingularity.js",
    "SafeQuantumIllusionsPack1.js",
    "_SafeEvolutionManager.js",
    "_SafeLegendaryLinkFX.js",
    "_SafeLegendaryWorldEvents.js",
    "_SafeAIWeatherPack.js",
    "_SafeWorldFXPack.js",
    "SynergyCascadeVisualizer.js",
    "T2_CorruptionVisualIntegration_v1.js",
    "T2_HarmonyVisualConsumer_v1.js",
    "VisualUpgradeSuperpack.js",
    "_LinkedGlyphMessaging3_0.js",
    "_LinkedGlyphSynchronization1_0.js",
    "_RecursiveGlyphMessaging4_0.js",
    "_ProceduralMeaningEngine.js",
    "_NodeVisualBootstrap3_0.js",
    "_ExtremeAIShaderPack.js",
    "_EmergentThoughtStorms5_0.js",
    "_GlyphFusionOverlay4_1.js",
    "PHASE5_CascadeVisuals.js",
    "TIER4_CorruptionFeedbackVisuals_v1.js",
    "_GlyphLayer4_MultiFusion.js",
    "_SemanticGlyphAI.js",
}

OWNER_CROSSREF_FILES = ["main.js", "EnvironmentDomainController.js"]


@dataclass
class ContractCheck:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class FXFileReport:
    filename: str
    filepath: str
    category: str = "UNKNOWN"
    owner: str = "UNKNOWN"
    trigger: str = "UNKNOWN"
    checks: List[ContractCheck] = field(default_factory=list)
    risk_score: int = 0
    risk_level: str = "LOW"
    verdict: str = "KEEP"
    console_count: int = 0
    has_debug_guard: bool = False
    class_name: Optional[str] = None


@dataclass
class VFXContractAuditResult:
    reports: List[FXFileReport]
    summary: Dict[str, int]


class FXFileScanner:
    def __init__(self, snapshot: Dict[str, Any], content_store: ContentStore):
        self.snapshot = snapshot
        self.content_store = content_store

    def scan(self) -> List[str]:
        files: List[str] = []
        explicit_found: Set[str] = set()

        for entry in self.snapshot.get("files", []):
            path = entry.get("path")
            if not path:
                continue

            filename = Path(path).name
            if filename in EXPLICIT_FX_FILES:
                files.append(Path(path).as_posix())
                explicit_found.add(filename)
                continue

            if not filename.endswith(".js"):
                continue

            try:
                content = self.content_store.get_text(path)
            except Exception:
                continue

            if self._is_fx_heuristic(content):
                files.append(Path(path).as_posix())

        unique_files = sorted({Path(path).as_posix() for path in files})
        return unique_files

    def _is_fx_heuristic(self, content: str) -> bool:
        has_export_class = "export class" in content
        has_three = any(
            token in content
            for token in (
                "THREE.Mesh",
                "THREE.Line",
                "THREE.Points",
                "THREE.Group",
            )
        )
        has_material = any(
            token in content
            for token in (
                "ShaderMaterial",
                "MeshBasicMaterial",
                "MeshStandardMaterial",
            )
        )
        has_scene = "scene.add" in content or "scene.remove" in content
        has_dispose = ".dispose()" in content
        return has_export_class and (has_three or has_material or has_scene or has_dispose)


class CategoryDetector:
    CATEGORIES: List[Tuple[str, List[str]]] = [
        (
            "LINK FX",
            [
                "linkId",
                "link.source",
                "link.target",
                "linkingSystem",
                "LinkFX",
                "LinkCascade",
                "LinkBead",
                "LinkCollapse",
            ],
        ),
        (
            "NODE FX",
            [
                "nodeId",
                "node.position",
                "node.userData",
                "NodeFX",
                "registerNode",
                "AINodes",
                "EnhancedNode",
                "NodeVisual",
                "NodeResonance",
            ],
        ),
        (
            "ENVIRONMENT FX",
            [
                "worldRoot",
                "environmentRoot",
                "WORLD_OVERLAY",
                "WORLD_BACKGROUND",
                "Environment",
                "WeatherPack",
                "WorldFX",
                "Atmosphere",
                "DreamDepth",
            ],
        ),
        (
            "CASCADE/WAVE",
            [
                "Cascade",
                "Wave",
                "Resonance",
                "Rupture",
                "Burst",
                "SynergyCascade",
                "HarmonicCascade",
                "CascadeParticle",
            ],
        ),
        (
            "PARTICLE FX",
            [
                "THREE.Points",
                "ParticleSystem",
                "Particle",
                "spawnCount",
                "pool",
                "PointsMaterial",
                "particlePools",
            ],
        ),
        (
            "SHADER/MATERIAL",
            [
                "ShaderMaterial",
                "onBeforeCompile",
                "uniforms",
                "vertexShader",
                "fragmentShader",
                "ArchetypeShader",
                "AuraShader",
                "HologramShader",
            ],
        ),
    ]

    def detect(self, content: str, filename: str) -> str:
        scores: Dict[str, int] = {}
        for category, keywords in self.CATEGORIES:
            score = sum(1 for keyword in keywords if keyword in content or keyword in filename)
            if score:
                scores[category] = score
        if not scores:
            return "UNKNOWN"
        return max(scores, key=scores.get)


class ContractChecker:
    def check(self, content: str, filename: str) -> List[ContractCheck]:
        return [
            self._check_purpose(content),
            self._check_owner(content, filename),
            self._check_trigger(content),
            self._check_gate(content),
            self._check_update(content),
            self._check_budget(content),
            self._check_lifetime(content),
            self._check_dispose(content),
            self._check_debug(content),
        ]

    def _check_purpose(self, content: str) -> ContractCheck:
        pattern = re.compile(
            r"/\*\*[\s\S]*?(visual|effect|vfx|fx|overlay|particle|shader|cascade|wave|aura|glow)",
            re.IGNORECASE,
        )
        if pattern.search(content):
            return ContractCheck("PURPOSE", True, "JSDoc/comment with FX keywords found")
        if re.search(r"/\*\*[\s\S]*?\*/", content):
            return ContractCheck("PURPOSE", True, "Block comment present (generic)")
        return ContractCheck("PURPOSE", False, "No purpose documentation")

    def _check_owner(self, content: str, filename: str) -> ContractCheck:
        owners: List[str] = []
        if "EnvironmentDomainController" in content:
            owners.append("EnvironmentDomainController")
        if "LinkRendererConduit" in content:
            owners.append("LinkRendererConduit")
        if "FrameScheduler" in content:
            owners.append("FrameScheduler")
        if "semanticBus" in content or "SemanticBus" in content:
            owners.append("SemanticBus")
        if "constructor" in content and "scene" in content:
            owners.append("scene-based")
        if owners:
            return ContractCheck("OWNER", True, f"Detected: {', '.join(owners)}")
        return ContractCheck("OWNER", False, "No known owner reference")

    def _check_trigger(self, content: str) -> ContractCheck:
        triggers: List[str] = []
        if re.search(r"\.(on\(|addEventListener|subscribe)", content):
            triggers.append("event")
        if re.search(r"synergy|harmony|stability|corruption|loadPressure", content, re.IGNORECASE):
            triggers.append("metric")
        if "link." in content or "linkId" in content:
            triggers.append("link-state")
        if "node." in content or "nodeId" in content:
            triggers.append("node-state")
        if re.search(r"worldState|atmosphereState|weatherState", content):
            triggers.append("environment")
        if "update(deltaTime" in content or "update(dt" in content:
            triggers.append("per-frame")
        if triggers:
            return ContractCheck("TRIGGER", True, f"Detected: {', '.join(triggers)}")
        return ContractCheck("TRIGGER", False, "No clear trigger mechanism")

    def _check_gate(self, content: str) -> ContractCheck:
        gates: List[str] = []
        if re.search(r"this\.(enabled|disabled)\b|setEnabled\b", content):
            gates.append("enabled-flag")
        if (
            "frameScheduler" in content
            or "shouldRunVisual" in content
            or "shouldRunSimulation" in content
        ):
            gates.append("scheduler")
        if re.search(r"LOD|distance|farDistance", content):
            gates.append("LOD")
        if re.search(r"cooldown|lastTime|interval", content, re.IGNORECASE):
            gates.append("cooldown")
        if re.search(r"if\s*\(\s*!this\.\w+", content):
            gates.append("null-guard")
        if "!this.frameScheduler?.shouldRunVisual?.()" in content:
            return ContractCheck("GATE", False, "CRITICAL: frameScheduler optional-chain bug — always blocks update")
        if gates:
            return ContractCheck("GATE", True, f"Detected: {', '.join(gates)}")
        return ContractCheck("GATE", False, "No gate mechanism found")

    def _check_update(self, content: str) -> ContractCheck:
        if re.search(r"update\s*\(", content):
            if re.search(r"update\s*\([^)]*\)\s*\{[^}]*?return", content, re.DOTALL):
                return ContractCheck("UPDATE", True, "update() with early return")
            return ContractCheck("UPDATE", True, "update() present (no early return)")
        return ContractCheck("UPDATE", False, "No update() method")

    def _check_budget(self, content: str) -> ContractCheck:
        if re.search(
            r"maxParticles|maxCount|pool.*size|cap|limit|MAX_",
            content,
            re.IGNORECASE,
        ):
            return ContractCheck("BUDGET", True, "Budget cap keywords found")
        return ContractCheck("BUDGET", False, "No budget cap detected")

    def _check_lifetime(self, content: str) -> ContractCheck:
        lifetime: List[str] = []
        if re.search(r"TTL|lifetime|duration|maxAge|age", content, re.IGNORECASE):
            lifetime.append("TTL")
        if re.search(r"fadeOut|dissolve|despawn", content, re.IGNORECASE):
            lifetime.append("fade-out")
        if re.search(r"pool.*release|returnToPool|recycle", content, re.IGNORECASE):
            lifetime.append("pool")
        if "scene.remove" in content or "removeFromScene" in content:
            lifetime.append("scene-remove")
        if lifetime:
            return ContractCheck("LIFETIME", True, f"Detected: {', '.join(lifetime)}")
        return ContractCheck("LIFETIME", False, "No lifetime management")

    def _check_dispose(self, content: str) -> ContractCheck:
        if re.search(r"dispose\s*\(\)", content):
            details: List[str] = []
            if "scene.remove" in content:
                details.append("scene-remove")
            if re.search(r"\.geometry\.dispose|geometry\.dispose", content):
                details.append("geometry")
            if re.search(r"\.material\.dispose|material\.dispose", content):
                details.append("material")
            if re.search(r"\.clear\(\)", content):
                details.append("clear-maps")
            if re.search(r"removeEventListener|unsubscribe|off\(", content):
                details.append("unsubscribe")
            detail = f"dispose() with: {', '.join(details)}" if details else "dispose() present"
            return ContractCheck("DISPOSE", True, detail)
        return ContractCheck("DISPOSE", False, "No dispose() method")

    def _check_debug(self, content: str) -> ContractCheck:
        console_calls = len(re.findall(r"console\.(log|warn|error|info)", content))
        has_debug = bool(re.search(r"debugMode|this\.debug|DEBUG|_debug", content))
        wrapped = len(
            re.findall(
                r"if\s*\(\s*(?:this\.)?debug(?:Mode)?\s*\)\s*\{[^}]*console\.(log|warn|error|info)",
                content,
            )
        )
        if console_calls == 0:
            return ContractCheck("DEBUG", True, "No console calls")
        if has_debug and (wrapped >= console_calls * 0.5 or console_calls <= 3):
            return ContractCheck("DEBUG", True, f"{console_calls} console calls, debug guard present")
        if console_calls > 3 and not has_debug:
            return ContractCheck("DEBUG", False, f"{console_calls} console calls without debug flag")
        return ContractCheck("DEBUG", True, f"{console_calls} console calls, debug flag present")


class RiskAssessor:
    def assess(self, checks: List[ContractCheck], content: str, filename: str) -> Tuple[int, str]:
        score = 0
        check_map = {check.name: check for check in checks}

        if not check_map.get("DISPOSE", ContractCheck("", True)).passed:
            score += 3
        if not check_map.get("GATE", ContractCheck("", True)).passed:
            score += 2
        if not check_map.get("BUDGET", ContractCheck("", True)).passed:
            score += 2
        if not check_map.get("DEBUG", ContractCheck("", True)).passed:
            score += 1
        if not check_map.get("OWNER", ContractCheck("", True)).passed:
            score += 1
        if not check_map.get("UPDATE", ContractCheck("", True)).passed:
            score += 1

        if (
            "RoundedBoxGeometry" in content
            and "opacity" in content
            and "0.0" in content
        ):
            score += 3
        if (
            "THREE.Points" in content
            and "sizeAttenuation" in content
            and "position(0,0,0)" in content.replace(" ", "")
        ):
            score += 2
        if "Geometry" in content and "BufferGeometry" not in content:
            score += 2

        if score <= 1:
            level = "LOW"
        elif score <= 3:
            level = "MID"
        else:
            level = "HIGH"
        return score, level


class VerdictEngine:
    def decide(self, checks: List[ContractCheck], risk_score: int, risk_level: str) -> str:
        passed = sum(1 for check in checks if check.passed)
        failed = len(checks) - passed

        if failed == 0:
            return "KEEP"
        if failed <= 2 and risk_level in ("LOW", "MID"):
            return "FIX"
        if failed >= 3 and risk_level == "MID":
            return "ISOLATE"
        if risk_level == "HIGH" or failed >= 6:
            return "KILL"
        if failed <= 2:
            return "FIX"
        return "ISOLATE"


class OwnerCrossRef:
    def __init__(self, content_store: ContentStore, snapshot: Dict[str, Any]):
        self.content_store = content_store
        self.snapshot = snapshot
        self.owners: Dict[str, str] = {}
        self._scan()

    def _scan(self) -> None:
        available_paths = {
            Path(entry.get("path", "")).as_posix(): entry
            for entry in self.snapshot.get("files", [])
            if entry.get("path")
        }

        for filename in OWNER_CROSSREF_FILES:
            for path in available_paths:
                if Path(path).name != filename:
                    continue
                try:
                    content = self.content_store.get_text(path)
                except Exception:
                    continue

                for match in re.finditer(r"new\s+([A-Za-z0-9_]+)\s*\(", content):
                    self.owners[match.group(1)] = filename

                for match in re.finditer(r"import\s+\{?\s*([A-Za-z0-9_]+)\s*\}?\s+from\s+['\"]([^'\"]+)['\"]", content):
                    class_name = match.group(1)
                    src = match.group(2)
                    if src.endswith(".js"):
                        self.owners[class_name] = filename

    def get_owner(self, class_name: Optional[str], filename: str) -> str:
        if class_name and class_name in self.owners:
            return self.owners[class_name]
        if "Environment" in filename or "World" in filename or "Weather" in filename:
            return "EnvironmentDomainController (heuristic)"
        if "Link" in filename:
            return "LinkRendererConduit (heuristic)"
        if "Node" in filename or "AINodes" in filename:
            return "main.js (heuristic)"
        return "UNKNOWN"


def _extract_class_name(content: str) -> Optional[str]:
    match = re.search(r"export\s+class\s+([A-Za-z0-9_]+)", content)
    return match.group(1) if match else None


def _build_report(
    path: str,
    content: str,
    category_detector: CategoryDetector,
    checker: ContractChecker,
    risk_assessor: RiskAssessor,
    verdict_engine: VerdictEngine,
    owner_xref: OwnerCrossRef,
) -> FXFileReport:
    filename = Path(path).name
    class_name = _extract_class_name(content)
    category = category_detector.detect(content, filename)
    checks = checker.check(content, filename)
    risk_score, risk_level = risk_assessor.assess(checks, content, filename)
    verdict = verdict_engine.decide(checks, risk_score, risk_level)
    owner = owner_xref.get_owner(class_name, filename)
    trigger_check = next((check for check in checks if check.name == "TRIGGER"), None)
    trigger = trigger_check.detail if trigger_check else "UNKNOWN"
    console_count = sum(1 for check in checks if check.name == "DEBUG" and not check.passed)
    has_debug_guard = any(check.name == "DEBUG" and check.passed for check in checks)

    return FXFileReport(
        filename=filename,
        filepath=Path(path).as_posix(),
        category=category,
        owner=owner,
        trigger=trigger,
        checks=checks,
        risk_score=risk_score,
        risk_level=risk_level,
        verdict=verdict,
        console_count=console_count,
        has_debug_guard=has_debug_guard,
        class_name=class_name,
    )


def analyze_vfx_contract(project_root: str | Path = ".") -> VFXContractAuditResult:
    root = Path(project_root)
    snapshot = load_snapshot(root)
    snapshot_path = root / ".project-control" / "snapshot.json"
    content_store = ContentStore(snapshot, snapshot_path)

    scanner = FXFileScanner(snapshot, content_store)
    candidate_paths = scanner.scan()

    category_detector = CategoryDetector()
    checker = ContractChecker()
    risk_assessor = RiskAssessor()
    verdict_engine = VerdictEngine()
    owner_xref = OwnerCrossRef(content_store, snapshot)

    reports: List[FXFileReport] = []
    for path in candidate_paths:
        try:
            content = content_store.get_text(path)
        except Exception:
            continue
        reports.append(_build_report(path, content, category_detector, checker, risk_assessor, verdict_engine, owner_xref))

    verdict_order = {"KILL": 0, "ISOLATE": 1, "FIX": 2, "KEEP": 3}
    reports.sort(key=lambda report: (verdict_order.get(report.verdict, 99), report.filename))

    summary = {
        "total_files": len(reports),
        "keep": sum(1 for report in reports if report.verdict == "KEEP"),
        "fix": sum(1 for report in reports if report.verdict == "FIX"),
        "isolate": sum(1 for report in reports if report.verdict == "ISOLATE"),
        "kill": sum(1 for report in reports if report.verdict == "KILL"),
    }

    return VFXContractAuditResult(reports=reports, summary=summary)


def vfx_contract_result_to_dict(result: VFXContractAuditResult) -> Dict[str, Any]:
    return {
        "summary": result.summary,
        "reports": [asdict(report) for report in result.reports],
    }