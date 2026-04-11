# SPDX-License-Identifier: MIT
import base64
import os
from typing import Optional

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import ENABLE_OPAQUE_IDS, OPAQUE_ID_ENCRYPTION_KEY
from app.core.exceptions import InvalidOpaqueIDError


class OpaqueIDService:
    """Service for encoding/decoding opaque IDs with AES-GCM encryption."""

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize with a persistent encryption key.

        Args:
            encryption_key: Base64-encoded 128-bit key. If None, uses config.
        """
        if encryption_key is None:
            encryption_key = OPAQUE_ID_ENCRYPTION_KEY

        try:
            # Ensure the key is clean ASCII (strip whitespace and encode to ASCII)
            encryption_key = encryption_key.strip()
            # Convert to ASCII bytes to ensure no Unicode issues
            key_bytes = base64.b64decode(encryption_key.encode('ascii'))
            if len(key_bytes) != 16:  # 128 bits
                raise ValueError("Key must be 128 bits (16 bytes)")
            self.aesgcm = AESGCM(key_bytes)
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {e}")

    def encode(self, value: str) -> str:
        """
        Encode a value into an opaque ID.

        Args:
            value: The plaintext value to encode (e.g., database ID)

        Returns:
            URL-safe base64-encoded opaque ID
        """
        try:
            nonce = os.urandom(12)  # 96-bit nonce for AES-GCM
            ciphertext = self.aesgcm.encrypt(nonce, value.encode('utf-8'), None)
            # Combine nonce + ciphertext and encode
            return base64.urlsafe_b64encode(nonce + ciphertext).decode('ascii')
        except Exception as e:
            raise ValueError(f"Failed to encode opaque ID: {e}")

    def decode(self, opaque_id: str) -> str:
        """
        Decode an opaque ID back to its original value.

        Args:
            opaque_id: The opaque ID to decode

        Returns:
            The original plaintext value

        Raises:
            ValueError: If the opaque ID is invalid or tampered with
        """
        try:
            # Decode from base64
            data = base64.urlsafe_b64decode(opaque_id)

            # Split nonce and ciphertext
            if len(data) < 13:  # At least 12 bytes nonce + 1 byte data
                raise ValueError("Invalid opaque ID: too short")

            nonce, ciphertext = data[:12], data[12:]

            # Decrypt and verify authenticity
            plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode('utf-8')

        except (ValueError, InvalidTag, Exception):
            # Don't leak information about why decryption failed
            raise InvalidOpaqueIDError("Invalid or tampered opaque ID")


# Initialize singleton instance
_opaque_id_service: Optional[OpaqueIDService] = None

def get_opaque_id_service() -> OpaqueIDService:
    """Get or create the singleton OpaqueIDService instance."""
    global _opaque_id_service
    if _opaque_id_service is None:
        _opaque_id_service = OpaqueIDService()
    return _opaque_id_service


def encode_opaque_id(value: str) -> str:
    """Convenience function to encode an opaque ID."""
    return get_opaque_id_service().encode(value)


def decode_opaque_id(opaque_id: str) -> str:
    """Convenience function to decode an opaque ID."""
    return get_opaque_id_service().decode(opaque_id)


def decode_if_enabled(value: str) -> str:
    """Decode value if opaque IDs are enabled, else return as-is."""
    if ENABLE_OPAQUE_IDS:
        return decode_opaque_id(value)
    return value