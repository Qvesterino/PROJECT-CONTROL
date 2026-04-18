# PROJECT CONTROL Deep Dive Audit

Datum: 2026-04-18
Auditor: Cursor AI

## Executive Summary

Projekt ma funkcne jadro pre `scan`, zakladny `ghost`, `graph build/report/trace` a jednoduchu menu vrstvu, ale aktualny stav posobi ako rozpracovany refaktor s viacerymi odpojenymi alebo nedotiahnutymi vetvami.

Najdolezitejsie zistenia:

- `ghost` API a testy uz nie su zosuladene. Existuje realne rozbita cesta okolo `deep` analyzy.
- Semanticka analyza je prakticky neaktivna, pretoze filter pripon neprepusti ani `.py`, ani `.js`, ani `.ts` subory.
- Dokumentacia (`MANUAL.md`) popisuje rozsiahle ghost funkcie, ktore live CLI vobec neexponuje.
- V repozitari su paralelne/legacy vrstvy (`ui.py` vs `cli/menu.py`, workflow/usecase vrstvy vs aktualne `core/ghost.py`), co zvysuje riziko dalsich regresii.
- Repo hygiene je slaba: generovane `.project-control` data, `__pycache__` a `egg-info` su sucastou pracovnej stopy a zahlcuju git stav.

Celkovy zaver:

- Stav jadra: `stredne funkcny`
- Stav konzistencie projektu: `slaby`
- Stav dokumentacie vs realita: `vysoke riziko`
- Stav bezpecnosti: `bez kritickej RCE chyby`, ale su pritomne prevadzkove a integracne rizika

## Scope Auditu

Kontrolovane oblasti:

- CLI entrypoint a router
- ghost analyza a detektory
- graph engine a trace/report flow
- scan/snapshot/content store vrstva
- UI/menu vrstva
- testy
- dokumentacia a prevadzkova hygiena repozitara

Pouzite overenia:

- citanie zdrojoveho kodu
- manualne CLI spustenia
- `python -m unittest` na vybranych moduloch

## Potvrdene Funkcne Problemy

### 1. Rozbita vetva `ghost --deep` / nekompatibilne API

Zavaznost: `High`

Pozorovanie:

- `tests/test_ghost_graph_core.py` vola `analyze_ghost(..., deep=True, project_root=...)`
- alias `analyze_ghost` dnes smeruje na `project_control/core/ghost.py::ghost()`
- `ghost()` neprijima argumenty `deep`, `mode`, `compare_snapshot`, `debug`, `project_root`

Potvrdenie:

- `python -m unittest tests.test_ghost_graph_core -q` zlyhal s:
  - `TypeError: ghost() got an unexpected keyword argument 'deep'`

Dopad:

- rozbita kompatibilita medzi testami, usecase vrstvou a realnym jadrom
- silny signal, ze refaktor nebol dokonceny

Odporucanie:

1. Rozhodnut sa, ci `deep ghost` ostava podporovany feature, alebo sa definitivne vyradi.
2. Ak ostava:
   - vratit kompatibilne API do `analyze_ghost()`
   - dopojit `deep` vysledky alebo aspon explicitne vratit `graph_orphans`, `metrics`, `anomalies`
3. Ak sa vyraduje:
   - odstranit stare testy
   - odstranit usecase/workflow vetvy, ktore stale predpokladaju stare DTO
   - vycistit `MANUAL.md`

### 2. Semanticka analyza je prakticky nefunkcna

Zavaznost: `High`

Subor:

- `project_control/analysis/semantic_detector.py`

Problem:

- `_is_code_file()` extrahuje priponu bez bodky (`py`, `ts`, `js`)
- porovnava ju vsak proti mnozine s bodkou (`.py`, `.ts`, `.js`, ...)
- vysledok je, ze vratena hodnota je stale `False`

Potvrdenie:

- manualny runtime check:
  - `_is_code_file('a.py') -> False`
  - `_is_code_file('a.ts') -> False`
  - `_is_code_file('a.js') -> False`
- lokalny `pc ghost` vratil `Semantic: 0`

Dopad:

- semantic detector sa tvari ako feature, ale v praxi neanalyzuje zdrojove subory
- vysledky `ghost` su neuplne a mozu vytvarat falosny pocit pokrytia

