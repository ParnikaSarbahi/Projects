"""
server.py - Secure File Transfer Server

Handshake Protocol:
  1. On startup: generate RSA-2048 keypair (or load existing)
  2. Client connects - server sends RSA public key (PEM)
  3. Client sends RSA-encrypted AES-256 session key
  4. Server decrypts session key with RSA private key
  5. Client sends metadata (filename, file size, original SHA-256)
  6. Client streams AES-256-CBC encrypted file chunks
  7. Server decrypts chunks, writes file, verifies SHA-256 integrity

Usage:
  python server.py [--host HOST] [--port PORT] [--output-dir DIR]
"""

import socket
import argparse
import time
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))

from crypto_utils import (
    generate_rsa_keypair, load_private_key, public_key_to_pem,
    rsa_decrypt_session_key, aes_decrypt,
    sha256_bytes, send_msg, recv_msg, get_logger, KEYS_DIR
)

log = get_logger("SERVER")

DEFAULT_HOST    = "127.0.0.1"
DEFAULT_PORT    = 9999
DEFAULT_OUT_DIR = Path(__file__).parent / "received"

# Key Management
def get_or_create_keypair():
    priv_path = KEYS_DIR / "server_private.pem"
    pub_path  = KEYS_DIR / "server_public.pem"
    if priv_path.exists() and pub_path.exists():
        log.info("Loading existing RSA keypair from keys/")
        private_key = load_private_key()
        from crypto_utils import load_public_key
        public_key  = load_public_key()
    else:
        log.info("No keypair found - generating new RSA-2048 keys")
        private_key, public_key = generate_rsa_keypair(save=True)
    return private_key, public_key

# Client Handler
def handle_client(conn, addr, private_key, public_key, output_dir: Path):
    log.info(f"New connection from {addr[0]}:{addr[1]}")
    session_start = time.perf_counter()

    try:
        # Step 1: Send RSA public key
        pub_pem = public_key_to_pem(public_key)
        send_msg(conn, pub_pem)
        log.info(f"[1/5] RSA public key sent ({len(pub_pem)} bytes)")

        # Step 2: Receive RSA-encrypted AES session key
        enc_session_key = recv_msg(conn)
        session_key = rsa_decrypt_session_key(enc_session_key, private_key)
        log.info(f"[2/5] AES-256 session key received and decrypted "
                 f"(RSA ciphertext: {len(enc_session_key)} bytes)")

        # Step 3: Receive file metadata
        meta_raw  = recv_msg(conn)
        meta_data = aes_decrypt(meta_raw, session_key)
        meta      = json.loads(meta_data.decode())
        filename       = Path(meta["filename"]).name  # sanitize path traversal
        original_hash  = meta["sha256"]
        total_chunks   = meta["total_chunks"]
        original_size  = meta["file_size"]

        log.info(f"[3/5] Metadata - file: '{filename}' | "
                 f"size: {original_size:,} bytes | chunks: {total_chunks}")
        log.info(f"Expected SHA-256: {original_hash}")

        # Step 4: Receive encrypted chunks
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path  = output_dir / filename
        received_data = b""
        chunk_times   = []
        bytes_received = 0

        log.info(f"[4/5] Receiving {total_chunks} encrypted chunks")
        for i in range(total_chunks):
            t0          = time.perf_counter()
            enc_chunk   = recv_msg(conn)
            chunk_data  = aes_decrypt(enc_chunk, session_key)
            received_data += chunk_data
            bytes_received += len(enc_chunk)
            chunk_times.append(time.perf_counter() - t0)

            if (i + 1) % max(1, total_chunks // 5) == 0 or (i + 1) == total_chunks:
                progress = (i + 1) / total_chunks * 100
                log.info(f"Progress: {progress:.0f}% ({i+1}/{total_chunks} chunks)")

        # Step 5: Integrity check & write
        received_hash = sha256_bytes(received_data)
        with open(output_path, "wb") as f:
            f.write(received_data)

        elapsed = time.perf_counter() - session_start
        throughput = (bytes_received / 1024 / 1024) / elapsed if elapsed > 0 else 0

        log.info(f"[5/5] Integrity check:")
        log.info(f"Expected : {original_hash}")
        log.info(f"Received : {received_hash}")

        if received_hash == original_hash:
            log.info("INTEGRITY VERIFIED - file is intact")
            send_msg(conn, b"OK:" + received_hash.encode())
        else:
            log.error("INTEGRITY MISMATCH - file may be corrupted")
            send_msg(conn, b"FAIL:" + received_hash.encode())

        log.info(f"Session summary")
        log.info(f"File saved: {output_path}")
        log.info(f"Original size: {original_size:,} bytes")
        log.info(f"Wire size: {bytes_received:,} bytes "
                 f"(+{(bytes_received - original_size) / original_size * 100:.1f}% encryption overhead)")
        log.info(f"Transfer time: {elapsed:.3f}s")
        log.info(f"Throughput: {throughput:.2f} MB/s (encrypted)")

    except Exception as e:
        log.error(f"  Error handling client {addr}: {e}", exc_info=True)
    finally:
        conn.close()
        log.info(f"Connection with {addr[0]}:{addr[1]} closed.")


# Main Server Loop
def run_server(host: str, port: int, output_dir: Path):
    private_key, public_key = get_or_create_keypair()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((host, port))
        srv.listen(5)

        log.info("SECURE FILE TRANSFER SERVER - READY")
        log.info(f"Listening on: {host}:{port}")
        log.info(f"Encryption: RSA-2048 key exchange + AES-256-CBC")
        log.info(f"Integrity: SHA-256 file verification")
        log.info(f"Output dir: {output_dir}")
        log.info("Waiting for connections (Ctrl+C to stop)")

        try:
            while True:
                conn, addr = srv.accept()
                handle_client(conn, addr, private_key, public_key, output_dir)
        except KeyboardInterrupt:
            log.info("Server shutting down gracefully.")


# CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Secure File Transfer Server (RSA + AES-256-CBC)"
    )
    parser.add_argument("--host",       default=DEFAULT_HOST,    help="Bind address")
    parser.add_argument("--port",       default=DEFAULT_PORT,    type=int, help="Port")
    parser.add_argument("--output-dir", default=DEFAULT_OUT_DIR, type=Path,
                        help="Directory to save received files")
    args = parser.parse_args()
    run_server(args.host, args.port, args.output_dir)
