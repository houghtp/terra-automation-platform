"""
Shared security utilities for password hashing and cryptographic operations.
Consolidates security functionality used across authentication and secrets management.
"""
import os
import re
import base64
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from typing import Union, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityManager:
    """
    Centralized security manager for password hashing, encryption, and verification.
    Provides consistent security settings across the application.
    """

    def __init__(self):
        """Initialize with configurable bcrypt rounds and encryption key."""
        bcrypt_rounds = int(os.getenv("BCRYPT_ROUNDS", "12"))
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=bcrypt_rounds
        )

        # Initialize encryption for sensitive data (like SMTP passwords)
        self._init_encryption()

    def _init_encryption(self):
        """Initialize Fernet encryption for sensitive data."""
        # Get encryption key from environment or generate one
        encryption_key = os.getenv("ENCRYPTION_KEY")

        if not encryption_key:
            # Generate a new key and warn about it
            encryption_key = Fernet.generate_key().decode()
            print(f"⚠️  WARNING: No ENCRYPTION_KEY environment variable found.")
            print(f"   Generated new key: {encryption_key}")
            print(f"   Add this to your environment variables for production!")

        try:
            # Ensure the key is in bytes format
            if isinstance(encryption_key, str):
                encryption_key = encryption_key.encode()

            self.fernet = Fernet(encryption_key)
        except Exception as e:
            print(f"❌ Invalid encryption key: {e}")
            print("   Generating a new key...")
            new_key = Fernet.generate_key()
            self.fernet = Fernet(new_key)
            print(f"   New key: {new_key.decode()}")
            print(f"   Add ENCRYPTION_KEY={new_key.decode()} to your environment!")

    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt with salt.

        Args:
            password: Plain text password to hash

        Returns:
            str: Hashed password with salt
        """
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Stored hash to verify against

        Returns:
            bool: True if password matches hash
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def encrypt_password(self, password: str) -> str:
        """
        Encrypt a password for storage (used for SMTP passwords that need to be decrypted).

        Args:
            password: Plain text password to encrypt

        Returns:
            str: Base64 encoded encrypted password
        """
        try:
            encrypted_bytes = self.fernet.encrypt(password.encode())
            return base64.b64encode(encrypted_bytes).decode()
        except Exception as e:
            raise ValueError(f"Password encryption failed: {e}")

    def decrypt_password(self, encrypted_password: str) -> str:
        """
        Decrypt a password for use (used for SMTP passwords).

        Args:
            encrypted_password: Base64 encoded encrypted password

        Returns:
            str: Plain text password
        """
        try:
            encrypted_bytes = base64.b64decode(encrypted_password.encode())
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            raise ValueError(f"Password decryption failed: {e}")

    def hash_secret(self, secret_value: str) -> str:
        """
        Hash a secret value (API key, token, etc.) using bcrypt.
        Note: This is one-way hashing for storage security.

        Args:
            secret_value: Secret value to hash

        Returns:
            str: Hashed secret value
        """
        return self.hash_password(secret_value)

    def verify_secret(self, plain_secret: str, hashed_secret: str) -> bool:
        """
        Verify a secret value against its hash.
        Note: This is for verification only - bcrypt is one-way.

        Args:
            plain_secret: Plain text secret to verify
            hashed_secret: Stored hash to verify against

        Returns:
            bool: True if secret matches hash
        """
        return self.verify_password(plain_secret, hashed_secret)

    def validate_password_complexity(self, password: str) -> List[str]:
        """
        Validate password complexity requirements.

        Args:
            password: Password to validate

        Returns:
            List[str]: List of validation errors (empty if valid)
        """
        errors = []

        # Configurable minimum length
        min_length = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
        if len(password) < min_length:
            errors.append(f"Password must be at least {min_length} characters long")

        # Maximum length (prevent DoS attacks)
        max_length = int(os.getenv("PASSWORD_MAX_LENGTH", "128"))
        if len(password) > max_length:
            errors.append(f"Password must not exceed {max_length} characters")

        # Require at least one lowercase letter
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")

        # Require at least one uppercase letter
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")

        # Require at least one digit
        if not re.search(r'[0-9]', password):
            errors.append("Password must contain at least one number")

        # Require at least one special character
        special_chars = r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]'
        if not re.search(special_chars, password):
            errors.append("Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)")

        # Check for common weak patterns
        if password.lower() in ['password', '12345678', 'qwerty123', 'admin123', 'password123']:
            errors.append("Password is too common and easily guessable")

        # Check for repeated characters (e.g., "aaaa")
        if re.search(r'(.)\1{3,}', password):
            errors.append("Password cannot contain more than 3 consecutive identical characters")

        # Check for simple sequences
        sequences = ['1234', 'abcd', 'qwer', 'asdf', 'zxcv']
        for seq in sequences:
            if seq in password.lower() or seq[::-1] in password.lower():
                errors.append("Password cannot contain common character sequences")

        return errors

    def is_password_valid(self, password: str) -> bool:
        """
        Check if password meets complexity requirements.

        Args:
            password: Password to validate

        Returns:
            bool: True if password is valid
        """
        return len(self.validate_password_complexity(password)) == 0


# Global security manager instance
security_manager = SecurityManager()


# Convenience functions for backward compatibility
def hash_password(password: str) -> str:
    """Hash a password using the global security manager."""
    return security_manager.hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password using the global security manager."""
    return security_manager.verify_password(plain_password, hashed_password)


def hash_secret(secret_value: str) -> str:
    """Hash a secret value using the global security manager."""
    return security_manager.hash_secret(secret_value)


def verify_secret(plain_secret: str, hashed_secret: str) -> bool:
    """Verify a secret value using the global security manager."""
    return security_manager.verify_secret(plain_secret, hashed_secret)


def validate_password_complexity(password: str) -> List[str]:
    """Validate password complexity using the global security manager."""
    return security_manager.validate_password_complexity(password)


def is_password_valid(password: str) -> bool:
    """Check if password is valid using the global security manager."""
    return security_manager.is_password_valid(password)


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    Helps protect against common web vulnerabilities.
    """

    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)

        # Security headers for all responses
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=()",
        }

        # Add Content Security Policy (CSP) for HTML responses
        if response.headers.get("content-type", "").startswith("text/html"):
            # Allow inline styles/scripts for HTMX and development
            # In production, consider tightening this policy
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com https://cdn.jsdelivr.net; "
                "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
                "img-src 'self' data: https:; "
                "connect-src 'self' ws://localhost:* wss://localhost:*; "
                "form-action 'self';"
            )
            security_headers["Content-Security-Policy"] = csp_policy

        # Add Strict Transport Security for HTTPS
        if request.url.scheme == "https":
            security_headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Apply all security headers
        for header_name, header_value in security_headers.items():
            response.headers[header_name] = header_value

        return response