Odporucanie:

1. Opravit filter pripon.
2. Pridat jednotkovy test pre `_is_code_file()` a aspon jeden end-to-end test so semantic vetvou.
3. Ak je feature optional, v reporte jasne oznacit, ci bola semantic analyza naozaj spustena alebo preskocena.

### 3. `MANUAL.md` slubuje funkcie, ktore parser ani router nepodporuju

Zavaznost: `High`

Dokumentacia slubuje napr.:

- `pc ghost --deep`
- `pc ghost --stats`
- `pc ghost --tree-only`
- `pc ghost --export-graph`
- `pc ghost --mode`
- `pc ghost --max-*`
- `pc ghost --compare-snapshot`
- `pc ghost --validate-architecture`
- `pc ghost --debug`

Realita:

- `project_control/pc.py` definuje `ghost` bez akychkolvek option flags
- `project_control/cli/router.py` pre `ghost` len zavola `run_ghost(args, PROJECT_DIR)` a vypise pocty
- `python -m project_control.pc --help` tieto volby nepotvrdzuje

Dopad:

- vysoky produktovy a operacny risk
- user sa moze spoliehat na neexistujuce capability
- dokumentacia komplikuje support aj dalsi vyvoj

Odporucanie:

1. Zosuladit dokumentaciu s realnym CLI okamzite.
2. Bud:
   - doplnit parser a implementaciu podla manualu, alebo
   - zredukovat manual na skutocne podporovane funkcie
3. Zaviest test, ktory porovnava CLI help surface s dokumentovanym command setom.

### 4. Workflow/usecase vrstva ma zastarany shape vysledkov

Zavaznost: `Medium-High`

Subory:

- `project_control/usecases/ghost_usecase.py`
- `project_control/usecases/ghost_workflow.py`

Problem:

- usecase/workflow pocita s klucmi ako `session`, `semantic_findings`, `graph_orphans`, `graph`, `metrics`, `anomalies`
- live `core/ghost.py` vracia len:
  - `orphans`
  - `legacy`
  - `duplicates`
  - `sessions`
  - `semantic`

Dopad:

- odpojena architektura
- vyssia pravdepodobnost, ze dalsia zmena rozbije UI alebo integracne flow
- tazsie udrziavat projekt, lebo nie je jasne, ktora vrstva je canonical

Odporucanie:

1. Vybrat jednu canonical result schema.
2. Neaktivne vrstvy bud dopojit, alebo odstranit.
3. Pre vysledky analyzy zaviest centralny datovy kontrakt a kontraktove testy.

## Architektonicke Medzery a Rizika

### 5. Paralelne UI implementacie

Zavaznost: `Medium`

Subory:

- `project_control/cli/menu.py`
- `project_control/ui.py`

Pozorovanie:

- repo obsahuje dve rozdielne textove UI/menu implementacie
- live cesta ide cez `project_control/cli/menu.py`
- `project_control/ui.py` vyzera ako starsia paralelna vetva

Dopad:

- duplikacia logiky
- nejasne, ktora cesta je oficialna
- vyssie riziko, ze fix v jednej vetve sa nedostane do druhej

Odporucanie:

- jednu implementaciu ponechat ako oficialnu, druhu odstranit alebo jasne oznacit ako deprecated

### 6. Duplicitna konfiguracna logika pre graph state

Zavaznost: `Medium`

Subory:

- `project_control/services/graph_service.py`
- `project_control/services/analyze_service.py`
- `project_control/services/explore_service.py`

Pozorovanie:

- `_config_with_state()` sa opakuje takmer identicky vo viacerych moduloch

Dopad:

- zbytocny maintenance overhead
- rastie sanca, ze sa spravanie tychto vrstiev casom rozide

Odporucanie:

- vytiahnut do jedneho helpera/factory modulu

### 7. `PROJECT_DIR = Path.cwd()` na module scope

Zavaznost: `Medium`

Subor:

- `project_control/cli/router.py`

Problem:

- `PROJECT_DIR` sa vyrata pri importe modulu, nie pri spusteni prikazu
- v netrivialnych integraciach alebo pri reuse modulu to moze viest k praci nad inym adresarom, nez sa ocakava

