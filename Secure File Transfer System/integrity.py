"""
integrity.py - File Integrity Verification Utility

Standalone tool to verify SHA-256 hashes of files.
Useful for manually checking that a received file matches the original.

Usage:
  python integrity.py --original <path> --received <path>
  python integrity.py --hash <hex> --file <path>
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from crypto_utils import sha256_file, get_logger

log = get_logger("INTEGRITY")


def verify_files(original: Path, received: Path) -> bool:
    """Compare SHA-256 of two files."""
    log.info("FILE INTEGRITY VERIFICATION")

    h_orig = sha256_file(original)
    h_recv = sha256_file(received)

    log.info(f"Original: {original.name}")
    log.info(f"SHA-256: {h_orig}")
    log.info(f"")
    log.info(f"Received: {received.name}")
    log.info(f"SHA-256: {h_recv}")

    if h_orig == h_recv:
        log.info("MATCH - Files are identical, no tampering detected.")
        return True
    else:
        log.error("MISMATCH - Files differ! Possible corruption or tampering.")
        # Show first differing nibble position for forensics
        for i, (a, b) in enumerate(zip(h_orig, h_recv)):
            if a != b:
                log.error(f"First difference at hex digest position {i}")
                break
        return False


def verify_against_hash(expected_hash: str, filepath: Path) -> bool:
    """Verify a file against a known SHA-256 hex string."""
    actual = sha256_file(filepath)
    log.info(f"File: {filepath}")
    log.info(f"Expected: {expected_hash}")
    log.info(f"Actual: {actual}")
    match = expected_hash.lower() == actual.lower()
    if match:
        log.info("VERIFIED")
    else:
        log.error("MISMATCH")
    return match


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SHA-256 File Integrity Checker")
    sub = parser.add_subparsers(dest="mode", required=True)

    p1 = sub.add_parser("compare", help="Compare two files")
    p1.add_argument("--original", required=True, type=Path)
    p1.add_argument("--received", required=True, type=Path)

    p2 = sub.add_parser("verify", help="Verify file against known hash")
    p2.add_argument("--hash", required=True, help="Expected SHA-256 hex digest")
    p2.add_argument("--file", required=True, type=Path)

    args = parser.parse_args()

    if args.mode == "compare":
        ok = verify_files(args.original, args.received)
    else:
        ok = verify_against_hash(args.hash, args.file)

    sys.exit(0 if ok else 1)



"""
demo.py - Full End-to-End Secure Transfer Demo

Self-contained demo that:
  1. Creates a sample test file with known content
  2. Starts the secure server in a background thread
  3. Sends the file using the secure client
  4. Verifies the received file matches original (SHA-256)
  5. Shows a side-by-side diff summary

No external processes needed - run with:
  python demo.py
"""

import threading
import time
import os
import sys
import socket
import json
import struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from crypto_utils import (
    generate_rsa_keypair, public_key_to_pem, public_key_from_pem,
    generate_aes_key, rsa_encrypt_session_key, rsa_decrypt_session_key,
    aes_encrypt, aes_decrypt,
    sha256_file, sha256_bytes,
    send_msg, recv_msg, get_logger, CHUNK_SIZE
)

log = get_logger("DEMO")

DEMO_HOST = "127.0.0.1"
DEMO_PORT = 29999
DEMO_DIR  = Path(__file__).parent / "demo_files"

# Embedded Server (for demo - no subprocess needed)
def _demo_server(private_key, public_key, ready_event, result):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((DEMO_HOST, DEMO_PORT))
        srv.listen(1)
        ready_event.set()
        conn, addr = srv.accept()
        with conn:
            # 1. Send public key
            send_msg(conn, public_key_to_pem(public_key))
            # 2. Receive + decrypt session key
            enc_sk = recv_msg(conn)
            sk = rsa_decrypt_session_key(enc_sk, private_key)
            # 3. Receive metadata
            meta_raw = recv_msg(conn)
            meta = json.loads(aes_decrypt(meta_raw, sk).decode())
            filename     = Path(meta["filename"]).name
            orig_hash    = meta["sha256"]
            total_chunks = meta["total_chunks"]
            # 4. Receive file chunks
            received = b""
            wire_bytes = 0
            for _ in range(total_chunks):
                enc = recv_msg(conn)
                received += aes_decrypt(enc, sk)
                wire_bytes += len(enc)
            # 5. Write received file
            out_path = DEMO_DIR / ("received_" + filename)
            out_path.write_bytes(received)
            # 6. Verify + respond
            recv_hash = sha256_bytes(received)
            ok = recv_hash == orig_hash
            send_msg(conn, (("OK:" if ok else "FAIL:") + recv_hash).encode())
            result.update({
                "path"      : out_path,
                "hash"      : recv_hash,
                "match"     : ok,
                "wire_bytes": wire_bytes,
            })

# Demo Transfer
def run_demo():
    DEMO_DIR.mkdir(exist_ok=True)

    # Create demo file
    demo_file = DEMO_DIR / "secret_document.txt"
    demo_content = """CONFIDENTIAL DOCUMENT
