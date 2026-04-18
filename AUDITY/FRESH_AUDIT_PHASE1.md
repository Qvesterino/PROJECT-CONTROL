# FRESH AUDIT — Phase 1 Stav (po reverte)

**Dátum:** 2026-04-18  
**Commit:** `3901030` (phase 1 dokončena) + `6b9c154` (záloha auditu)  
**Testy:** 9/9 ✅ prechádzajú

---

## 📋 ČO FUNGUJE (overené)

| Príkaz | Stav | Poznámka |
|--------|------|----------|
| `pc init` | ✅ | Vytvorí .project-control, patterns.yaml, status.yaml |
| `pc scan` | ✅ | Rekurzívny scan, SHA256, ContentStore, snapshot.json |
| `pc ghost` | ✅ | Shallow detektory: orphan, legacy, session, duplicate |
| `pc graph build` | ✅ | Nový graph builder s Python+JS/TS extractormi |
| `pc graph report` | ✅ | Používa cache (Phase1 fix), rýchly opakovaný beh |
| `pc graph trace <target>` | ✅ | Inbound/outbound trace s line-level kontextom |
| `pc ui` | ✅ | Interaktívne menu |
| `pc embed build/search` | ✅ | Vyžaduje Ollama + optional deps |
| `pc find <symbol>` | ✅ | Ripgrep search |
| `pc writers` | ✅ | Writers analysis |
| `pc checklist` | ✅ | Generuje checklist.md |

## 🐛 BUGY V AKTUÁLNOM STAVE

### Bug 1: `_is_code_file` v semantic_detector.py (NÍZKA PRIORITA)

**Súbor:** `project_control/analysis/semantic_detector.py:21-22`

```python
ext = path.rsplit(".", 1)[-1].lower()  # → "py", "js", "ts"
return ext in {".js", ".ts", ".jsx", ".tsx", ".py", ".mjs", ".cjs"}  # ← s bodkou!
```

**Dopad:** Semantic detector nikdy nespracuje žiadny kódový súbor. Ale keďže semantic detector vyžaduje Ollama (ktoré beží ako externý server), tento bug sa prejaví až keď embedding funguje.

**Fix:** Odstrániť bodky z množiny: `{".js", ...}` → `{"js", ...}`

### Bug 2: Dead legacy kód (NÍZKA PRIORITA)

Nasledujúce súbory **nie sú importované** nikde v aktívnom kóde:

```
analysis/import_graph_detector.py     ← nikde neimportovaný
analysis/python_import_graph_engine.py ← len z import_graph_detector
analysis/js_import_graph_engine.py     ← len z import_graph_detector
analysis/import_graph_engine.py        ← len z horeuvedených
analysis/graph_anomaly.py              ← len z import_graph_detector
analysis/graph_drift.py                ← len z import_graph_detector
analysis/graph_metrics.py              ← len z import_graph_detector
analysis/entrypoint_policy.py          ← len z import_graph_detector
analysis/graph_exporter.py             ← nikde neimportovaný
analysis/tree_renderer.py              ← nikde neimportovaný
```

**Jediný aktívny legacy import:** `graph_trend.py` → `ghost_workflow.py` (používa sa pre deep trend analýzu, ktorá je momentálne vypnutá).

**Dopad:** Žiadny — dead code neovplyvňuje beh. Ale zavadzuje v codebase.

## 🏗️ ARCHITEKTÚRA (aktuálny stav)

```
pc.py (CLI entrypoint)
  └── cli/router.py (dispatch)
        ├── cli/graph_cmd.py (graph build/report/trace)
        ├── cli/menu.py (UI)
        ├── core/ghost_service.py → usecases/ghost_workflow.py → usecases/ghost_usecase.py → core/ghost.py
        │                                                     └── analysis/graph_trend.py (legacy, deep only)
        ├── core/snapshot_service.py
        ├── core/writers.py
        └── embedding/ (optional, needs Ollama)

graph/ (NOVÝ systém - aktívny)
  ├── builder.py
  ├── metrics.py
  ├── trace.py
  ├── artifacts.py
  └── extractors/ (python_ast, js_ts)

analysis/ (detektory - aktívne)
  ├── orphan_detector.py    ← ghost.py volá analyze()
  ├── legacy_detector.py    ← ghost.py volá analyze()
  ├── session_detector.py   ← ghost.py volá analyze()
  ├── duplicate_detector.py ← ghost.py volá analyze()
  ├── semantic_detector.py  ← ghost.py volá analyze() (needs Ollama)
  ├── layer_boundary_validator.py
  ├── self_architecture_validator.py
  └── [11 legacy súborov - dead code]
```

