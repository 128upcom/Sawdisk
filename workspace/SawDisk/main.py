#!/usr/bin/env python3
"""
SawDisk - Main Entry Point
A harddisk seeker in search of all existing crypto keys and wallets on external volumes.
"""

import click
import os
import sys
from pathlib import Path
from colorama import init, Fore, Style

import sys
sys.path.append('/app/workspace/SawDisk')

from scanner import DiskScanner
from reporter import ReportGenerator
from config import Config

# Initialize colorama for cross-platform colored output
init()

@click.command()
@click.option('--path', '-p', 'scan_path', 
              help='Path to scan (default: /mnt/volumes)',
              default='/mnt/volumes',
              type=str)
@click.option('--output', '-o', 'output_dir',
              help='Output directory for reports',
              default='/app/data/sawdisk_reports',
              type=str)
@click.option('--format', 'report_format',
              type=click.Choice(['html', 'json', 'markdown'], case_sensitive=False),
              default='html',
              help='Report format')
@click.option('--depth', '-d',
              help='Maximum directory depth to scan',
              default=20,
              type=int)
@click.option('--threads', '-t',
              help='Number of scanning threads',
              default=4,
              type=int)
@click.option('--verbose', '-v',
              is_flag=True,
              help='Verbose output')
def main(scan_path, output_dir, report_format, depth, threads, verbose):
    """
    SawDisk - A cryptographic wallet and key scanner.
    
    Scans external volumes for cryptocurrency wallets, private keys, and related files.
    Generates comprehensive reports of found items.
    """
    print(f"{Fore.CYAN}🔍 SawDisk - Crypto Wallet Scanner{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Version: 1.0.0{Style.RESET_ALL}")
    print("-" * 50)
    
    # Validate inputs
    if not os.path.exists(scan_path):
        click.echo(f"{Fore.RED}❌ Error: Path '{scan_path}' does not exist!{Style.RESET_ALL}")
        sys.exit(1)
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Initialize configuration
    config = Config(
        scan_path=scan_path,
        output_dir=output_dir,
        report_format=report_format,
        max_depth=depth,
        num_threads=threads,
        verbose=verbose
    )
    
    try:
        # Initialize scanner
        scanner = DiskScanner(config)
        
        # Start scanning
        click.echo(f"{Fore.GREEN}🚀 Starting scan of: {scan_path}{Style.RESET_ALL}")
        results = scanner.scan()
        
        # Generate report
        if results:
            click.echo(f"{Fore.GREEN}📊 Generating {report_format.upper()} report...{Style.RESET_ALL}")
            reporter = ReportGenerator(config)
            report_path = reporter.generate_report(results)
            
            click.echo(f"{Fore.GREEN}✅ Scan complete! Report saved to: {report_path}{Style.RESET_ALL}")
            click.echo(f"{Fore.CYAN}📈 Total items found: {len(results)}{Style.RESET_ALL}")
        else:
            click.echo(f"{Fore.YELLOW}⚠️  No crypto-related items found.{Style.RESET_ALL}")
            
    except KeyboardInterrupt:
        click.echo(f"\n{Fore.YELLOW}⏹️  Scan interrupted by user.{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}❌ Error during scan: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    main()

