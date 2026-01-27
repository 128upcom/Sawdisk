#!/usr/bin/env python3
"""
Test script for SawDisk
"""
import tempfile
import os
from pathlib import Path

# Create test files
test_dir = Path("/tmp/sawdisk_test")
test_dir.mkdir(exist_ok=True)

# Test Bitcoin wallet.dat signature
fake_wallet_dat = test_dir / "test_wallet.dat"
with open(fake_wallet_dat, 'wb') as f:
    f.write(b'\xE6\xE1\xCF\xFA' + b'fake bitcoin wallet data')

# Test JSON keystore
fake_keystore = test_dir / "UTC--keystore.json"
keystore_data = """{
    "crypto": {
        "cipher": "aes-128-ctr",
        "ciphertext": "fakeciphetext",
        "kdf": "scrypt",
        "mac": "fakemac"
    },
    "version": 3
}"""
with open(fake_keystore, 'w') as f:
    f.write(keystore_data)

# Test private key file
fake_keys = test_dir / "private_keys.txt"
keys_data = """5KJvsngHeMpm884wtkJvQa3EhhFmqzr7cPJjjLQj5vhYzUWjJmN
L3iXrJpLJFqZQFmJWjqxJcQcMjpAJJxqQHcQxQmZJYHkPQRQJhM
0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"""
with open(fake_keys, 'w') as f:
    f.write(keys_data)

# Test seed phrase file
fake_seed = test_dir / "seed_backup.txt"
seed_data = "abandon ability able about above absent absolute absorb abstract absurd accept access"
with open(fake_seed, 'w') as f:
    f.write(seed_data)

print(f"✅ Test files created in: {test_dir}")
print(f"Files created:")
for file in test_dir.iterdir():
    print(f"  - {file.name}")

print(f"\nTo test SawDisk:")
print(f"python workspace/SawDisk/main.py -p {test_dir} -v")
