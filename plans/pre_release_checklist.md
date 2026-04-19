# Pre-Release Checklist — GitHub Open Source Launch

## 🔴 MUST FIX (blocking release)

### 1. LICENSE file missing
- **Problem:** No `LICENSE` file in repo root. Without it, nobody can legally use your code.
- **Fix:** Add `LICENSE` file. MIT is the most permissive and popular for dev tools.
- **Also update** `pyproject.toml` → `license = {text = "MIT"}`

### 2. pyproject.toml has placeholder author
- **Problem:** `authors = [{ name = "Your Name" }]` — not professional
- **Fix:** Replace with your real name/handle + add GitHub URL
- **Missing fields:** `license`, `classifiers`, `urls` (Homepage, Bug Tracker, Repository)

### 3. Internal dev files in repo (Slovak, messy)
These should NOT be in a public repo:

| Path | Description | Action |
|------|-------------|--------|
| `AUDITY/` | 12 internal audit files in Slovak | **Delete or .gitignore** |
| `documentation/` | 7 dev docs in Slovak | **Delete or .gitignore** |
| `orientačny graf.md` | Internal note | **Delete** |
| `filetree.txt` | File tree dump | **Delete** |
| `contract/` | Empty directory | **Delete** |
| `docs/` | Empty directory | **Keep** (for future docs) |

### 4. .gitignore incomplete
- **Missing:** `.qodo/`, `.idea/`, `.vscode/`, `*.egg-info/` (already has some)
- **Fix:** Add editor/IDE directories

---

## 🟡 SHOULD FIX (before v0.1.0 announcement)

### 5. Add GitHub Actions CI
- Run 27 tests on every push/PR
- Python 3.10, 3.11, 3.12 matrix
- File: `.github/workflows/tests.yml`
- **Why:** Shows project is alive and tested. Contributors trust green badges.

### 6. Add CONTRIBUTING.md
- How to install dev dependencies
- How to run tests
- Code style expectations
- PR process

### 7. Add CHANGELOG.md
- Document what changed between versions
- Start with `## [0.1.0] - 2026-04-19` and list what's included

### 8. Clean up pyproject.toml metadata
```toml
[project]
name = "project-control"
version = "0.1.0"
description = "Deterministic architectural analysis engine — find dead code, understand your architecture"
license = {text = "MIT"}
requires-python = ">=3.10"
authors = [
    { name = "YOUR_NAME", email = "YOUR_EMAIL" }
]
keywords = ["static-analysis", "dependency-graph", "dead-code", "architecture", "developer-tools"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Quality Assurance",
]

[project.urls]
Homepage = "https://github.com/YOUR_HANDLE/project-control"
Repository = "https://github.com/YOUR_HANDLE/project-control"
Issues = "https://github.com/YOUR_HANDLE/project-control/issues"
```

---

## 🟢 NICE TO HAVE (post-launch)

### 9. Add screenshots/ASCII demo to README
- Show the actual menu output in README
- Shows ghost output example
- People want to SEE what they're getting

### 10. Add `pc --version` flag
- Simple but expected for any CLI tool
- Read from `importlib.metadata.version("project-control")`

### 11. PyPI publishing
- `python -m build && twine upload dist/*`
- Users can `pip install project-control`
- But wait for v0.1.0 tag first

### 12. Add badges to README
- ![Tests](badge) ![License: MIT](badge) ![Python](badge)
- Only after CI is set up

---

## 📋 Recommended Release Order

1. Add `LICENSE` (MIT)
2. Clean `pyproject.toml` (author, license, classifiers, URLs)
3. Delete internal files (`AUDITY/`, `documentation/`, `orientačny graf.md`, `filetree.txt`, `contract/`)
4. Update `.gitignore` (add `.qodo/`, IDE dirs)
5. Add `CONTRIBUTING.md`
6. Add `CHANGELOG.md`
7. Add GitHub Actions CI (`.github/workflows/tests.yml`)
8. Tag `v0.1.0` and push
9. Publish to PyPI (optional, can wait)

---

## 🏗️ Current Codebase Health

| Metric | Status |
|--------|--------|
| Tests | ✅ 27/27 passing |
| Dead code | ✅ Removed |
| Ghost core | ✅ Canonical pure function |
| Menu UI | ✅ Proper UX with back/options |
| Windows compat | ✅ Path fixes applied |
| Architecture layers | ✅ Validated |
| Import consistency | ✅ Clean |
