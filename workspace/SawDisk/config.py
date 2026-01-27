"""
Configuration management for SawDisk
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Configuration settings for SawDisk scanner"""
    scan_path: str
    output_dir: str
    report_format: str = 'html'
    max_depth: int = 20
    num_threads: int = 4
    verbose: bool = False
    
    # File size limits
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    
    # Supported crypto file extensions
    crypto_extensions = {
        '.wallet', '.json', '.dat', '.key', '.pem', '.p12', '.pfx',
        '.txt', '.csv', '.kdbx', '.db', '.sqlite', '.walletdb',
        '.seed', '.mnemonic', '.backup', '.keystore', '.cert', '.crt',
        '.pub', '.private', '.wallet', '.store'
    }
    
    # Additional files to scan for crypto content
    crypto_content_extensions = {
        '.txt', '.json', '.csv', '.log', '.cfg', '.conf', '.ini'
    }
    
    # Known crypto wallet patterns
    wallet_patterns = {
        'bitcoin_core': ['wallet.dat', 'wallet'],
        'electrum': ['default_wallet', 'electrum'],
        'ethereum': ['keystore', 'UTC--'],
        'litecoin': ['wallet.dat', 'litecoin'],
        'monero': ['wallet'],
        'dogecoin': ['wallet.dat'],
        'tron': ['wallet'],
        'binance': ['Binance'],
        'coinbase': ['Coinbase'],
        'trust_wallet': ['TrustWallet']
    }
    
    # Private key patterns (regex patterns)
    private_key_patterns = [
        r'[1-9A-HJ-NP-Za-km-z]{30,}',  # Generic base58
        r'[0-9a-fA-F]{64}',  # Hex (64 chars)
        r'^5[HJK][1-9A-HJ-NP-Za-km-z]{49}$',  # Bitcoin WIF
        r'^[KLNQ][1-9A-HJ-NP-Za-km-z]{49}$',  # Bitcoin WIF compressed
        r'^0x[a-fA-F0-9]{64}$',  # Ethereum private key
    ]

