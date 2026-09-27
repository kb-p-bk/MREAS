"""
vector_store.py
---------------
ChromaDB wrapper for moon_reader_extract.
"""

import hashlib
from pathlib import Path

import chromadb

from mreas.storage.db import get_connection, get_pending_chunks, mark_chunks_indexed
from mreas.core.config import CHROMA_DIR
COLLECTION_NAME = "moon_reader_notes"
EMBED_BATCH_SIZE = 500  # ChromaDB handles this well; tune if needed


class MoonReaderVectorStore:
    def __init__(self, db_dir: str | Path = CHROMA_DIR):
        self.client = chromadb.PersistentClient(path=str(db_dir))
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME
        )

    # ── Embedding API ─────────────────────────────────────────────────────────

    def embed_pending(self, db_path: Path, verbose: bool = True) -> int:
        """
        Read all chunks with indexed_in_chroma=0 from the database,
        embed them in batches, and mark them as indexed.

        Returns the number of chunks newly embedded.
        """
        conn = get_connection(db_path)
        pending = get_pending_chunks(conn)

        if not pending:
            if verbose:
                print("[EMBED] No pending chunks to index.")
            conn.close()
            return 0

        if verbose:
            print(f"[EMBED] Indexing {len(pending)} pending chunk(s)...")

        ids, docs, metas, hashes = [], [], [], []

        for row in pending:
            source_name = row["source_name"]
            highlight = row["highlight"] or ""
            user_note = row["user_note"] or ""
            content_hash = row["content_hash"]

            # Build document text
            content = (
                f"BOOK: {source_name}\n"
                f"HIGHLIGHT: {highlight}\n"
                f"MY NOTE: {user_note}"
            )

            # ChromaDB ID: use content_hash directly (stable, unique)
            chroma_id = f"chunk_{content_hash}"

            ids.append(chroma_id)
            docs.append(content)
            metas.append({
                "source": source_name,
                "book": source_name,   # keep 'book' for V1 search compatibility
                "type": row["origin"] if row["origin"] == "external" else "highlight",
                "origin": row["origin"],
            })
            hashes.append(content_hash)

        # Upsert in batches
        total_upserted = 0
        for start in range(0, len(ids), EMBED_BATCH_SIZE):
            batch_ids = ids[start: start + EMBED_BATCH_SIZE]
            batch_docs = docs[start: start + EMBED_BATCH_SIZE]
            batch_metas = metas[start: start + EMBED_BATCH_SIZE]
            batch_hashes = hashes[start: start + EMBED_BATCH_SIZE]

            try:
                self.collection.upsert(
                    ids=batch_ids,
                    documents=batch_docs,
                    metadatas=batch_metas,
                )
                mark_chunks_indexed(conn, batch_hashes)
                total_upserted += len(batch_ids)
                if verbose:
                    print(
                        f"[EMBED] Batch {start // EMBED_BATCH_SIZE + 1}: "
                        f"upserted {len(batch_ids)} chunks "
                        f"({total_upserted}/{len(ids)})"
                    )
            except Exception as e:
                print(f"[ERROR] Batch upsert failed: {e}")

        conn.close()
        if verbose:
            print(f"[EMBED] Done. {total_upserted} chunk(s) indexed.")
        return total_upserted

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        source_filter: str | None = None,
    ) -> dict:
        """
        Semantic search. Optionally filter by source name.

        source_filter matches against 'source' and 'book'
        metadata fields using a ChromaDB $or where clause.
        """
        kwargs: dict = {
            "query_texts": [query_text],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }

        if source_filter:
            # ChromaDB where filter: match either 'source' or 'book' field
            kwargs["where"] = {
                "$or": [
                    {"source": {"$eq": source_filter}},
                    {"book": {"$eq": source_filter}},
                ]
            }

        return self.collection.query(**kwargs)

    def get_total_count(self) -> int:
        return self.collection.count()

    def list_sources_in_chroma(self) -> list[str]:
        """Return all unique source/book names in the ChromaDB collection."""
        # ChromaDB doesn't have a native distinct query; fetch all metadata
        all_meta = self.collection.get(include=["metadatas"])["metadatas"]
        seen = set()
        for m in all_meta:
            name = m.get("source") or m.get("book") or ""
            if name:
                seen.add(name)
        return sorted(seen)

    # ── V1 compatibility API ──────────────────────────────────────────────────

    def upsert_batch(
        self,
        ids: list[str],
        docs: list[str],
        metas: list[dict],
        title: str,
        progress_str: str,
    ):
        """
        V1 per-book upsert. Kept for backward compatibility.
        New code should use embed_pending() instead.
        """
        if not ids:
            return

        unique_map = {ids[i]: {"d": docs[i], "m": metas[i]} for i in range(len(ids))}

        try:
            self.collection.upsert(
                ids=list(unique_map.keys()),
                documents=[v["d"] for v in unique_map.values()],
                metadatas=[v["m"] for v in unique_map.values()],
            )
            print(f"[LOG] {progress_str} Indexed {len(unique_map)} items for '{title}'")
        except Exception as e:
            print(f"[ERROR] {progress_str} Failed to index '{title}': {e}")
