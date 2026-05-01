# UX zjednodušenie pre ne-programátorov

## Problém
Súčasná terminológia je príliš technická pre ne-programátorov:
- "Snapshot", "Graph", "Trace" - neprehľadné pojmy
- "Dependency", "Import", "Module" - programátorský jazyk
- Príliš veľa volieb bez kontextu
- Chýbajúce vysvetlenia "prečo" a "čo to znamená pre mňa"

## Cieľ
Urobiť nástroj **pochopiteľný pre každého**, kto potrebuje porozumieť codebase:
- Project manažéri
- Tech leadi
- Analytici
- Business stakeholderi
- Zaujímai sa o štruktúru projektu

---

## Zmeny terminológie

### Hlavné menu - zjednodušené

| Pôvodné | Nové | Vysvetlenie pre ne-programátora |
|---------|------|-------------------------------|
| Snapshot | 📂 Skenovať projekt | "Vytvorí zoznam všetkých súborov v projekte" |
| Graph | 🔗 Závislosti | "Ukáže, ktoré súbory používajú ktoré" |
| Analyze | 🔍 Nájsť problémy | "Nájde nepoužívané súbory a duplicity" |
| Explore | 📍 Sledovať kód | "Ukáže cestu, akou prechádza kód" |
| Settings | ⚙️ Nastavenia | "Konfigurácia nástroja" |

### Quick Actions - ešte jednoduchšie

**Predtým:**
```
Quick Actions:
  1) Full Analysis      — Scan → Find Issues → Dependencies
  2) Quick Health Check — Validate everything
  3) Quick Reports      — View all findings
```

**Po zjednodušení:**
```
🚀 Rýchle akcie
==================
  1) Kompletná analýza
     → Zobrazí všetko: súbory, problémy, závislosti
     
  2) Rýchla kontrola
     → Skontroluje, či je všetko OK
     
  3) Zobraziť výsledky
     → Ukáže nájdené problémy
```

---

## Nový hlavný menu pre ne-programátorov

```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              PROJECT CONTROL                              ║
║                                                           ║
║  Projekt:  moj-aplikacia                                  ║
║  Stav:     ⚠️ 3 problémy nájdené                          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

🚀 Čo chcete urobiť?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1) 👻 Nájsť nepoužívané súbory
     → Odstrániť zbytočný kód, ktorý sa nikde nepoužíva

  2) 📋 Nájsť duplicity
     → Zistiť, ktoré časti kódu sú opakované

  3) 🔗 Zobraziť závislosti
     → Ukáže, aké súbory sú prepojené

  4) ✅ Skontrolovať zdravie projektu
     → Rýchla kontrola všetkých súborov

  5) 📂 Znova skenovať projekt
     → Aktualizovať zoznam súborov

  6) 💾 Zobraziť všetky správy
     → Prehľad všetkých nájdených problémov

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ? Pomoc   |   ⚙️ Nastavenia   |   🚪 Koniec
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Vyberte číslo (1-6) alebo písmeno (?/⚙️/🚪): 
```

---

## Zmeny v pod-menu

### Nájsť problémy (Find Issues)

**Predtým:**
```
Analyze:
1) Ghost detectors (shallow)
2) Structural metrics (from graph)
```

**Po zjednodušení:**
```
🔍 Nájsť problémy
==================

  1) 👻 Nepoužívané súbory
     → Súbory, ktoré nikto neimportuje a nepoužíva
     → Výstup: Zoznam súborov, ktoré môžete bezpečne odstrániť

  2) 🔄 Cyklické závislosti
     → Súbory, ktoré sa navzájom očakávajú (možné problémy)
     → Výstup: Zoznam cyklov, ktoré treba opraviť

  3) 📊 Štatistika kódu
     → Počet súborov, veľkosť, zložitosť
     → Výstup: Prehľadná správa o projekte

  [?] Čo to znamená?  |  [0] Späť
```

### Závislosti (Dependencies)

**Predtým:**
```
Trace:
  Current: direction=Inbound, depth=3, all=False
```

**Po zjednodušení:**
```
🔗 Zobraziť závislosti
=======================

  Aký súbor chcete skúmať?
  ──────────────────────────────────────────────────────
  
  Napríklad:
    • src/main.js
    • components/Button.tsx
    • utils/helpers.py
  
  Cesta k súboru: [_______________________]
  
  ──────────────────────────────────────────────────────
  
  1) Kto toto používa? (koho to importuje)
     → Ukáže, ktoré súbory závisia na tomto súbore
  
  2) Čo toto používa? (čo tento súbor importuje)
     → Ukáže, od koho tento súbor závisí
  
  3) Obidve smeri
     → Kompletný prehľad závislostí
  
  [?] Ako to čítať?  |  [0] Späť
```

---

## Kontextová pomoc (?) pre každé menu

### Príklad: Nájsť nepoužívané súbory

