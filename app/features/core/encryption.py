"""
Advanced encryption utilities for secrets management.
Implements AES-256-GCM with proper key derivation, rotation, and integrity verification.
"""
import os
import base64
import secrets
import structlog
from typing import Tuple, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = structlog.get_logger(__name__)


class EncryptionKeyError(Exception):
    """Raised when encryption key operations fail."""
    pass


class EncryptionError(Exception):
    """Raised when encryption/decryption operations fail."""
    pass


class SecretsEncryption:
    """
    High-security encryption manager for secrets storage.
    Uses AES-256-GCM with PBKDF2 key derivation and integrity verification.
    """
    
    # Security constants
    KEY_LENGTH = 32  # 256 bits for AES-256
    NONCE_LENGTH = 12  # 96 bits for GCM (recommended)
    SALT_LENGTH = 32  # 256 bits for PBKDF2 salt
    PBKDF2_ITERATIONS = 600000  # OWASP recommended minimum (2023)
    
    def __init__(self):
        """Initialize encryption manager with master key validation."""
        self._master_key = None
        self._derived_keys = {}  # Cache for derived keys
        self._validate_master_key()
    
    def _validate_master_key(self) -> None:
        """Validate and set the master encryption key."""
        master_key = os.getenv("SECRETS_MASTER_KEY")
        
        if not master_key:
            raise EncryptionKeyError(
                "SECRETS_MASTER_KEY environment variable is required for secrets encryption"
            )
        
        # Decode base64 key
        try:
            decoded_key = base64.b64decode(master_key)
        except Exception:
            raise EncryptionKeyError(
                "SECRETS_MASTER_KEY must be a valid base64-encoded 256-bit key"
            )
        
        # Validate key length (256 bits = 32 bytes)
        if len(decoded_key) != self.KEY_LENGTH:
            raise EncryptionKeyError(
                f"SECRETS_MASTER_KEY must be exactly {self.KEY_LENGTH} bytes ({self.KEY_LENGTH * 8} bits)"
            )
        
        self._master_key = decoded_key
        logger.info("Secrets encryption initialized with AES-256-GCM")
    
    def _derive_key(self, salt: bytes, context: str = "secrets") -> bytes:
        """
        Derive encryption key from master key using PBKDF2.
        
        Args:
            salt: Unique salt for key derivation
            context: Context string for key separation
            
        Returns:
            bytes: Derived 256-bit encryption key
        """
        # Create cache key for performance
        cache_key = base64.b64encode(salt + context.encode()).decode()
        
        if cache_key in self._derived_keys:
            return self._derived_keys[cache_key]
        
        # Use PBKDF2 with SHA-256
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_LENGTH,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
        )
        
        # Derive key from master key + context
        input_key_material = self._master_key + context.encode('utf-8')
        derived_key = kdf.derive(input_key_material)
        
        # Cache the derived key (limit cache size)
        if len(self._derived_keys) > 1000:
            # Remove oldest entries (simple LRU approximation)
            oldest_keys = list(self._derived_keys.keys())[:100]
            for old_key in oldest_keys:
                del self._derived_keys[old_key]
        
        self._derived_keys[cache_key] = derived_key
        return derived_key
    
    def encrypt_secret(self, plaintext_value: str, tenant_id: str) -> str:
        """
        Encrypt a secret value with AES-256-GCM.
        
        Args:
            plaintext_value: The secret to encrypt
            tenant_id: Tenant ID for key derivation context
            
        Returns:
            str: Base64-encoded encrypted data (salt:nonce:ciphertext:tag)
            
        Raises:
            EncryptionError: If encryption fails
        """
        if not plaintext_value:
            raise EncryptionError("Cannot encrypt empty value")
        
        try:
            # Generate random salt and nonce
            salt = secrets.token_bytes(self.SALT_LENGTH)
            nonce = secrets.token_bytes(self.NONCE_LENGTH)
            
            # Derive encryption key for this tenant
            encryption_key = self._derive_key(salt, f"tenant_{tenant_id}")
            
            # Initialize AES-GCM cipher
            aesgcm = AESGCM(encryption_key)
            
            # Encrypt with associated data (tenant_id for additional security)
            associated_data = f"tenant_{tenant_id}".encode('utf-8')
            ciphertext = aesgcm.encrypt(
                nonce, 
                plaintext_value.encode('utf-8'),
                associated_data
            )
            
            # The ciphertext includes the authentication tag
            # Format: salt:nonce:ciphertext_with_tag
            encrypted_data = salt + nonce + ciphertext
            
            # Return base64-encoded result
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt secret: {str(e)}")
    
    def decrypt_secret(self, encrypted_value: str, tenant_id: str) -> str:
        """
        Decrypt a secret value with AES-256-GCM.
        
        Args:
            encrypted_value: Base64-encoded encrypted data
            tenant_id: Tenant ID for key derivation context
            
        Returns:
            str: Decrypted plaintext value
            
        Raises:
            EncryptionError: If decryption fails or data is tampered
        """
        if not encrypted_value:
            raise EncryptionError("Cannot decrypt empty value")
        
        try:
            # Decode base64
            encrypted_data = base64.b64decode(encrypted_value)
            
            # Extract components
            if len(encrypted_data) < self.SALT_LENGTH + self.NONCE_LENGTH + 16:  # 16 = min GCM tag
                raise EncryptionError("Invalid encrypted data format")
            
            salt = encrypted_data[:self.SALT_LENGTH]
            nonce = encrypted_data[self.SALT_LENGTH:self.SALT_LENGTH + self.NONCE_LENGTH]
            ciphertext = encrypted_data[self.SALT_LENGTH + self.NONCE_LENGTH:]
            
            # Derive the same encryption key
            encryption_key = self._derive_key(salt, f"tenant_{tenant_id}")
            
            # Initialize AES-GCM cipher
            aesgcm = AESGCM(encryption_key)
            
            # Decrypt with associated data verification
            associated_data = f"tenant_{tenant_id}".encode('utf-8')
            plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, associated_data)
            
            return plaintext_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError(f"Failed to decrypt secret: {str(e)}")
    
    def verify_encryption(self, encrypted_value: str, tenant_id: str) -> bool:
        """
        Verify that encrypted data is valid and can be decrypted.
        
        Args:
            encrypted_value: Base64-encoded encrypted data
            tenant_id: Tenant ID for key derivation context
            
        Returns:
            bool: True if data is valid and decryptable
        """
        try:
            # Attempt decryption (this verifies integrity)
            self.decrypt_secret(encrypted_value, tenant_id)
            return True
        except EncryptionError:
            return False
    
    @staticmethod
    def generate_master_key() -> str:
        """
        Generate a new 256-bit master key for secrets encryption.
        
        Returns:
            str: Base64-encoded master key
        """
        master_key = secrets.token_bytes(32)  # 256 bits
        return base64.b64encode(master_key).decode('utf-8')
    
    def rotate_key_derivation(self, old_encrypted_value: str, tenant_id: str) -> str:
        """
        Re-encrypt a secret with a fresh salt (key rotation).
        
        Args:
            old_encrypted_value: Currently encrypted value
            tenant_id: Tenant ID
            
        Returns:
            str: Re-encrypted value with new salt
        """
        # Decrypt with old key
        plaintext = self.decrypt_secret(old_encrypted_value, tenant_id)
        
        # Re-encrypt with fresh salt
        return self.encrypt_secret(plaintext, tenant_id)


# Global encryption manager instance
_secrets_encryption = None


def get_secrets_encryption() -> SecretsEncryption:
    """Get the global secrets encryption manager."""
    global _secrets_encryption
    if _secrets_encryption is None:
        _secrets_encryption = SecretsEncryption()
    return _secrets_encryption


# Convenience functions
def encrypt_secret(plaintext_value: str, tenant_id: str) -> str:
    """Encrypt a secret using the global encryption manager."""
    return get_secrets_encryption().encrypt_secret(plaintext_value, tenant_id)


def decrypt_secret(encrypted_value: str, tenant_id: str) -> str:
    """Decrypt a secret using the global encryption manager."""
    return get_secrets_encryption().decrypt_secret(encrypted_value, tenant_id)


def verify_secret_encryption(encrypted_value: str, tenant_id: str) -> bool:
    """Verify encrypted secret integrity using the global encryption manager."""
    return get_secrets_encryption().verify_encryption(encrypted_value, tenant_id)