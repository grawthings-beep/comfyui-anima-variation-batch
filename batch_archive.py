# SPDX-License-Identifier: GPL-3.0-only
"""Atomic ZIP writing helpers with no ComfyUI runtime dependencies."""

from __future__ import annotations

import os
import pathlib
import zipfile


def write_archive(
    archive_path,
    entries,
    *,
    manifest: str = "",
):
    """Write named byte entries to a ZIP and atomically publish it."""
    archive_path = pathlib.Path(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = archive_path.with_suffix(archive_path.suffix + ".tmp")

    try:
        with zipfile.ZipFile(
            temporary_path,
            mode="w",
            compression=zipfile.ZIP_STORED,
            allowZip64=True,
        ) as archive:
            for name, payload in entries:
                archive.writestr(name, payload)
            manifest_text = manifest() if callable(manifest) else manifest
            if manifest_text.strip():
                archive.writestr("manifest.txt", manifest_text.strip() + "\n")
        os.replace(temporary_path, archive_path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise

    return archive_path
