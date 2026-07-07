/**
 * Client-side certificate verification — UI-only, not backend logic.
 * Mirrors backend/verifier/verify.py for zero-trust browser verification.
 * Fetches only the public key from the server; all crypto runs locally.
 */

import * as ed from '@noble/ed25519'

async function sha256Hex(text) {
  const data = new TextEncoder().encode(text)
  const hash = await crypto.subtle.digest('SHA-256', data)
  return Array.from(new Uint8Array(hash))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('')
}

function hashHexPair(leftHex, rightHex) {
  const combined = leftHex + rightHex
  const data = new TextEncoder().encode(combined)
  return crypto.subtle.digest('SHA-256', data).then((hash) =>
    Array.from(new Uint8Array(hash))
      .map((byte) => byte.toString(16).padStart(2, '0'))
      .join('')
  )
}

async function verifyMerkleProof(leafHash, proof, root, leafIndex) {
  let current = leafHash
  let index = leafIndex

  for (const sibling of proof) {
    if (index % 2 === 0) {
      current = await hashHexPair(current, sibling)
    } else {
      current = await hashHexPair(sibling, current)
    }
    index = Math.floor(index / 2)
  }

  return current === root
}

function sortKeys(value) {
  if (Array.isArray(value)) {
    return value.map(sortKeys)
  }
  if (value !== null && typeof value === 'object') {
    return Object.keys(value)
      .sort()
      .reduce((sorted, key) => {
        sorted[key] = sortKeys(value[key])
        return sorted
      }, {})
  }
  return value
}

function canonicalJsonBytes(payload) {
  return new TextEncoder().encode(JSON.stringify(sortKeys(payload)))
}

function pemToRawPublicKey(pem) {
  const b64 = pem
    .replace(/-----BEGIN PUBLIC KEY-----/g, '')
    .replace(/-----END PUBLIC KEY-----/g, '')
    .replace(/\s/g, '')
  const der = Uint8Array.from(atob(b64), (char) => char.charCodeAt(0))
  return der.slice(-32)
}

function base64ToBytes(value) {
  const binary = atob(value)
  return Uint8Array.from(binary, (char) => char.charCodeAt(0))
}

async function verifySignature(payloadBytes, signatureB64, publicKeyPem) {
  try {
    const publicKey = pemToRawPublicKey(publicKeyPem)
    const signature = base64ToBytes(signatureB64)
    return await ed.verifyAsync(signature, payloadBytes, publicKey)
  } catch {
    return false
  }
}

/**
 * Verify an AnswerCertificate entirely in the browser.
 *
 * @param {object} certificate - Parsed certificate JSON
 * @param {string} publicKeyPem - PEM-encoded Ed25519 public key
 * @returns {Promise<{ok: boolean, reason: string, hash_match: boolean, proof_valid: boolean, signature_valid: boolean}>}
 */
export async function verifyCertificateClient(certificate, publicKeyPem) {
  const signature = certificate.signature
  if (!signature) {
    return {
      ok: false,
      reason: 'Certificate missing signature',
      hash_match: false,
      proof_valid: false,
      signature_valid: false,
    }
  }

  const certCopy = { ...certificate }
  delete certCopy.signature
  const payloadBytes = canonicalJsonBytes(certCopy)

  const signatureValid = await verifySignature(payloadBytes, signature, publicKeyPem)
  if (!signatureValid) {
    return {
      ok: false,
      reason: 'Signature verification failed',
      hash_match: false,
      proof_valid: false,
      signature_valid: false,
    }
  }

  const merkleRoot = certificate.merkle_root
  if (!merkleRoot) {
    return {
      ok: false,
      reason: 'Certificate missing merkle_root',
      hash_match: true,
      proof_valid: false,
      signature_valid: true,
    }
  }

  const chunks = certificate.chunks || []
  if (chunks.length === 0) {
    return {
      ok: false,
      reason: 'Certificate has no chunks',
      hash_match: true,
      proof_valid: false,
      signature_valid: true,
    }
  }

  for (const chunkData of chunks) {
    const chunkText = chunkData.text
    const chunkHash = chunkData.hash
    const merkleProof = chunkData.merkle_proof || []
    const chunkIndex = chunkData.chunk_index ?? 0

    if (!chunkText || !chunkHash) {
      return {
        ok: false,
        reason: `Chunk missing text or hash at index ${chunkIndex}`,
        hash_match: false,
        proof_valid: false,
        signature_valid: true,
      }
    }

    const actualHash = await sha256Hex(chunkText)
    if (actualHash !== chunkHash) {
      return {
        ok: false,
        reason: `Chunk hash mismatch at index ${chunkIndex}`,
        hash_match: false,
        proof_valid: false,
        signature_valid: true,
      }
    }

    const proofOk = await verifyMerkleProof(chunkHash, merkleProof, merkleRoot, chunkIndex)
    if (!proofOk) {
      return {
        ok: false,
        reason: `Merkle proof verification failed for chunk ${chunkIndex}`,
        hash_match: true,
        proof_valid: false,
        signature_valid: true,
      }
    }
  }

  const manifestTimestamp = certificate.manifest_timestamp || 'unknown'
  return {
    ok: true,
    reason: `VALID — grounded in unaltered source at ${manifestTimestamp}`,
    hash_match: true,
    proof_valid: true,
    signature_valid: true,
  }
}