Odporucanie:

- vyrabat project root az pri `dispatch()` / command execution

### 8. `run_rg()` nema scope na `project_root`

Zavaznost: `Medium`

Subory:

- `project_control/utils/fs_helpers.py`
- `project_control/cli/graph_cmd.py`
- `project_control/analysis/orphan_detector.py`

Problem:

- `run_rg()` spusta `rg` bez explicitneho target path
- vyhladavanie teda zavisi od aktualneho process CWD, nie od analyzovaneho `project_root`
- to je problem hlavne pri `graph trace` a orphan detekcii mimo aktualneho working directory

Dopad:

- nespolahlive vysledky pri integraciach, testoch alebo pouziti nad inym rootom

Odporucanie:

- rozsir `run_rg()` o parameter `cwd` alebo priamo `search_root`

## Kvalita Analyz a False Positives

### 9. Orphan detector je heuristicky a moze mat vysoku chybovost

Zavaznost: `Medium`

Subor:

- `project_control/analysis/orphan_detector.py`

Problem:

- orphan detekcia stoji na tokenoch zo stemu suboru a jednom velkom `rg` pattern-e
- reference sa hladaju textovo, nie cez realne import resolution
- reference v komentaroch alebo dokumentacii mozu generovat false negatives
- subory s podobnymi nazvami mozu vytvarat false positives/false negatives

Dopad:

- vysledky `ghost` su skor heuristic hints ako spolahliva analyza

Odporucanie:

- oznacit orphan vysledky ako heuristic
- pre JS/TS/Python preferovat graph-backed orphan detekciu

### 10. Duplicate detector porovnava len basename

Zavaznost: `Medium`

Subor:

- `project_control/analysis/duplicate_detector.py`

Problem:

- dnes ide iba o "rovnaky nazov suboru v inom priecinku"
- nejde o skutocnu obsahovu duplicitu

Dopad:

- vysoka miera false positives

Odporucanie:

- feature premenovat na `same-name candidates`, alebo
- doplnit obsahove hash/similarity porovnanie

### 11. Session detector je prilis siroky

Zavaznost: `Low-Medium`

Subor:

- `project_control/analysis/session_detector.py`

Problem:

- flaguje vsetko, co obsahuje retazec `session`
- nerozlisuje legit session management od docasnych/odpadovych suborov

Odporucanie:

- doplnit allowlist/ignore pravidla
- zvazit severity downgrade alebo presnejsiu heuristiku

## Vykonove a Prevadzkove Rizika

### 12. Scan vytvara trvalu blob ulozku bez cleanup strategie

Zavaznost: `Medium-High`

Subor:

- `project_control/core/scanner.py`

Problem:

- scan cita kazdy zodpovedajuci subor cely do pamate
- zapisuje blob do `.project-control/content/<sha>.blob`
- neexistuje ziadny cleanup staleho obsahu, retention policy ani garbage collection

Dopad:

- dlhodoby rast `.project-control/content`
- diskova amplifikacia
- pomalsie skeny a horsia hygiena repozitara

Odporucanie:

1. Zaviest cleanup neodkazovanych blobov po novom scan-e.
2. Pridat size limity / skip pre velke subory.
3. Oddelit runtime data od git tracked obsahu.

### 13. Repo obsahuje generovane artefakty a cache

Zavaznost: `Medium`

Pozorovanie:

- git working tree obsahuje:
  - `.project-control/snapshot.json`
  - `.project-control/content/*.blob`
  - `project_control/cli/__pycache__/*.pyc`
  - `project_control/core/__pycache__/*.pyc`
  - `project_control.egg-info`

Dopad:

- obrovsky sum v gite
- horsie code reviews
- riziko nahodneho commitnutia runtime stavu namiesto zdrojaku

Odporucanie:

- doplnit/utiahnut `.gitignore`
- runtime vystupy a cache explicitne vyradit z verzionovania

### 14. `ContentStore` ticho ignoruje chyby citania

Zavaznost: `Low-Medium`

Subor:

- `project_control/core/content_store.py`

Problem:

- `iter_files()` pri chybe len `continue`
- `read_text(..., errors='ignore')` moze potichu zahodit bytes

Dopad:

