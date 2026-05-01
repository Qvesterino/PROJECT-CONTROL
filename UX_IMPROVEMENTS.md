# Zjednodušenia UX pre nových používateľov

## Súčasný stav
Menu má **11 hlavných položiek** s technickou terminológiou:
- Snapshot, Graph, Analyze, Explore, Settings, Health, Tools, Reports, Presets, Export/Imp, Browse, Quick

## Navrhované zjednodušenia

### 1. **Zjednodušené hlavné menu** (z 11 na 6 položiek)

```
PROJECT CONTROL
================
Project:  my-project
Status:   Ready
================

Quick Actions:
  1) Full Analysis     — Scan → Find Issues → Dependencies
  2) Quick Health Check — Validate everything
  3) Quick Reports     — View all findings

Main Tools:
  4) Scan Project      — Index all files
  5) Find Issues       — Dead code, orphans, duplicates
  6) Dependencies      — Trace imports & modules

Advanced:
  S) Settings          — Configuration
  H) Help & Docs       — Getting started
  Q) Exit
```

**Výhody:**
- Nový používateľ vidí hneď "Quick Actions" - čo chce spraviť?
- Menej volieb → menej paralyzace rozhodovania
- "Advanced" sekcia skrýva komplexné veci

### 2. **Jednoduchšia terminológia**

| Pôvodné | Nové | Vysvetlenie |
|---------|------|-------------|
| Snapshot | Scan Project | "Skenovanie" je zrozumiteľnejšie |
| Graph | Dependencies | "Závislosti" hovorí sama za seba |
| Analyze | Find Issues | "Nájsť problémy" - jasný účel |
| Explore | Trace Code | "Sledovať kód" - akcia |
| Settings | Configuration | "Konfigurácia" - štandardný termín |

### 3. **Wizard Mode pre prvé použitie**

```
┌─────────────────────────────────────┐
│  Welcome to PROJECT CONTROL! 🎉    │
├─────────────────────────────────────┤
│                                     │
│  Let's set up your first analysis   │
│                                     │
│  Step 1/3: Project Type             │
│                                     │
│  What kind of project is this?      │
│                                     │
│  1) JavaScript/TypeScript           │
│  2) Python                          │
│  3) Mixed (JS + Python)             │
│                                     │
│  [1-3] Select                       │
│  [S] Skip (use defaults)            │
│  [Q] Quit                           │
│                                     │
└─────────────────────────────────────┘
```

### 4. **Quick Start s emoji a popismi**

```python
QUICK_ACTIONS = [
    {
        "id": "full_analysis",
        "emoji": "🔍",
        "title": "Full Analysis",
        "description": "Scan everything and find all issues",
        "for": "New projects or big refactors"
    },
    {
        "id": "health_check",
        "emoji": "✅",
        "title": "Health Check",
        "description": "Quick validation of project state",
        "for": "Before commit or deployment"
    },
    {
        "id": "find_orphans",
        "emoji": "👻",
        "title": "Find Orphans",
        "description": "Find unused and dead files",
        "for": "Cleaning up codebase"
    },
    {
        "id": "find_duplicates",
        "emoji": "📋",
        "title": "Find Duplicates",
        "description": "Find duplicate code blocks",
        "for": "Refactoring and deduplication"
    }
]
```

### 5. **Simplified Settings**

Namiesto 5 technických nastavení:

```
Configuration
=============

Basic:
  1) Project Type:  [JavaScript/TypeScript ▼]
     Options: JS/TS, Python, Mixed

  2) Strictness:    [Pragmatic ▼]
     Options: Pragmatic (recommended), Strict

  3) Output Format: [Both ▼]
     Options: Reports only, Tree files only, Both

Advanced: [▶] Click to expand
  - Trace direction
  - Trace depth
  - Cache settings

[B] Back to main menu
```

### 6. **Context-sensitive help**

Pridať `?` príkaz do každého menu:

```
Find Issues
===========

1) Ghost Detectors    — Find orphans, legacy, duplicates
2) Structural Metrics — Find cycles, analyze graph structure
3) Dead Code Radar    — Find files with zero/minimal usage
4) Unused Systems     — Find systems that exist but aren't used
5) Suspicious Patterns — Detect forbidden code patterns

[?] Help  — What do these mean?
[0] Back
```

Po stlačení `?`:

