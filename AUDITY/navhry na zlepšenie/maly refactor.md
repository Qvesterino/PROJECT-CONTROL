GOAL:
Refaktoruj PROJECT CONTROL z technického toolu na user-facing diagnostický CLI nástroj.

Zameraj sa na:

* jednoduché, zrozumiteľné názvy
* stabilné analyzery (ripgrep-based)
* čistý, konzistentný output
* žiadne experimentálne alebo nedokončené features

---

CORE PRINCÍPY:

* každá commanda = odpoveď na konkrétnu otázku
* žiadne print debugy
* všetko vracia structured data → render layer rieši output
* ripgrep je jediný search engine (cez helper funkciu)
* minimalizuj počet features (quality > quantity)

---

CLI REDESIGN:

Staré:

* pc ghost
* orphan_detector
* misc analyzers

Nové:

pc dead        # Dead Code Radar
pc unused      # Unused System Scan
pc patterns    # Suspicious Patterns
pc search      # Smart Search

---

COMMAND DEFINITIONS:

1. pc dead
   Popis:
   Nájde súbory s nulovým alebo minimálnym usage.

Logika:

* pre každý file:

  * použi rg na vyhľadanie jeho názvu v projekte
  * ak count <= 1 → orphan candidate
* voliteľne:

  * low usage threshold (napr. <= 2)

Output (structured):
{
"high": [orphan_files],
"medium": [low_usage_files],
"stats": {
"total_files": int,
"dead_files": int
}
}

---

2. pc unused
   Popis:
   Nájde systémy, ktoré existujú, ale nie sú používané.

Heuristika:

* file name obsahuje:

  * System
  * Manager
  * Controller
* a zároveň:

  * rg -L "SystemName" → žiadny usage

Output:
{
"unused_systems": [paths],
"stats": {...}
}

---

3. pc patterns
   Popis:
   Detekcia podozrivých / zakázaných patternov.

Zdroj:

* .project-control/patterns.yaml

Príklad:
patterns:
legacy_metrics:
- energy
- clarity
- instability

Logika:

* rg multi-pattern (-e)
* collect matches

Output:
{
"pattern_name": {
"matches": [
{ "file": str, "line": int, "text": str }
]
}
}

---

4. pc search
   Popis:
   Power-user search.

Features:

* pattern exists
* pattern NOT exists (invert)
* file-only mode (-l)
* JSON parsing

Input args:
--pattern "string"
--not
--files-only

Output:
{
"matches": [...]
}

---

RIPGREP LAYER:

Vytvor helper:

run_rg(query: list[str], flags: list[str]) -> list[dict]

* vždy používaj:
  --json
* parse output do:
  {
  "file": str,
  "line": int,
  "text": str
  }

Podpora:

* multi-pattern (-e)
* invert (-L)
* file-only (-l)

---

OUTPUT RENDERING:

Oddel render layer:

render_dead(result)
render_unused(result)
render_patterns(result)

Príklad CLI output:

Dead Code Radar:

HIGH (Orphan Files): 12

* OldRenderer.js
* TempFX.js

MEDIUM (Low Usage): 8

* DebugHelper.js

---

NAMING RULES:

Nepoužívaj:

* orphan
* ghost
* detector

Používaj:

* radar
* scan
* patterns
* search

---

NON-GOALS:

* žiadne AST parsing
* žiadne komplexné graph systémy
* žiadne UI frameworky
* žiadne experimentálne analyzery

---

SUCCESS CRITERIA:

* každá commanda musí byť pochopiteľná bez dokumentácie
* output musí byť okamžite použiteľný
* tool musí byť stabilný na veľkých repo
* minimálne false positives

---

OPTIONAL (LOW PRIORITY):

* pc inspect (interactive menu wrapper)
* ripgrep version check (rg --version vs latest)

---

IMPLEMENTATION STYLE:

* čisté moduly (core/, analysis/, render/)
* žiadne side effects v analyzeroch
* CLI iba orchestruje

---

END
