# core/format_manager.py
"""
Manages message format settings from the database.
"""
import json
from typing import Dict, List


def get_available_formats() -> List[Dict]:
    """Return all supported output formats with metadata."""
    return [
        {"id": "message", "name": "WhatsApp Message", "icon": "💬",
         "description": "Send marks via WhatsApp with formatted text"},
        {"id": "pdf", "name": "PDF Document", "icon": "📄",
         "description": "Generate a downloadable PDF report"},
        {"id": "image", "name": "Image Report", "icon": "🖼️",
         "description": "Generate a visual image card with marks"},
    ]


def get_format_by_id(format_id: str) -> Dict:
    """Get format details by ID."""
    for fmt in get_available_formats():
        if fmt["id"] == format_id:
            return fmt
    return get_available_formats()[0]


def validate_format_settings(default_format: str, allowed: List[str]) -> bool:
    """Ensure default is in allowed list."""
    valid_ids = [f["id"] for f in get_available_formats()]
    if default_format not in valid_ids:
        return False
    for a in allowed:
        if a not in valid_ids:
            return False
    return default_format in allowed
