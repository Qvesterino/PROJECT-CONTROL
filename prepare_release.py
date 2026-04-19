#!/usr/bin/env python3
"""
Skript na prípravu čistého verejného repozitára pre PROJECT_CONTROL
Vytvorí nový adresár s len produkčnými súbormi, bez interných auditov a vývojových artefaktov.
"""

import os
import shutil
from pathlib import Path

# Definícia, čo má ísť do verejného repozitára
PUBLIC_INCLUDE = [
    "project_control/",
    "tests/",
    "LICENSE",
    "README.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "pyproject.toml",
    ".gitignore",
    ".github/workflows/",
]

# Definícia, čo NEMÁ ísť do verejného repozitára (interné súbory)
PUBLIC_EXCLUDE = [
    "AUDITY/",
    ".project-control/",
    "documentation/",
    "plans/",
    "filetree.txt",
    "MANUAL.md",
    "deep dive audit.md",
    "orientačny graf.md",
    "contract/",
    "docs/",
    ".qodo/",
]

def prepare_public_release(source_dir: Path, target_dir: Path):
    """
    Pripraví čisté verejné vydanie z aktuálneho repozitára.

    Args:
        source_dir: Zdrojový adresár (aktuálne PROJECT_CONTROL)
        target_dir: Cieľový adresár pre verejné vydanie
    """
    print(f"📦 Príprava verejného vydania...")
    print(f"📂 Zdroj: {source_dir}")
    print(f"📂 Cieľ: {target_dir}")
    print()

    # Vytvor cieľový adresár
    if target_dir.exists():
        print(f"⚠️  Cieľový adresár už existuje: {target_dir}")
        response = input("Chceš ho zmazať a znovu vytvoriť? (y/N): ")
        if response.lower() == 'y':
            shutil.rmtree(target_dir)
            print(f"🗑️  Zmazaný existujúci adresár")
        else:
            print("❌ Zrušené")
            return

    target_dir.mkdir(parents=True, exist_ok=True)

    # Skopíruj povolené súbory/adresáre
    copied_count = 0
    for item in PUBLIC_INCLUDE:
        source_path = source_dir / item
        if source_path.exists():
            if source_path.is_dir():
                shutil.copytree(source_path, target_dir / item)
                print(f"✅ Adresár: {item}")
            else:
                shutil.copy2(source_path, target_dir / item)
                print(f"✅ Súbor: {item}")
            copied_count += 1
        else:
            print(f"⚠️  Neexistuje: {item}")

    print()
    print(f"📊 Štatistika:")
    print(f"   - Skopírovaných položiek: {copied_count}")
    print(f"   - Vylúčených interných položiek: {len(PUBLIC_EXCLUDE)}")
    print()

    # Vypíš zoznam vylúčených súborov
    print("🚫 Vylúčené interné súbory:")
    for item in PUBLIC_EXCLUDE:
        print(f"   - {item}")
    print()

    # Vytvor README pre verejné vydanie
    create_public_readme(target_dir)

    print(f"✅ Verejné vydanie pripravené v: {target_dir}")
    print()
    print("Ďalšie kroky:")
    print("1. Skontroluj obsah v cieľovom adresári")
    print("2. Inicializuj git repozitár: cd target_dir && git init")
    print("3. Pridaj vzdialené repo: git remote add origin <url>")
    print("4. Commitni a pushni: git add . && git commit -m 'Initial release' && git push -u origin main")

def create_public_readme(target_dir: Path):
    """
    Vytvorí alebo aktualizuje README pre verejné vydanie s príslušnými informáciami.
    """
    readme_path = target_dir / "README.md"
    
    # Ak už README existuje, len ho doplníme o sekciu inštalácie
    if readme_path.exists():
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skontrolujme, či už obsahuje inštalačnú sekciu
        if "## Installation" in content or "## Inštalácia" in content:
            print("ℹ️  README už obsahuje inštalačnú sekciu")
            return
    
    # Vytvoríme základnú inštalačnú sekciu
    installation_section = """

## Installation

```bash
pip install project-control
```

Or from source:

```bash
git clone https://github.com/danielhlavac/project-control.git
cd project-control
pip install -e .
```

## Quick Start

```bash
pc --help
```

## License

MIT License - see [LICENSE](LICENSE) file for details.
"""
    
    if readme_path.exists():
        with open(readme_path, 'a', encoding='utf-8') as f:
            f.write(installation_section)
        print("✅ Doplnená inštalačná sekcia do README")
    else:
        # Vytvoríme základné README
        basic_readme = """# PROJECT_CONTROL

Deterministic architectural analysis engine for Python projects.

## Features

- Static code analysis
- Import graph visualization
- Architecture validation
- Duplicate detection
- Orphan detection
- Semantic analysis (with optional embedding support)

"""
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(basic_readme + installation_section)
        print("✅ Vytvorené základné README")

if __name__ == "__main__":
    # Získaj aktuálny adresár
    current_dir = Path.cwd()
    
    # Definuj cieľový adresár (vedľa aktuálneho)
    target_dir = current_dir.parent / "project-control-public"
    
    # Spusti prípravu
    prepare_public_release(current_dir, target_dir)
