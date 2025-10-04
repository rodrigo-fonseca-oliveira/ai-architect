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

    def ingest(self, docs_path: str):
        # Simple ingestion: read .txt and .md files
        docs = []
        metadatas = []
        ids = []
        for root, _, files in os.walk(docs_path):
            for f in files:
                if f.lower().endswith((".txt", ".md")):
                    p = os.path.join(root, f)
                    with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                        text = fh.read()
                    docs.append(text)
                    metadatas.append({"source": os.path.relpath(p, docs_path)})
                    ids.append(os.path.relpath(p, docs_path))
        if not docs:
            return 0
        embeddings = self.emb.embed(docs)
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
