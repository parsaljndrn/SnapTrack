from cryptography.fernet import Fernet
from django.conf import settings
import base64
import os
import json

def get_encryption_key():
    """Get or generate encryption key"""
    # Try to get key from settings first
    if hasattr(settings, 'QR_ENCRYPTION_KEY'):
        key = settings.QR_ENCRYPTION_KEY
    else:
        # Generate a new key if not exists
        key = Fernet.generate_key().decode()
        # In production, you should store this securely
        print(f"Generated new encryption key: {key}")
        print("Please add this to your settings.py as QR_ENCRYPTION_KEY")
    
    if isinstance(key, str):
        key = key.encode()
    
    return key

def encrypt_qr_data(data: dict) -> str:
    """Encrypt data for QR code with system-specific header"""
    try:
        key = get_encryption_key()
        cipher_suite = Fernet(key)
        
        json_data = json.dumps(data)
        encrypted = cipher_suite.encrypt(json_data.encode())
        
        # Add custom header to identify our encrypted data
        return f"EQR1:{base64.urlsafe_b64encode(encrypted).decode()}"
    except Exception as e:
        print(f"Encryption error: {e}")
        return None

def decrypt_qr_data(encrypted_str: str) -> dict:
    """Decrypt QR code data, returns None if invalid"""
    if not encrypted_str or not encrypted_str.startswith('EQR1:'):
        return None
    
    try:
        key = get_encryption_key()
        cipher_suite = Fernet(key)
        
        encrypted = base64.urlsafe_b64decode(encrypted_str[5:])
        decrypted = cipher_suite.decrypt(encrypted).decode()
        return json.loads(decrypted)
    except Exception as e:
        print(f"Decryption error: {e}")
        return None

def verify_qr_data(encrypted_str: str, expected_event_id: int, expected_member_id: str) -> bool:
    """Verify that QR data matches expected values"""
    decrypted_data = decrypt_qr_data(encrypted_str)
    if not decrypted_data:
        return False
    
    return (
        decrypted_data.get('event_id') == expected_event_id and
        decrypted_data.get('member_id') == expected_member_id
    )