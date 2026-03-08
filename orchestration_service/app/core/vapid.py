import os
import json
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

VAPID_PRIVATE_KEY_FILE = "vapid_private.pem"
VAPID_PUBLIC_KEY_FILE = "vapid_public.pem"

def generate_vapid_keys():
    if os.path.exists(VAPID_PRIVATE_KEY_FILE) and os.path.exists(VAPID_PUBLIC_KEY_FILE):
        with open(VAPID_PUBLIC_KEY_FILE, "r") as f:
            return f.read().strip()

    # Generate EC private key using SECP256R1 (P-256)
    private_key = ec.generate_private_key(ec.SECP256R1())
    
    # Save private key
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open(VAPID_PRIVATE_KEY_FILE, "wb") as f:
        f.write(pem)

    # Note: we should strictly use urlsafe base64 unpadded string of the uncompressed public key
    public_numbers = private_key.public_key().public_numbers()
    x = public_numbers.x.to_bytes(32, byteorder='big')
    y = public_numbers.y.to_bytes(32, byteorder='big')
    
    uncompressed_public_key = b'\x04' + x + y
    public_key_b64 = base64.urlsafe_b64encode(uncompressed_public_key).replace(b'=', b'').decode('utf-8')
    
    with open(VAPID_PUBLIC_KEY_FILE, "w") as f:
        f.write(public_key_b64)

    return public_key_b64

def get_vapid_public_key():
    if os.path.exists(VAPID_PUBLIC_KEY_FILE):
        with open(VAPID_PUBLIC_KEY_FILE, "r") as f:
            return f.read().strip()
    return generate_vapid_keys()

def get_vapid_private_key_path():
    if not os.path.exists(VAPID_PRIVATE_KEY_FILE):
        generate_vapid_keys()
    return VAPID_PRIVATE_KEY_FILE
