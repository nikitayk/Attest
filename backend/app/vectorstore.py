"""Chroma vector store with OpenAI embeddings."""

from __future__ import annotations

from typing import Any

from app.config import get_settings


class VectorStore:
    """ChromaDB wrapper with OpenAI embeddings API."""

    def __init__(self, collection_name: str = "attest_chunks"):
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from openai import OpenAI

        settings = get_settings()
        self._openai_client = OpenAI(api_key=settings.openai_api_key)
        self._embedding_model = settings.embedding_model
        self._chroma_path = settings.resolve_path(settings.chroma_path)

        # Keep Chroma on disk-backed storage to avoid duplicating the full index in RAM.
        self._chroma_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(self._chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts using OpenAI API."""
        response = self._openai_client.embeddings.create(
            input=texts,
            model=self._embedding_model
        )
        return [item.embedding for item in response.data]

    def add_chunks(
        self,
        chunk_ids: list[str],
        texts: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Add chunks with embeddings to the collection."""
        embeddings = self.embed_texts(texts)
        self._collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

    def query(self, query_text: str, top_k: int = 3) -> list[dict[str, Any]]:
        """
        Retrieve top-k chunks by semantic similarity.

        Returns list of dicts with: id, text, metadata, distance.
        """
        query_embedding = self.embed_texts([query_text])

        results = self._collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, self._collection.count()),
        )

        # Convert Chroma format to list of dicts
        chunks = []
        for i in range(len(results["ids"][0])):
            chunks.append(
                {
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                }
            )

        return chunks

    def delete_collection(self) -> None:
        """Wipe the collection for reseed-on-boot."""
        self._client.delete_collection(self._collection.name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection.name,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        """Return total number of chunks in the collection."""
        return self._collection.count()

    def add_documents(
        self,
        doc_id: str,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        """
        Add all chunks for a single document.
        
        Used for document upload functionality.
        """
        chunk_ids = [f"{doc_id}#{i}" for i in range(len(chunks))]
        metadatas = [
            {"doc_id": doc_id, "chunk_index": i}
            for i in range(len(chunks))
        ]
        
        self._collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )

    def delete_document(self, doc_id: str) -> None:
        """
        Delete all chunks for a specific document.
        
        Used for document deletion functionality.
        """
        # Get all chunk IDs for this document
        all_chunks = self._collection.get()
        ids_to_delete = []
        
        for chunk_id, metadata in zip(all_chunks["ids"], all_chunks["metadatas"]):
            if metadata.get("doc_id") == doc_id:
                ids_to_delete.append(chunk_id)
        
        if ids_to_delete:
            self._collection.delete(ids=ids_to_delete)
