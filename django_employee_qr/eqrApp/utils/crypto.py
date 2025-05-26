from cryptography.fernet import Fernet
from django.conf import settings
import base64
import os
import json

# Generate or get encryption key
def get_encryption_key():
    key = getattr(settings, 'QR_ENCRYPTION_KEY', None)
    if not key:
        key = Fernet.generate_key().decode()
        setattr(settings, 'QR_ENCRYPTION_KEY', key)
    return key

# Initialize cipher
cipher_suite = Fernet(get_encryption_key())

def encrypt_qr_data(data: dict) -> str:
    """Encrypt data for QR code with system-specific header"""
    json_data = json.dumps(data)
    encrypted = cipher_suite.encrypt(json_data.encode())
    # Add custom header to identify our encrypted data
    return f"EQR1:{base64.urlsafe_b64encode(encrypted).decode()}"

def decrypt_qr_data(encrypted_str: str) -> dict:
    """Decrypt QR code data, returns None if invalid"""
    if not encrypted_str.startswith('EQR1:'):
        return None
    
    try:
        encrypted = base64.urlsafe_b64decode(encrypted_str[5:])
        decrypted = cipher_suite.decrypt(encrypted).decode()
        return json.loads(decrypted)
    except:
        return None