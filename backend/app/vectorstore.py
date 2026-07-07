"""pgvector vector store with sentence-transformers embeddings."""

from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.db_models import Base, Chunk
from pgvector.sqlalchemy import Vector
from sentence_transformers import SentenceTransformer
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


def _engine_connect_args(database_url: str) -> dict:
    if "sslmode=require" in database_url or "neon.tech" in database_url:
        return {"ssl": "require"}
    return {}


class VectorStore:
    """pgvector wrapper with sentence-transformers embeddings."""

    def __init__(self):
        settings = get_settings()
        db_url = (
            settings.database_url.replace("postgres://", "postgresql+asyncpg://")
            .replace("postgresql://", "postgresql+asyncpg://")
        )
        self.engine = create_async_engine(
            db_url,
            echo=False,
            connect_args=_engine_connect_args(settings.database_url),
        )
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Load embedding model
        self._embedding_model = SentenceTransformer(settings.embedding_model)
        self._embedding_dim = self._embedding_model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts using sentence-transformers."""
        embeddings = self._embedding_model.encode(texts, convert_to_numpy=False)
        # convert_to_numpy=False returns a list, but ensure it's the right format
        if hasattr(embeddings, 'tolist'):
            return embeddings.tolist()
        return embeddings

    async def add_chunks(
        self,
        chunk_ids: list[str],
        texts: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Add chunks with embeddings to the collection."""
        embeddings = self.embed_texts(texts)
        
        async with self.async_session() as session:
            for chunk_id, text, embedding, metadata in zip(chunk_ids, texts, embeddings, metadatas):
                doc_id = metadata.get("doc_id")
                chunk_index = metadata.get("chunk_index")
                
                # Ensure embedding is a list of floats, not a string
                if isinstance(embedding, str):
                    import json
                    embedding = json.loads(embedding)
                
                chunk = Chunk(
                    doc_id=doc_id,
                    chunk_index=chunk_index,
                    text=text,
                    embedding=embedding,
                )
                session.add(chunk)
            
            await session.commit()

    async def query(self, query_text: str, top_k: int = 3) -> list[dict[str, Any]]:
        """
        Retrieve top-k chunks by semantic similarity using pgvector.

        Returns list of dicts with: id, text, metadata, distance.
        """
        query_embedding = self.embed_texts([query_text])[0]
        
        async with self.async_session() as session:
            # Use pgvector cosine similarity
            from sqlalchemy import func
            
            result = await session.execute(
                select(
                    Chunk,
                    (1 - Chunk.embedding.cosine_distance(query_embedding)).label("similarity")
                )
                .order_by(Chunk.embedding.cosine_distance(query_embedding))
                .limit(top_k)
            )
            
            chunks = []
            for row in result:
                chunk, similarity = row
                chunks.append({
                    "id": f"{chunk.doc_id}#{chunk.chunk_index}",
                    "text": chunk.text,
                    "metadata": {"doc_id": chunk.doc_id, "chunk_index": chunk.chunk_index},
                    "distance": 1 - similarity,  # Convert similarity to distance
                })
            
            return chunks

    async def delete_collection(self) -> None:
        """Wipe all chunks for reseed-on-boot."""
        async with self.async_session() as session:
            await session.execute(delete(Chunk))
            await session.commit()

    async def count(self) -> int:
        """Return total number of chunks in the collection."""
        async with self.async_session() as session:
            from sqlalchemy import func
            
            result = await session.execute(select(func.count()).select_from(Chunk))
            return result.scalar() or 0

    async def add_documents(
        self,
        doc_id: str,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        """
        Add all chunks for a single document.
        
        Used for document upload functionality.
        """
        async with self.async_session() as session:
            for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                # Ensure embedding is a list of floats, not a string
                if isinstance(embedding, str):
                    import json
                    embedding = json.loads(embedding)
                
                chunk = Chunk(
                    doc_id=doc_id,
                    chunk_index=i,
                    text=chunk_text,
                    embedding=embedding,
                )
                session.add(chunk)
            
            await session.commit()

    async def delete_document(self, doc_id: str) -> None:
        """Delete all chunks for a specific document."""
        async with self.async_session() as session:
            await session.execute(delete(Chunk).where(Chunk.doc_id == doc_id))
            await session.commit()
