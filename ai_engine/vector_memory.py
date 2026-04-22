import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

class VectorMemory:
    def __init__(self, persist_dir="data/vector_memory"):
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.index = None
        self.docs = []
        self.max_chat_history_chars = 240
        self._load_store()

    def _load_store(self):
        index_path = os.path.join(self.persist_dir, "index.faiss")
        docs_path = os.path.join(self.persist_dir, "docs.pkl")
        if os.path.exists(index_path) and os.path.exists(docs_path):
            try:
                self.index = faiss.read_index(index_path)
                with open(docs_path, "rb") as f:
                    self.docs = pickle.load(f)
                self._compact_store()
            except Exception:
                self.index = None
                self.docs = []

    def _save_store(self):
        if self.index is None:
            return
        index_path = os.path.join(self.persist_dir, "index.faiss")
        docs_path = os.path.join(self.persist_dir, "docs.pkl")
        faiss.write_index(self.index, index_path)
        with open(docs_path, "wb") as f:
            pickle.dump(self.docs, f)

    def _rebuild_index(self):
        if not self.docs:
            self.index = None
            return
        texts = [doc["page_content"] for doc in self.docs]
        vectors = self._embed_texts(texts)
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)

    def _compact_doc(self, doc):
        metadata = doc.get("metadata", {})
        text = " ".join(str(doc.get("page_content", "")).split())
        if metadata.get("type") == "chat_history" and len(text) > self.max_chat_history_chars:
            text = text[: self.max_chat_history_chars - 3] + "..."
        return {"page_content": text, "metadata": metadata}

    def _compact_store(self):
        compacted = [self._compact_doc(doc) for doc in self.docs]
        changed = compacted != self.docs
        self.docs = compacted
        if changed:
            self._rebuild_index()
            self._save_store()

    def is_empty(self):
        return self.index is None or len(self.docs) == 0

    def _embed_texts(self, texts):
        return np.array(self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True), dtype="float32")

    def add_documents(self, items):
        texts = [item["text"] for item in items]
        vectors = self._embed_texts(texts)
        for item in items:
            self.docs.append({"page_content": item["text"], "metadata": item.get("metadata", {})})
        if self.index is None:
            self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)
        self._save_store()

    def similarity_search(self, query, k=5):
        if self.index is None or len(self.docs) == 0:
            return []
        vector = self._embed_texts([query])
        scores, indices = self.index.search(vector, k)
        results = []
        for idx in indices[0]:
            if idx < 0 or idx >= len(self.docs):
                continue
            results.append(self.docs[idx])
        return results