=====================
Project: Secure File Transfer System
Classification: TOP SECRET

This document contains sensitive information about our encryption protocol.
It uses RSA-2048 for key exchange and AES-256-CBC for data confidentiality.

Key Points:
  1. Hybrid encryption mimics real-world TLS behaviour
  2. Session keys are ephemeral - never reused across connections
  3. SHA-256 hashing ensures end-to-end integrity
  4. Any tampering of the ciphertext is detected at the receiver

If you can read this on the receiver side with integrity verified,
the secure transfer system works correctly!

Random payload to increase file size and make the demo more realistic:
""" + ("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" * 50 + "\n") * 30

    demo_file.write_text(demo_content)
    file_size  = demo_file.stat().st_size
    orig_hash  = sha256_file(demo_file)

    print("\n" + "=" * 60)
    print("  SECURE FILE TRANSFER SYSTEM - LIVE DEMO")
    print("=" * 60)
    print(f"\n  File: {demo_file.name}")
    print(f"  Size: {file_size:,} bytes")
    print(f"  SHA-256: {orig_hash[:32]}\n")

    # Start embedded server
    private_key, public_key = generate_rsa_keypair(save=True)
    srv_result  = {}
    ready       = threading.Event()
    t = threading.Thread(target=_demo_server,
                         args=(private_key, public_key, ready, srv_result),
                         daemon=True)
    t.start()
    ready.wait()
    print("  [SERVER] Listening on 127.0.0.1:29999")
    print("  [SERVER] RSA-2048 keypair loaded\n")

    # Client connects and sends
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((DEMO_HOST, DEMO_PORT))
        print("  [CLIENT] Connected to server")

        pub_pem    = recv_msg(sock)
        public_key = public_key_from_pem(pub_pem)
        print(f"  [CLIENT] Received server RSA public key ({len(pub_pem)} bytes)")

        session_key = generate_aes_key()
        enc_sk      = rsa_encrypt_session_key(session_key, public_key)
        send_msg(sock, enc_sk)
        print(f"  [CLIENT] AES-256 session key generated + RSA-encrypted -> sent")
        print(f"           Session key: {session_key.hex()[:24]} (ephemeral)")

        with open(demo_file, "rb") as f:
            file_data = f.read()

        chunks = [file_data[i:i + CHUNK_SIZE]
                  for i in range(0, len(file_data), CHUNK_SIZE)]
        meta = json.dumps({
            "filename"    : demo_file.name,
            "file_size"   : file_size,
            "sha256"      : orig_hash,
            "total_chunks": len(chunks),
        }).encode()
        send_msg(sock, aes_encrypt(meta, session_key))
        print(f"  [CLIENT] Metadata sent (AES-encrypted)")

        t0 = time.perf_counter()
        total_wire = 0
        for i, chunk in enumerate(chunks):
            enc = aes_encrypt(chunk, session_key)
            send_msg(sock, enc)
            total_wire += len(enc)
        elapsed = time.perf_counter() - t0
        print(f"  [CLIENT] {len(chunks)} chunk(s) sent in {elapsed:.4f}s "
              f"({total_wire:,} wire bytes)")

        response  = recv_msg(sock).decode()
        status, _ = response.split(":", 1)

    t.join(timeout=5)

    # Results
    recv_path = srv_result.get("path")
    recv_hash = srv_result.get("hash", "-")
    match     = srv_result.get("match", False)

    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print(f"  Original file: {demo_file}")
    print(f"  Received file: {recv_path}")
    print(f"  Original SHA-256: {orig_hash}")
    print(f"  Received SHA-256: {recv_hash}")
    print(f"  Integrity: {'VERIFIED - files are identical' if match else 'FAILED'}")
    print(f"  Wire overhead: {(total_wire - file_size) / file_size * 100:.1f}% "
          f"(AES IV + PKCS7 padding)")
    print(f"  Encryption algo: AES-256-CBC (session key) + RSA-2048 (key exchange)")
    print("=" * 60 + "\n")

    if recv_path and recv_path.exists():
        print("  Verifying received file content (first 3 lines):")
        lines = recv_path.read_text().splitlines()[:3]
        for line in lines:
            print(f"    | {line}")
        print("  Content decrypted successfully.\n")


if __name__ == "__main__":
    run_demo()
