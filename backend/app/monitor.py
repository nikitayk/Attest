"""Integrity monitor — implemented in Part 6 Week 2.5–3 (Should-Have)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.crypto import hash_bytes
from app.models import CorpusHealth, DocumentHealth, MonitorStatus
from app.storage import ManifestStore


class IntegrityMonitor:
    """Periodic and manual integrity checking for document tamper detection."""

    def __init__(self, manifest_store: ManifestStore | None = None):
        if manifest_store is None:
            manifest_store = ManifestStore()
        self._manifest_store = manifest_store

    async def check_corpus_health(self) -> CorpusHealth:
        """
        Check all documents against stored hashes in manifest.

        Returns corpus health with quarantined documents flagged.
        """
        settings = get_settings()
        data_dir = settings.resolve_path(settings.data_dir)

        manifest = await self._manifest_store.get_latest_manifest()
        if not manifest:
            return CorpusHealth(documents=[], quarantined_count=0)

        documents: list[DocumentHealth] = []
        quarantined_count = 0

        for doc_id, expected_hash in manifest.document_hashes.items():
            # Check if already quarantined
            if await self._manifest_store.is_quarantined(doc_id):
                documents.append(
                    DocumentHealth(
                        doc_id=doc_id,
                        status="QUARANTINED",
                        doc_hash=expected_hash,
                        last_checked=datetime.now(timezone.utc),
                    )
                )
                quarantined_count += 1
                continue

            # Re-hash file from disk
            doc_path = data_dir / f"{doc_id}.md"
            if not doc_path.exists():
                doc_path = data_dir / f"{doc_id}.txt"

            if not doc_path.exists():
                # File missing — quarantine
                await self._manifest_store.quarantine_doc(doc_id, "File missing from disk")
                documents.append(
                    DocumentHealth(
                        doc_id=doc_id,
                        status="QUARANTINED",
                        doc_hash="missing",
                        last_checked=datetime.now(timezone.utc),
                    )
                )
                quarantined_count += 1
                continue

            try:
                current_hash = hash_bytes(doc_path.read_bytes())
                if current_hash != expected_hash:
                    # Hash mismatch — quarantine
                    await self._manifest_store.quarantine_doc(
                        doc_id, "Document hash mismatch detected"
                    )
                    documents.append(
                        DocumentHealth(
                            doc_id=doc_id,
                            status="QUARANTINED",
                            doc_hash=current_hash,
                            last_checked=datetime.now(timezone.utc),
                        )
                    )
                    quarantined_count += 1
                else:
                    documents.append(
                        DocumentHealth(
                            doc_id=doc_id,
                            status="OK",
                            doc_hash=current_hash,
                            last_checked=datetime.now(timezone.utc),
                        )
                    )
            except Exception as e:
                # Error reading file — quarantine
                await self._manifest_store.quarantine_doc(doc_id, f"Error reading file: {e}")
                documents.append(
                    DocumentHealth(
                        doc_id=doc_id,
                        status="QUARANTINED",
                        doc_hash="error",
                        last_checked=datetime.now(timezone.utc),
                    )
                )
                quarantined_count += 1

        return CorpusHealth(documents=documents, quarantined_count=quarantined_count)

    async def trigger_monitor(self) -> MonitorStatus:
        """
        Run full corpus health check and return status.

        Called by cron job or manual "Check Now" button.
        """
        corpus_health = await self.check_corpus_health()

        # Get quarantined doc IDs
        quarantined_docs = [
            d.doc_id for d in corpus_health.documents if d.status == "QUARANTINED"
        ]

        return MonitorStatus(
            last_run=datetime.now(timezone.utc),
            quarantined_count=corpus_health.quarantined_count,
            docs_checked=len(corpus_health.documents),
            mismatches=quarantined_docs,
        )
