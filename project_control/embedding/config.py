from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EmbedConfig:
    base_url: str = "http://localhost:11434"
    model: str = "nomic-embed-text"
    chunk_size_chars: int = 800
    overlap_chars: int = 200
    exts: tuple[str, ...] = (".js", ".ts", ".md")

    @property
    def embedding_dir(self) -> Path:
        return Path(".project-control") / "embedding"

    @property
    def index_path(self) -> Path:
        return self.embedding_dir / "index.faiss"

    @property
    def metadata_path(self) -> Path:
        return self.embedding_dir / "metadata.json"

    @property
    def meta_path(self) -> Path:
        return self.embedding_dir / "meta.json"