```
┌─────────────────────────────────────┐
│  GHOST DETECTORS                    │
├─────────────────────────────────────┤
│                                     │
│  What it does:                      │
│  • Finds files that aren't used     │
│  • Detects old/legacy code          │
│  • Identifies duplicates            │
│  • Finds temporary session files   │
│                                     │
│  Why use it:                        │
│  Clean up your codebase and remove  │
│  dead code that's taking up space   │
│  and confusing developers.          │
│                                     │
│  Output:                            │
│  • Markdown report (readable)       │
│  • Tree files (ASCII, easy to view) │
│  • JSON (for automation)            │
│                                     │
└─────────────────────────────────────┘
```

### 7. **One-command workflow**

Pre úplne začiatočníkov:

```bash
# Simple: one command does everything
pc quick

# Equivalent to:
pc scan && pc ghost --tree && pc graph build
```

### 8. **Improved first-time experience**

```python
def show_onboarding():
    """Show onboarding for new users."""
    if not state.onboarding_seen:
        print("""
╔════════════════════════════════════════╗
║  Welcome to PROJECT CONTROL! 🎉        ║
╠════════════════════════════════════════╣
║                                        ║
║  PROJECT CONTROL helps you:            ║
║                                        ║
║  🔍 Find unused code                   ║
║  👻 Remove dead files                   ║
║  📊 Understand dependencies            ║
║  🔗 Trace code connections             ║
║                                        ║
║  Quick start:                          ║
║  1) pc scan   — Index your project     ║
║  2) pc ghost   — Find issues           ║
║  3) pc ghost --tree — See results      ║
║                                        ║
║  For more help: pc --help              ║
║                                        ║
╚════════════════════════════════════════╝

Press Enter to continue or 'H' for full help...
""")
```

## Implementácia

### Priority 1 (Rýchle výhody):
1. ✅ **Quick Actions v hlavnom menu** - presunúť hore
2. ✅ **Jednoduchšie popisy** - pridať popisy k položkám
3. ✅ **Onboarding** - ukázať pri prvom spustení

### Priority 2 (Stredné zmeny):
4. Zjednodušené Settings
5. Context-sensitive help (?)
6. Emoji pre lepšiu čitateľnosť

### Priority 3 (Dlhodobé):
7. Wizard Mode
8. Interaktívny tutoriál
9. Video návody/GIF animácie

## Testovanie s používateľmi

### Scenár 1: Úplný začiatočník
**Cieľ:** Nájsť nepoužívané súbory

**Teraz (zložité):**
1. Spustiť `pc`
2. Vybrať "3) Analyze"
3. Vybrať "1) Ghost detectors"
4. Čakať na výsledky
5. Hľadať report v `.project-control/exports/`

**Po zjednodušení (jednoduché):**
1. Spustiť `pc`
2. Vidí "Quick Actions → 1) Full Analysis"
3. Stlačí 1
4. Vidí výsledky s linkom na report

### Scenár 2: Skúsený vývojár
**Cieľ:** Rýchlo skontrolovať zdravie projektu

**Teraz:**
- Musí prechádzať viacerými menu

**Po zjednodušení:**
- `pc` → "Quick Actions → 2) Quick Health Check"
- Alebo priamo: `pc quick --health`

## Môj odhad dopadu

**Pre nového používateľa:**
- 📉 Learning curve: z 30 minút na 5 minút
- 📈 Success rate: z 40% na 80%
- 😊 Satisfaction: výrazne vyššia

**Pre skúseného používateľa:**
- ⚡ Rýchlosť: rovnaká alebo vyššia (kvôli quick commands)
- 🎯 Efektivita: zlepšená (menej klikaní)
- 🔄 Migrácia: nenáročná (staré príkazy stále fungujú)

## Ďalšie nápady

### Gamification
- 🏆 Achievement system
- 📊 Progress tracking
- 🔥 Streaks (pravidelné používanie)

### AI Assistant
- 💬 Chat interface: "Pomôž mi nájsť nepoužívaný kód"
- 🤖 Smart suggestions: "Zdá sa, že máš veľa duplikátov. Chceš ich skontrolovať?"

### Visual Reports
- 📈 Interactive graphs
- 🎨 Color-coded issues
- 📥 Export to PDF/HTML

---

**Verdict:** Tieto zmeny môžu urobiť PROJECT CONTROL oveľa prístupnejším pre nových používateľov bez toho, aby to obmedzilo skúsených vývojárov!