from __future__ import annotations

import requests
import numpy as np
from typing import List

from project_control.embedding.config import EmbedConfig


class OllamaEmbedProvider:
    def __init__(self, config: EmbedConfig):
        self.config = config

    def _call(self, text: str) -> List[float]:
        url = f"{self.config.base_url.rstrip('/')}/api/embeddings"
        try:
            resp = requests.post(
                url,
                json={"model": self.config.model, "input": text},
                timeout=60,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc
        if resp.status_code != 200:
            raise RuntimeError(f"Ollama error {resp.status_code}: {resp.text}")
        data = resp.json()
        emb = data.get("embedding")
        if not isinstance(emb, list) or not all(isinstance(v, (int, float)) for v in emb):
            raise RuntimeError("Invalid embedding payload from Ollama")
        return [float(v) for v in emb]

    def embed(self, text: str) -> np.ndarray:
        vec = self._call(text)
        return np.array(vec, dtype=np.float32)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        vectors = [self.embed(t) for t in texts]
        if not vectors:
            return np.zeros((0, 0), dtype=np.float32)
        return np.stack(vectors, axis=0)
