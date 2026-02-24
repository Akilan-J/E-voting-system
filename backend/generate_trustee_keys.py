from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import os

# Create keys directory if it doesn't exist
os.makedirs("keys", exist_ok=True)

# List of all trustees
trustees = ["alice", "bob", "carol", "dan", "eve"]

print("=" * 60)
print("GENERATING TRUSTEE KEYS")
print("=" * 60)

for trustee in trustees:
    print(f"\nGenerating keys for Trustee {trustee.capitalize()}...")
    
    # Generate key pair
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Save private key
    private_path = f"keys/trustee_{trustee}_private.pem"
    with open(private_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Save public key
    public_key = private_key.public_key()
    public_path = f"keys/trustee_{trustee}_public.pem"
    with open(public_path, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    
    print(f"  ✓ Private key: {private_path}")
    print(f"  ✓ Public key: {public_path}")

print("\n" + "=" * 60)
print(f"✓ All {len(trustees)} trustee keypairs generated successfully")
print("=" * 60)
