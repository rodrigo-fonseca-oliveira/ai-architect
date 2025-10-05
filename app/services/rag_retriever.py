import os
import hashlib
from typing import List, Dict, Any

import chromadb
from chromadb.utils import embedding_functions


class EmbeddingsProvider:
    def embed(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError


class LocalEmbeddings(EmbeddingsProvider):
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def embed(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()


class OpenAIEmbeddings(EmbeddingsProvider):
    def __init__(self, model: str = "text-embedding-3-small"):
        import openai

        self.client = openai.OpenAI(api_key=os.getenv("LLM_API_KEY"))
        self.model = model

    def embed(self, texts: List[str]) -> List[List[float]]:
        # Batch for simplicity; OpenAI SDK v1 style
        resp = self.client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in resp.data]


class StubEmbeddings(EmbeddingsProvider):
    def __init__(self, dim: int = 384):
        self.dim = dim

    def embed(self, texts: List[str]) -> List[List[float]]:
        vecs = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            # Repeat hash to reach dim
            raw = (h * ((self.dim // len(h)) + 1))[: self.dim]
            vec = [(b - 128) / 128.0 for b in raw]
            vecs.append(vec)
        return vecs


class RAGRetriever:
    def __init__(self, persist_path: str, provider: str = "local", model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.client = chromadb.PersistentClient(path=persist_path)
        self.collection = self.client.get_or_create_collection(name="docs")
        self.provider_name = provider
        if provider == "openai":
            self.emb = OpenAIEmbeddings(model=os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-small"))
        elif provider == "stub":
            self.emb = StubEmbeddings()
        else:
            self.emb = LocalEmbeddings(model_name=os.getenv("EMBEDDINGS_MODEL", model))

    @staticmethod
    def reformulate_queries(question: str, n: int) -> list[str]:
        base = question.strip()
        variants = [base]
        if n <= 1:
            return variants
        variants.append(f"Key terms: {base}")
        if n > 2:
            variants.append(f"Rephrase: {base}")
        return variants[:n]

    @staticmethod
    def merge_citations(citation_lists: list[list[dict]], k: int) -> list[dict]:
        seen = set()
        merged = []
        for lst in citation_lists:
            for c in lst:
                key = (c.get("source"), c.get("page"))
                if key in seen:
                    continue
                seen.add(key)
                merged.append(c)
                if len(merged) >= k:
                    return merged
        return merged

    @staticmethod
    def hyde_snippet(question: str) -> str:
        return f"Hypothetical answer summary: This question likely pertains to policy and compliance for: {question[:80]}..."

    def retrieve_multi(self, question: str, k: int = 3, n: int = 3, hyde: bool = False) -> list[dict]:
        queries = self.reformulate_queries(question, n)
        if hyde:
            snippet = self.hyde_snippet(question)
            queries.append(f"{snippet}\n\n{question}")
        results: list[list[dict]] = []
        for q in queries:
            try:
                results.append(self.retrieve(q, k=k))
            except Exception:
                results.append([])
        return self.merge_citations(results, k)

    def ingest(self, docs_path: str):
        # Simple ingestion: read .txt and .md files with idempotency by content hash
        docs = []
        metadatas = []
        ids = []
        for root, _, files in os.walk(docs_path):
            for f in files:
                if f.lower().endswith((".txt", ".md")):
                    p = os.path.join(root, f)
                    with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                        text = fh.read()
                    rel = os.path.relpath(p, docs_path)
                    # Deterministic ID: hash of content + relative path
                    h = hashlib.sha256((rel + "|" + text).encode("utf-8")).hexdigest()
                    docs.append(text)
                    metadatas.append({"source": rel})
                    ids.append(h)
        if not docs:
            return 0
        embeddings = self.emb.embed(docs)
        # Use upsert semantics if available; chromadb collection.add will error on duplicate IDs.
        # To keep idempotent, we first delete any existing with same IDs, then add.
        try:
            self.collection.delete(ids=ids)
        except Exception:
            pass
        self.collection.add(documents=docs, embeddings=embeddings, metadatas=metadatas, ids=ids)
        return len(docs)

    def ensure_loaded(self, docs_path: str):
        try:
            count = self.collection.count()
        except Exception:
            count = 0
        if count == 0 and os.path.isdir(docs_path):
            self.ingest(docs_path)

    def retrieve(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        qvec = self.emb.embed([query])[0]
        results = self.collection.query(query_embeddings=[qvec], n_results=k)
        citations: List[Dict[str, Any]] = []
        docs = results.get("documents") or [[]]
        metas = results.get("metadatas") or [[]]
        if docs and metas and len(docs[0]) and len(metas[0]):
            for doc, meta in zip(docs[0], metas[0]):
                snippet = doc[:200].replace("\n", " ") if doc else None
                citations.append({"source": meta.get("source", "unknown"), "page": None, "snippet": snippet})
        return citations
