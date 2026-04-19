# FINAL AUDIT V1 — Project Control

**Dátum:** 2026-04-19  
**Commit:** `b62b1af`  
**Testy:** 11/11 ✅  
**Rozsah:** Celá aktívna codebase (experimental/ vylúčený)

---

## 📊 CELKOVÉ HODNOTENIE

| Metrika | Hodnota |
|---------|---------|
| Aktívne moduly | 42 |
| Dead code moduly | 6 |
| Bugy | 1 (nízka) |
| Architektonické problémy | 0 kritických |
| Inconsistencies | 3 |
| Test coverage | čiastočná |
| **Celkový stav** | **STABILNÝ, s drobnými problémami** |

---

## ✅ ČO JE V PORIADKU

### Core systém (výborný)
- **`ghost.py`** — čistá funkcia, žiadne side effects, canonical contract ✅
- **`scanner.py`** — deterministický, SHA256, content deduplication ✅
- **`snapshot_service.py`** — čisté I/O, dobré error handling ✅
- **`content_store.py`** — filesystem-independent access, dobrá abstrakcia ✅
- **`snapshot_validator.py`** — prísna validácia, inline sanity checky ✅
- **`embedding_service.py`** — caching, chunking, averaging, graceful fallback ✅

### Graph engine (výborný)
- **`builder.py`** — deterministický, hash-based caching, extractor registry ✅
- **`ensure.py`** — freshness check so snapshot/config hash comparison ✅
- **`metrics.py`** — Tarjan SCC, fan-in/out, depth, cycles ✅
- **`trace.py`** — inbound/outbound, line-level context, cycle detection ✅
- **`artifacts.py`** — čistý output writing ✅
- **`config/graph_config.py`** — frozen dataclass, hash function, YAML merge ✅

### Analysis (dobrý)
- **`orphan_detector.py`** — ripgrep-based, entrypoint filtering ✅
- **`legacy_detector.py`** — pattern matching, configurable ✅
- **`session_detector.py`** — jednoduchý, funkčný ✅
- **`semantic_detector.py`** — embedding-based s graceful fallback ✅

### CLI (dobrý)
- **`pc.py`** — čistý argument parsing ✅
- **`router.py`** — prehľadný dispatch ✅
- **`graph_cmd.py`** — caching, error handling ✅
- **`menu.py`** — interaktívne menu ✅

---

## 🐛 BUGY

### BUG 1: `duplicate_detector.py` — Windows path issue (NÍZKA)

**Súbor:** `project_control/analysis/duplicate_detector.py:30`

```python
stem = path.rsplit("/", 1)[-1].lower()
```

