# Contributing to PROJECT_CONTROL

Ďakujeme za záujem prispievať do PROJECT_CONTROL! Tento dokument ti pomôže začať.

## 🚀 Quick Start

### Prerequisities

- Python 3.10 or higher
- Git
- Virtual environment (recommended)

### Development Setup

1. **Fork the repository**
   ```bash
   # Click "Fork" button on GitHub
   ```

2. **Clone your fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/project-control.git
   cd project-control
   ```

3. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. **Install in development mode**
   ```bash
   pip install -e .
   ```

5. **Install development dependencies**
   ```bash
   pip install pytest pytest-cov flake8 mypy
   ```

## 🧪 Running Tests

### Run all tests
```bash
pytest tests/
```

### Run tests with coverage
```bash
pytest tests/ --cov=project_control --cov-report=term-missing
```

### Run specific test file
```bash
pytest tests/test_ghost_graph_core.py
```

### Run specific test
```bash
pytest tests/test_ghost_graph_core.py::test_specific_function
```

### Run tests with verbose output
```bash
pytest tests/ -v
```

## 🔍 Code Quality

### Linting with flake8
```bash
flake8 project_control/
```

### Type checking with mypy
```bash
mypy project_control/ --ignore-missing-imports
```

### Run all quality checks
```bash
flake8 project_control/ && mypy project_control/ --ignore-missing-imports && pytest tests/
```

## 📝 Development Workflow

1. **Create a new branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**
   - Write clean, readable code
   - Add tests for new functionality
   - Update documentation if needed

3. **Run tests locally**
   ```bash
   pytest tests/
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   # or
   git commit -m "fix: resolve bug in module"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create Pull Request**
   - Go to GitHub
   - Click "New Pull Request"
   - Provide clear description of changes

## 🎯 Commit Message Convention

Používame konvenčné commit správy:

- `feat:` - nová funkcia
- `fix:` - oprava bugu
- `docs:` - zmeny v dokumentácii
- `style:` - zmeny formátovania (nezmena funkčnosti)
- `refactor:` - refaktoring kódu
- `test:` - pridanie alebo úprava testov
- `chore:` - údržba, build zmeny

Príklady:
```
feat: add support for JavaScript import graphs
fix: resolve issue with orphan detection in nested directories
docs: update installation instructions
test: add integration tests for graph service
```

## 🏗️ Project Structure

```
project_control/
├── analysis/          # Analysis detectors (orphan, duplicate, etc.)
├── cli/              # Command-line interface
├── config/           # Configuration management
├── core/             # Core services (ghost, embedding, etc.)
├── embedding/        # Semantic embedding system
├── experimental/     # Experimental features
├── graph/            # Import graph engine
├── persistence/      # Data persistence layer
├── services/         # Business logic services
├── ui/               # User interface components
├── utils/            # Utility functions
└── usecases/         # Use case implementations
```

## 🐛 Reporting Bugs

Pred nahlásením bugu:

1. Skontroluj, či už existuje podobný issue
2. Vytvor nový issue s:
   - Jasným popisom problému
   - Kroky na reprodukovanie
   - Očakávaným vs. skutočným správaním
   - Verziou Pythonu a PROJECT_CONTROL
   - Prípadným logom alebo error outputom

## 💡 Feature Requests

Pre návrh novej funkcie:

1. Skontroluj, či už podobný request existuje
2. Vytvor issue s:
   - Popisom navrhovanej funkcie
   - Use case (prečo to potrebuješ)
   - Prípadnými návrhmi implementácie

## 📖 Adding Documentation

Ak pridávaš novú funkciu:

1. Aktualizuj príslušnú dokumentáciu
2. Pridaj docstrings do nových funkcií
3. Aktualizuj README ak je to potrebné

## 🤝 Code Review Process

Po vytvorení Pull Requestu:

1. CI automaticky spustí testy
2. Maintainer skontroluje tvoje zmeny
3. Môžeš očakávať komentáre a návrhy na zlepšenie
4. Po schválení bude tvoj PR mergnutý

## 🎨 Coding Style

- Používaj 4 spaces pre indentáciu
- Maximálna dĺžka riadku: 127 znakov
- Používaj typové hinty kde je to vhodné
- Píš clear, self-documenting code
- Dodržiavaj PEP 8 kde je to možné

## 📧 Contact

Ak máš otázky:

- Otvoriť issue na GitHub
- Kontaktovať maintainera: Daniel Hlaváč

## 📄 License

Prispievaním do projektu súhlasíš, že tvoje príspevky budú licencované pod MIT licenciou.

---

Ďakujeme za tvoje príspevky! 🎉
