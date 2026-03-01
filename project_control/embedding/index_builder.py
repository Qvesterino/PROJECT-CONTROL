from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np

from project_control.embedding.config import EmbedConfig
from project_control.embedding.chunker import Chunker, Chunk
from project_control.embedding.embed_provider import OllamaEmbedProvider
from project_control.config.patterns_loader import load_patterns

IGNORE_DIRS = {".git", ".project-control", "node_modules", "__pycache__"}


def _normalize(vecs: np.ndarray) -> np.ndarray:
    if vecs.size == 0:
        return vecs
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


def _iter_files(root: Path, exts: Tuple[str, ...], ignore_dirs: set[str]) -> List[Path]:
    files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix in exts:
                files.append(path.relative_to(root))
    return sorted(files, key=lambda p: p.as_posix())


def build_index(project_root: Path, cfg: EmbedConfig, overwrite: bool = False) -> Tuple[int, int, int]:
    embedding_dir = project_root / cfg.embedding_dir
    embedding_dir.mkdir(parents=True, exist_ok=True)

    if not overwrite and cfg.index_path.exists():
        raise RuntimeError("Index exists; use rebuild.")

    patterns = load_patterns(str(project_root))
    ignore_dirs = set(patterns.get("ignore_dirs", [])) | IGNORE_DIRS

    files = _iter_files(project_root, cfg.exts, ignore_dirs)
    chunker = Chunker(cfg.chunk_size_chars, cfg.overlap_chars)
    provider = OllamaEmbedProvider(cfg)

    chunks: List[Chunk] = []
    for path in files:
        chunks.extend(chunker.chunk_file(project_root / path))

    vectors = []
    metadata = []
    for idx, chunk in enumerate(chunks, start=1):
        vec = provider.embed(chunk.text)
        vectors.append(vec)
        preview = chunk.text[:200].replace("\n", " ").replace("\r", " ")
        metadata.append(
            {
                "id": idx,
                "file_path": chunk.file_path,
                "start_offset": chunk.start_offset,
                "end_offset": chunk.end_offset,
                "preview_text": preview,
            }
        )

    if vectors:
        dim = len(vectors[0])
        matrix = np.stack(vectors, axis=0).astype(np.float32)
        matrix = _normalize(matrix)
        index = faiss.IndexFlatIP(dim)
        index.add(matrix)
        faiss.write_index(index, str(cfg.index_path))
    else:
        dim = 0
        faiss.write_index(faiss.IndexFlatIP(0), str(cfg.index_path))

    cfg.metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    meta_payload = {
        "model": cfg.model,
        "dim": dim,
        "chunk_size_chars": cfg.chunk_size_chars,
        "overlap_chars": cfg.overlap_chars,
        "created_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "file_count": len(files),
        "chunk_count": len(chunks),
    }
    cfg.meta_path.write_text(json.dumps(meta_payload, indent=2), encoding="utf-8")

    return len(files), len(chunks), dim
