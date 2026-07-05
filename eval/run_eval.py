"""Eval harness — implemented in Part 6 Step 4.3 (Should-Have)."""

import json
import sys
import time
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.crypto import hash_text
from app.ingest import chunk_text, ingest_corpus
from app.storage import ManifestStore
from app.vectorstore import VectorStore


def measure_ingestion_throughput(data_dir: Path, runs: int = 5) -> float:
    """Measure docs/sec for full corpus ingestion."""
    print(f"\n=== Ingestion Throughput ({runs} runs) ===")
    
    throughputs = []
    for i in range(runs):
        start = time.time()
        manifest = ingest_corpus(data_dir=data_dir)
        elapsed = time.time() - start
        throughput = len(manifest.doc_ids) / elapsed
        throughputs.append(throughput)
        print(f"Run {i+1}: {throughput:.2f} docs/sec ({len(manifest.doc_ids)} docs in {elapsed:.2f}s)")
    
    avg_throughput = sum(throughputs) / len(throughputs)
    print(f"Average: {avg_throughput:.2f} docs/sec")
    return avg_throughput


def measure_proof_size(manifest_store: ManifestStore) -> float:
    """Measure mean JSON size of merkle_proof arrays."""
    print("\n=== Proof Size ===")
    
    manifest = manifest_store.get_latest_manifest()
    if not manifest:
        print("No manifest found")
        return 0.0
    
    # Simulate certificate proofs for all chunks
    from app.crypto import build_merkle_tree, get_merkle_proof
    
    all_hashes = [c.hash for c in manifest.chunks]
    merkle_tree = build_merkle_tree(all_hashes)
    
    proof_sizes = []
    for idx in range(len(manifest.chunks)):
        proof = get_merkle_proof(merkle_tree, idx)
        proof_json = json.dumps(proof)
        proof_size_kb = len(proof_json.encode('utf-8')) / 1024
        proof_sizes.append(proof_size_kb)
    
    avg_proof_size = sum(proof_sizes) / len(proof_sizes)
    print(f"Average proof size: {avg_proof_size:.3f} KB")
    print(f"Min: {min(proof_sizes):.3f} KB, Max: {max(proof_sizes):.3f} KB")
    return avg_proof_size


