"""
client.py - Secure File Transfer Client

Handshake Protocol (mirrors server.py):
  1. Connect to server - receive RSA public key
  2. Generate random AES-256 session key
  3. Encrypt session key with server's RSA public key - send
  4. Send AES-encrypted metadata (filename, size, SHA-256)
  5. Stream file in 64 KB chunks, each AES-256-CBC encrypted
  6. Receive and display server's integrity confirmation

Usage:
  python client.py --file <path> [--host HOST] [--port PORT]
"""

import socket
import argparse
import time
import json
import math
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))

from crypto_utils import (
    public_key_from_pem, generate_aes_key,
    rsa_encrypt_session_key, aes_encrypt,
    sha256_file, sha256_bytes,
    send_msg, recv_msg, get_logger, CHUNK_SIZE
)

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

log = get_logger("CLIENT")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9999

# Core Transfer Logic
def send_file(filepath: Path, host: str, port: int) -> dict:
    """
    Encrypt and transfer a file to the secure server.
    Returns a stats dict for use by benchmark.py.
    """
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    file_size = filepath.stat().st_size
    log.info("SECURE FILE TRANSFER CLIENT")
    log.info(f"Target file: {filepath.name}")
    log.info(f"File size: {file_size:,} bytes ({file_size / 1024:.1f} KB)")
    log.info(f"Server: {host}:{port}")

    # Compute file hash before anything
    log.info("Computing SHA-256 of original file")
    original_hash = sha256_file(filepath)
    log.info(f"SHA-256: {original_hash}")

    connect_start = time.perf_counter()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        connect_time = time.perf_counter() - connect_start
        log.info(f"[1/5] Connected to server in {connect_time*1000:.1f}ms")

        # Step 1: Receive RSA public key
        pub_pem     = recv_msg(sock)
        public_key  = public_key_from_pem(pub_pem)
        log.info(f"[2/5] Received server RSA public key ({len(pub_pem)} bytes)")

        # Step 2: Generate & send AES session key
        session_key     = generate_aes_key()
        enc_session_key = rsa_encrypt_session_key(session_key, public_key)
        send_msg(sock, enc_session_key)
        log.info(f"[3/5] AES-256 session key generated and sent "
                 f"(RSA-encrypted: {len(enc_session_key)} bytes)")

        # Step 3: Read file & compute chunk count
        with open(filepath, "rb") as f:
            file_data = f.read()

        chunks       = [file_data[i:i + CHUNK_SIZE]
                        for i in range(0, len(file_data), CHUNK_SIZE)]
        total_chunks = len(chunks)

        # Step 4: Send encrypted metadata
        meta = json.dumps({
            "filename"    : filepath.name,
            "file_size"   : file_size,
            "sha256"      : original_hash,
            "total_chunks": total_chunks,
        }).encode()
        send_msg(sock, aes_encrypt(meta, session_key))
        log.info(f"[4/5] Metadata sent (encrypted) - "
                 f"{total_chunks} chunks of {CHUNK_SIZE // 1024} KB each")

        # Step 5: Stream encrypted chunks
        log.info(f"[5/5] Streaming encrypted file")
        transfer_start   = time.perf_counter()
        total_wire_bytes = 0

        if HAS_TQDM:
            iterator = tqdm(chunks, unit="chunk", desc="  Encrypting & sending",
                            bar_format="{l_bar}{bar:30}{r_bar}")
        else:
            iterator = chunks

        for chunk in iterator:
            enc_chunk = aes_encrypt(chunk, session_key)
            send_msg(sock, enc_chunk)
            total_wire_bytes += len(enc_chunk)

        transfer_time = time.perf_counter() - transfer_start
        throughput    = (total_wire_bytes / 1024 / 1024) / transfer_time \
                        if transfer_time > 0 else 0

        # Step 6: Receive integrity confirmation
        response = recv_msg(sock).decode()
        status, server_hash = response.split(":", 1)

        if status == "OK":
            log.info("SERVER CONFIRMED: File integrity VERIFIED")
        else:
            log.error("SERVER REPORTED: Integrity check FAILED")
        log.info(f"Server SHA-256: {server_hash}")
        log.info(f"Match: {server_hash == original_hash}")

        overhead_pct = (total_wire_bytes - file_size) / file_size * 100

        log.info("Transfer Statistics:")
        log.info(f"Original size: {file_size:,} bytes")
        log.info(f"Wire size: {total_wire_bytes:,} bytes")
        log.info(f"Enc overhead: +{overhead_pct:.1f}%")
        log.info(f"Transfer time: {transfer_time:.3f}s")
        log.info(f"Throughput: {throughput:.2f} MB/s")
        log.info(f"Session key: {session_key.hex()[:16]} (AES-256, ephemeral)")

        return {
            "file_size"      : file_size,
            "wire_bytes"     : total_wire_bytes,
            "transfer_time"  : transfer_time,
            "throughput_mbs" : throughput,
            "integrity_ok"   : status == "OK",
            "overhead_pct"   : overhead_pct,
        }

# CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Secure File Transfer Client (RSA + AES-256-CBC)"
    )
    parser.add_argument("--file", required=True, type=Path,
                        help="Path to file to transfer")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Server address")
    parser.add_argument("--port", default=DEFAULT_PORT, type=int, help="Server port")
    args = parser.parse_args()

    try:
        send_file(args.file, args.host, args.port)
    except FileNotFoundError as e:
        log.error(str(e))
        sys.exit(1)
    except ConnectionRefusedError:
        log.error(f"Could not connect to {args.host}:{args.port}. Is the server running?")
        sys.exit(1)
