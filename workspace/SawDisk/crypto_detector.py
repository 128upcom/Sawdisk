"""
Cryptocurrency detection logic for SawDisk
"""
import re
import json
import base58
import magic
from pathlib import Path
from typing import Dict, Any, Optional
import binascii

from models import ScanResult


class CryptoDetector:
    """Detects cryptocurrency wallets and keys in files"""
    
    def __init__(self, config):
        self.config = config
    
    def analyze_file(self, file_path: str) -> Optional[ScanResult]:
        """Analyze a file and return results if crypto content is found"""
        
        file_path_obj = Path(file_path)
        
        # Check file type
        if self._is_binary_file(file_path):
            result = self._analyze_binary_file(file_path)
        else:
            result = self._analyze_text_file(file_path)
            
        return result
    
    def _is_binary_file(self, file_path: str) -> bool:
        """Check if file is binary"""
        try:
            mime_type = magic.from_file(file_path, mime=True)
            return not mime_type.startswith('text/')
        except:
            # Fallback: read first few bytes
            try:
                with open(file_path, 'rb') as f:
                    chunk = f.read(1024)
                    return b'\0' in chunk
            except:
                return True
    
    def _analyze_binary_file(self, file_path: str) -> Optional[ScanResult]:
        """Analyze binary file for crypto patterns"""
        file_path_obj = Path(file_path)
        
        # Check filename patterns first
        filename_match = self._check_filename_patterns(file_path_obj)
        if filename_match:
            return filename_match
            
        # Analyze file content for known crypto patterns
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return self._scan_binary_content(content, file_path)
        except Exception:
            return None
    
    def _analyze_text_file(self, file_path: str) -> Optional[ScanResult]:
        """Analyze text file for crypto patterns"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                return self._scan_text_content(content, file_path)
        except Exception:
            return None
    
    def _check_filename_patterns(self, file_path: Path) -> Optional[ScanResult]:
        """Check filename against known wallet patterns"""
        name = file_path.name.lower()
        
        for wallet_type, patterns in self.config.wallet_patterns.items():
            for pattern in patterns:
                if pattern.lower() in name:
                    return ScanResult(
                        file_path=str(file_path),
                        item_type=f"{wallet_type}_wallet_file",
                        confidence=0.8,
                        details={
                            'detection_method': 'filename_pattern',
                            'pattern_matched': pattern,
                            'wallet_type': wallet_type
                        }
                    )
        return None
    
    def _scan_binary_content(self, content: bytes, file_path: str) -> Optional[ScanResult]:
        """Scan binary content for crypto patterns"""
        
        # Look for common crypto signatures
        signatures = {
            b'Bitcoin': ('bitcoin_core_wallet', 0.7),
            b'Electrum': ('electrum_wallet', 0.7),
            b'Ethereum': ('ethereum_wallet', 0.6),
            b'Litecoin': ('litecoin_wallet', 0.7),
        }
        
        for signature, (type_name, confidence) in signatures.items():
            if signature in content:
                return ScanResult(
                    file_path=file_path,
                    item_type=type_name,
                    confidence=confidence,
                    details={
                        'detection_method': 'binary_signature',
                        'signature': signature.decode('utf-8', errors='ignore')
                    }
                )
        
        # Look for Bitcoin wallet.dat signature
        if b'\xE6\xE1\xCF\xFA' in content:  # Bitcoin wallet.dat magic
            return ScanResult(
                file_path=file_path,
                item_type='bitcoin_core_wallet',
                confidence=0.9,
                details={'detection_method': 'bitcoin_wallet_magic'}
            )
        
        return None
    
    def _scan_text_content(self, content: str, file_path: str) -> Optional[ScanResult]:
        """Scan text content for crypto patterns"""
        
        # Check for JSON wallet files
        json_result = self._check_json_wallet(content, file_path)
        if json_result:
            return json_result
        
        # Check for private keys
        key_result = self._check_private_keys(content, file_path)
        if key_result:
            return key_result
        
        # Check for seed phrases
        seed_result = self._check_seed_phrases(content, file_path)
        if seed_result:
            return seed_result
        
        # Check for wallet configs
        config_result = self._check_wallet_configs(content, file_path)
        if config_result:
            return config_result
        
        return None
    
    def _check_json_wallet(self, content: str, file_path: str) -> Optional[ScanResult]:
        """Check if content is a JSON wallet file"""
        try:
            data = json.loads(content)
            
            # Common wallet JSON structures
            if isinstance(data, dict):
                # Ethereum keystore
                if 'crypto' in data and 'keystore' in file_path.lower():
                    return ScanResult(
                        file_path=file_path,
                        item_type='ethereum_keystore',
                        confidence=0.9,
                        details={'detection_method': 'ethereum_keystore_json'}
                    )
                
                # MultiBit wallet
                if 'walletModel' in data or 'wallets' in data:
                    return ScanResult(
                        file_path=file_path,
                        item_type='multibit_wallet',
                        confidence=0.8,
                        details={'detection_method': 'multibit_json'}
                    )
                
                # Exodus wallet
                if 'primaryWallet' in data or 'wallets' in data:
                    return ScanResult(
                        file_path=file_path,
                        item_type='exodus_wallet',
                        confidence=0.8,
                        details={'detection_method': 'exodus_json'}
                    )
                    
        except json.JSONDecodeError:
            pass
        
        return None
    
    def _check_private_keys(self, content: str, file_path: str) -> Optional[ScanResult]:
        """Check for private key patterns"""
        
        # Bitcoin WIF private key
        wif_pattern = r'^[5KLNQ][123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]{50,51}$'
        if re.search(wif_pattern, content.strip(), re.MULTILINE):
            return ScanResult(
                file_path=file_path,
                item_type='bitcoin_private_key',
                confidence=0.7,
                details={'detection_method': 'wif_pattern'}
            )
        
        # Ethereum private key (64 hex chars)
        eth_pattern = r'^(0x)?[a-fA-F0-9]{64}$'
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if re.match(eth_pattern, line):
                return ScanResult(
                    file_path=file_path,
                    item_type='ethereum_private_key',
                    confidence=0.7,
                    details={'detection_method': 'eth_hex_pattern'}
                )
        
        # Generic hex private key
        hex_pattern = r'^[a-fA-F0-9]{64}$'
        for line in lines:
            if re.match(hex_pattern, line.strip()) and len(line.strip()) == 64:
                return ScanResult(
                    file_path=file_path,
                    item_type='generic_private_key',
                    confidence=0.5,
                    details={'detection_method': 'hex_64_pattern'}
                )
        
        return None
    
    def _check_seed_phrases(self, content: str, file_path: str) -> Optional[ScanResult]:
        """Check for mnemonic seed phrases"""
        
        # Common BIP39 seed phrase pattern
        words = content.strip().split()
        if 12 <= len(words) <= 24:
            # Check if words look like BIP39 words (simplified check)
            bip39_words = {
                'abandon', 'ability', 'able', 'about', 'above', 'absent', 'absolute',
                'absorb', 'abstract', 'absurd', 'accept', 'access', 'accident',
                'account', 'accuse', 'achieve', 'acid', 'acoustic', 'acquire',
                'action', 'actor', 'actual', 'adapt', 'addiction', 'address'
            }
            
            if any(word.lower() in bip39_words for word in words[:5]):
                return ScanResult(
                    file_path=file_path,
                    item_type='bip39_seed_phrase',
                    confidence=0.6,
                    details={
                        'detection_method': 'bip39_word_check',
                        'word_count': len(words)
                    }
                )
        
        return None
    
    def _check_wallet_configs(self, content: str, file_path: str) -> Optional[ScanResult]:
        """Check for wallet configuration files"""
        
        # Look for common wallet config patterns
        config_patterns = [
             ('bitcoin', r'bitcoin.*:.*true'),
             ('litecoin', r'litecoin.*:.*true'),
             ('database', r'db.*=.*wallet'),
             ('wallet', r'wallet.*pass'),
             ('electrum', r'electrum.*:.*true'),
             ('multibit', r'multibit.*wallet')
         ]
        
        for wallet_type, pattern in config_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return ScanResult(
                    file_path=file_path,
                    item_type=f'{wallet_type}_config',
                    confidence=0.5,
                    details={'detection_method': 'config_pattern', 'pattern': pattern}
                )
        
        return None
