"""Generate Ed25519 keypair for ATTEST."""

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

# Generate keypair
private_key = Ed25519PrivateKey.generate()
private_pem = private_key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption()
)
public_pem = private_key.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo
)

# Save keys
with open('keys/private.pem', 'wb') as f:
    f.write(private_pem)
with open('keys/public_key.pem', 'wb') as f:
    f.write(public_pem)

print('Keys generated successfully')
print('Private key: keys/private.pem (DO NOT COMMIT)')
print('Public key: keys/public_key.pem (COMMIT THIS)')
