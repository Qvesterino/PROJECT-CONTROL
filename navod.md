

## ✅ STEP 0 – Over si základy

V termináli napíš:

*overenie verzie pythonu* :==>     `python --version`

*overenie verzie ripgrepu* :==>    `.\rg.exe --version`

*scan* :==>      `python pc.py scan`
*ghost* :==>     `python pc.py ghost`

*scan ATOMA* :==>     `python "D:\PROJECT_CONTROL\pc.py" scan`

*ghost ATOMA* :==>     `python "D:\PROJECT_CONTROL\pc.py" ghost`

pc.py
   ↓
core/ghost.py
   ↓
analysis/*
   ↓
structured result
   ↓
exports/ghost_candidates.md


## ✅ STEP 1 – Choď do priečinka projektu

*V termináli:*  -->   cd D:\PROJECT CONTROL --->  Uisti sa, že tam máš pc.py.

## ✅ STEP 2 – Spusti INIT

`python pc.py init`   --->  *Toto vytvorí:*  ---> .project-control/


## ✅ STEP 3 – Spusti SCAN

`python pc.py scan`


prejde celý priečinok
      ↓
vytvorí snapshot.json
      ↓
vypíše počet súborov
      ↓
Ak vidíš: --> Scan complete. XXX files indexed. → **funguje.**

## ✅ STEP 4 – Generuj checklist
`python pc.py checklist`
      ↓
Potom otvor:
      ↓
.project-control/exports/checklist.md
      ↓
**uvidíš prvý výstup.**

## ✅ STEP 5 – Otestuj find
`python pc.py find pc`  <--> alebo <-->`python pc.py find argparse`
      ↓
*Pozri* .project-control/exports/find_pc.md

## ✅ STEP 6 – Otestuj writers
`python pc.py writers`
      ↓
Otvor:

writers_report.md

🧠 Ako to funguje (ultra jednoduché vysvetlenie)

Keď napíšeš:

python pc.py scan


Python:

Načíta tento súbor

Prečíta argument “scan”

Zavolá funkciu cmd_scan

Tá:

prejde priečinok

uloží info do JSON

To je celé.

Žiadna mágia.
Žiadne AI.
Len skript, ktorý číta súbory a zapisuje reporty.

🧠 Prečo si videl help správu na screenshote

Lebo si spustil:

python pc.py


Bez príkazu.

Správne musíš dať:

python pc.py init


alebo

python pc.py scan

💪 Najdôležitejšie

Ty teraz nerobíš Python projekt.

Ty:

buduješ CLI nástroj

pracuješ s filesystemom

voláš externý nástroj (ripgrep)

generuješ reporty

Toto je real engineering.