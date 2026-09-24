"""Domain-scoped retrieval over fictional policy documents."""

import hashlib
import json
from pathlib import Path

import faiss
import numpy as np
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
CACHE = ROOT / ".cache" / "policy_embeddings.npz"
DOMAIN_FILES = {
    "hr": {"company.md", "leave.md"},
    "leave": {"leave.md"},
    "payroll": set(),
    "finance": {"finance.md"},
    "it": {"it.md"},
    "access": {"it.md"},
    "facilities": set(),
    "travel": {"travel.md"},
    "benefits": set(),
    "learning": set(),
    "procurement": set(),
    "company": {"company.md"},
}


class Knowledge:
    def __init__(self, api_key: str, embedding_model: str):
        self.client = OpenAI(api_key=api_key)
        self.model = embedding_model
        self.chunks: list[tuple[str, str]] = []
        for path in sorted(DATA.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            sections = [part.strip() for part in content.split("\n## ") if part.strip()]
            self.chunks.extend(
                (path.name, ("## " if index else "") + section)
                for index, section in enumerate(sections)
            )
        if not self.chunks:
            raise RuntimeError("No demo policy files found under data/")
        content_key = hashlib.sha256(
            json.dumps([embedding_model, self.chunks], ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        vectors = None
        if CACHE.exists():
            try:
                with np.load(CACHE, allow_pickle=False) as saved:
                    if str(saved["key"]) == content_key:
                        vectors = saved["vectors"].astype("float32")
            except (OSError, ValueError, KeyError):
                vectors = None
        if vectors is None or len(vectors) != len(self.chunks):
            vectors = self._embed([text for _, text in self.chunks])
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(CACHE, key=content_key, vectors=vectors)
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)

    def _embed(self, texts: list[str]) -> np.ndarray:
        response = self.client.embeddings.create(model=self.model, input=texts)
        matrix = np.asarray([item.embedding for item in response.data], dtype="float32")
        faiss.normalize_L2(matrix)
        return matrix

    def search(self, query: str, domains: list[str], limit: int = 4) -> list[dict]:
        allowed = set().union(*(DOMAIN_FILES.get(domain, set()) for domain in domains))
        if not allowed:
            return []
        vector = self._embed([query])
        scores, indices = self.index.search(vector, len(self.chunks))
        result = []
        for score, index in zip(scores[0], indices[0]):
            if index < 0:
                continue
            title, content = self.chunks[int(index)]
            if title in allowed:
                result.append({"source": title, "text": content[:2400], "score": float(score)})
            if len(result) >= limit:
                break
        return result
