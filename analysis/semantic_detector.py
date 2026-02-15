"""
Semantic detector for PROJECT CONTROL.
Identifies:
  1. Semantic orphans: files with low similarity to rest of codebase
  2. Semantic duplicates: files with high similarity to other files
Uses qwen3-embedding:8b via EmbeddingService.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from core.embedding_service import EmbeddingService, cosine_similarity


def _is_code_file(path: str) -> bool:
    """Filter for code files (JS/TS/Python) – skip assets/docs."""
    ext = os.path.splitext(path)[1].lower()
    return ext in {".js", ".ts", ".jsx", ".tsx", ".py", ".mjs", ".cjs"}


def analyze(snapshot: Dict[str, Any], patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Perform semantic analysis of codebase.
    
    Returns:
        List of semantic findings with structure:
        [
            {
                "type": "orphan" | "duplicate",
                "path": "src/file.js",
                "similarity": 0.42,  # avg similarity for orphans, pairwise for duplicates
                "related_to": "src/other.js"  # only for duplicates
            },
            ...
        ]
    """
    files = snapshot.get("files", [])
    if not files:
        return []
    
    # Initialize embedding service
    project_root = Path.cwd()
    embedding_service = EmbeddingService(project_root)
    
    # Load configuration (with defaults)
    embedding_config = patterns.get("embedding", {})
    orphan_threshold = embedding_config.get("semantic_orphan_threshold", 0.65)
    duplicate_threshold = embedding_config.get("semantic_duplicate_threshold", 0.92)
    
    # Step 1: Compute embeddings for all code files
    file_embeddings: Dict[str, List[float]] = {}
    file_sha256: Dict[str, str] = {}
    
    for file in files:
        path = file.get("path", "")
        sha256 = file.get("sha256", "")
        
        if not _is_code_file(path) or not sha256:
            continue
        
        try:
            # Read file content (relative to project root)
            full_path = project_root / path
            if not full_path.exists():
                continue
            
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            if len(content.strip()) < 50:  # Skip near-empty files
                continue
            
            # Compute embedding (cached via SHA256)
            embedding = embedding_service.compute_embedding(content, sha256)
            file_embeddings[path] = embedding
            file_sha256[path] = sha256
            
        except Exception as e:
            print(f"⚠️  Warning: Failed to process {path} ({e})")
            continue
    
    if len(file_embeddings) < 2:
        return []  # Need at least 2 files for semantic analysis
    
    # Step 2: Detect semantic orphans (files with low avg similarity to others)
    findings: List[Dict[str, Any]] = []
    paths = list(file_embeddings.keys())
    
    for path in paths:
        similarities = []
        for other_path in paths:
            if path == other_path:
                continue
            sim = cosine_similarity(file_embeddings[path], file_embeddings[other_path])
            similarities.append(sim)
        
        avg_sim = sum(similarities) / len(similarities) if similarities else 0.0
        
        if avg_sim < orphan_threshold:
            findings.append({
                "type": "orphan",
                "path": path,
                "similarity": round(avg_sim, 3),
                "related_to": None
            })
    
    # Step 3: Detect semantic duplicates (files with high pairwise similarity)
    for i, path1 in enumerate(paths):
        for path2 in paths[i + 1:]:
            sim = cosine_similarity(file_embeddings[path1], file_embeddings[path2])
            if sim > duplicate_threshold:
                findings.append({
                    "type": "duplicate",
                    "path": path1,
                    "similarity": round(sim, 3),
                    "related_to": path2
                })
    
    # Sort findings: orphans first, then duplicates, by similarity (ascending for orphans)
    findings.sort(key=lambda x: (0 if x["type"] == "orphan" else 1, x["similarity"]))
    
    return findings