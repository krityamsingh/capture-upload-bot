# utils.py
import re
import json
from typing import Optional

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove multiple spaces
    filename = re.sub(r'\s+', ' ', filename)
    # Trim
    filename = filename.strip()
    return filename[:255]  # Limit length

def parse_cookie_file(cookie_path: str) -> dict:
    """Parse Netscape cookie file"""
    cookies = {}
    try:
        with open(cookie_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        name, value = parts[5], parts[6]
                        cookies[name] = value
        return cookies
    except Exception as e:
        print(f"Error parsing cookie file: {e}")
        return {}
