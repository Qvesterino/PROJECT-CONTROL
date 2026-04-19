# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-XX

### Added
- **Initial release of PROJECT_CONTROL**
- **Ghost Analysis Engine**
  - Orphan detection - find files never referenced by anything
  - Legacy detection - identify outdated code matching legacy patterns
  - Session detection - find temporary or session artifacts
  - Duplicate detection - locate files with identical names in different paths
  - Semantic detection - identify files that don't belong (optional, embedding-powered)

- **Import Graph Engine**
  - Multi-language support (Python, JavaScript/TypeScript)
  - AST-based parsing for accurate dependency extraction
  - Graph visualization and export
  - Dependency tracking and analysis

- **Architecture Validation**
  - Layer boundary validation
  - Self-architecture validation
  - Import graph anomaly detection
  - Graph drift tracking (experimental)

- **CLI Interface**
  - `pc init` - Initialize project control
  - `pc scan` - Scan project structure
  - `pc ghost` - Run ghost analysis
  - `pc graph` - Import graph operations
  - `pc analyze` - Run various analyzers
  - `pc explore` - Interactive exploration

- **Core Services**
  - Ghost service for dead code detection
  - Embedding service for semantic analysis
  - Graph service for import graph management
  - Snapshot service for project state tracking

- **Testing**
  - Comprehensive test suite
  - Integration tests
  - Unit tests for all major components

- **Documentation**
  - README with quick start guide
  - CONTRIBUTING.md for contributors
  - Inline code documentation

- **Development Tools**
  - GitHub Actions CI/CD pipeline
  - Automated testing on Python 3.10, 3.11, 3.12
  - Code quality checks (flake8, mypy)
  - Coverage reporting

### Dependencies
- **Core**: PyYAML >= 6.0
- **Optional (embedding)**: Ollama >= 0.1.0, FAISS-CPU >= 1.7.0, NumPy >= 1.24.0

### System Requirements
- Python 3.10 or higher
- Git (for version control integration)

### Known Limitations
- Semantic analysis requires Ollama server running locally
- Graph drift tracking is experimental and may change
- Some advanced features require additional dependencies

### Documentation
- See [README.md](README.md) for installation and usage
- See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines
- See [LICENSE](LICENSE) for license information

---

## [Unreleased]

### Planned
- Enhanced visualization options
- Additional language support
- Performance improvements
- More detectors and analyzers
- Web interface (experimental)
