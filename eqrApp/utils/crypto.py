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
        print(f"Using encryption key from settings")
    else:
        # Generate a consistent key based on SECRET_KEY
        import hashlib
        secret_key = settings.SECRET_KEY.encode()
        key_material = hashlib.sha256(secret_key).digest()
        key = base64.urlsafe_b64encode(key_material)
        print(f"Generated encryption key from SECRET_KEY")
    
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
        encrypted_string = f"EQR1:{base64.urlsafe_b64encode(encrypted).decode()}"
        print(f"Encrypted QR data: {encrypted_string[:50]}...")
        return encrypted_string
    except Exception as e:
        print(f"Encryption error: {e}")
        import traceback
        traceback.print_exc()
        return None

def decrypt_qr_data(encrypted_str: str) -> dict:
    """Decrypt QR code data, returns None if invalid"""
    if not encrypted_str:
        print("No encrypted string provided")
        return None
        
    if not encrypted_str.startswith('EQR1:'):
        print(f"Invalid QR format - doesn't start with EQR1: {encrypted_str[:20]}...")
        return None
    
    try:
        key = get_encryption_key()
        cipher_suite = Fernet(key)
        
        encrypted_part = encrypted_str[5:]  # Remove 'EQR1:' prefix
        encrypted = base64.urlsafe_b64decode(encrypted_part)
        decrypted = cipher_suite.decrypt(encrypted).decode()
        result = json.loads(decrypted)
        print(f"Successfully decrypted QR data for member: {result.get('member_id')}")
        return result
    except Exception as e:
        print(f"Decryption error: {e}")
        print(f"Encrypted string: {encrypted_str[:50]}...")
        import traceback
        traceback.print_exc()
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