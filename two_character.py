# SPDX-License-Identifier: GPL-3.0-only

import json
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parent
CHARACTER_LORA_MANIFEST = REPO_ROOT / "config" / "anima-loras.json"
LORA_ROOT = PurePosixPath("models/loras")
DEFAULT_CHARACTER_A_ID = "rapi"
DEFAULT_CHARACTER_B_ID = "anis"
FALLBACK_CHARACTERS = (
    {
        "id": "rapi",
        "name": "Rapi Anima LoRA (trigger: r4pi)",
        "trigger": "r4pi",
        "path": "models/loras/anima/Rapi - Anima.safetensors",
    },
    {
        "id": "anis",
        "name": "Anis Anima LoRA (trigger: an1s)",
        "trigger": "an1s",
        "path": "models/loras/anima/Anis - Anima.safetensors",
    },
)


class AnyType(str):
    def __ne__(self, other):
        return False


ANY = AnyType("*")


def character_entries():
    try:
        manifest = json.loads(
            CHARACTER_LORA_MANIFEST.read_text(encoding="utf-8")
        )
        candidates = manifest.get("loras", [])
    except Exception:
        candidates = FALLBACK_CHARACTERS

    entries = []
    seen_labels = set()
    for candidate in candidates:
        if candidate.get("usage", "character") != "character":
            continue
        label = str(candidate.get("name", "")).strip()
        trigger = str(candidate.get("trigger", "")).strip()
        path = PurePosixPath(
            str(candidate.get("path", "")).replace("\\", "/")
        )
        try:
            lora_name = path.relative_to(LORA_ROOT).as_posix()
        except ValueError:
            continue
        if not label or not trigger or not lora_name.endswith(".safetensors"):
            continue
        if label in seen_labels:
            continue
        seen_labels.add(label)
        entries.append(
            {
                "id": str(candidate.get("id", "")).strip(),
                "label": label,
                "trigger": trigger,
                "lora_name": lora_name,
            }
        )

    if not entries:
        return [
            {
                "id": item["id"],
                "label": item["name"],
                "trigger": item["trigger"],
                "lora_name": PurePosixPath(item["path"])
                .relative_to(LORA_ROOT)
                .as_posix(),
            }
            for item in FALLBACK_CHARACTERS
        ]
    return entries


def character_options():
    return [entry["label"] for entry in character_entries()]


def default_character_label(character_id):
    entries = character_entries()
    for entry in entries:
        if entry["id"] == character_id:
            return entry["label"]
    return entries[0]["label"]


def resolve_character(selection):
    entries = character_entries()
    for entry in entries:
        if selection in (
            entry["label"],
            entry["id"],
            entry["lora_name"],
        ):
            return entry
    return entries[0]


def describe_position(center_x_pct, center_y_pct):
    x = float(center_x_pct)
    y = float(center_y_pct)
    horizontal = "left" if x < 45.0 else "right" if x > 55.0 else "center"
    vertical = "upper" if y < 45.0 else "lower" if y > 55.0 else "middle"

    if vertical == "middle":
        return (
            "central region"
            if horizontal == "center"
            else f"{horizontal}-side region"
        )
    if horizontal == "center":
        return f"{vertical}-center region"
    return f"{vertical}-{horizontal} region"


def compose_character_prompt(
    shared_scene,
    position,
    entry,
    details,
    location=None,
):
    scene = str(shared_scene).strip()
    description = str(details).strip().rstrip(".")
    location = str(location or "").strip()
    if not location:
        location = (
            "left-side region"
            if position == "A"
            else "right-side region"
        )
    parts = [
        scene,
        (
            f"Character {position}, located in the {location}: "
            f"{entry['trigger']}."
        ),
    ]
    if description:
        parts.append(f"{description}.")
    other = "B" if position == "A" else "A"
    parts.append(
        f"Keep Character {position}'s face, hair, clothes, and limbs visually "
        f"distinct from Character {other}."
    )
    return "\n".join(part for part in parts if part)


