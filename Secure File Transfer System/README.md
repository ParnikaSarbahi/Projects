# Secure File Transfer System

A secure file transfer system built in Python that demonstrates the practical use of **hybrid encryption** for protecting data in transit. The project combines **RSA-2048** for secure session key exchange, **AES-256-CBC** for file encryption, and **SHA-256** for integrity verification.

Rather than encrypting entire files with RSA, the system follows the same high-level approach used by modern secure communication protocols: a public-key algorithm establishes a shared symmetric key, which is then used to encrypt the actual data.

---

## Overview

**Features**

* RSA-2048 key generation and secure session establishment
* RSA-OAEP encrypted AES session key exchange
* AES-256-CBC encryption for metadata and file contents
* SHA-256 integrity verification
* Chunk-based encrypted file transfer
* Performance benchmarking
* Standalone demo for testing without manually starting client and server

---

## Architecture

### Transfer Workflow

```text
CLIENT                                    SERVER
  |                                          |
  | <------ RSA Public Key (PEM) ----------- | 1. Public key exchange
  |                                          |
  | ------ RSA-OAEP(AES Session Key) ------> | 2. Session establishment
  |                                          |
  | ------ AES-256-CBC(File Metadata) -----> | 3. Metadata transfer
  |                                          |
  | ------ AES-256-CBC(File Chunks) -------> | 4. Encrypted file transfer
  |                                          |
  | <------ SHA-256 Verification + ACK ----- | 5. Integrity verification
```

### Why Hybrid Encryption?

RSA encryption is computationally expensive and limited to encrypting relatively small amounts of data. Encrypting an entire file directly with RSA is therefore impractical.

Instead, this project uses a hybrid approach:

1. The server generates an RSA key pair.
2. The client generates a random 256-bit AES session key.
3. The AES key is encrypted with the server's RSA public key.
4. Both sides use the shared AES key to encrypt and decrypt the file.

This design combines the security of asymmetric cryptography with the performance of symmetric encryption.

---

## Project Structure

```text
.
├── client.py          # TCP client and encrypted file sender
├── server.py          # TCP server and encrypted file receiver
├── crypto_utils.py    # RSA, AES, SHA-256, framing utilities
├── integrity.py       # File integrity verification tool
├── benchmark.py       # Encryption performance benchmark
├── demo.py            # End-to-end demonstration
├── requirements.txt
└── keys/              # Auto-generated RSA key pair
```

---

## Installation

Clone the repository and install the required dependencies.

```bash
git clone <repository-url>
cd secure-file-transfer-system

pip install -r requirements.txt
```

---

## Usage

### Run the Demo

Runs both the client and server automatically for a complete demonstration.

```bash
python demo.py
```

### Start the Server

```bash
python server.py --host 127.0.0.1 --port 9999
```

### Run the Client

```bash
python client.py \
    --file path/to/file.pdf \
    --host 127.0.0.1 \
    --port 9999
```

### Verify File Integrity

```bash
python integrity.py compare \
    --original original.pdf \
    --received received/original.pdf
```

### Benchmark Performance

```bash
python benchmark.py
```

---

## Security Design

| Property             | Implementation                                     |
| -------------------- | -------------------------------------------------- |
| Confidentiality      | AES-256-CBC encryption                             |
| Session Key Exchange | RSA-2048 with OAEP padding                         |
| Integrity            | SHA-256 hash verification                          |
| Session Isolation    | Fresh AES key generated for every connection       |
| Randomization        | New random IV generated for each encrypted message |

### Cryptographic Components

#### RSA-2048

RSA is used only during the initial handshake to securely exchange the AES session key. Once the key is shared, RSA is no longer used for the remainder of the transfer.

#### AES-256-CBC

AES encrypts both the file metadata and the file contents. Files are transferred in encrypted chunks to support files larger than available memory.

#### SHA-256

The sender computes the SHA-256 hash of the original file before transmission. After decryption, the receiver computes the hash again and compares the two values to verify file integrity.

---

## Sample Output

```text
SECURE FILE TRANSFER SYSTEM

File: secret_document.txt
Size: 54,726 bytes

SHA-256:
9d6b559aae903b1c6c9d6e...

[CLIENT] Received server RSA public key (451 bytes)

[CLIENT] Generated AES-256 session key
[CLIENT] Session key encrypted using RSA-OAEP

[CLIENT] Sent 1 encrypted chunk
Transfer Time : 0.0006 s
Wire Size     : 54,752 bytes

Integrity Check : VERIFIED
Files are identical.

Wire Overhead : 0.0%
```

---

## Performance

The benchmark compares encrypted and plaintext file transfers to measure the computational and bandwidth overhead introduced by encryption.

Typical observations include:

* Minimal bandwidth overhead caused by IVs and PKCS#7 padding
* Efficient transfer using streamed file chunks
* Encryption overhead small relative to overall transfer time for typical file sizes

---

## Project Highlights

This project demonstrates practical implementation of:

* Hybrid cryptography using RSA and AES
* Secure TCP socket communication
* Binary protocol design
* Chunked encrypted file transfer
* SHA-256 based integrity verification
* Performance benchmarking for encrypted communication

---

## Limitations

This project is intended as an educational implementation and should not be considered a replacement for production protocols such as TLS.

Current limitations include:

* AES-CBC provides confidentiality but not authenticated encryption. Modern systems typically use AES-GCM or ChaCha20-Poly1305.
* RSA key exchange alone does not provide Perfect Forward Secrecy (PFS). Modern TLS achieves PFS using ephemeral Diffie-Hellman key exchange (ECDHE).
* Server authentication is limited to trusting the exchanged public key and does not use certificates or a certificate authority.

---

## Dependencies

| Package                 | Purpose                                  |
| ----------------------- | ---------------------------------------- |
| cryptography            | RSA, AES, OAEP, PKCS#7 primitives        |
| tqdm                    | Progress bars                            |
| Python Standard Library | socket, hashlib, struct, json, threading |

---

## License

This project is provided for educational purposes and to demonstrate practical cryptography concepts in Python.
