"""Private object storage. Paths are systematic:

    organizations/<org_id>/documents/<doc_id>/original.<ext>
    organizations/<org_id>/assets/<doc_id>.<ext>
    organizations/<org_id>/generated/...           (later waves)

`LocalStorage` keeps files in a private folder that is never served directly; files are only reachable through
a permission check and a short-lived signed URL. An S3/Supabase backend implements the same four methods."""
import os
import shutil
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Protocol

from ..config import get_settings


class Storage(Protocol):
    def put_file(self, key: str, src: Path) -> None: ...
    def open(self, key: str) -> BinaryIO: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...


def document_key(org_id: str, doc_id: str, ext: str, purpose: str) -> str:
    if purpose == "asset":
        return f"organizations/{org_id}/assets/{doc_id}.{ext}"
    return f"organizations/{org_id}/documents/{doc_id}/original.{ext}"


class LocalStorage:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        rel = PurePosixPath(key)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("bad storage key")
        return self.root.joinpath(*rel.parts)

    def put_file(self, key: str, src: Path) -> None:
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        shutil.copyfile(src, tmp)
        os.replace(tmp, dest)  # atomic: a reader never sees half a file

    def open(self, key: str) -> BinaryIO:
        return open(self._path(key), "rb")

    def path(self, key: str) -> Path:
        return self._path(key)

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()


_storage: LocalStorage | None = None


def get_storage() -> LocalStorage:
    global _storage
    s = get_settings()
    if _storage is None or _storage.root != Path(s.storage_dir / "files").resolve():
        _storage = LocalStorage(s.storage_dir / "files")
    return _storage
