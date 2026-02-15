"""
Embedding service for PROJECT CONTROL.
Uses SHA256 hashes as cache keys for deterministic, incremental embedding computation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ollama import embeddings as ollama_embeddings
from hashlib import sha256 as hashlib_sha256


class EmbeddingService:
    """Service for computing and caching embeddings using SHA256-based cache."""

    def __init__(self, project_root: Path, cache_dir: Optional[Path] = None):
        self.project_root = project_root
        self.cache_dir = cache_dir or project_root / ".project-control" / "embeddings"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "embeddings_cache.json"
        self.cache: Dict[str, List[float]] = self._load_cache()
         # Configurable via patterns.yaml in future
        self.model_name = os.getenv("PC_EMBED_MODEL", "qwen3-embedding:8b-q4_K_M")
        
    def _load_cache(self) -> Dict[str, List[float]]:
        """Load embedding cache from JSON file."""
        if self.cache_file.exists():
            try:
                return json.loads(self.cache_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"⚠️  Warning: Failed to load embedding cache ({e}), starting fresh")
        return {}

    def _save_cache(self) -> None:
        """Persist cache to disk."""
        self.cache_file.write_text(json.dumps(self.cache, indent=2), encoding="utf-8")

    def _compute_sha256(self, content: str) -> str:
        """Compute SHA256 hash of content (for cache key)."""
        return hashlib_sha256(content.encode("utf-8")).hexdigest()

    def _chunk_content(self, content: str, chunk_size: int = 4000) -> List[str]:
        """
        Split content into chunks for better semantic representation.
        For files >8KB, we compute embeddings per chunk and average them.
        """
        if len(content) <= chunk_size * 2:
            return [content]  # Small files: single chunk
        
        lines = content.split("\n")
        chunks = []
        current_chunk = []
        current_size = 0
        
        for line in lines:
            line_size = len(line) + 1  # +1 for newline
            if current_size + line_size > chunk_size and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_size = 0
            current_chunk.append(line)
            current_size += line_size
        
        if current_chunk:
            chunks.append("\n".join(current_chunk))
        
        return chunks[:5]  # Limit to 5 chunks max (prevents OOM on huge files)

    def _average_embeddings(self, embeddings: List[List[float]]) -> List[float]:
        """Average multiple embeddings into a single vector."""
        if not embeddings:
            return []
        dim = len(embeddings[0])
        averaged = [0.0] * dim
        for emb in embeddings:
            for i in range(dim):
                averaged[i] += emb[i]
        return [v / len(embeddings) for v in averaged]

    def compute_embedding(self, content: str, sha256: str) -> List[float]:
        """
        Compute embedding for content using Ollama.
        Uses SHA256 as cache key to avoid redundant computation.
        """
        # Check cache first
        if sha256 in self.cache:
            return self.cache[sha256]
        
        # Chunk large files for better semantic representation
        chunks = self._chunk_content(content)
        chunk_embeddings = []
        
        for chunk in chunks:
            try:
                result = ollama_embeddings(model=self.model_name, prompt=chunk)
                chunk_embeddings.append(result["embedding"])
            except Exception as e:
                print(f"⚠️  Warning: Failed to embed chunk ({e}), skipping")
                continue
        
        if not chunk_embeddings:
            raise ValueError("Failed to compute any embeddings for content")
        
        # Average chunk embeddings for final representation
        final_embedding = self._average_embeddings(chunk_embeddings)
        self.cache[sha256] = final_embedding
        self._save_cache()
        
        return final_embedding

    def invalidate_cache(self, sha256: str) -> None:
        """Remove embedding from cache (e.g., when file content changes)."""
        self.cache.pop(sha256, None)
        self._save_cache()

    def clear_cache(self) -> None:
        """Clear entire embedding cache."""
        self.cache = {}
        self._save_cache()
        print("✅ Embedding cache cleared")


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)