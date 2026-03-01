from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(frozen=True)
class Chunk:
    text: str
    file_path: str
    start_offset: int
    end_offset: int


class Chunker:
    def __init__(self, chunk_size_chars: int = 800, overlap_chars: int = 200):
        self.chunk_size = chunk_size_chars
        self.overlap = overlap_chars

    def chunk_file(self, path: Path) -> List[Chunk]:
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text:
            return []
        chunks: List[Chunk] = []
        step = max(1, self.chunk_size - self.overlap)
        start = 0
        length = len(text)
        while start < length:
            end = min(length, start + self.chunk_size)
            piece = text[start:end]
            if piece:
                chunks.append(
                    Chunk(
                        text=piece,
                        file_path=path.as_posix(),
                        start_offset=start,
                        end_offset=end,
                    )
                )
            if end == length:
                break
            start += step
        return chunks
