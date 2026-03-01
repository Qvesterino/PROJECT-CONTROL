from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

import faiss
import numpy as np

from project_control.embedding.config import EmbedConfig
from project_control.embedding.embed_provider import OllamaEmbedProvider
from project_control.embedding.index_builder import _normalize


@dataclass(frozen=True)
class SearchResult:
    file_path: str
    start_offset: int
    end_offset: int
    similarity_score: float
    preview_text: str


class SearchEngine:
    def __init__(self, project_root: Path, cfg: EmbedConfig | None = None):
        self.cfg = cfg or EmbedConfig()
        self.root = project_root
        self._load_index()
        self.provider = OllamaEmbedProvider(self.cfg)

    def _load_index(self) -> None:
        if not self.cfg.index_path.exists():
            raise FileNotFoundError("Embedding index not found. Run 'pc embed build' first.")
        self.index = faiss.read_index(str(self.cfg.index_path))
        self.metadata = json.loads(self.cfg.metadata_path.read_text(encoding="utf-8"))

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        query_vec = self.provider.embed(query)
        if self.index.d != len(query_vec):
            raise RuntimeError("Embedding dimension mismatch between index and provider.")
        query_mat = _normalize(np.array([query_vec], dtype=np.float32))
        scores, idxs = self.index.search(query_mat, top_k)
        results: List[SearchResult] = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            meta = self.metadata[idx]
            results.append(
                SearchResult(
                    file_path=meta.get("file_path", ""),
                    start_offset=int(meta.get("start_offset", 0)),
                    end_offset=int(meta.get("end_offset", 0)),
                    similarity_score=float(score),
                    preview_text=meta.get("preview_text", ""),
                )
            )
        return results
