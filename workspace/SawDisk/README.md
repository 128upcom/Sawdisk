# 🔍 SawDisk - Crypto Wallet Scanner

A forensic tool for detecting cryptocurrency wallets, private keys, and related files on external volumes.

## Features

- 🚀 **Multi-threaded scanning** for fast performance
- 🔍 **Advanced detection patterns** for various crypto wallets
- 📊 **Multiple report formats** (HTML, JSON, Markdown)
- 🛡️ **Safe scanning** with read-only access to external volumes
- 🎯 **High-precision detection** with confidence scoring

## Supported Wallet Types

- **Bitcoin Core** (wallet.dat, etc.)
- **Electrum** wallets
- **Ethereum** (keystores, Geth)
- **Litecoin** wallets
- **Monero** wallets
- **MultiBit** wallets
- **Exodus** wallets
- **Various other** crypto wallets

## Supported File Types

- `.wallet`, `.dat`, `.key`, `.pem`
- `.json` (keystores)
- `.kdbx`, `.db`, `.sqlite`
- `.seed`, `.mnemonic`, `.backup`
- And many more...

## Quick Start

### Build Docker Environment

```bash
# Build and start the Python environment
docker-compose build
docker-compose up -d
```

### Run SawDisk

```bash
# Enter the container
docker-compose exec python bash

# Scan default path
python -m SawDisk.main

# Scan specific path with HTML report
python -m SawDisk.main -p /mnt/external_drive -f html -o /app/data/reports

# Verbose scanning with custom settings
python -m SawDisk.main -p /path/to/scan -t 8 -d 30 -v
```

### Command Line Options

```
Usage: main.py [OPTIONS]

Options:
  -p, --path PATH           Path to scan (default: /mnt/volumes)
  -o, --output PATH         Output directory for reports
  -f, --format [html|json|markdown]  Report format (default: html)
  -d, --depth INTEGER       Maximum directory depth to scan
  -t, --threads INTEGER     Number of scanning threads
  -v, --verbose            Enable verbose output
  --help                   Show help
```

## Reports

SawDisk generates comprehensive reports showing:

- 📈 **Summary statistics**
- 🎯 **Detection confidence levels**
- 📁 **File locations and sizes**
- 🔍 **Detection methods used**
- ⚠️ **Detailed findings**

## Security & Ethics

⚠️ **Important:** This tool is designed for:
- 🔐 **Legitimate forensic investigations**
- 🛡️ **Security assessments**
- 📋 **Personal wallet recovery** (your own wallets only)
- 📚 **Educational purposes**

**Never use this tool to scan systems you don't own!**

## Technical Details

- **Python 3.11+**
- **Multi-threaded file scanning**
- **Pattern-based crypto detection**
- **Magic file type detection**
- **Read-only scanning for safety**

## Contributing

Contributions are welcome! Areas for improvement:
- Additional wallet type detection
- New crypto format support
- Performance optimizations
- Better false positive filtering