def soft_region_bounds(center_pct, width_pct, feather_pct):
    half_width = max(0.0, float(width_pct)) / 2.0
    feather = max(0.0, float(feather_pct))
    hard_left = float(center_pct) - half_width
    hard_right = float(center_pct) + half_width
    return (
        hard_left - feather,
        hard_left,
        hard_right,
        hard_right + feather,
    )


def soft_box_bounds(
    center_x_pct,
    center_y_pct,
    width_pct,
    height_pct,
    feather_pct,
):
    return {
        "x": soft_region_bounds(center_x_pct, width_pct, feather_pct),
        "y": soft_region_bounds(center_y_pct, height_pct, feather_pct),
    }


def _soft_interval(values, hard_low, hard_high, feather):
    if feather <= 0.0:
        return ((values >= hard_low) & (values <= hard_high)).float()
    enter = ((values - (hard_low - feather)) / feather).clamp(0.0, 1.0)
    leave = (((hard_high + feather) - values) / feather).clamp(
        0.0, 1.0
    )
    enter = enter * enter * (3.0 - 2.0 * enter)
    leave = leave * leave * (3.0 - 2.0 * leave)
    return enter * leave


def build_soft_box_masks(width, height, character_a, character_b, feather_pct):
    import torch

    width = int(width)
    height = int(height)
    x = torch.linspace(0.0, 100.0, width)
    y = torch.linspace(0.0, 100.0, height)
    feather = max(0.0, float(feather_pct))

    def person_mask(box):
        center_x, center_y, box_width, box_height = map(float, box)
        half_width = max(0.0, box_width) / 2.0
        half_height = max(0.0, box_height) / 2.0
        horizontal = _soft_interval(
            x,
            center_x - half_width,
            center_x + half_width,
            feather,
        ).unsqueeze(0)
        vertical = _soft_interval(
            y,
            center_y - half_height,
            center_y + half_height,
            feather,
        ).unsqueeze(1)
        return (vertical * horizontal).clamp(0.0, 1.0)

    mask_a = person_mask(character_a)
    mask_b = person_mask(character_b)

    base = torch.tensor([0.045, 0.055, 0.075]).view(1, 1, 3)
    color_a = torch.tensor([0.72, 0.22, 0.12]).view(1, 1, 3)
    color_b = torch.tensor([0.08, 0.48, 0.72]).view(1, 1, 3)
    preview = (
        base
        + mask_a.unsqueeze(-1) * color_a
        + mask_b.unsqueeze(-1) * color_b
    ).clamp(0.0, 1.0)

    return (
        mask_a.unsqueeze(0),
        mask_b.unsqueeze(0),
        preview.unsqueeze(0),
    )


