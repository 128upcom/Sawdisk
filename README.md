# SawDisk – Crypto Wallet Scanner

A forensic tool for detecting cryptocurrency wallets, private keys, and related files on disks and external volumes. Includes a **web dashboard** for scanning and viewing results, and a **CLI** for scripted use.

**Repository:** [github.com/128upcom/Sawdisk](https://github.com/128upcom/Sawdisk)

---

## Features

- **Web interface** – Dashboard, scan launcher, per-scan summary, scan history
- **Multi-threaded scanning** – Configurable threads and max depth
- **Crypto detection** – Bitcoin Core, Electrum, Ethereum, Litecoin, Monero, and others
- **Per-scan summaries** – Summary and stats saved per run, view any past scan
- **Reports** – HTML (and optional JSON/Markdown) reports per scan
- **Read-only scanning** – No writes to scanned volumes
- **Docker-based** – Single service, reproducible environment

---

## Prerequisites

- **Docker** and **Docker Compose**
- **macOS**: For scanning host volumes, mount `/Volumes` and optionally `/Users` (see [Configuration](#configuration))

---

## Quick Start

### 1. Build and start

```bash
docker compose build
docker compose up -d
```

Or use the helper script:

```bash
./start_sawdisk.sh
```

### 2. Open the web app

- **Dashboard:** http://localhost:5000  
- **Scan:** http://localhost:5000/scan  
- **Summary:** http://localhost:5000/summary  

### 3. Run a scan

1. Go to **Scan**.
2. Choose a drive (e.g. **/PoCII** at `/mnt/volumes/PoCII` or `/mnt/users` for macOS system drive).
3. Set threads and max depth.
4. Click **Start Scan**. Progress and results appear on the dashboard and scan page.

---

## Project Structure

```
Ocelot/
├── README.md                 # This file
├── docker-compose.yml        # Service and volume mounts
├── Dockerfile                # Python 3.11 image + deps
├── requirements.txt          # Python dependencies
├── start_sawdisk.sh          # Build, start, and show URLs
├── test_dashboard.sh         # Basic API/UI checks
├── test_sawdisk.py           # Scanner tests
└── workspace/
    └── SawDisk/
        ├── web_app.py        # Flask app (dashboard, scan, summary, APIs)
        ├── main.py           # CLI entrypoint
        ├── scanner.py        # Disk scanner + file collection
        ├── crypto_detector.py # Crypto pattern detection
        ├── scan_manager.py   # One scan at a time, status, stop
        ├── scan_history.py   # Scan records + summary.json per scan
        ├── config.py         # Paths, extensions, wallet patterns
        ├── reporter.py       # HTML/JSON report generation
        ├── models.py         # ScanResult, etc.
        ├── utils.py          # format_file_size, etc.
        ├── static/           # CSS, JS
        ├── templates/        # HTML (dashboard, scan, summary, base)
        └── README.md         # SawDisk module overview
```

---

## Web Interface

| Page       | URL           | Description |
|-----------|----------------|-------------|
| Dashboard | http://localhost:5000 | System info, drives, real-time scan status, scan history |
| Scan      | http://localhost:5000/scan | Select drive, set options, start/stop scan |
| Summary   | http://localhost:5000/summary | Per-scan summary; dropdown to pick which scan |

- **Real-time status** – Files scanned, progress %, speed, current file.
- **Per-scan summary** – Each run has its own summary (and optional `summary.json` on disk). Use the Summary page dropdown to switch between scans.
- **Scan history** – List of past scans with drive, time, and item count.

---

## CLI Usage

Run the scanner inside the container:

```bash
docker compose exec python python workspace/SawDisk/main.py --help
```

Examples:

```bash
# Default path
docker compose exec python python workspace/SawDisk/main.py

# Specific path, HTML report
docker compose exec python python workspace/SawDisk/main.py -p /mnt/volumes/PoCII -f html -o /app/data/reports  # volume /PoCII

# More threads and depth, verbose
docker compose exec python python workspace/SawDisk/main.py -p /path/to/scan -t 8 -d 30 -v
```

Options:

| Option | Description |
|--------|-------------|
| `-p, --path` | Path to scan (default: /mnt/volumes) |
| `-o, --output` | Report output directory |
| `-f, --format` | Report format: html, json, markdown |
| `-d, --depth` | Max directory depth |
| `-t, --threads` | Number of threads |
| `-v, --verbose` | Verbose output |

---

## Configuration

### Ports

- **5000** – Flask web app (dashboard, scan, summary).
- **8080** – Alternative port (same app).

### Volume mounts (docker-compose.yml)

- `./workspace` → `/app/workspace` (code)
- `./data` → `/app/data` (scan data, history, reports)
- `/Volumes` → `/mnt/volumes:ro` (e.g. external drives on macOS)
- `/Users` → `/mnt/users:ro` (macOS home dir; used to represent “system” drive in the UI)

Adjust paths for your OS. Scanned paths inside the container are under `/mnt/volumes/...` or `/mnt/users/...`.

### Environment

- `PYTHONPATH=/app`
- `FLASK_ENV=development`, `FLASK_DEBUG=1`

---

## Supported Wallet Types

- Bitcoin Core (e.g. wallet.dat)
- Electrum
- Ethereum (keystores, Geth)
- Litecoin
- Monero
- MultiBit, Exodus, and others

## Supported File Types

- `.wallet`, `.dat`, `.key`, `.pem`, `.p12`, `.pfx`
- `.json` (keystores)
- `.kdbx`, `.db`, `.sqlite`
- `.seed`, `.mnemonic`, `.backup`, `.keystore`
- Plus config/content extensions: `.txt`, `.csv`, `.log`, `.cfg`, `.conf`, `.ini`

---

## API Endpoints (for integration/tests)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/system-info` | GET | Mounts, drives, sizes |
| `/api/scan/start` | POST | Start scan (JSON: scan_path, threads, max_depth) |
| `/api/scan/stop` | POST | Request stop |
| `/api/scan/status` | GET | Current scan status and progress |
| `/api/scan/history` | GET | List of past scans |
| `/api/scan/summary?scan_id=...` | GET | Summary for a given scan |
| `/api/scan/<scan_id>` | GET | Scan record by ID |

---

## Security & Ethics

This tool is intended for:

- Legitimate forensic or security assessments
- Personal wallet recovery (your own data only)
- Educational use

**Only scan systems and volumes you are authorized to access.** Do not use on systems you do not own or have permission to scan.

---

## Development

### Dependencies

See `requirements.txt`. Main stacks: Flask, psutil, python-magic, pycryptodome, base58, tqdm, jinja2, etc.

### Tests

```bash
docker compose exec python python test_sawdisk.py
./test_dashboard.sh
```

### Stopping

```bash
docker compose down
```

### Logs

```bash
docker compose logs -f python
```

---

## License & Contributing

See repository and local docs for license. Contributions (e.g. new wallet/format detection, performance improvements) are welcome.
