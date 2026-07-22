# SPDX-License-Identifier: GPL-3.0-only
"""Dependency-free Prompt Queue node used by the bundled Anima workflow."""

from __future__ import annotations

import re


MAX_SEED = 0xFFFFFFFFFFFFFFFF
BATCH_RANGES = (
    "1-50",
    "51-100",
    "101-150",
    "151-200",
    "201-250",
    "251-300",
)


def split_scenes(text: str) -> list[str]:
    """Split scene prompts on one or more whitespace-only blank lines."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    return [
        scene.strip()
        for scene in re.split(r"\n[\t ]*\n+", normalized)
        if scene.strip()
    ]


class AnimaPromptQueue:
    """Expand blank-line-separated scenes into aligned ComfyUI lists."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "scene_prompts": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": False,
                        "default": (
                            "masterpiece, best quality, scene one\n\n"
                            "masterpiece, best quality, scene two"
                        ),
                    },
                ),
                "batch_range": (list(BATCH_RANGES),),
                "start_in_range": (
                    "INT",
                    {"default": 1, "min": 1, "max": 50},
                ),
                "scene_limit": ("INT", {"default": 50, "min": 1, "max": 50}),
                "base_seed": (
                    "INT",
                    {"default": 566871253377100, "min": 0, "max": MAX_SEED},
                ),
                "filename_prefix": (
                    "STRING",
                    {"default": "Anima_latent_queue"},
                ),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "INT", "STRING", "STRING")
    RETURN_NAMES = (
        "positive_prompt",
        "first_pass_seed",
        "second_pass_seed",
        "filename_prefix",
        "archive_name",
    )
    OUTPUT_IS_LIST = (True, True, True, True, True)
    FUNCTION = "expand"
    CATEGORY = "Anima/Batch"

    def expand(
        self,
        scene_prompts: str,
        batch_range: str,
        start_in_range: int,
        scene_limit: int,
        base_seed: int,
        filename_prefix: str,
    ):
        scenes = split_scenes(scene_prompts)
        if not scenes:
            raise ValueError(
                "Scene prompts are empty. Separate scenes with a blank line."
            )

        if batch_range not in BATCH_RANGES:
            raise ValueError(f"unknown batch_range: {batch_range}")
        range_start, range_end = (int(value) for value in batch_range.split("-"))

        local_start_index = start_in_range - 1
        if local_start_index >= len(scenes):
            raise ValueError(
                f"start_in_range is {start_in_range}, but only "
                f"{len(scenes)} scenes are pasted"
            )

        range_capacity = range_end - range_start + 1
        remaining_capacity = range_capacity - local_start_index
        selected = scenes[
            local_start_index : local_start_index + min(scene_limit, remaining_capacity)
        ]
        absolute_start_index = range_start - 1 + local_start_index
        scene_indexes = range(
            absolute_start_index,
            absolute_start_index + len(selected),
        )
        first_pass_seeds = [
            (base_seed + scene_index * 2) % (MAX_SEED + 1)
            for scene_index in scene_indexes
        ]
        second_pass_seeds = [
            (seed + 1) % (MAX_SEED + 1) for seed in first_pass_seeds
        ]

        clean_prefix = filename_prefix.strip().replace("\\", "/").strip("/")
        if not clean_prefix:
            clean_prefix = "Anima_latent_queue"
        prefixes = [
            f"{clean_prefix}/scene_{scene_index + 1:03d}"
            for scene_index in range(
                absolute_start_index,
                absolute_start_index + len(selected),
            )
        ]
        archive_base = clean_prefix.rsplit("/", 1)[-1]
        range_tag = f"{range_start:03d}-{range_end:03d}"
        archive_names = [
            f"anima_batches/{archive_base}_{range_tag}"
        ] * len(selected)

        return (
            selected,
            first_pass_seeds,
            second_pass_seeds,
            prefixes,
            archive_names,
        )


NODE_CLASS_MAPPINGS = {
    "AnimaPromptQueue": AnimaPromptQueue,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaPromptQueue": "Anima Prompt Queue (blank-line scenes)",
}
