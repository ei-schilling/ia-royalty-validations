"""Upload processing service — parses uploaded files and returns row counts."""

from pathlib import Path

from typing import Optional
from app.validation.parser import parse_file


async def process_upload(file_path: Path, file_format: str) -> Optional[int]:
    """Parse the uploaded file and return the row count.

    Returns None if the file cannot be parsed for a row count.
    """
    try:
        data = parse_file(file_path, file_format)
        return len(data)
    except Exception:
        return None