## ✅ ČO JE NA TOM PROJEKTE DOBRÉ

1. **Deterministický snapshot systém** — SHA256, ContentStore, deduplikácia
2. **Nový graph builder** — extractor registry, caching, rich edges, Tarjan SCC
3. **Shallow ghost detektory** — jednoduché, funkčné, rozšíriteľné
4. **CLI je kompletné** — všetky príkazy fungujú
5. **UI mód** — interaktívne menu
6. **Embedding systém** — architektonicky hotový, len potrebuje externý Ollama

## 🎯 ODPORÚČANÝ PLÁN — "PHASE 2: PRODUKČNÁ KVALITA"

### Princíp: **Každý krok musí byť commitovateľný a testovateľný samostatne.**

---

### STEP 1: Cleanup (30 min, bez rizika)

**Cieľ:** Odstrániť dead code a bugy, pridať .gitignore

1. **Fix `_is_code_file` bug** — odstrániť bodky z množiny
2. **Odstrániť 10 dead legacy súborov** z `analysis/`
3. **Pridať `.gitignore`** — `__pycache__/`, `.project-control/`, `*.egg-info/`, `.venv/`
4. **Commit:** "cleanup: remove dead legacy code, fix semantic detector bug"

### STEP 2: Test Coverage (1-2 hod)

**Cieľ:** Pridať testy pre ghost detektory a integration test

1. **`tests/test_ghost_detectors.py`** — testy pre orphan, legacy, session, duplicate detektory
2. **`tests/test_integration.py`** — end-to-end test: scan → ghost → graph build → graph report
3. **Commit:** "tests: add ghost detector tests and integration test"

### STEP 3: Rozhodnutie o Deep Ghost (1 hod)

**Cieľ:** Rozhodnúť čo s deep ghost funkcionality

**Možnosti:**
- **A: Odstrániť** — vymazať `graph_trend.py`, `ghost_workflow.py` deep logiku, zjednodušiť
- **B: Integrovať** — prepojiť deep ghost s novým graph builderom (anomaly detection, drift, trend z nového grafu)
- **C: Nechať** — ponechať ako-je, deep mode je deaktivovaný ale kód existuje

**Odporúčam Možnosť B** — pretože:
- Nový graph builder už má metrics, cycles, orphans — anomaly detection by bolo prirodzené rozšírenie
- Drift tracking má zmysel (porovnať 2 snapshoty)
- Trend analysis má zmysel (sledovať vývoj v čase)
- Ale: implementovať nad NOVÝM graph systémom, nie legacy

### STEP 4: Feature Completion (podľa potreby)

Možné rozšírenia:
- Graph anomaly detection (god modules, dead clusters) nad novým graph builderom
- Graph drift detection (porovnanie 2 grafových snapshotov)
- Graph export (DOT/Mermaid formát z nového grafu)
- Lepší graph report (viac detailov, vizualizácia)

---

## 📊 ZHRNUTIE

| Metrika | Hodnota |
|---------|---------|
| Testy prechádzajúce | 9/9 ✅ |
| CLI príkazy funkčné | 11/11 ✅ |
| Dead code súbory | 10 |
| Bugy (nízka priorita) | 1 |
| Architektonické problémy | 0 kritických |
| Celkový stav | **STABILNÝ, PRIPRAVENÝ NA PHASE 2** |

Projekt je v **dobrom stave**. Phase 1 urobila svoju prácu — systém je stabilný a deterministický. Phase 2 by mala byť **opatrná a inkrementálna** — žiadne veľké refaktoringy, len cielené vylepšenia.