```
[?] Pomoc - Nepoužívané súbory
═══════════════════════════════

Čo to robí?
───────────
Hľadá súbory, ktoré:
  • Sú v projekte, ale nikde sa nepoužívajú
  • Nikto ich neimportuje alebo nespomína
  • Pravdepodobne sú "zabudnuté" alebo "zastaralé"

Prečo je to dôležité?
────────────────────
  • Nepoužívaný kód zbytočne zvyšuje veľkosť projektu
  • Zbytočne si myslíte, že projekt je komplikovanejší
  • Môže viesť k zmätkam - "Prečo je tu tento súbor?"
  • Zabíra miesto v repozitári a pomaly sa načítava

Čo s tým môžem urobiť?
──────────────────────
  • Bezpečne odstrániť nepoužívané súbory
  • Presunúť ich do archívu (ak si myslíte, že ešte potrebujete)
  • Pýtať sa tímu, či ešte potrebujú

Aký je výstup?
────────────
  • 📄 ghost_orphans_tree.txt
    → Zoznam nepoužívaných súborov s ich cestami
    
  • 📄 ghost_orphans.md
    → Podrobná správa s vysvetleniami

Tip: Pozrite si najprv .txt súbor - je ľahšie čitateľný!

═══════════════════════════════════════════════════════
Press Enter to continue...
```

---

## Zjednodušené nastavenia

**Predtým:**
```
[Configuration]
Basic:
  1) Project Type:  [JS/TS]
  2) Strictness:    [Pragmatic]
  3) Output Format: [Tree files ⭐ recommended]
Advanced:
  4) Trace Options  — direction, depth, all paths
```

**Po zjednodušení:**
```
⚙️ Nastavenia
=============

🎯 Základné nastavenia (väčšinou netreba meniť)
───────────────────────────────────────────────────

  1) Typ projektu
     → Automaticky sa zistí
     • JavaScript/TypeScript
     • Python
     • Zmiešaný
     
     [?] Prečo je to dôležité?
     Každý jazyk má iné spôsoby importovania. 
     Nástroj to potrebuje vedieť, aby správne našiel závislosti.

  2) Prísnosť analýzy
     → ⭐ Odporúčané: Pragmatické
     • Pragmatické (odporúčané) - vyvážené, málo falošných nálezo
     • Prísné - viac nájdených problémov, ale viac "šumu"

     [?] Čo to znamená?
     Pragmatické = Nájde skutočné problémy, vyhne sa falošným poplachom.
     Prísné = Nájde všetko, aj veci, ktoré môžu byť v poriadku.

  3) Výstupný formát
     → ⭐ Odporúčané: ASCII stromy
     • ASCII stromy ⭐ - ľahko čitateľné pre ľudí
     • Správy (Markdown) - detailné vysvetlenia
     • Obe - aj aj
     
     [?] Ktorý si vybrať?
     Ak ste začiatočník → ASCII stromy
     Ak chcete detaily → Správy
     Ak si nie ste istí → Obe

───────────────────────────────────────────────────
  [0] Späť  |  [?] Viac o nastaveniach
```

---

## Wizard Mode pre ne-programátorov

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│          Vitajte v PROJECT CONTROL! 🎉                  │
│                                                         │
│  PROJECT CONTROL vám pomôže porozumieť vašej aplikácii  │
│  a nájsť nepoužívaný kód a problémy.                   │
│                                                         │
│  Nie je potrebné byť programátorom!                     │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Na úvod nám povieme niekoľko vecí o vašom projekte:    │
│                                                         │
│  1) Aký typ projektu máte?                             │
│  2) Ako prísne máme skontrolovať?                      │
│  3) Aký výstup preferujete?                            │
│  4) Chcete ihneď skontrolovať projekt?                 │
│                                                         │
│  Každý krok môžete preskočiť (stlačte S)               │
│                                                         │
└─────────────────────────────────────────────────────────┘