class AnimaCharacterPairPrompt:
    @classmethod
    def INPUT_TYPES(cls):
        options = character_options()
        return {
            "required": {
                "shared_scene": (
                    "STRING",
                    {
                        "default": (
                            "masterpiece, best quality, score_7, safe, 2girls. "
                            "Two adult women share a natural candid conversation "
                            "in one coherent full-body anime illustration. They "
                            "make eye contact with relaxed body language, while "
                            "their faces, hair, clothes, arms, and legs remain "
                            "clearly separate. Soft sunset light falls across a "
                            "detailed city terrace."
                        ),
                        "multiline": True,
                        "dynamicPrompts": True,
                    },
                ),
                "character_a": (
                    options,
                    {
                        "default": default_character_label(
                            DEFAULT_CHARACTER_A_ID
                        )
                    },
                ),
                "character_a_details": (
                    "STRING",
                    {
                        "default": (
                            "canonical hairstyle, eye color, and signature "
                            "outfit, full face visible, standing naturally and "
                            "turning slightly toward Character B"
                        ),
                        "multiline": True,
                        "dynamicPrompts": True,
                    },
                ),
                "character_a_strength": (
                    "FLOAT",
                    {
                        "default": 0.8,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.05,
                    },
                ),
                "character_b": (
                    options,
                    {
                        "default": default_character_label(
                            DEFAULT_CHARACTER_B_ID
                        )
                    },
                ),
                "character_b_details": (
                    "STRING",
                    {
                        "default": (
                            "canonical hairstyle, eye color, and signature "
                            "outfit, full face visible, standing naturally and "
                            "turning slightly toward Character A"
                        ),
                        "multiline": True,
                        "dynamicPrompts": True,
                    },
                ),
                "character_b_strength": (
                    "FLOAT",
                    {
                        "default": 0.8,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.05,
                    },
                ),
            },
            "optional": {
                "character_a_position": (
                    "STRING",
                    {"forceInput": True},
                ),
                "character_b_position": (
                    "STRING",
                    {"forceInput": True},
                ),
            },
        }

    RETURN_TYPES = (
        "STRING",
        "STRING",
        ANY,
        "FLOAT",
        ANY,
        "FLOAT",
        "STRING",
    )
    RETURN_NAMES = (
        "character_a_prompt",
        "character_b_prompt",
        "character_a_lora",
        "character_a_strength",
        "character_b_lora",
        "character_b_strength",
        "shared_prompt",
    )
    FUNCTION = "build"
    CATEGORY = "Anima/Regional"

    def build(
        self,
        shared_scene,
        character_a,
        character_a_details,
        character_a_strength,
        character_b,
        character_b_details,
        character_b_strength,
        character_a_position=None,
        character_b_position=None,
    ):
        entry_a = resolve_character(character_a)
        entry_b = resolve_character(character_b)
        global_prompt = str(shared_scene).strip()
        return (
            compose_character_prompt(
                global_prompt,
                "A",
                entry_a,
                character_a_details,
                character_a_position,
            ),
            compose_character_prompt(
                global_prompt,
                "B",
                entry_b,
                character_b_details,
                character_b_position,
            ),
            entry_a["lora_name"],
            float(character_a_strength),
            entry_b["lora_name"],
            float(character_b_strength),
            global_prompt,
        )


class AnimaTwoCharacterMasks:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": (
                    "INT",
                    {
                        "default": 832,
                        "min": 256,
                        "max": 4096,
                        "step": 8,
                    },
                ),
                "height": (
                    "INT",
                    {
                        "default": 1216,
                        "min": 256,
                        "max": 4096,
                        "step": 8,
                    },
                ),
                "left_center_pct": (
                    "FLOAT",
                    {
                        "default": 26.0,
                        "min": 0.0,
                        "max": 100.0,
                        "step": 1.0,
                    },
                ),
                "right_center_pct": (
                    "FLOAT",
                    {
                        "default": 74.0,
                        "min": 0.0,
                        "max": 100.0,
                        "step": 1.0,
                    },
                ),
                "region_width_pct": (
                    "FLOAT",
                    {
                        "default": 48.0,
                        "min": 10.0,
                        "max": 90.0,
                        "step": 1.0,
                    },
                ),
                "top_pct": (
                    "FLOAT",
                    {
                        "default": 2.0,
                        "min": 0.0,
                        "max": 95.0,
                        "step": 1.0,
                    },
                ),
                "bottom_pct": (
                    "FLOAT",
                    {
                        "default": 98.0,
                        "min": 5.0,
                        "max": 100.0,
                        "step": 1.0,
                    },
                ),
                "feather_pct": (
                    "FLOAT",
                    {
                        "default": 6.0,
                        "min": 0.0,
                        "max": 25.0,
                        "step": 0.5,
                    },
                ),
            }
        }

    RETURN_TYPES = ("MASK", "MASK", "IMAGE")
    RETURN_NAMES = ("character_a_mask", "character_b_mask", "layout_preview")
    FUNCTION = "build"
    CATEGORY = "Anima/Regional"

    def build(
        self,
        width,
        height,
        left_center_pct,
        right_center_pct,
        region_width_pct,
        top_pct,
        bottom_pct,
        feather_pct,
    ):
        top, bottom = sorted((float(top_pct), float(bottom_pct)))
        center_y = (top + bottom) / 2.0
        region_height = bottom - top
        return build_soft_box_masks(
            width,
            height,
            (
                left_center_pct,
                center_y,
                region_width_pct,
                region_height,
            ),
            (
                right_center_pct,
                center_y,
                region_width_pct,
                region_height,
            ),
            feather_pct,
        )


