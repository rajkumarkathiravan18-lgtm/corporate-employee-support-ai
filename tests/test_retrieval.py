from backend.rag import retrieval


class FakeEmbeddingResponse:
    def __init__(self, texts):
        self.data = [type("Item", (), {"embedding": [float(len(t) % 7 + 1), 1.0, 0.5]}) for t in texts]


class FakeOpenAI:
    calls = []

    def __init__(self, api_key):
        self.embeddings = self

    def create(self, model, input):
        self.calls.append(input)
        return FakeEmbeddingResponse(input)


def test_cache_and_domain_scope(tmp_path, monkeypatch):
    FakeOpenAI.calls.clear()
    monkeypatch.setattr(retrieval, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(retrieval, "CACHE", tmp_path / "embeddings.npz")
    retrieval.Knowledge("test-key", "demo-model")
    assert len(FakeOpenAI.calls) == 1
    another = retrieval.Knowledge("test-key", "demo-model")
    assert len(FakeOpenAI.calls) == 1
    found = another.search("How do I travel?", ["travel"])
    assert found and all(item["source"] == "travel.md" for item in found)
    assert another.search("What is payroll?", ["payroll"]) == []
