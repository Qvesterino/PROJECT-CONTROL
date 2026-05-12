# ARCHITEKTONICKÝ AUDIT PROJECT CONTROL
## Kompletná mapa systému pre debugovanie a údržbu

**Dátum:** 12. máj 2026  
**Verzia:** 1.0  
**Účel:** Rýchla orientácia v kódovej základni pri debugovaní a používaní v iných projektoch

---

## 📋 OBSAH

1. [Architektonický prehľad](#architektonický-prehľad)
2. [Tok dát v systéme](#tok-dát-v-systéme)
3. [Kľúčové komponenty a ich umiestnenie](#kľúčové-komponenty-a-ich-umiestnenie)
4. [Konfiguračný systém](#konfiguračný-systém)
5. [CLI a Command Dispatch](#cli-a-command-dispatch)
6. [Core Layer](#core-layer)
7. [Analysis Layer](#analysis-layer)
8. [Graph Engine](#graph-engine)
9. [Service Layer](#service-layer)
10. [Storage a Persistence](#storage-a-persistence)
11. [Debugovacie stratégie](#debugovacie-stratégie)
12. [Časté problémy a riešenia](#časté-problémy-a-riešenia)
13. [Mapa súborov pre rýchly prístup](#mapa-súborov-pre-rýchly-prístup)

---

## 🏗️ ARCHITEKTONICKÝ PREHLAD

### Vizuálna mapa architektúry

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI LAYER                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ pc.py (CLI entrypoint)                                   │   │
│  │   • build_parser() - argparse konfigurácia               │   │
│  │   • main() - entry point                                 │   │
│  └───────────────────────┬───────────────────────────────────┘   │
│                          │                                        │
│                          ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ cli/router.py (Command Dispatcher)                      │   │
│  │   • dispatch() - smerovanie príkazov                   │   │
│  │   • cmd_*() functions - handlery príkazov               │   │
│  └───────────────────────┬───────────────────────────────────┘   │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                         SERVICE LAYER                             │
│  ┌──────────────────┬──────────────────┬──────────────────┐     │
│  │ scan_service.py  │ ghost_service.py │ graph_service.py │     │
│  │ • run_scan()     │ • run_ghost()    │ • graph_build()  │     │
│  └──────────────────┴──────────────────┴──────────────────┘     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                         CORE LAYER                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ scanner.py (Snapshot System)                             │   │
│  │   • scan_project() - vytvorí snapshot                    │   │
│  └───────────────────────┬───────────────────────────────────┘   │
│                          │                                        │
│                          ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ghost.py (Ghost Analysis Core)                          │   │
│  │   • ghost() - pure function pre ghost analysis          │   │
│  └───────────────────────┬───────────────────────────────────┘   │
│                          │                                        │
│                          ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ content_store.py (Content Deduplication)                │   │
│  │   • ContentStore - prístup k obsahu súborov              │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
           ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│  ANALYSIS LAYER     │         │  GRAPH LAYER        │
│  ┌───────────────┐  │         │  ┌───────────────┐  │
│  │ orphan_      │  │         │  │ builder.py    │  │
│  │ detector.py  │  │         │  │ • build_graph()│  │
│  └───────────────┘  │         │  └───────────────┘  │
│  ┌───────────────┐  │         │  ┌───────────────┐  │
│  │ legacy_      │  │         │  │ metrics.py    │  │
│  │ detector.py  │  │         │  │ • compute_    │  │
│  └───────────────┘  │         │  │   metrics()   │  │
│  ┌───────────────┐  │         │  └───────────────┘  │
│  │ session_     │  │         │  ┌───────────────┐  │
│  │ detector.py  │  │         │  │ trace.py      │  │
│  └───────────────┘  │         │  │ • trace_path()│  │
│  ┌───────────────┐  │         │  └───────────────┘  │
│  │ duplicate_   │  │         └─────────────────────┘
│  │ detector.py  │  │
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │ semantic_    │  │
│  │ detector.py  │  │
│  └───────────────┘  │
└─────────────────────┘
```

### Kľúčové princípy architektúry

1. **Determinizmus** - rovnaký vstup vždy produkuje rovnaký výstup
2. **Pure Functions** - core logika je bez side-effects (napr. `ghost()`)
3. **Layer Separation** - jasná separácia medzi CLI, Service, Core, Analysis
4. **Content Deduplication** - SHA256 hashovanie pre identifikáciu duplicit
5. **Snapshot-based** - všetka analýza pracuje nad snapshotom, nie nad filesystemom

---

## 🔄 TOK DÁT V SYSTÉME

### Typický tok: Scan → Ghost Analysis

```
1. USER RUNS: pc scan
   │
   ├─> pc.py::main()
   │   └─> build_parser() → parse_args()
   │
   ├─> cli/router.py::dispatch()
   │   └─> cmd_scan(args)
   │       └─> run_scan(project_root)
   │           │
   │           └─> config/patterns_loader.py::load_patterns()
   │               └─> načíta .project-control/patterns.yaml
   │
   └─> core/scanner.py::scan_project()
       │
       ├─> Walks directory tree
       ├─> Computes SHA256 hashes
       ├─> Stores content blobs in .project-control/content/
       └─> Creates snapshot.json

2. USER RUNS: pc ghost
   │
   ├─> cli/router.py::dispatch()
   │   └─> cmd_ghost(args)
   │       └─> core/ghost_service.py::run_ghost()
   │           │
   │           ├─> core/snapshot_service.py::load_snapshot()
   │           │   └─> načíta .project-control/snapshot.json
   │           │
   │           ├─> core/content_store.py::ContentStore()
   │           │   └─> inicializuje prístup k .project-control/content/
   │           │
   │           └─> core/ghost.py::ghost(snapshot, patterns, content_store)
   │               │
   │               ├─> analysis/orphan_detector.py::analyze()
   │               ├─> analysis/legacy_detector.py::analyze()
   │               ├─> analysis/session_detector.py::analyze()
   │               ├─> analysis/duplicate_detector.py::analyze()
   │               └─> analysis/semantic_detector.py::analyze()
   │
   └─> core/ghost_service.py::write_ghost_report()
       └─> .project-control/exports/ghost_candidates.md
```

### Tok dát pre Graph Building

```
1. USER RUNS: pc graph build
   │
   ├─> cli/router.py::dispatch()
   │   └─> cli/graph_cmd.py::graph_build()
   │       └─> graph/builder.py::build_graph()
   │           │
   │           ├─> core/snapshot_service.py::load_snapshot()
   │           ├─> graph/extractors/python_ast.py::extract()
   │           ├─> graph/extractors/js_ts.py::extract()
   │           └─> graph/resolver.py::resolve()
   │
   └─> graph/artifacts.py::write_artifacts()
       ├─> .project-control/out/graph.snapshot.json
       ├─> .project-control/out/graph.metrics.json
       └─> .project-control/out/graph.report.md
```

---

## 📍 KĽÚČOVÉ KOMPONENTY A ICH UMIESTNENIE

### 1. CLI Entrypoint

**Súbor:** `project_control/pc.py`
**Účel:** Hlavný vstupný bod CLI aplikácie
**Kľúčové funkcie:**
- `build_parser()` - konfiguruje argparse pre všetky príkazy
- `main()` - entry point, parsuje argumenty a volá dispatch
- `_add_tui_subcommands()` - pridáva TUI subpríkazy
- `_add_ui_verify_subcommand()` - pridáva UI verify subpríkaz

**Debugovanie:** Ak CLI nefunguje:
1. Skontrolujte `build_parser()` - či sú všetky príkazy registrované
2. Skontrolujte `main()` - či sa správne volá `dispatch()`
3. Skontrolujte importy - či sú všetky moduly dostupné

---

### 2. Command Dispatcher

**Súbor:** `project_control/cli/router.py`
**Účel:** Smerovanie príkazov na príslušné handlery
**Kľúčové funkcie:**
- `dispatch(args)` - hlavný switch pre všetky príkazy
- `cmd_*()` functions - handlery pre každý príkaz (napr. `cmd_scan`, `cmd_ghost`)
- `_resolve_project_root()` - rozlíši project root path
- `run_scan()` - spustí scan s konfiguráciou

**Mapovanie príkazov na handlery:**
```python
"init"           → cmd_init()
"scan"           → cmd_scan()
"checklist"      → cmd_checklist()
"ghost"          → cmd_ghost()
"dead"           → cmd_dead()
"unused"         → cmd_unused()
"patterns"       → cmd_patterns()
"search"         → cmd_search()
"artifacts"      → cmd_artifacts()
"audits" → cmd_audit_retention()
"graph build"    → graph_build()
"graph report"   → graph_report()
"graph trace"    → graph_trace()
```

**Debugovanie:** Ak príkaz nefunguje:
1. Skontrolujte `dispatch()` - či je príkaz registrovaný v switchi
2. Skontrolujte `cmd_*()` handler - či má správny import a logiku
3. Skontrolujte `_resolve_project_root()` - či sa nájde správny project root

---

### 3. Snapshot System (Scanner)

**Súbor:** `project_control/core/scanner.py`
**Účel:** Vytvorí deterministický snapshot projektu
**Kľúčové funkcie:**
- `scan_project(project_root, ignore_dirs, extensions)` - hlavná funkcia
- Vracia `Snapshot` TypedDict s:
  - `snapshot_id` - SHA256 hash všetkých súborov
  - `file_count` - počet súborov
  - `files` - list `FileEntry` s metadátami

**Tok práce:**
1. Phase 1: Collect file paths (walk directory tree)
2. Phase 2: Process files with progress bar
   - Read file bytes
   - Compute SHA256 hash
   - Store content blob in `.project-control/content/<sha256>.blob`
   - Create FileEntry with metadata
3. Sort files by path
4. Generate snapshot_id from concatenated paths+hashes

**Dátové štruktúry:**
```python
class FileEntry(TypedDict):
    path: str           # Relatívna cesta (posix formát)
    size: int           # Veľkosť v bytoch
    modified: str       # ISO datetime (UTC)
    sha256: str         # SHA256 hash obsahu

class Snapshot(TypedDict):
    snapshot_version: int
    snapshot_id: str    # Deterministický ID
    file_count: int
    files: List[FileEntry]
```

**Debugovanie:** Ak scan nefunguje:
1. Skontrolujte `ignore_dirs` - či sú správne definované
2. Skontrolujte `extensions` - či sú .py, .js, .ts atď.
3. Skontrolujte `.project-control/content/` - či sa vytvárajú bloby
4. Skontrolujte logy - či nie sú varovania o nečitateľných súboroch

---

### 4. Ghost Analysis Core

**Súbor:** `project_control/core/ghost.py`
**Účel:** Kanonická čistá funkcia pre ghost analysis
**Kľúčové funkcie:**
- `ghost(snapshot, patterns, content_store)` - pure function, žiadne side-effects
- `_run_detector(module, snapshot, patterns, content_store)` - helper pre volanie detectorov
- Vracia dict s presne 5 kľúčmi: `orphans`, `legacy`, `duplicates`, `sessions`, `semantic`

**Dôležité:** Toto je JEDINÝ zdroj pravdy pre ghost analysis. Neobsahuje žiadnu deep/anomaly/drift logiku.

**Tok práce:**
1. Pre každý detector v `analysis/`:
   - Zavolá `module.analyze(snapshot, patterns, content_store)`
   - Vráti list nájdených položiek
2. Sortuje results (orphans by path)
3. Vracia dict s všetkými 5 kategóriami

**Debugovanie:** Ak ghost analysis nefunguje:
1. Skontrolujte `ghost()` - či sú importované všetky detektory
2. Skontrolujte `_run_detector()` - či má modul `analyze()` funkciu
3. Skontrolujte jednotlivé detektory v `analysis/`
4. Skontrolujte `ContentStore` - či je správne inicializovaný

---

### 5. Content Store

**Súbor:** `project_control/core/content_store.py`
**Účel:** Súborovo-nezávislý prístup k obsahu súborov
**Kľúčové funkcie:**
- `ContentStore.__init__(snapshot, snapshot_path)` - inicializácia
- `ContentStore.get_text(path)` - vráti textový obsah súboru
- `ContentStore.get_bytes(path)` - vráti binárny obsah súboru
- `ContentStore.has_file(path)` - overí, či súbor existuje v snapshot-e

**Dôležité:** Nikdy neprečítajte súbor priamo po scane - vždy použite ContentStore!

**Tok práce:**
1. Načíta `snapshot.json`
2. Derivuje content directory: `snapshot_path.parent / "content"`
3. Pre `get_text(path)`:
   - Nájde `FileEntry` v snapshot-e podľa `path`
   - Načíta SHA256 hash
   - Načíta blob z `.project-control/content/<sha256>.blob`
   - Dekóduje na text (UTF-8)

**Debugovanie:** Ak ContentStore nefunguje:
1. Skontrolujte `snapshot.json` - či obsahuje `files` array
2. Skontrolujte `.project-control/content/` - či existujú bloby
3. Skontrolujte path matching - či používate posix paths (forward slashes)
4. Skontrolujte snapshot_path - či ukazuje na správny snapshot.json

---

### 6. Analysis Detectors

**Adresár:** `project_control/analysis/`
**Obsah:** Detektory pre rôzne typy analýz

#### Orphan Detector
**Súbor:** `analysis/orphan_detector.py`
**Funkcia:** `analyze(snapshot, patterns, content_store)`
**Účel:** Nájde súbory, ktoré nie sú referencované žiadnym iným súborom
**Metóda:** Používa ripgrep na vyhľadanie súborových ciest v obsahu iných súborov

#### Legacy Detector
**Súbor:** `analysis/legacy_detector.py`
**Funkcia:** `analyze(snapshot, patterns, content_store)`
**Účel:** Identifikuje súbory zodpovedajúce legacy patternom
**Metóda:** Porovnáva názvy súborov s definovanými patternmi

#### Session Detector
**Súbor:** `analysis/session_detector.py`
**Funkcia:** `analyze(snapshot, patterns, content_store)`
**Účel:** Nájde dočasné/session súbory
**Metóda:** Porovnáva názvy súborov s session patternmi

#### Duplicate Detector
**Súbor:** `analysis/duplicate_detector.py`
**Funkcia:** `analyze(snapshot, patterns, content_store)`
**Účel:** Detekuje súbory s identickými názvami v rôznych cestách
**Metóda:** Groupuje súbory podľa názvu a hlásí duplicity

#### Semantic Detector
**Súbor:** `analysis/semantic_detector.py`
**Funkcia:** `analyze(snapshot, patterns, content_store)`
**Účel:** Používa embedding na nájdenie sémanticky podobných alebo orphan súborov
**Metóda:** Vyžaduje Ollama server a embedding model
**Poznámka:** Voliteľný, vyžaduje `pip install -e ".[embedding]"`

#### Ďalšie detektory:
- `dead_analyzer.py` - Dead Code Radar (nulté alebo minimálne použitie)
- `unused_analyzer.py` - Unused System Scan
- `patterns_analyzer.py` - Suspicious Patterns detekcia
- `search_analyzer.py` - Smart Search pre power-users
- `artifact_detector.py` - Artifact Hygiene Engine
- `audit_retention_detector.py` - Audit Retention Engine

---

### 7. Graph Engine

**Adresár:** `project_control/graph/`
**Účel:** Stavanie a analýza import dependency grafov

#### Graph Builder
**Súbor:** `graph/builder.py`
**Kľúčové funkcie:**
- `build_graph(snapshot, config)` - hlavná funkcia
- Vracia `Graph` dátovú štruktúru s:
  - `nodes` - zoznam súborov
  - `edges` - import závislosti
  - `node_map` - mapping path → node_id

**Tok práce:**
1. Načíta snapshot a graph config
2. Pre každý súbor v snapshot-e:
   - Volá príslušný extractor podľa prípony
   - Extrahuje importy
3. Resolvuje importy na absolútne cesty
4. Builduje graf a metricky
5. Cache-uje results podľa snapshot_hash

#### Graph Metrics
**Súbor:** `graph/metrics.py`
**Kľúčové funkcie:**
- `compute_metrics(graph)` - vypočíta graf metriky
- Vracia metriky: node_count, edge_count, avg_fan_in, avg_fan_out, cycles, depth

#### Graph Trace
**Súbor:** `graph/trace.py`
**Kľúčové funkcie:**
- `trace_path(graph, target, direction, max_depth, max_paths)` - trace dependency paths
- Podporuje inbound/outbound/both directions

#### Extractors
**Adresár:** `graph/extractors/`

**Python AST Extractor**
**Súbor:** `graph/extractors/python_ast.py`
**Funkcia:** `extract(path, content_text)`
**Metóda:** Používa `ast` modul na parsovanie Python importov
**Presnosť:** Vysoká (AST-based)

**JS/TS Regex Extractor**
**Súbor:** `graph/extractors/js_ts.py`
**Funkcia:** `extract(path, content_text)`
**Metóda:** Používa regex na parsovanie JS/TS importov
**Presnosť:** Nižšia (regex-based, ale rýchla)

**Base Extractor Protocol**
**Súbor:** `graph/extractors/base.py`
**Definuje:** `BaseExtractor` protocol s metódou `extract(path, content_text)`

---

### 8. Configuration System

#### Patterns Loader
**Súbor:** `config/patterns_loader.py`
**Kľúčové funkcie:**
- `load_patterns(project_root)` - načíta `.project-control/patterns.yaml`
- `get_scan_extensions(patterns)` - vráti list extensions na scan
- Vracia dict s:
  - `writers` - list writer patterns
  - `entrypoints` - list entrypoint files
  - `ignore_dirs` - list directories na ignorovanie
  - `extensions` - list file extensions na scan
  - `artifacts` - artifact hygiene config
  - `audit_retention` - audit retention config

**Default config:**
```yaml
writers: [scale, emissive, opacity, position]
entrypoints: [main.js, index.ts]
ignore_dirs: [.git, .project-control, node_modules, __pycache__]
extensions: [.py, .js, .ts, .md, .txt]
artifacts:
  older_than_days: 30
  min_score: 8
audit_retention:
  older_than_days: 45
  keep_latest_per_family: 3
```

#### Graph Config
**Súbor:** `config/graph_config.py`
**Kľúčové funkcie:**
- `load_graph_config(project_root)` - načíta `.project-control/graph_config.yaml`
- Vracia dict s:
  - `include_globs` - glob patterns na includovanie
  - `exclude_globs` - glob patterns na excludovanie
  - `entrypoints` - list entrypoint files
  - `alias` - mapping import alias → real path
  - `orphan_allow_patterns` - patterny pre povolené orphans
  - `treat_dynamic_imports_as_edges` - či spracovať dynamic imports
  - `languages` - konfigurácia pre každý jazyk

**Default languages:**
```yaml
languages:
  js_ts:
    enabled: true
    include_exts: [".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"]
  python:
    enabled: false
    include_exts: [".py"]
```

---

### 9. Storage a Persistence

#### Snapshot Service
**Súbor:** `core/snapshot_service.py`
**Kľúčové funkcie:**
- `create_snapshot(project_root, ignore_dirs, extensions)` - vytvorí nový snapshot
- `save_snapshot(snapshot, project_root)` - uloží snapshot do `.project-control/snapshot.json`
- `load_snapshot(project_root)` - načíta snapshot zo súboru
- `validate_snapshot(snapshot)` - overí snapshot integritu

**Umiestnenie:**
- Snapshot metadata: `.project-control/snapshot.json`
- Content blobs: `.project-control/content/<sha256>.blob`

#### Content Store Storage
**Obsah:**
- Deduplikovaný obsah všetkých súborov
- Názvy súborov: SHA256 hash obsahu
- Umožňuje súborovo-nezávislý prístup

#### State Manager
**Súbor:** `persistence/state_manager.py`
**Kľúčové funkcie:**
- `export_state(path, include_metadata)` - exportuje projekt state do súboru
- `import_state(path, merge)` - importuje state zo súboru
- Umožňuje backup/restore konfigurácie

---

### 10. Output a Reports

#### Export Directory
**Umiestnenie:** `.project-control/exports/`
**Obsah:**
- `ghost_candidates.md` - Ghost analysis report
- `ghost_*_tree.txt` - ASCII tree reports pre každú kategóriu
- `artifact_candidates.md` - Artifact hygiene report
- `artifact_candidates.json` - Artifact hygiene data
- `delete_candidates.txt` - Safe-to-delete list pre artifacts
- `audit_retention_candidates.md` - Audit retention report
- `audit_retention_candidates.json` - Audit retention data
- `audit_delete_candidates.txt` - Safe-to-delete list pre audits
- `checklist.md` - Checklist všetkých súborov
- `find_<symbol>.md` - Symbol search results
- `writers_report.md` - Writers analysis report

#### Graph Output Directory
**Umiestnenie:** `.project-control/out/`
**Obsah:**
- `graph.snapshot.json` - Graph structure
- `graph.metrics.json` - Computed metrics
- `graph.report.md` - Generated report
- `graph.trace.txt` - Trace output

---

## 🗂️ MAPA SÚBOROV PRE RÝCHLY PRÍSTUP

### Kedy čo hľadať

#### Chcem pridať nový CLI príkaz:
1. Pridaj subparser v `pc.py::build_parser()`
2. Pridaj handler funkciu v `cli/router.py::cmd_*()`
3. Pridaj case v `cli/router.py::dispatch()`

#### Chcem pridať nový detector:
1. Vytvor `analysis/<name>_detector.py`
2. Implementuj `analyze(snapshot, patterns, content_store) → List[Any]`
3. Importuj v `core/ghost.py` a pridaj do return dictu

#### Chcem pridať nový jazyk do graph engine:
1. Vytvor `graph/extractors/<lang>.py` implementujúci `BaseExtractor`
2. Registruj v `graph/extractors/registry.py`
3. Pridaj resolver v `graph/resolver.py` (ak potrebné)
4. Pridaj do defaults v `config/graph_config.py`

#### Debugujem scan problémy:
1. Skontroluj `core/scanner.py::scan_project()`
2. Skontroluj `.project-control/snapshot.json`
3. Skontroluj `.project-control/content/` blobs
4. Skontroluj `config/patterns_loader.py` extensions

#### Debugujem ghost problémy:
1. Skontroluj `core/ghost.py::ghost()`
2. Skontroluj jednotlivé detektory v `analysis/`
3. Skontroluj `core/content_store.py` prístup k obsahu
4. Skontroluj ripgrep dostupnosť (`rg --version`)

#### Debugujem graph problémy:
1. Skontroluj `graph/builder.py::build_graph()`
2. Skontroluj `graph/extractors/<lang>.py` extraction
3. Skontroluj `graph/resolver.py` resolution
4. Skontroluj `.project-control/out/` outputs

#### Debugujem CLI problémy:
1. Skontroluj `pc.py::build_parser()` argumenty
2. Skontroluj `cli/router.py::dispatch()` routing
3. Skontroluj `cli/router.py::cmd_*()` handler
4. Skontroluj importy v `pc.py` a `cli/router.py`

---

## 🐛 DEBUGOVACIE STRATÉGIE

### 1. Zapnutie logovania

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Alebo cez CLI:
```bash
pc scan --verbose  # Ak je implementované
```

### 2. Kontrola snapshot integrity

```bash
# Skontrolujte či snapshot existuje
cat .project-control/snapshot.json

# Overte file_count
jq '.file_count' .project-control/snapshot.json

# Overte snapshot_id
jq '.snapshot_id' .project-control/snapshot.json
```

### 3. Kontrola content store

```bash
# Overte či existujú bloby
ls .project-control/content/ | wc -l

# Overte či zodpovedá file_count
jq '.file_count' .project-control/snapshot.json
```

### 4. Kontrola ripgrep dostupnosti

```bash
rg --version
# Ak nie je nainštalované:
#   Windows: winget install ripgrep
#   macOS: brew install ripgrep
#   Linux: apt install ripgrep
```

### 5. Kontrola konfigurácie

```bash
# Skontrolujte patterns.yaml
cat .project-control/patterns.yaml

# Skontrolujte graph_config.yaml
cat .project-control/graph_config.yaml
```

### 6. Testovanie jednotlivých komponentov

```python
# Test scanner
from project_control.core.scanner import scan_project
from project_control.config.patterns_loader import load_patterns, get_scan_extensions

patterns = load_patterns(Path("."))
extensions = get_scan_extensions(patterns)
snapshot = scan_project(".", patterns["ignore_dirs"], extensions)

# Test ghost
from project_control.core.ghost import ghost
from project_control.core.content_store import ContentStore

content_store = ContentStore(snapshot, Path(".project-control/snapshot.json"))
result = ghost(snapshot, patterns, content_store)
print(result)
```

---

## ⚠️ ČASTÉ PROBLÉMY A RIEŠENIA

### Problém: "Run 'pc scan' first"

**Príčina:** Snapshot neexistuje alebo je poškodený
**Riešenie:**
```bash
pc scan
```

### Problém: "ripgrep not found"

**Príčina:** ripgrepg nie je nainštalovaný
**Riešenie:**
```bash
# Windows
winget install ripgrep

# macOS
brew install ripgrep

# Linux
apt install ripgrep
```

### Problém: "Embedding dependencies not installed"

**Príčina:** Embedding support nie je nainštalovaný
**Riešenie:**
```bash
pip install -e ".[embedding]"
ollama serve
ollama pull qwen3-embedding:8b
```

### Problém: "FileNotFoundError: snapshot.json"

**Príčina:** Project nie je inicializovaný
**Riešenie:**
```bash
pc init
pc scan
```

### Problém: Ghost analysis nefunguje

**Príčiny:**
1. ContentStore nenájde bloby
2. Detektory nemajú `analyze()` funkciu
3. Ripgrep nie je dostupný

**Riešenie:**
1. Skontrolujte `.project-control/content/` existencia
2. Skontrolujte importy v `core/ghost.py`
3. Spustite `rg --version`

### Problém: Graph build nefunguje

**Príčiny:**
1. Snapshot nie je validný
2. Extractory vrátia prázdne results
3. Resolution zlyhal

**Riešenie:**
1. Spustite `pc scan` pre nový snapshot
2. Skontrolujte `graph/extractors/<lang>.py`
3. Skontrolujte `graph/resolver.py` logiku

### Problém: Windows path issues

**Príčina:** Používate Windows paths (`\`) namiesto posix paths (`/`)
**Riešenie:**
Vždy používajte `Path.as_posix()` pri konverzii paths na strings:
```python
path_str = Path(path).as_posix()
```

---

## 📊 QUICK REFERENCE

### CLI Commands Mapping

| Command | Handler | Core Function | Output |
|---------|---------|---------------|--------|
| `pc init` | `cmd_init` | `ensure_project_initialized()` | `.project-control/` created |
| `pc scan` | `cmd_scan` | `scan_project()` | `snapshot.json` + content blobs |
| `pc ghost` | `cmd_ghost` | `ghost()` | `ghost_candidates.md` |
| `pc dead` | `cmd_dead` | `analyze_dead_code()` | Console output |
| `pc unused` | `cmd_unused` | `analyze_unused_systems()` | Console output |
| `pc patterns` | `cmd_patterns` | `analyze_patterns()` | Console output |
| `pc search` | `cmd_search` | `smart_search()` | Console output |
| `pc artifacts` | `cmd_artifacts` | `run_artifact_hygiene()` | `artifact_candidates.md` |
| `pc audits retention` | `cmd_audit_retention` | `run_audit_retention()` | `audit_retention_candidates.md` |
| `pc graph build` | `graph_build` | `build_graph()` | `graph.snapshot.json` |
| `pc graph report` | `graph_report` | - | `graph.report.md` |
| `pc graph trace` | `graph_trace` | `trace_path()` | `graph.trace.txt` |

### Key Data Structures

```python
# FileEntry (z scanner.py)
{
    "path": "src/main.py",
    "size": 1024,
    "modified": "2024-01-01T12:00:00+00:00",
    "sha256": "abc123..."
}

# Snapshot (z scanner.py)
{
    "snapshot_version": 1,
    "snapshot_id": "def456...",
    "file_count": 100,
    "files": [FileEntry, ...]
}

# Ghost Result (z ghost.py)
{
    "orphans": [...],
    "legacy": [...],
    "duplicates": [...],
    "sessions": [...],
    "semantic": [...]
}

# Graph (z builder.py)
{
    "nodes": [...],
    "edges": [...],
    "node_map": {...},
    "entrypoints": [...]
}
```

### Important Paths

| Path | Purpose |
|------|---------|
| `.project-control/` | Root directory pre všetky Project Control dáta |
| `.project-control/snapshot.json` | Snapshot metadata |
| `.project-control/content/` | Deduplikovaný content blobs |
| `.project-control/patterns.yaml` | Hlavná konfigurácia |
| `.project-control/graph_config.yaml` | Graph konfigurácia |
| `.project-control/exports/` | Exportované reporty |
| `.project-control/out/` | Graph outputs |
| `.project-control/embeddings/` | Embedding cache (optional) |

---

## 🎯 RÝCHLY ŠTART PRE NOVÝ PROJEKT

```bash
# 1. Inicializácia
cd /path/to/project
pc init

# 2. Scan
pc scan

# 3. Ghost analysis
pc ghost

# 4. Graph build
pc graph build

# 5. Report
pc graph report

# 6. Diagnostika
pc dead
pc unused
pc patterns
pc artifacts
pc audits retention

# 7. UI
pc tui    # Terminal UI
pc gui    # Desktop GUI
```

---

## 📝 ZÁVER

Tento auditový dokument poskytuje kompletnú mapu PROJECT CONTROL architektúry. Kľúčové body:

1. **Deterministický snapshot systém** - základ všetkých analýz
2. **Pure functions v core** - `ghost()` je kánonická funkcia bez side-effects
3. **Content Store** - jediný spôsob prístupu k obsahu súborov po scane
4. **Layer separation** - jasné rozlíšenie medzi CLI, Service, Core, Analysis
5. **Comprehensive error handling** - ErrorHandler v `core/error_handler.py`

Pre debugovanie vždy začnite s:
1. Kontrolou snapshot integrity
2. Kontrolou config súborov
3. Kontrolou dependency dostupnosti (ripgrep, Ollama)
4. Logovaním problematickej komponenty

Pre rozšírenie systému:
- Nový príkaz → `pc.py` + `cli/router.py`
- Nový detector → `analysis/<name>_detector.py` + `core/ghost.py`
- Nový jazyk → `graph/extractors/<lang>.py` + `graph/extractors/registry.py`

---

**Dokument vytvorený:** 12. máj 2026  
**Verzia PROJECT_CONTROL:** 0.1.0  
**Autor:** Architectural Audit System