"""Upload validation: allowed extension, real file type (magic bytes, not the browser's claim), size limit and
empty/corrupt checks. The upload streams to a temp file while hashing, so a large file never sits in memory."""
import hashlib
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from ..config import get_settings
from ..errors import AppError, bad_request

TYPES = {
    "pdf": ("application/pdf", "source"),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "source"),
    "pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "source"),
    "txt": ("text/plain", "source"),
    "md": ("text/markdown", "source"),
    "png": ("image/png", "image"),
    "jpg": ("image/jpeg", "image"),
    "jpeg": ("image/jpeg", "image"),
    "webp": ("image/webp", "image"),
}
IMAGE_EXTS = {e for e, (_, k) in TYPES.items() if k == "image"}


@dataclass
class CheckedFile:
    path: Path
    ext: str
    mime: str
    size: int
    sha256: str
    filename: str


def _sniff(path: Path, ext: str) -> bool:
    with open(path, "rb") as f:
        head = f.read(16)
    if ext == "pdf":
        return head.startswith(b"%PDF-")
    if ext == "png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in ("jpg", "jpeg"):
        return head.startswith(b"\xff\xd8\xff")
    if ext == "webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    if ext in ("docx", "pptx"):
        if not head.startswith(b"PK\x03\x04"):
            return False
        try:
            with zipfile.ZipFile(path) as z:
                names = set(z.namelist())
        except zipfile.BadZipFile:
            return False
        return ("word/document.xml" if ext == "docx" else "ppt/presentation.xml") in names
    if ext in ("txt", "md"):
        with open(path, "rb") as f:
            chunk = f.read(65536)
        if b"\x00" in chunk:
            return False
        try:
            chunk.decode("utf-8")
        except UnicodeDecodeError as e:
            return e.start > len(chunk) - 4  # a multi-byte character cut off at the chunk edge is fine
        return True
    return False


async def receive(upload: UploadFile, only_images: bool = False) -> CheckedFile:
    name = (upload.filename or "").strip().replace("\\", "/").split("/")[-1][:255]
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    allowed = IMAGE_EXTS if only_images else set(TYPES)
    if ext not in allowed:
        raise bad_request("FILE_TYPE_NOT_ALLOWED", "That kind of file isn't supported yet.",
                          {"allowed": sorted(allowed)})
    limit = get_settings().max_upload_mb * 1024 * 1024
    digest, size = hashlib.sha256(), 0
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
    try:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                raise AppError(413, "FILE_TOO_LARGE", f"Files can be up to {get_settings().max_upload_mb} MB.")
            digest.update(chunk)
            tmp.write(chunk)
        tmp.close()
        if size == 0:
            raise bad_request("FILE_EMPTY", "That file is empty.")
        if not _sniff(Path(tmp.name), ext):
            raise bad_request("FILE_CONTENT_MISMATCH", f"This file doesn't look like a real .{ext} file. It may be damaged.")
    except Exception:
        tmp.close()
        Path(tmp.name).unlink(missing_ok=True)
        raise
    return CheckedFile(Path(tmp.name), ext, TYPES[ext][0], size, digest.hexdigest(), name)
