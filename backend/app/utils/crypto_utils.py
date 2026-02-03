from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import os

# Global simplified key storage (In reality, use KMS)
# Generating a key pair for the Issuer
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)
public_key = private_key.public_key()

def get_issuer_public_key():
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return pem.decode('utf-8')

def sign_blinded_message(blinded_message_int: int) -> int:
    """
    Performs RSA signing of a blinded message (integer).
    s' = (m')^d mod n
    """
    priv_numbers = private_key.private_numbers()
    d = priv_numbers.d
    n = priv_numbers.public_numbers.n
    
    signed_int = pow(blinded_message_int, d, n)
    return signed_int

def verify_signature(message_int: int, signature_int: int) -> bool:
    """
    Verifies s^e = m mod n
    """
    pub_numbers = public_key.public_numbers()
    e = pub_numbers.e
    n = pub_numbers.n
    
    calculated_message = pow(signature_int, e, n)
    return calculated_message == message_int
