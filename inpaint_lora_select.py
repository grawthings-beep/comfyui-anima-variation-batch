# SPDX-License-Identifier: GPL-3.0-only

import json
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parent
CHARACTER_LORA_MANIFEST = REPO_ROOT / "config" / "anima-loras.json"
LORA_ROOT = PurePosixPath("models/loras")
DEFAULT_CHARACTER_ID = "rapi"
FALLBACK_CHARACTERS = (
    {
        "id": "rapi",
        "name": "Rapi",
        "path": "models/loras/anima/Rapi - Anima.safetensors",
    },
    {
        "id": "anis",
        "name": "Anis",
        "path": "models/loras/anima/Anis - Anima.safetensors",
    },
)


class AnyType(str):
    def __ne__(self, other):
        return False


ANY = AnyType("*")


def _read_candidates():
    try:
        manifest = json.loads(
            CHARACTER_LORA_MANIFEST.read_text(encoding="utf-8")
        )
        return manifest.get("loras", [])
    except Exception:
        return FALLBACK_CHARACTERS


def _display_name(candidate):
    label = str(candidate.get("name", "")).strip()
    for marker in (" Anima LoRA", " - Anima", " (trigger:"):
        if marker in label:
            label = label.split(marker, 1)[0].strip()
    return label


def character_entries():
    entries = []
    seen_labels = set()
    for candidate in _read_candidates():
        if candidate.get("usage", "character") != "character":
            continue

        label = _display_name(candidate)
        path = PurePosixPath(
            str(candidate.get("path", "")).replace("\\", "/")
        )
        try:
            lora_name = path.relative_to(LORA_ROOT).as_posix()
        except ValueError:
            continue

        if (
            not label
            or label in seen_labels
            or not lora_name.endswith(".safetensors")
        ):
            continue

        seen_labels.add(label)
        entries.append(
            {
                "id": str(candidate.get("id", "")).strip(),
                "label": label,
                "lora_name": lora_name,
            }
        )

    if entries:
        return entries

    return [
        {
            "id": item["id"],
            "label": item["name"],
            "lora_name": PurePosixPath(item["path"])
            .relative_to(LORA_ROOT)
            .as_posix(),
        }
        for item in FALLBACK_CHARACTERS
    ]


def character_options():
    return [entry["label"] for entry in character_entries()]


def default_character_label(character_id=DEFAULT_CHARACTER_ID):
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


class AnimaCharacterLoRASelect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "character": (
                    character_options(),
                    {"default": default_character_label()},
                ),
                "strength": (
                    "FLOAT",
                    {
                        "default": 0.8,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.05,
                    },
                ),
            }
        }

    RETURN_TYPES = (ANY, "FLOAT")
    RETURN_NAMES = ("lora_name", "strength")
    FUNCTION = "select"
    CATEGORY = "Anima/Inpaint"

    def select(self, character, strength):
        entry = resolve_character(character)
        return (entry["lora_name"], float(strength))


NODE_CLASS_MAPPINGS = {
    "AnimaCharacterLoRASelect": AnimaCharacterLoRASelect,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaCharacterLoRASelect": "Anima Character LoRA Select",
}
