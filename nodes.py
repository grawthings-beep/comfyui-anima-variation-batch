# SPDX-License-Identifier: GPL-3.0-only
"""Small dependency-free nodes used by the bundled Anima workflows."""

from __future__ import annotations

import re


MAX_SEED = 0xFFFFFFFFFFFFFFFF


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
                "start_scene": (
                    "INT",
                    {"default": 1, "min": 1, "max": 10000},
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

    RETURN_TYPES = ("STRING", "INT", "INT", "STRING")
    RETURN_NAMES = (
        "positive_prompt",
        "first_pass_seed",
        "second_pass_seed",
        "filename_prefix",
    )
    OUTPUT_IS_LIST = (True, True, True, True)
    FUNCTION = "expand"
    CATEGORY = "Anima/Batch"

    def expand(
        self,
        scene_prompts: str,
        start_scene: int,
        scene_limit: int,
        base_seed: int,
        filename_prefix: str,
    ):
        scenes = split_scenes(scene_prompts)
        if not scenes:
            raise ValueError(
                "Scene prompts are empty. Separate scenes with a blank line."
            )

        start_index = start_scene - 1
        if start_index >= len(scenes):
            raise ValueError(
                f"start_scene is {start_scene}, but only {len(scenes)} scenes exist"
            )

        selected = scenes[start_index : start_index + scene_limit]
        scene_indexes = range(start_index, start_index + len(selected))
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
            for scene_index in range(start_index, start_index + len(selected))
        ]

        return selected, first_pass_seeds, second_pass_seeds, prefixes


NODE_CLASS_MAPPINGS = {
    "AnimaPromptQueue": AnimaPromptQueue,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaPromptQueue": "Anima Prompt Queue (blank-line scenes)",
}
