"""Upload processing service — parses uploaded files and returns row counts."""

from pathlib import Path

from app.validation.parser import parse_file


async def process_upload(file_path: Path, file_format: str) -> int | None:
    """Parse the uploaded file and return the row count.

    Returns None if the file cannot be parsed for a row count.
    """
    try:
        data = parse_file(file_path, file_format)
        return len(data)
    except Exception:
        return None