class AnimaTwoCharacterFreeMasks:
    @classmethod
    def INPUT_TYPES(cls):
        position = {
            "default": 50.0,
            "min": 0.0,
            "max": 100.0,
            "step": 1.0,
        }
        region_size = {
            "default": 48.0,
            "min": 10.0,
            "max": 100.0,
            "step": 1.0,
        }
        return {
            "required": {
                "width": (
                    "INT",
                    {
                        "default": 832,
                        "min": 256,
                        "max": 4096,
                        "step": 8,
                    },
                ),
                "height": (
                    "INT",
                    {
                        "default": 1216,
                        "min": 256,
                        "max": 4096,
                        "step": 8,
                    },
                ),
                "character_a_x_pct": (
                    "FLOAT",
                    {**position, "default": 26.0},
                ),
                "character_a_y_pct": ("FLOAT", {**position}),
                "character_a_width_pct": ("FLOAT", {**region_size}),
                "character_a_height_pct": (
                    "FLOAT",
                    {**region_size, "default": 96.0},
                ),
                "character_b_x_pct": (
                    "FLOAT",
                    {**position, "default": 74.0},
                ),
                "character_b_y_pct": ("FLOAT", {**position}),
                "character_b_width_pct": ("FLOAT", {**region_size}),
                "character_b_height_pct": (
                    "FLOAT",
                    {**region_size, "default": 96.0},
                ),
                "feather_pct": (
                    "FLOAT",
                    {
                        "default": 6.0,
                        "min": 0.0,
                        "max": 25.0,
                        "step": 0.5,
                    },
                ),
            }
        }

    RETURN_TYPES = ("MASK", "MASK", "IMAGE", "STRING", "STRING")
    RETURN_NAMES = (
        "character_a_mask",
        "character_b_mask",
        "layout_preview",
        "character_a_position",
        "character_b_position",
    )
    FUNCTION = "build"
    CATEGORY = "Anima/Regional"

    def build(
        self,
        width,
        height,
        character_a_x_pct,
        character_a_y_pct,
        character_a_width_pct,
        character_a_height_pct,
        character_b_x_pct,
        character_b_y_pct,
        character_b_width_pct,
        character_b_height_pct,
        feather_pct,
    ):
        masks = build_soft_box_masks(
            width,
            height,
            (
                character_a_x_pct,
                character_a_y_pct,
                character_a_width_pct,
                character_a_height_pct,
            ),
            (
                character_b_x_pct,
                character_b_y_pct,
                character_b_width_pct,
                character_b_height_pct,
            ),
            feather_pct,
        )
        return (
            *masks,
            describe_position(character_a_x_pct, character_a_y_pct),
            describe_position(character_b_x_pct, character_b_y_pct),
        )


NODE_CLASS_MAPPINGS = {
    "AnimaCharacterPairPrompt": AnimaCharacterPairPrompt,
    "AnimaTwoCharacterMasks": AnimaTwoCharacterMasks,
    "AnimaTwoCharacterFreeMasks": AnimaTwoCharacterFreeMasks,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaCharacterPairPrompt": "Anima Two-Character Prompt + LoRAs",
    "AnimaTwoCharacterMasks": "Anima Two-Character Regional Masks (Legacy)",
    "AnimaTwoCharacterFreeMasks": "Anima Two-Character Free Regional Masks",
}