**Problém:** Na Windows sú cesty s `\`, nie `/`. `rsplit("/", 1)` nevráti správny názov súboru.

**Dopad:** Na Windows môže duplicate detector nesprávne zoskupovať súbory.

**Fix:**
```python
stem = Path(path).name.lower()
```

---

## 🧹 DEAD CODE (moduly ktoré nie sú nikde importované)

### DC-1: `core/snapshot.py` — DUPLIKÁT `snapshot_service.py`

Má `load_snapshot()` a `get_snapshot_files()` — identické funkcie ako `snapshot_service.py`. Nie je importovaný nikde.

**Odporúčanie:** VYMAZAŤ

### DC-2: `core/dto.py` — Deep ghost DTO

`GhostAnalysisResult` očakáva `graph`, `metrics`, `anomalies`, `drift`, `trend` — to sú deep ghost polia. Canonical ghost core to nepoužíva. Nie je importovaný nikde.

**Odporúčanie:** VYMAZAŤ

### DC-3: `core/result_dto.py` — Deep ghost DTO builder

`build_ui_result_dto()` a `validate_ui_result_dto()` — builderi pre deep ghost DTO. Neboli importované nikde po vymazaní `ghost_workflow.py`.

**Odporúčanie:** VYMAZAŤ

### DC-4: `core/drift_history_store.py` — Deep ghost persistence

Bounded drift history persistence. Bol používaný len v `ghost_workflow.py` ktorý bol vymazaný. Nie je importovaný nikde.

**Odporúčanie:** PRESUNÚŤ do `experimental/ghost_deep/` (má hodnotu pre budúcnosť)

### DC-5: `analysis/python_import_graph_detector.py` — Standalone analyzer

`detect_python_import_graph_orphans()` — nie je volaný z ghost core ani z CLI. Samostatný modul bez napojenia.

**Odporúčanie:** PRESUNÚŤ do `experimental/ghost_deep/` (má hodnotu pre budúcnosť)

### DC-6: `core/exit_codes.py` — Nepoužívané konštanty

`EXIT_CONTRACT_ERROR = 3` a `EXIT_LAYER_VIOLATION = 4` — definované ale nikde nepoužívané.

**Odporúčanie:** VYMAZAŤ tieto dva riadky (ponechať `EXIT_OK` a `EXIT_VALIDATION_ERROR`)

---

## ⚠️ INCONSISTENCIES

### INC-1: `load_patterns()` — typ argumentu

**Súbor:** `config/patterns_loader.py:27`

```python
def load_patterns(project_root: str) -> Dict[str, Any]:
```

Typ hint je `str`, ale volajúci často prechádzajú `Path` objekt:
- `ghost_service.py` — `load_patterns(project_root)` kde `project_root` je `Path`
- `analyze_service.py` — `load_patterns(project_root)` kde `project_root` je `Path`
- `scan_service.py` — `load_patterns(project_root)` kde `project_root` je `Path`

**Dopad:** Funguje vďaka `Path(project_root)` vo funkcii, ale type checkery by vyhodili warning.

**Fix:** Zmeniť typ hint na `str | Path` alebo `Any`.

### INC-2: `session_detector.py` — chýba `from __future__ import annotations`

Všetky ostatné moduly majú tento import, `session_detector.py` nemá.

**Dopad:** Žiadny pre runtime, ale inconsistent s ostatnými modulmi.

**Fix:** Pridať `from __future__ import annotations`.

### INC-3: `self_architecture_validator.py` — zastaralé layer definície

```python
LAYER_ORDER = ["analysis", "usecases", "core", "persistence", "cli"]
ALLOWED_DEPS = {
    "usecases": {"analysis"},
    "persistence": {"analysis", "core"},
    ...
}
```

`usecases` layer bol redukovaný (ghost_workflow, ghost_usecase vymazané), `persistence` layer je minimálny.

**Dopad:** Self-validation môže hlásiť falošné violations alebo prehliadať reálne.

**Fix:** Aktualizovať `LAYER_ORDER` a `ALLOWED_DEPS` na aktuálnu architektúru.

### INC-4: `layer_boundary_validator.py` — zastaralé FORBIDDEN_PREFIXES

```python
FORBIDDEN_PREFIXES = (
    "project_control.core",
    "project_control.persistence",
    "project_control.cli",
    "project_control.usecases",  # ← vymazané
    "project_control.pc",
)
```

**Fix:** Odstrániť `"project_control.usecases"` zo zoznamu.

---

## 🏗️ ARCHITEKTÚRA — AKTUÁLNY STAV

```
pc.py (CLI entrypoint)
  └── cli/router.py (dispatch)
        ├── cli/graph_cmd.py → graph/builder.py → graph/metrics.py → graph/trace.py
        ├── cli/menu.py → services/* → ui/state.py
        ├── core/ghost_service.py → core/ghost.py → analysis/*_detector.py
        ├── core/snapshot_service.py → core/scanner.py
        ├── core/writers.py
        └── embedding/* (optional, lazy import)

config/
  ├── patterns_loader.py → patterns.yaml
  └── graph_config.py → graph.config.yaml

utils/
  └── fs_helpers.py → ripgrep wrapper
```

**Hodnotenie:** Architektúra je čistá a konzistentná. Žiadne cyklické závislosti. Žiadne cross-layer violations (okrem dead code).

---

## 📋 ODPORÚČANIA (podľa priority)

### 🔴 PRIORITY 1: Cleanup (30 min, bez rizika)

| # | Akcia | Súbor | Dôvod |
|---|-------|-------|-------|
| 1 | VYMAZAŤ | `core/snapshot.py` | Duplikát `snapshot_service.py` |
| 2 | VYMAZAŤ | `core/dto.py` | Dead code (deep ghost DTO) |
| 3 | VYMAZAŤ | `core/result_dto.py` | Dead code (deep ghost DTO builder) |
| 4 | PRESUNÚŤ | `core/drift_history_store.py` → `experimental/ghost_deep/` | Dead code ale má hodnotu |
| 5 | PRESUNÚŤ | `analysis/python_import_graph_detector.py` → `experimental/ghost_deep/` | Dead code ale má hodnotu |
| 6 | FIX | `analysis/duplicate_detector.py:30` | Windows path bug |
| 7 | CLEANUP | `core/exit_codes.py` | Odstrániť nepoužívané konštanty |

### 🟠 PRIORITY 2: Inconsistencies (15 min, bez rizika)

| # | Akcia | Súbor | Dôvod |
|---|-------|-------|-------|
| 8 | FIX | `config/patterns_loader.py:27` | Type hint `str` → `str \| Path` |
| 9 | FIX | `analysis/session_detector.py` | Pridať `from __future__ import annotations` |
| 10 | UPDATE | `analysis/self_architecture_validator.py` | Aktualizovať LAYER_ORDER |
| 11 | UPDATE | `analysis/layer_boundary_validator.py` | Odstrániť `usecases` z FORBIDDEN_PREFIXES |

### 🟡 PRIORITY 3: Test coverage (1-2 hod)

| # | Akcia | Dôvod |
|---|-------|-------|
| 12 | Pridať testy pre `orphan_detector` | Kľúčový detector, žiadne testy |
| 13 | Pridať testy pre `duplicate_detector` | Bug fix potrebný, žiadne testy |
| 14 | Pridať integration test | scan → ghost → graph build → report |
| 15 | Pridať test pre `duplicate_detector` Windows path | Regresný test pre bug fix |

### 🔵 PRIORITY 4: Budúcnosť

| # | Akcia | Dôvod |
|---|-------|-------|
| 16 | Pridať `.gitignore` do `pc init` | Nový user nemá .gitignore |
| 17 | Optimalizovať `orphan_detector` | 3 ripgrep calls per file → 1 combined |
| 18 | Pridať `pc graph export` | DOT/Mermaid výstup z nového grafu |

---

## 📊 MODUL SUMMARY

| Modul | Stav | Dead code | Bugy | Testy |
|-------|------|-----------|------|-------|
| `core/ghost.py` | ✅ Nový canonical | Nie | Nie | ✅ 3 testy |
| `core/scanner.py` | ✅ Stabilný | Nie | Nie | Nie |
| `core/snapshot_service.py` | ✅ Stabilný | Nie | Nie | Nie |
| `core/content_store.py` | ✅ Stabilný | Nie | Nie | Nie |
| `core/snapshot_validator.py` | ✅ Stabilný | Nie | Nie | Inline |
| `core/ghost_service.py` | ✅ Nový | Nie | Nie | Nie |
| `core/markdown_renderer.py` | ✅ Nový | Nie | Nie | Nie |
| `core/embedding_service.py` | ✅ Stabilný | Nie | Nie | Nie |
| `core/writers.py` | ✅ Stabilný | Nie | Nie | Nie |
| `core/import_parser.py` | ✅ Stabilný | Nie | Nie | Nie |
| `core/exit_codes.py` | ✅ Stabilný | Čiastočný | Nie | Nie |
| `core/snapshot.py` | ❌ Dead | Áno | Nie | Nie |
| `core/dto.py` | ❌ Dead | Áno | Nie | Nie |
| `core/result_dto.py` | ❌ Dead | Áno | Nie | Nie |
| `core/drift_history_store.py` | ❌ Dead | Áno | Nie | Nie |
| `core/debug.py` | ✅ OK | Nie | Nie | Nie |
| `analysis/orphan_detector.py` | ✅ Stabilný | Nie | Nie | Nie |
| `analysis/legacy_detector.py` | ✅ Stabilný | Nie | Nie | Nie |
| `analysis/session_detector.py` | ✅ Stabilný | Nie | Nie | Nie |
| `analysis/duplicate_detector.py` | ⚠️ Bug | Nie | Áno (Windows) | Nie |
| `analysis/semantic_detector.py` | ✅ Fixnutý | Nie | Nie | Nie |
| `analysis/layer_boundary_validator.py` | ⚠️ Stale | Nie | Nie | Nie |
| `analysis/self_architecture_validator.py` | ⚠️ Stale | Nie | Nie | Nie |
| `analysis/python_import_graph_detector.py` | ❌ Dead | Áno | Nie | Nie |
| `graph/builder.py` | ✅ Výborný | Nie | Nie | ✅ |
| `graph/metrics.py` | ✅ Výborný | Nie | Nie | ✅ |
| `graph/trace.py` | ✅ Výborný | Nie | Nie | ✅ |
| `graph/ensure.py` | ✅ Výborný | Nie | Nie | Nie |
| `graph/artifacts.py` | ✅ Stabilný | Nie | Nie | Nie |
| `graph/resolver.py` | ✅ Stabilný | Nie | Nie | ✅ |
| `graph/extractors/*` | ✅ Stabilný | Nie | Nie | ✅ |
| `cli/router.py` | ✅ Nový | Nie | Nie | Nie |
| `cli/graph_cmd.py` | ✅ Stabilný | Nie | Nie | Nie |
| `cli/menu.py` | ✅ Stabilný | Nie | Nie | Nie |
| `config/patterns_loader.py` | ⚠️ Type hint | Nie | Nie | Nie |
| `config/graph_config.py` | ✅ Výborný | Nie | Nie | Nie |
| `services/*` | ✅ Stabilný | Nie | Nie | Nie |
| `embedding/*` | ✅ Stabilný | Nie | Nie | Nie |
| `ui.py` | ✅ Nový | Nie | Nie | Nie |
| `ui/state.py` | ✅ Stabilný | Nie | Nie | Nie |
| `utils/fs_helpers.py` | ✅ Stabilný | Nie | Nie | Nie |

---

## 🎯 ZÁVER

**Projekt je v stabilnom stave.** Hlavné problémy sú:

1. **Dead code** — 6 modulov ktoré nie sú napojené (ľahko odstrániteľné)
2. **1 bug** — Windows path v duplicate_detector (triviálny fix)
3. **Inconsistencies** — type hinty, zastaralé validator definície

Žiadne kritické problémy. Žiadne architektonické violationy. Ghost core je čistý. Graph engine je výborný. CLI je konzistentné.

**Po aplikovaní Priority 1 a 2 odporúčaní bude projekt v produktion-ready stave.**