Press Enter to continue alebo 'Q' pre koniec...
```

### Krok 1: Typ projektu

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  Krok 1/4: Typ projektu                                 │
│                                                         │
│  Aký typ projektu toto je?                             │
│                                                         │
│  To nám povie, aké súbory máme hľadať a ako fungujú.   │
│                                                         │
│  → 1) JavaScript/TypeScript                             │
│     • Súbory končia na .js, .ts, .jsx, .tsx            │
│     • Napríklad: React, Vue, Angular aplikácie         │
│                                                         │
│    2) Python                                            │
│     • Súbory končia na .py                             │
│     • Napríklad: Django, Flask aplikácie               │
│                                                         │
│    3) Zmiešané (obe)                                   │
│     • Obsahuje aj JavaScript aj Python                 │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [1-3] Vyberte  |  [S] Preskočiť (použiť automatické) │
│  [Q] Koniec                                              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Krok 3: Výstupný formát

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  Krok 3/4: Výstupný formát                              │
│                                                         │
│  Ako chcete vidieť výsledky?                           │
│                                                         │
│  ASCII stromy sú najľahšie na čítanie pre ľudí -       │
│  okamžite uvidíte štruktúru a vzťahy.                 │
│                                                         │
│  → 1) ASCII stromy ⭐ (odporúčané)                      │
│     • Ľahko čitateľné, vizuálne, prehľadné            │
│     • Ideálne pre začiatočníkov                        │
│     • Otvoríte ich v akomkoľvek editore                │
│                                                         │
│    2) Obe (stromy + správy)                            │
│     • ASCII stromy pre rýchly prehľad                  │
│     • Markdown správy pre detailné vysvetlenia          │
│                                                         │
│    3) Iba správy (Markdown)                            │
│     • Detailné textové správy                          │
│     • Vhodné pre automatizáciu                         │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [1-3] Vyberte  |  [S] Preskočiť (použiť automatické) │
│  [Q] Koniec                                              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Tipy pre začiatočníkov v menu

Po spustení nástroja (ak je prvýkrát):

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│          💡 Rychlý štart pre začiatočníkov             │
│                                                         │
│  Ste tu prvýkrát? Tu sú 3 jednoduché kroky:            │
│                                                         │
│  1️⃣  Skenujte projekt                                 │
│      → Vytvorí zoznam všetkých súborov                 │
│                                                         │
│  2️⃣  Nájdite problémy                                │
│      → Zistí, čo je nepoužívané alebo duplicitné       │
│                                                         │
│  3️⃣  Pozrite si výsledky                             │
│      → Prečítajte správy a opravte nájdené chyby      │
│                                                         │
│  ───────────────────────────────────────────────────── │
│                                                         │
│  TIP: Použite "Kompletnú analýzu" (voľba 1) -         │
│       urobí všetko automaticky!                       │
│                                                         │
│  ───────────────────────────────────────────────────── │
│                                                         │
│  Stlačte ? kedykoľvek pre pomoc!                      │
│                                                         │
└─────────────────────────────────────────────────────────┘

Press Enter to continue...
```

---

## Príklad výstupu pre ne-programátora

### Výstup: ghost_orphans_tree.txt

**Predtým (technické):**
```
src/components/
├── Button.tsx (ORPHAN)
├── Modal.tsx (ORPHAN)
└── Header.tsx
```

**Po zjednodušení:**
```
📂 Nepoužívané súbory
═══════════════════════════════════════════════════════════

Tieto súbory sú v projekte, ale nikde sa nepoužívajú.
Môžete ich bezpečne odstrániť, aby ste zredukovali veľkosť projektu.

src/components/
  ⚠️  Button.tsx
      → Tento súbor nie je importovaný v žiadnom inom súbore
      → Veľkosť: 2.3 KB
      → Naposledy upravený: pred 45 dňami
      → Odporúčanie: Odstrániť, ak nepotrebujete

  ⚠️  Modal.tsx
      → Tento súbor nie je importovaný v žiadnom inom súbore
      → Veľkosť: 5.1 KB
      → Naposledy upravený: pred 120 dňami
      → Odporúčanie: Odstrániť alebo presunúť do archívu

═══════════════════════════════════════════════════════════
💡 TIP: Pozrite si súbory pred odstránením, aby ste sa ubezpečili,
         že ich skutočne nepotrebujete.

Celkom nájdené: 2 nepoužívané súbory
```

---

## Zhrnutie zmien

### Terminológia
- **Snapshot** → **Skenovať projekt**
- **Graph** → **Závislosti**
- **Analyze** → **Nájsť problémy**
- **Explore** → **Sledovať kód**
- **Settings** → **Nastavenia**

### Menu
- Menej volieb, viac vysvetlení
- Emoji pre vizuálnu orientáciu
- Kontextová pomoc (?)

### Wizard
- Jasný jazyk pre ne-programátorov
- Vysvetlenia "prečo" a "čo to znamená"
- Odporúčania pre každý krok

### Výstupy
- Ľudsky čitateľné formáty
- Jasné odporúčania
- Kontext a vysvetlenia

---

## Ďalšie nápady

### Gamification pre nových používateľov
- 🏆 Prvá analýza - Odznak za prvé prehľadanie projektu
- 🎯 Čistý kód - Odznak za odstránenie 10+ nepoužívaných súborov
- 🔍 Detektív - Odznak za nájdenie 5+ cyklických závislostí

### Smart tipy
- Ak nájde veľa nepoužívaných súborov → "Váš projekt môže byť o 30% menší po vyčistení!"
- Ak nájde cykly → "Cyklické závislosti môžu spôsobiť problémy s načítaním."
- Ak nájde duplicity → "Duplicity zvyšujú údržbu - zvážte refaktoring."

### Interaktívne otázky
- Namiesto zložitého menu: "Nenašli ste, čo ste hľadali? Povedzte mi, čo chcete urobiť..."
  • "Chcem zistiť, či je tento súbor používaný"
  • "Chcem nájsť všetky súbory, ktoré používajú tento súbor"
  • "Chcem odstrániť nepoužívaný kód"

---

**Cieľ:** Urobiť PROJECT CONTROL nástrojom, ktorý porozumie každý, nie len programátori.