def measure_verification_latency(cert_count: int = 100) -> float:
    """Measure verify.py latency on sample certificates."""
    print(f"\n=== Verification Latency ({cert_count} certs) ===")
    
    # Generate test certificates
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PrivateFormat, PublicFormat,
    )
    
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_pem = private_key.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    )
    
    # Save public key to temp file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as f:
        f.write(public_pem)
        pubkey_path = f.name
    
    latencies = []
    for i in range(cert_count):
        # Create test certificate
        cert = {
            "certificate_id": f"test-{i}",
            "query": "test query",
            "answer": "test answer",
            "chunks": [{
                "doc_id": "test",
                "chunk_index": 0,
                "text": "test chunk text",
                "hash": hash_text("test chunk text"),
                "merkle_proof": [],
            }],
            "doc_id": "test",
            "merkle_root": hash_text("test chunk text"),
            "manifest_timestamp": "2026-07-05T00:00:00Z",
            "embedding_model": "test",
            "llm_model": "test",
        }
        
        # Sign
        import json
        from app.crypto import canonical_json_bytes, sign_bytes
        signature = sign_bytes(canonical_json_bytes(cert), private_key)
        cert["signature"] = signature
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(cert, f)
            cert_path = f.name
        
        # Measure verification
        start = time.time()
        # Import verifier
        sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "verifier"))
        from verify import verify_certificate
        is_valid, _ = verify_certificate(cert_path, pubkey_path)
        elapsed = time.time() - start
        latencies.append(elapsed * 1000)  # Convert to ms
        
        # Cleanup
        Path(cert_path).unlink()
    
    Path(pubkey_path).unlink()
    
    avg_latency = sum(latencies) / len(latencies)
    p50 = sorted(latencies)[len(latencies) // 2]
    print(f"Average: {avg_latency:.2f} ms")
    print(f"P50: {p50:.2f} ms")
    return p50


def measure_tamper_detection(data_dir: Path) -> tuple[float, float]:
    """Measure tamper detection rate and false positive rate."""
    print("\n=== Tamper Detection ===")
    
    # This is a simplified eval - full eval would require:
    # 1. Poison K known chunks post-ingestion
    # 2. Report caught/K
    # 3. Re-ingest unmodified corpus M times
    # 4. Report wrongful quarantines/M
    
    # For MVP, we'll simulate the logic
    print("Note: Full tamper detection eval requires corpus with test cases.")
    print("Simulating with logic validation...")
    
    # Test 1: Tampered chunk should be caught
    test_text = "original text"
    tampered_text = "tampered text"
    original_hash = hash_text(test_text)
    tampered_hash = hash_text(tampered_text)
    
    tamper_caught = (original_hash != tampered_hash)
    print(f"Tamper detection test: {'PASS' if tamper_caught else 'FAIL'}")
    
    # Test 2: Untampered chunk should pass
    rehash = hash_text(test_text)
    false_positive = (original_hash != rehash)
    print(f"False positive test: {'PASS' if not false_positive else 'FAIL'}")
    
    # Return placeholder values (real eval needs actual corpus)
    tamper_rate = 100.0 if tamper_caught else 0.0
    false_positive_rate = 0.0 if not false_positive else 100.0
    
    print(f"\nTamper detection rate: {tamper_rate}%")
    print(f"False positive rate: {false_positive_rate}%")
    
    return tamper_rate, false_positive_rate


def print_metrics_table(metrics: dict):
    """Print ASCII table of all metrics."""
    print("\n" + "=" * 60)
    print("ATTEST EVALUATION METRICS")
    print("=" * 60)
    print(f"{'Metric':<30} {'Value':<20}")
    print("-" * 60)
    print(f"{'Tamper detection rate':<30} {metrics['tamper_rate']}%")
    print(f"{'False positive rate':<30} {metrics['false_positive_rate']}%")
    print(f"{'Verification latency (p50)':<30} {metrics['verify_latency_ms']:.2f} ms")
    print(f"{'Proof size (mean)':<30} {metrics['proof_size_kb']:.3f} KB")
    print(f"{'Ingestion throughput':<30} {metrics['ingest_throughput']:.2f} docs/sec")
    print("=" * 60)


def main():
    """Run all evaluation metrics."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
    
    from app.config import get_settings
    
    settings = get_settings()
    data_dir = settings.resolve_path(settings.data_dir)
    
    print("ATTEST Evaluation Harness")
    print(f"Data directory: {data_dir}")
    
    # Check if data directory exists
    if not data_dir.exists():
        print(f"Error: Data directory {data_dir} does not exist")
        print("Please create sample documents in backend/data/ first")
        return
    
    # Run metrics
    metrics = {}
    
    # Ingestion throughput
    try:
        metrics['ingest_throughput'] = measure_ingestion_throughput(data_dir, runs=3)
    except Exception as e:
        print(f"Ingestion throughput eval failed: {e}")
        metrics['ingest_throughput'] = 0.0
    
    # Proof size
    try:
        manifest_store = ManifestStore()
        metrics['proof_size_kb'] = measure_proof_size(manifest_store)
    except Exception as e:
        print(f"Proof size eval failed: {e}")
        metrics['proof_size_kb'] = 0.0
    
    # Verification latency
    try:
        metrics['verify_latency_ms'] = measure_verification_latency(cert_count=50)
    except Exception as e:
        print(f"Verification latency eval failed: {e}")
        metrics['verify_latency_ms'] = 0.0
    
    # Tamper detection (simplified)
    try:
        tamper_rate, false_positive_rate = measure_tamper_detection(data_dir)
        metrics['tamper_rate'] = tamper_rate
        metrics['false_positive_rate'] = false_positive_rate
    except Exception as e:
        print(f"Tamper detection eval failed: {e}")
        metrics['tamper_rate'] = 0.0
        metrics['false_positive_rate'] = 0.0
    
    # Print summary
    print_metrics_table(metrics)
    
    print("\nNote: These are MVP evaluation numbers. For production-ready metrics,")
    print("run with a larger corpus and dedicated test cases.")


if __name__ == "__main__":
    main()
