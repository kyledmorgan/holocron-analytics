"""
Pack and unpack operations for cold storage.

Provides compression (zip) and optional encryption for snapshot packs.
"""

import json
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .manifest import SnapshotManifest

logger = logging.getLogger(__name__)


class SnapshotPacker:
    """
    Packs a snapshot dataset into a compressed archive.
    
    Supports:
    - ZIP compression (always available)
    - Optional encryption (when cryptography library is available)
    """

    def __init__(
        self,
        dataset_dir: Path,
        encrypt: bool = False,
        encryption_key: Optional[bytes] = None,
    ):
        """
        Initialize the packer.
        
        Args:
            dataset_dir: Path to the dataset directory
            encrypt: Whether to encrypt the archive
            encryption_key: Encryption key (required if encrypt=True)
        """
        self.dataset_dir = Path(dataset_dir)
        self.encrypt = encrypt
        self.encryption_key = encryption_key
        
        if not self.dataset_dir.exists():
            raise FileNotFoundError(f"Dataset directory not found: {self.dataset_dir}")
        
        # Load manifest for metadata
        manifest_path = self.dataset_dir / "manifest.json"
        if manifest_path.exists():
            self.manifest = SnapshotManifest.load(manifest_path)
        else:
            self.manifest = None

    def pack(self, output_path: Path) -> Path:
        """
        Pack the dataset into a zip archive.
        
        Args:
            output_path: Path for the output archive
            
        Returns:
            Path to the created archive
        """
        output_path = Path(output_path)
        
        # Ensure .zip extension
        if output_path.suffix != ".zip":
            output_path = output_path.with_suffix(".zip")
        
        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Packing dataset {self.dataset_dir.name} to {output_path}")
        
        # Create zip archive
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add all files in the dataset directory
            for file_path in self.dataset_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.dataset_dir)
                    zf.write(file_path, arcname)
                    logger.debug(f"  Added: {arcname}")
            
            # Add pack metadata
            pack_meta = {
                "packed_at": datetime.now(timezone.utc).isoformat(),
                "dataset_name": self.dataset_dir.name,
                "encrypted": self.encrypt,
            }
            zf.writestr("_pack_meta.json", json.dumps(pack_meta, indent=2))
        
        logger.info(f"Created archive: {output_path} ({output_path.stat().st_size} bytes)")
        
        # Apply encryption if requested
        if self.encrypt:
            output_path = self._encrypt_archive(output_path)
        
        return output_path

    def _encrypt_archive(self, archive_path: Path) -> Path:
        """
        Encrypt an archive using AES-256-GCM.
        
        Args:
            archive_path: Path to the zip archive
            
        Returns:
            Path to the encrypted archive
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:
            raise ImportError(
                "cryptography library is required for encryption. "
                "Install with: pip install cryptography"
            )
        
        if not self.encryption_key:
            raise ValueError("Encryption key is required for encryption")
        
        # Ensure key is 32 bytes (256 bits) for AES-256
        key = self.encryption_key
        if len(key) != 32:
            # Hash the key to get consistent 32 bytes
            import hashlib
            key = hashlib.sha256(key).digest()
        
        # Read archive data
        with open(archive_path, "rb") as f:
            data = f.read()
        
        # Generate nonce (12 bytes for GCM)
        nonce = os.urandom(12)
        
        # Encrypt
        aesgcm = AESGCM(key)
        encrypted = aesgcm.encrypt(nonce, data, None)
        
        # Write encrypted file (nonce + ciphertext)
        encrypted_path = archive_path.with_suffix(".zip.enc")
        with open(encrypted_path, "wb") as f:
            f.write(nonce + encrypted)
        
        # Remove unencrypted archive
        archive_path.unlink()
        
        logger.info(f"Encrypted archive: {encrypted_path}")
        return encrypted_path


class SnapshotUnpacker:
    """
    Unpacks a compressed snapshot archive.
    """

    def __init__(
        self,
        archive_path: Path,
        decryption_key: Optional[bytes] = None,
    ):
        """
        Initialize the unpacker.
        
        Args:
            archive_path: Path to the archive file
            decryption_key: Decryption key (required if archive is encrypted)
        """
        self.archive_path = Path(archive_path)
        self.decryption_key = decryption_key
        
        if not self.archive_path.exists():
            raise FileNotFoundError(f"Archive not found: {self.archive_path}")
        
        self.is_encrypted = self.archive_path.suffix == ".enc"

    def unpack(self, output_dir: Path) -> Path:
        """
        Unpack the archive to a directory.
        
        Args:
            output_dir: Directory to extract to
            
        Returns:
            Path to the extracted dataset directory
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        archive_to_extract = self.archive_path
        
        # Decrypt if necessary
        if self.is_encrypted:
            archive_to_extract = self._decrypt_archive()
        
        logger.info(f"Unpacking {archive_to_extract} to {output_dir}")
        
        # Extract zip
        with zipfile.ZipFile(archive_to_extract, "r") as zf:
            zf.extractall(output_dir)
        
        # Clean up temporary decrypted file
        if self.is_encrypted and archive_to_extract != self.archive_path:
            archive_to_extract.unlink()
        
        # Find the dataset directory (look for manifest.json)
        for item in output_dir.iterdir():
            if item.is_dir() and (item / "manifest.json").exists():
                logger.info(f"Unpacked dataset: {item}")
                return item
        
        # If manifest is at root level
        if (output_dir / "manifest.json").exists():
            return output_dir
        
        logger.warning("Could not find manifest.json in unpacked archive")
        return output_dir

    def _decrypt_archive(self) -> Path:
        """
        Decrypt an encrypted archive.
        
        Returns:
            Path to the decrypted zip archive
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:
            raise ImportError(
                "cryptography library is required for decryption. "
                "Install with: pip install cryptography"
            )
        
        if not self.decryption_key:
            raise ValueError("Decryption key is required")
        
        # Ensure key is 32 bytes
        key = self.decryption_key
        if len(key) != 32:
            import hashlib
            key = hashlib.sha256(key).digest()
        
        # Read encrypted data
        with open(self.archive_path, "rb") as f:
            data = f.read()
        
        # Extract nonce (first 12 bytes)
        nonce = data[:12]
        ciphertext = data[12:]
        
        # Decrypt
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(nonce, ciphertext, None)
        
        # Write to temporary file
        decrypted_path = self.archive_path.with_suffix("")  # Remove .enc
        if decrypted_path.suffix != ".zip":
            decrypted_path = decrypted_path.with_suffix(".zip")
        
        # Use temp location to avoid conflicts
        import tempfile
        fd, temp_path = tempfile.mkstemp(suffix=".zip")
        os.close(fd)
        temp_path = Path(temp_path)
        
        with open(temp_path, "wb") as f:
            f.write(decrypted)
        
        logger.info(f"Decrypted archive to: {temp_path}")
        return temp_path


def get_encryption_key(
    key_source: str = "env",
    key_env_var: str = "SNAPSHOT_ENCRYPTION_KEY",
    key_file_path: Optional[str] = None,
    prompt: bool = False,
) -> Optional[bytes]:
    """
    Get encryption key from configured source.
    
    Args:
        key_source: Source type ('env', 'file', 'prompt')
        key_env_var: Environment variable name
        key_file_path: Path to key file
        prompt: Whether to prompt interactively
        
    Returns:
        Encryption key as bytes, or None if not available
    """
    if key_source == "env":
        key_str = os.environ.get(key_env_var)
        if key_str:
            return key_str.encode("utf-8")
    
    elif key_source == "file" and key_file_path:
        key_path = Path(key_file_path)
        if key_path.exists():
            return key_path.read_bytes().strip()
    
    elif key_source == "prompt" and prompt:
        import getpass
        key_str = getpass.getpass("Enter encryption key: ")
        if key_str:
            return key_str.encode("utf-8")
    
    return None
