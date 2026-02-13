# Input:
- context: (čo už funguje)
- goal: (čo chceme)
- constraints: (čo sa nesmie)
- output: (čo očakávame)
____________________________
*pc.py*  ---> to je naš orchestrator
____________________________
## scanner.py
- context: ty máš PROJECT CONTROL CLI a scan logiku v pc.py
- goal: presunúť funkciu _scan_ do core/scanner.py
- constraints:
  - nechceme žiadne print() vnútri funkcie
  - funkcia nemá robiť export snapshot, len vrátiť snapshot dict
  - ignorovať patterns ignore_dirs a extensions
- output: python code modul scanner.py so signatúrou:

def scan_project(project_root: str, ignore_dirs: list[str], extensions: list[str]) -> dict
_______________________________________
## patterns_loader.py
- context: patterns.yaml lives in project root .project-control
- goal: vytvoriť modul config/patterns_loader.py
- constraints:
  - načítanie configu musí brať do úvahy chyby / missing file
  - funkcia get_patterns() musí vracať dict s defaults
- output: code modul patterns_loader.py
_______________________________________________
## ghost.py (v2 Orchestrator)
- context: analyzers will live in analysis/
- goal: ghost.py to combine detectors
- constraints:
  - do not write markdown
  - call each analyzer and build structured result
- output: core/ghost.py
_____________________________________________
## orphan_detector.py
- context: snapshot files array, patterns entrypoints
- goal: detect files with no import patterns
- constraints:
  - use run_rg helper from utils/fs_helpers
  - return list of paths that match orphan criteria
- output: analysis/orphan_detector.py
_____________________________________________
## legacy_detector.py
- context: snapshot + patterns
- goal: detect legacy files by filename patterns
- constraints:
  - legacy patterns come from patterns.yaml
- output: analysis/legacy_detector.py
_________________________________________
## duplicate_detector.py
- context: duplicate patterns
- goal: find duplicates based on patterns (e.g., repeated names)
- constraints:
  - use simple heuristic (same base name, different folder)
- output: analysis/duplicate_detector.py
___________________________________________
## session_detector.py
- context: some session files are named like SessionXX_*
- goal: detect all session-based experimental files
- constraints:
  - should be case-insensitive
- output: analysis/session_detector.py
_____________________________________________
## markdown_renderer.py
- context: structured ghost result dict
- goal: generate a clean markdown file
- constraints:
  - group sections
  - no print()
- output: core/markdown_renderer.py
____________________________________________
## writer.py
- načítať patterns
- pre každý writer pattern spustiť rg
- vrátiť štruktúrované dáta (nie markdown) 
**žiadne print(), žiadne zapisovanie súborov, žiadne markdown**
____________________________________________
## snapshot.py
- načíta snapshot.json
- vráti zoznam súborov
**nič netlačí, nič neukladá**