- tiche skreslenie analyz
- tazsie debugovanie problemov s kodovanim alebo blob konzistenciou

Odporucanie:

- logovat pocet/cestu zlyhanych blobov
- nepouzivat tiche swallow bez telemetry

## Bezpecnostne Zistenia

### 15. Priama kriticka bezpecnostna chyba nebola najdena

Zavaznost: `Info`

Nenasiel som zjavnu RCE, shell injection ani eval-like kriticku chybu v hlavnych runtime cestach.

### 16. Regex / search input nie je osetreny na bezpecny literal

Zavaznost: `Low`

Subory:

- `project_control/utils/fs_helpers.py`
- `project_control/cli/router.py`
- `project_control/cli/graph_cmd.py`

Problem:

- user input pre `find` a cast `trace` ide priamo do `rg` ako regex pattern
- nejde o shell injection (subprocess dostava list argumentov), ale ide o neobmedzeny regex input

Dopad:

- mozne nepresne vysledky
- mozne spomalenie pri zlozitych regexoch

Odporucanie:

- pri simple symbol search pouzit escaped literal mode
- explicitne odlisit `regex search` vs `literal search`

## Testy a Dovod Dôvery

Pozitivne:

- `tests/test_graph_core.py` prebehli uspesne
- `tests/test_integration.py` prebehol uspesne

Negativne:

- `tests/test_ghost_graph_core.py` zlyhava na realnej nekompatibilite API
- `pytest` nie je v prostredi nainstalovany, audit sa preto opieral o `unittest` a manualne CLI spustenia

Zaver:

- graph jadro ma lepsiu stabilitu ako ghost/usecase vrstva
- najvacsie riziko je prave v nekonzistentnom ghost refaktore

## Co Vyzera Dokoncene

Relativne konzistentne casti:

- `scan` -> vytvorenie snapshotu a blob store
- `graph build/report/trace`
- zakladny CLI dispatch
- zakladne graph testy

## Co Vyzera Nedokoncene alebo Opustene

- rozsiahla `ghost --deep` funkcionalita popisana v manuali
- drift/trend/architecture validation vetva
- workflow/usecase DTO vrstva pre ghost
- paralelna starsia UI vrstva
- semantic analyza ako realne pouzitelna capability

## Prioritizovany Akcny Plan

### Priorita P0

1. Rozhodnut a zjednotit ghost kontrakt:
   - bud vratit `deep` API
   - alebo odstranit stare vetvy, testy a dokumentaciu
2. Opravit `semantic_detector._is_code_file()`
3. Zosuladit `MANUAL.md` s realnym parserom

### Priorita P1

1. Zaviest jeden canonical result DTO pre ghost analyzu
2. Zrusit alebo archivovat legacy `ui.py`
3. Vytiahnut zdielanu graph-state konfiguraciu do jedneho modulu
4. Upravit `run_rg()` tak, aby pracoval nad explicitnym `project_root`

### Priorita P2

1. Zaviest cleanup pre `.project-control/content`
2. Zlepsit detektory:
   - orphan -> graph-backed
   - duplicate -> obsahova podobnost
   - session -> presnejsie pravidla
3. Doplnenie testov pre semantic a ghost contract

## Odporucany Cielovy Stav

Projekt by mal mat len 3 jasne vrstvy:

1. `CLI/UI layer`
   - parser, menu, output formatting
2. `Application layer`
   - scan/ghost/graph usecases s jednou canonical DTO schema
3. `Analysis engines`
   - scanner, content store, graph builder, detektory

Vsetko ostatne, co nie je aktivne napojene, by malo byt:

- bud odstranene
- alebo presunute medzi experimental/internal moduly s jasnym oznacenim

## Finalne Hodnotenie

`PROJECT CONTROL` ma pouzitelne technicke jadro, ale momentalne nie je dost konzistentny na to, aby som ho oznacil za plne dokonceny produkt. Najvacsi problem nie je len jednotliva chyba v kode, ale to, ze projekt hovori troma roznymi jazykmi naraz:

- parser a live CLI hovoria jedno
- testy a usecase vrstva hovoria druhe
- `MANUAL.md` hovori tretie

Kym sa tieto tri vrstvy nezjednotia, bude kazda dalsia feature alebo refaktor zbytocne rizikovy.
