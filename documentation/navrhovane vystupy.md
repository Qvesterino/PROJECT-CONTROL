
## 🔥 Ghost v2 – Smart Severity
{
  "orphans": [...],
  "legacy_snippets": [...],
  "session_files": [...],
  "duplicates": [...]
}

{ "scale": "...", "opacity": "...", "emissive": "...", "position": "...", }

✅ 1. Architektúra

pc.py = iba orchestration layer ✔

scan → core.scanner

ghost → core.ghost

writers → core.writers

render → core.markdown_renderer

Architektúra Ghost v2 flow
pc.py
   ↓
core/ghost.py
   ↓
analysis/*
   ↓
structured result
   ↓
exports/ghost_candidates.md