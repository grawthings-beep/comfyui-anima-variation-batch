# SPDX-License-Identifier: GPL-3.0-only
"""ZIP output node for Prompt Queue images."""

from __future__ import annotations

import io
import json
import pathlib
import re

try:
    from .batch_archive import write_archive
except ImportError:  # Supports standalone unit tests outside ComfyUI's loader.
    from batch_archive import write_archive


def first(value, default=None):
    if isinstance(value, list):
        return value[0] if value else default
    return value if value is not None else default


def safe_stem(value, index: int) -> str:
    raw = pathlib.PurePosixPath(str(value).replace("\\", "/")).name
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._")
    return stem or f"scene_{index:03d}"


def iter_images(image_batches):
    for batch in image_batches:
        for image in batch:
            yield image


class AnimaSaveQueueZip:
    """Save every mapped Prompt Queue image into one downloadable ZIP."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "file_stems": ("STRING", {"forceInput": True}),
                "archive_name": (
                    "STRING",
                    {"default": "anima_batches/Anima_latent_queue"},
                ),
                "auto_download": ("BOOLEAN", {"default": True}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_zip"
    OUTPUT_NODE = True
    INPUT_IS_LIST = True
    CATEGORY = "Anima/Batch"
    DESCRIPTION = (
        "Stores all final Prompt Queue images in one ZIP and triggers one "
        "browser download when the archive is complete."
    )

    def save_zip(
        self,
        images,
        file_stems,
        archive_name,
        auto_download=True,
        prompt=None,
        extra_pnginfo=None,
    ):
        # Lazy imports keep node discovery and repository tests independent of
        # the heavy libraries already supplied by ComfyUI.
        import folder_paths
        import numpy as np
        from comfy.cli_args import args
        from PIL import Image
        from PIL.PngImagePlugin import PngInfo

        flattened = list(iter_images(images))
        if not flattened:
            raise ValueError("images must contain at least one final image")

        archive_prefix = str(first(archive_name, "Anima_latent_queue"))
        (
            full_output_folder,
            filename,
            counter,
            subfolder,
            _filename_prefix,
        ) = folder_paths.get_save_image_path(
            archive_prefix,
            folder_paths.get_output_directory(),
            flattened[0].shape[1],
            flattened[0].shape[0],
        )
        zip_filename = f"{filename}_{counter:05d}.zip"
        archive_path = pathlib.Path(full_output_folder) / zip_filename

        prompt_data = first(prompt)
        extra_data = first(extra_pnginfo)
        stems = [safe_stem(value, index) for index, value in enumerate(file_stems, 1)]
        used_names: set[str] = set()
        manifest_lines = []

        def png_entries():
            for index, image in enumerate(flattened, 1):
                stem = stems[index - 1] if index <= len(stems) else f"scene_{index:03d}"
                name = f"{stem}.png"
                if name in used_names:
                    name = f"{stem}_{index:03d}.png"
                used_names.add(name)

                pixels = 255.0 * image.cpu().numpy()
                output_image = Image.fromarray(
                    np.clip(pixels, 0, 255).astype(np.uint8)
                )
                metadata = None
                if not args.disable_metadata:
                    metadata = PngInfo()
                    if prompt_data is not None:
                        metadata.add_text("prompt", json.dumps(prompt_data))
                    if isinstance(extra_data, dict):
                        for key, value in extra_data.items():
                            metadata.add_text(str(key), json.dumps(value))
                    metadata.add_text("anima_scene", stem)

                buffer = io.BytesIO()
                output_image.save(
                    buffer,
                    format="PNG",
                    pnginfo=metadata,
                    compress_level=4,
                )
                manifest_lines.append(f"{index:03d}\t{name}")
                yield name, buffer.getvalue()

        write_archive(
            archive_path,
            png_entries(),
            manifest=lambda: "\n".join(manifest_lines),
        )

        return {
            "ui": {
                "zip": [
                    {
                        "filename": zip_filename,
                        "subfolder": subfolder.replace("\\", "/"),
                        "type": "output",
                        "count": len(flattened),
                        "auto_download": bool(first(auto_download, True)),
                    }
                ]
            }
        }


NODE_CLASS_MAPPINGS = {
    "AnimaSaveQueueZip": AnimaSaveQueueZip,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaSaveQueueZip": "Anima Save Queue ZIP + Auto Download",
}
