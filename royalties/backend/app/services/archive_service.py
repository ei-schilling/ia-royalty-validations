"""Archive extraction service — handles zip, tar, tar.gz, and rar files."""

import tarfile
import uuid
import zipfile
from pathlib import Path

ARCHIVE_EXTENSIONS = {"zip", "tar", "gz", "rar"}
INNER_ALLOWED = {"csv", "xlsx", "json", "pdf"}


def is_archive(ext: str) -> bool:
    """Check if a file extension is a supported archive format."""
    return ext.lower() in ARCHIVE_EXTENSIONS


def _inner_ext(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def _should_skip(name: str) -> bool:
    """Skip hidden files (macOS __MACOSX, .DS_Store, etc.)."""
    parts = Path(name).parts
    return any(p.startswith(".") or p.startswith("__") for p in parts)


def extract_archive(archive_path: Path, ext: str, output_dir: Path) -> list[dict]:
    """Extract an archive and return metadata about each extracted file.

    Returns a list of dicts, each with:
        - ``original_name``: original filename inside the archive
        - ``stored_path``: absolute path on disk where it was extracted
        - ``file_format``: lowercase extension (csv, xlsx, json, pdf)
        - ``file_id``: a UUID assigned to this extracted file

    Files with unsupported extensions are silently skipped.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    if ext == "zip":
        results = _extract_zip(archive_path, output_dir)
    elif ext in ("tar", "gz"):
        results = _extract_tar(archive_path, output_dir)
    elif ext == "rar":
        results = _extract_rar(archive_path, output_dir)

    return results


def _extract_zip(archive_path: Path, output_dir: Path) -> list[dict]:
    results: list[dict] = []
    with zipfile.ZipFile(archive_path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            fname = info.filename
            if _should_skip(fname):
                continue
            inner_ext = _inner_ext(fname)
            if inner_ext not in INNER_ALLOWED:
                continue

            file_id = uuid.uuid4()
            stored_name = f"{file_id}.{inner_ext}"
            stored_path = output_dir / stored_name

            with zf.open(info) as src:
                stored_path.write_bytes(src.read())

            results.append({
                "original_name": Path(fname).name,
                "stored_path": str(stored_path),
                "file_format": inner_ext,
                "file_id": file_id,
            })

    return results


def _extract_tar(archive_path: Path, output_dir: Path) -> list[dict]:
    results: list[dict] = []
    # Detect compression from filename
    mode = "r:gz" if archive_path.name.endswith((".tar.gz", ".tgz", ".gz")) else "r:"
    try:
        with tarfile.open(archive_path, mode) as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                fname = member.name
                if _should_skip(fname):
                    continue
                inner_ext = _inner_ext(fname)
                if inner_ext not in INNER_ALLOWED:
                    continue

                file_id = uuid.uuid4()
                stored_name = f"{file_id}.{inner_ext}"
                stored_path = output_dir / stored_name

                f = tf.extractfile(member)
                if f is None:
                    continue
                stored_path.write_bytes(f.read())

                results.append({
                    "original_name": Path(fname).name,
                    "stored_path": str(stored_path),
                    "file_format": inner_ext,
                    "file_id": file_id,
                })
    except tarfile.TarError:
        pass

    return results


def _extract_rar(archive_path: Path, output_dir: Path) -> list[dict]:
    results: list[dict] = []
    try:
        import rarfile

        with rarfile.RarFile(archive_path, "r") as rf:
            for info in rf.infolist():
                if info.is_dir():
                    continue
                fname = info.filename
                if _should_skip(fname):
                    continue
                inner_ext = _inner_ext(fname)
                if inner_ext not in INNER_ALLOWED:
                    continue

                file_id = uuid.uuid4()
                stored_name = f"{file_id}.{inner_ext}"
                stored_path = output_dir / stored_name

                with rf.open(info) as src:
                    stored_path.write_bytes(src.read())

                results.append({
                    "original_name": Path(fname).name,
                    "stored_path": str(stored_path),
                    "file_format": inner_ext,
                    "file_id": file_id,
                })
    except ImportError:
        # rarfile not installed — skip
        pass

    return results
