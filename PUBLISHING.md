# Publishing to PyPI

Tento dokument vysvetľuje, ako publikovať PROJECT_CONTROL na PyPI.

## 🚀 Automatické publikovanie (odporúčané)

Projekt je nastavený na automatické publikovanie na PyPI pomocou GitHub Actions.

### Prvotné nastavenie

1. **Vytvoriť PyPI účet**
   - Choď na https://pypi.org/account/register/
   - Zaregistruj sa a overiť email

2. **Nastaviť Trusted Publishing**
   - Choď na https://pypi.org/manage/account/publishing/
   - Klikni "Add a new pending publisher"
   - Vyplň:
     - **PyPI Project Name**: `project-control`
     - **Owner**: tvoje GitHub username (napr. `danielhlavac`)
     - **Repository name**: `project-control`
     - **Workflow name**: `publish.yml`
     - **Environment name**: `pypi`

3. **Vytvoriť GitHub Release**
   - Choď na GitHub repozitár
   - Klikni "Releases" → "Create a new release"
   - Tag: `v0.1.0`
   - Release title: `v0.1.0`
   - Description: Skopíruj obsah z CHANGELOG.md pre verziu 0.1.0
   - Klikni "Publish release"

4. **Automatické publikovanie**
   - GitHub Actions automaticky:
     - Stiahne kód
     - Zbuilduje balík
     - Skontroluje ho s twine
     - Publikuje na PyPI

### Použitie po publikovaní

Po úspešnom publikovaní môžu používatelia inštalovať:

```bash
pip install project-control
```

Alebo s voliteľnými závislosťami:

```bash
pip install project-control[embedding]
```

## 🔧 Manuálne publikovanie

Ak potrebuješ publikovať manuálne:

### 1. Nainštalovať build nástroje

```bash
pip install build twine
```

### 2. Zbuildovať balík

```bash
python -m build
```

Toto vytvorí:
- `dist/project_control-0.1.0.tar.gz` (source distribution)
- `dist/project_control-0.1.0-py3-none-any.whl` (wheel)

### 3. Skontrolovať balík

```bash
twine check dist/*
```

### 4. Publikovať na PyPI

**Testovacie PyPI (pre testovanie):**

```bash
twine upload --repository testpypi dist/*
```

Inštalácia z testovacieho PyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ project-control
```

**Produkčné PyPI:**

```bash
twine upload dist/*
```

Budeš požiadaný o PyPI username a password (alebo API token).

### 5. Overenie

Skontroluj, či je balík na PyPI:

- Choď na https://pypi.org/project/project-control/
- Skús nainštalovať: `pip install project-control`

## 🔄 Verzovanie

Používame [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (napr. 0.1.0)
- MAJOR: nekompatibilné zmeny
- MINOR: nové funkcie, spätne kompatibilné
- PATCH: bug fixy, spätne kompatibilné

### Aktualizácia verzie

1. Uprav verziu v `pyproject.toml`:
   ```toml
   version = "0.1.1"
   ```

2. Uprav verziu v `project_control/pc.py`:
   ```python
   __version__ = "0.1.1"
   ```

3. Aktualizuj `CHANGELOG.md` s novými zmenami

4. Commitni zmeny:
   ```bash
   git add .
   git commit -m "chore: bump version to 0.1.1"
   git push
   ```

5. Vytvor nový GitHub release s tagom `v0.1.1`

## 🔐 API Token (pre manuálne publikovanie)

Ak používaš manuálne publikovanie, odporúča sa použiť API token namiesto hesla:

1. Choď na https://pypi.org/manage/account/token/
2. Vytvor nový token s scope "Entire account"
3. Skopíruj token (zobrazí sa len raz!)
4. Pri publikovaní použi token ako password:
   ```bash
   twine upload dist/*
   Username: __token__
   Password: pypi-... (tvoj token)
   ```

## 📝 Kontrolný zoznam pred publikovaním

- [ ] Verzia v `pyproject.toml` je aktualizovaná
- [ ] Verzia v `project_control/pc.py` je aktualizovaná
- [ ] `CHANGELOG.md` obsahuje zmeny pre túto verziu
- [ ] Všetky testy prechádzajú (`pytest tests/`)
- [ ] CI je green (pozri GitHub Actions)
- [ ] `README.md` je aktuálny
- [ ] `LICENSE` je prítomný a správny
- [ ] Balík sa lokálne zbuilduje (`python -m build`)
- [ ] Balík prechádza twine check (`twine check dist/*`)

## 🐛 Riešenie problémov

### "403 Forbidden" pri publikovaní

- Skontroluj, či máš správne nastavené Trusted Publishing
- Skontroluj, či sa názov projektu zhoduje (case-sensitive)

### "File already exists"

- Verzia už existuje na PyPI
- Zvýš číslo verzie a zbuilduj znovu

### "Invalid metadata"

- Skontroluj `pyproject.toml`
- Spusti `twine check dist/*` pre detaily

### Balík sa nenainštaluje

- Skontroluj, či sú všetky závislosti v `pyproject.toml`
- Skontroluj, či `MANIFEST.in` obsahuje všetky potrebné súbory

## 📚 Ďalšie zdroje

- [PyPI User Guide](https://packaging.python.org/tutorials/packaging-projects/)
- [GitHub Actions PyPI Publish](https://github.com/pypa/gh-action-pypi-publish)
- [Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
- [Semantic Versioning](https://semver.org/)
