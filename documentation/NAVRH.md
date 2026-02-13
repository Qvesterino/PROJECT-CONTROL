PROJECT CONTROL v1: cieľ a pravidlá

Cieľ v1: „Folder → Dashboard → Akčný výstup“
Nie IDE. Nie nový editor. Nie ďalší “AI buddy”.
Jedna appka, ktorá urobí projekt akčným.

Základné pravidlá:

Local-first (žiadny cloud nutný)

Deterministické (to isté vstupy → to isté výstupy)

Explainable (každý výsledok má “prečo”)

Non-destructive (nič nemaže; iba generuje reporty a návrhy)

—

Architektúra v1: moduly

Scanner (File System Snapshot)

načíta strom priečinkov

zistí metadáta: veľkosť, typ, modified time

vytvorí “snapshot” (JSON alebo SQLite)

Výstup:

file_tree.txt (ľudský)

snapshot.json / project.db (strojový)

Indexer (ripgrep + základné parsovanie)

spúšťa ripgrep pre:

symbol usage (imports, requires, “new X()”, “setupX”, “enableX”)

call-site map (kde sa inicializuje čo)

postaví jednoduché mapy:

file → referenced_by[]

symbol → occurrences[]

entrypoints (main.js, index.ts, app.ts…)

Poznámka: nepotrebuješ plný AST parser v1. Stačí heuristika + rg. AST je v2.

Checklist Engine (akčný workflow)
Toto je tvoja killer feature.

generuje checklist.md (Markdown task list)

umožní “tagovať” veci:

CORE
LEGACY
GHOST
DISABLED
REVIEW

V1 to môže byť jednoduchý súbor:

.project-control/status.yaml
kde si odškrtávaš a taguješ.

Reports (1 klik = kontrola)
Generuje 3 reporty, ktoré reálne používaš:

A) “What’s big?”

top 20 largest files

top 20 most edited recently

B) “What’s probably ghosting?”

súbory, ktoré nikto nereferencuje (podľa indexu)

duplicity názvov (NodeVisualStateBinder_v2, _v3, _legacy…)

C) “Where are the writers?”

pre vybrané kľúčové parametre (scale/emissive/opacity/position)

vypíše všetky miesta, kde sa mutujú
(na základe hľadania vzorov cez rg + tvoje custom patterns)

UI/CLI (MVP rozhodnutie)
Najrýchlejšie MVP je CLI s pekným outputom + exporty.
UI môže prísť hneď po tom (Tauri/Electron).

V1 odporúčam:

CLI: project-control scan, project-control checklist, project-control find, project-control report

a exporty do .md/.txt

Keď to používaš denne, UI sa robí ľahko.

—

Dátový model v1 (extrémne dôležité)

Projekt bude mať svoj “control folder”:
.project-control/

snapshot.json (alebo project.db)

status.yaml (tvoje tagy, checkboxy)

patterns.yaml (regexy pre “writers”, entrypoints, risky calls)

exports/
checklist.md
report_ghost.md
report_big.md
report_writers.md