import json
import csv
import io
import re
from typing import Dict, Any

def parse_txt_log(content: str) -> Dict[str, Any]:
    lines = content.splitlines()
    total_lines = len(lines)
    error_count = 0
    warning_count = 0
    critical_count = 0
    services = {}
    
    error_patterns = re.compile(r'(error|exception|fail|timeout|crash)', re.IGNORECASE)
    warning_patterns = re.compile(r'(warn|warning)', re.IGNORECASE)
    critical_patterns = re.compile(r'(critical|fatal|oom|panic)', re.IGNORECASE)
    
    # Common microservices matching
    service_pattern = re.compile(r'\[(auth_service|db_service|gateway|payment|checkout|nginx|redis)\]', re.IGNORECASE)
    
    for line in lines:
        if critical_patterns.search(line):
            critical_count += 1
        elif error_patterns.search(line):
            error_count += 1
        elif warning_patterns.search(line):
            warning_count += 1
            
        service_match = service_pattern.search(line)
        if service_match:
            srv = service_match.group(1).lower()
            services[srv] = services.get(srv, 0) + 1
            
    detected_service = max(services, key=services.get) if services else "unknown"
    
    return {
        "format": "txt",
        "total_lines": total_lines,
        "error_count": error_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "detected_service": detected_service,
        "summary": f"TXT log: {total_lines} lines, {error_count} errors, {critical_count} critical failures. Primary service: {detected_service}."
    }

def parse_json_log(content: str) -> Dict[str, Any]:
    error_count = 0
    warning_count = 0
    critical_count = 0
    services = {}
    total_records = 0
    
    # Try reading as JSON list or JSON-lines
    records = []
    try:
        data = json.loads(content)
        if isinstance(data, list):
            records = data
        else:
            records = [data]
    except json.JSONDecodeError:
        # Try line-by-line reading (JSON-Lines format)
        for line in content.splitlines():
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
                    
    total_records = len(records)
    for rec in records:
        level = str(rec.get("level", rec.get("status", rec.get("type", "")))).lower()
        service = str(rec.get("service", rec.get("module", rec.get("logger", "")))).lower()
        
        if service:
            services[service] = services.get(service, 0) + 1
            
        if any(w in level for w in ["crit", "fatal", "emerg", "panic", "oom"]):
            critical_count += 1
        elif any(w in level for w in ["err", "fail", "timeout", "exception"]):
            error_count += 1
        elif "warn" in level:
            warning_count += 1
            
    detected_service = max(services, key=services.get) if services else "unknown"
    
    return {
        "format": "json",
        "total_records": total_records,
        "error_count": error_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "detected_service": detected_service,
        "summary": f"JSON log: {total_records} records, {error_count} errors, {critical_count} critical failures. Primary service: {detected_service}."
    }

def parse_csv_log(content: str) -> Dict[str, Any]:
    error_count = 0
    warning_count = 0
    critical_count = 0
    services = {}
    total_lines = 0
    
    f = io.StringIO(content)
    reader = csv.reader(f)
    
    headers = []
    try:
        headers = [h.lower().strip() for h in next(reader)]
    except StopIteration:
        return {"format": "csv", "total_lines": 0, "error_count": 0, "warning_count": 0, "critical_count": 0, "detected_service": "unknown"}
        
    level_idx = -1
    service_idx = -1
    msg_idx = -1
    
    for idx, h in enumerate(headers):
        if any(w in h for w in ["level", "type", "status", "severity"]):
            level_idx = idx
        elif any(w in h for w in ["service", "logger", "module", "app"]):
            service_idx = idx
        elif any(w in h for w in ["msg", "message", "info", "log"]):
            msg_idx = idx
            
    for row in reader:
        total_lines += 1
        level = row[level_idx].lower() if (level_idx != -1 and level_idx < len(row)) else ""
        service = row[service_idx].lower() if (service_idx != -1 and service_idx < len(row)) else ""
        msg = row[msg_idx].lower() if (msg_idx != -1 and msg_idx < len(row)) else ""
        
        if service:
            services[service] = services.get(service, 0) + 1
            
        combined_text = f"{level} {msg}"
        if any(w in combined_text for w in ["crit", "fatal", "emerg", "panic", "oom"]):
            critical_count += 1
        elif any(w in combined_text for w in ["err", "fail", "timeout", "exception"]):
            error_count += 1
        elif "warn" in combined_text:
            warning_count += 1
            
    detected_service = max(services, key=services.get) if services else "unknown"
    
    return {
        "format": "csv",
        "total_lines": total_lines,
        "error_count": error_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "detected_service": detected_service,
        "summary": f"CSV log: {total_lines} rows, {error_count} errors, {critical_count} critical failures. Primary service: {detected_service}."
    }

def parse_log_content(filename: str, content: str) -> Dict[str, Any]:
    ext = filename.split(".")[-1].lower()
    if ext == "json":
        return parse_json_log(content)
    elif ext == "csv":
        return parse_csv_log(content)
    else:
        return parse_txt_log(content)
