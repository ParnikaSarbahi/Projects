"""
crypto_utils.py - Core cryptographic primitives for Secure File Transfer System

Implements:
  - RSA-2048 key generation and PEM serialization
  - AES-256-CBC encryption / decryption with random IV
  - RSA-OAEP encrypt / decrypt for session-key exchange
  - SHA-256 file integrity hashing
  - Logging helper
"""

import os
import hashlib
import logging
import struct
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives import hashes, serialization, padding as sym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Constants
AES_KEY_SIZE   = 32          # 256-bit AES key
AES_BLOCK_SIZE = 16          # AES block size (bytes)
RSA_KEY_BITS   = 2048
CHUNK_SIZE     = 64 * 1024   # 64 KB transfer chunks
KEYS_DIR       = Path(__file__).parent / "keys"

# Logging Setup
def get_logger(name: str, level=logging.DEBUG) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        fmt = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        logger.addHandler(ch)
        fh = logging.FileHandler(Path(__file__).parent / "transfer.log")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger

log = get_logger("crypto_utils")

# RSA Key Generation
def generate_rsa_keypair(save: bool = True, force: bool = False):
    """Generate RSA-2048 keypair. Optionally persist to keys/ directory.
    
    Args:
        save: Whether to save keys to disk
        force: Whether to overwrite existing keys
    """
    log.info(f"Generating RSA-{RSA_KEY_BITS} keypair")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=RSA_KEY_BITS,
        backend=default_backend()
    )
    public_key = private_key.public_key()

    if save:
        KEYS_DIR.mkdir(exist_ok=True)
        priv_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        pub_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        (KEYS_DIR / "server_private.pem").write_bytes(priv_pem)
        (KEYS_DIR / "server_public.pem").write_bytes(pub_pem)
        log.info(f"Keys saved to {KEYS_DIR}/server_{{private,public}}.pem")

    return private_key, public_key


def load_private_key(path: Path = None):
    path = path or KEYS_DIR / "server_private.pem"
    return serialization.load_pem_private_key(
        path.read_bytes(), password=None, backend=default_backend()
    )


def load_public_key(path: Path = None):
    path = path or KEYS_DIR / "server_public.pem"
    return serialization.load_pem_public_key(
        path.read_bytes(), backend=default_backend()
    )


def public_key_to_pem(public_key) -> bytes:
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )


def public_key_from_pem(pem: bytes):
    return serialization.load_pem_public_key(pem, backend=default_backend())

# RSA-OAEP Session Key Encryption
def rsa_encrypt_session_key(session_key: bytes, public_key) -> bytes:
    """Encrypt a short session key with RSA-OAEP + SHA-256."""
    return public_key.encrypt(
        session_key,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )


def rsa_decrypt_session_key(ciphertext: bytes, private_key) -> bytes:
    """Decrypt session key using RSA private key."""
    return private_key.decrypt(
        ciphertext,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

# AES-256-CBC Encryption
def generate_aes_key() -> bytes:
    """Generate a cryptographically secure random 256-bit AES key."""
    return os.urandom(AES_KEY_SIZE)


def aes_encrypt(plaintext: bytes, key: bytes) -> bytes:
    """
    Encrypt plaintext with AES-256-CBC.
    Returns:  IV (16 bytes) || ciphertext (PKCS7-padded)
    """
    iv = os.urandom(AES_BLOCK_SIZE)
    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    enc = cipher.encryptor()
    ciphertext = enc.update(padded) + enc.finalize()
    return iv + ciphertext          # IV prepended for receiver


def aes_decrypt(data: bytes, key: bytes) -> bytes:
    """
    Decrypt AES-256-CBC data.
    Expects: IV (16 bytes) || ciphertext
    """
    iv         = data[:AES_BLOCK_SIZE]
    ciphertext = data[AES_BLOCK_SIZE:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    dec = cipher.decryptor()
    padded = dec.update(ciphertext) + dec.finalize()
    unpadder = sym_padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()

# SHA-256 File Integrity
def sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

# Socket Framing Helpers
# All messages are length-prefixed: [4-byte big-endian length][payload]

def send_msg(sock, data: bytes):
    """Send length-prefixed message over socket."""
    sock.sendall(struct.pack(">I", len(data)) + data)


def recv_msg(sock) -> bytes:
    """Receive length-prefixed message from socket."""
    raw_len = _recv_exact(sock, 4)
    if not raw_len:
        return b""
    length = struct.unpack(">I", raw_len)[0]
    return _recv_exact(sock, length)


def _recv_exact(sock, n: int) -> bytes:
    """Read exactly n bytes from socket."""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Socket closed before receiving expected bytes.")
        buf += chunk
    return buf
