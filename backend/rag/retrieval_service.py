import logging
import os
from typing import List, Dict

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader

from config import Config

for _name in ("pypdf", "pypdf._reader"):
    logging.getLogger(_name).setLevel(logging.ERROR)


class RetrievalService:
    """
    Handles:
    - Document loading
    - Chunking
    - Embedding creation
    - FAISS indexing
    - Query retrieval
    """

    def __init__(self, docs_path: str = "docs"):
        self.docs_path = docs_path
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

        self.chunks: List[Dict] = []
        self.index = None

        self._load_documents()
        self._build_index()


    def _load_documents(self):
        if not os.path.exists(self.docs_path):
            os.makedirs(self.docs_path, exist_ok=True)
            return
        for filename in os.listdir(self.docs_path):
            if filename.endswith(".pdf"):
                file_path = os.path.join(self.docs_path, filename)
                reader = PdfReader(file_path, strict=False)

                for page_number, page in enumerate(reader.pages, start=1):
                    text = page.extract_text()
                    if text:
                        self._chunk_text(
                            text=text,
                            document_name=filename,
                            page_number=page_number
                        )


    def _chunk_text(self, text: str, document_name: str, page_number: int):
        words = text.split()
        chunk_size = Config.CHUNK_SIZE
        overlap = Config.CHUNK_OVERLAP

        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)

            self.chunks.append({
                "text": chunk_text,
                "document": document_name,
                "page": page_number
            })

            start += chunk_size - overlap


    def _build_index(self):
        if not self.chunks:
            self.index = None
            return
        texts = [chunk["text"] for chunk in self.chunks]
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)

        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)

    def retrieve(self, query: str) -> List[Dict]:
        if self.index is None:
            return []
        query_embedding = self.embedding_model.encode(
            [query],
            convert_to_numpy=True
        )

        distances, indices = self.index.search(query_embedding, Config.TOP_K)

        results = []
        for idx, distance in zip(indices[0], distances[0]):
            chunk = self.chunks[idx]

            results.append({
                "text": chunk["text"],
                "document": chunk["document"],
                "page": chunk["page"],
                "relevance_score": float(1 / (1 + distance))
            })

        return results