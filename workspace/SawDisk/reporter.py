"""
Report generation for SawDisk
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List
from jinja2 import Template

from models import ScanResult
from config import Config


class ReportGenerator:
    """Generates reports from scan results"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def generate_report(self, results: List[ScanResult]) -> str:
        """Generate report based on results and format"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_name = f"sawdisk_report_{timestamp}"
        
        if self.config.report_format == 'html':
            return self._generate_html_report(results, report_name)
        elif self.config.report_format == 'json':
            return self._generate_json_report(results, report_name)
        elif self.config.report_format == 'markdown':
            return self._generate_markdown_report(results, report_name)
        else:
            raise ValueError(f"Unsupported report format: {self.config.report_format}")
    
    def _generate_html_report(self, results: List[ScanResult], report_name: str) -> str:
        """Generate HTML report"""
        
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SawDisk Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #2c3e50; color: white; padding:.20px; border-radius: 5px; }
        .summary { background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .result-item { border: 1px solid #bdc3c7; margin: 10px 0; border-radius: 5px; }
        .result-header { background: #3498db; color: white; padding: 10px; font-weight: bold; }
        .result-body { padding: 15px; }
        .confidence-high { color: #e74c3c; font-weight: bold; }
        .confidence-medium { color: #f39c12; font-weight: bold; }
        .confidence-low { color: #27ae60; font-weight: bold; }
        .details { background: #f8f9fa; padding: 10px; margin-top: 10px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 SawDisk Crypto Scanner Report</h1>
        <p>Generated: {{ timestamp }}</p>
    </div>
    
    <div class="summary">
        <h2>📊 Summary</h2>
        <ul>
            <li><strong>Scan Path:</strong> {{ scan_path }}</li>
            <li><strong>Total Items Found:</strong> {{ total_items }}</li>
            <li><strong>High Confidence:</strong> {{ high_conf_count }}</li>
            <li><strong>Medium Confidence:</strong> {{ medium_conf_count }}</li>
            <li><strong>Low Confidence:</strong> {{ low_conf_count }}</li>
        </ul>
    </div>
    
    <h2>🔍 Findings</h2>
    {% for result in results %}
    <div class="result-item">
        <div class="result-header">
            {{ result.item_type }} ({{ result.confidence * 100 }}% confidence)
        </div>
        <div class="result-body">
            <strong>Path:</strong> {{ result.file_path }}<br>
            <strong>Type:</strong> {{ result.item_type }}<br>
            <strong>Size:</strong> {{ result.file_size | format_size }}<br>
            <strong>Detected:</strong> {{ result.scan_time | datetime }}<br>
            
            {% if result.details %}
            <div class="details">
                <strong>Details:</strong><br>
                {% for key, value in result.details.items() %}
                • {{ key }}: {{ value }}<br>
                {% endfor %}
            </div>
            {% endif %}
        </div>
    </div>
    {% endfor %}
    
    <div class="summary">
        <h2>⚠️ Disclaimer</h2>
        <p>This report is generated for forensic and security purposes only. 
        Handle sensitive information with extreme care and follow applicable laws.</p>
    </div>
</body>
</html>
        """
        
        template = Template(html_template)
        html_content = template.render(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            scan_path=self.config.scan_path,
            total_items=len(results),
            results=results,
            high_conf_count=len([r for r in results if r.confidence >= 0.7]),
            medium_conf_count=len([r for r in results if 0.7 > r.confidence >= 0.5]),
            low_conf_count=len([r for r in results if r.confidence < 0.5]),
            format_size=self._format_size,
            datetime=lambda x: datetime.fromtimestamp(x).strftime("%Y-%m-%d %H:%M:%S")
        )
        
        report_path = Path(self.config.output_dir) / f"{report_name}.html"
        report_path.write_text(html_content)
        
        return str(report_path)
    
    def _generate_json_report(self, results: List[ScanResult], report_name: str) -> str:
        """Generate JSON report"""
        
        report_data = {
            'report_info': {
                'generated_at': datetime.now().isoformat(),
                'scan_path': self.config.scan_path,
                'total_items': len(results)
            },
            'results': [
                {
                    'file_path': result.file_path,
                    'item_type': result.item_type,
                    'confidence': result.confidence,
                    'file_size': result.file_size,
                    'scan_time': result.scan_time,
                    'details': result.details
                }
                for result in results
            ]
        }
        
        report_path = Path(self.config.output_dir) / f"{report_name}.json"
        report_path.write_text(json.dumps(report_data, indent=2))
        
        return str(report_path)
    
    def _generate_markdown_report(self, results: List[ScanResult], report_name: str) -> str:
        """Generate Markdown report"""
        
        md_content = f"""# 🔍 SawDisk Crypto Scanner Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Scan Path:** {self.config.scan_path}

## 📊 Summary

- **Total Items Found:** {len(results)}
- **High Confidence (≥70%):** {len([r for r in results if r.confidence >= 0.7])}
- **Medium Confidence (50-69%):** {len([r for r in results if 0.7 > r.confidence >= 0.5])}
- **Low Confidence (<50%):** {len([r for r in results if r.confidence < 0.5])}

## 🔍 Findings

"""
        
        for i, result in enumerate(results, 1):
            confidence_label = "🔴 High" if result.confidence >= 0.7 else "🟡 Medium" if result.confidence >= 0.5 else "🟢 Low"
            
            md_content += f"""### {i}. {result.item_type} {confidence_label}

**Path:** `{result.file_path}`  
**Confidence:** {result.confidence * 100:.1f}%  
**File Size:** {self._format_size(result.file_size)}  
**Type:** {result.item_type}  

"""
            
            if result.details:
                md_content += "**Details:**\n"
                for key, value in result.details.items():
                    md_content += f"- {key}: {value}\n"
                md_content += "\n"
            
            md_content += "---\n\n"
        
        md_content += """
## ⚠️ Disclaimer

This report is generated for forensic and security purposes only. Handle sensitive information with extreme care and follow applicable laws.
"""
        
        report_path = Path(self.config.output_dir) / f"{report_name}.md"
        report_path.write_text(md_content)
        
        return str(report_path)
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
