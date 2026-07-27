# SPDX-License-Identifier: GPL-3.0-only

import json
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parent
POSE_LORA_MANIFEST = REPO_ROOT / "config" / "anima-pose-loras.json"
FALLBACK_POSE_LORAS = ("anima_pose/01 BallsDeep - Anima v1.safetensors",)


class AnyType(str):
    def __ne__(self, other):
        return False


ANY = AnyType("*")


def pose_lora_names():
    try:
        manifest = json.loads(POSE_LORA_MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        return list(FALLBACK_POSE_LORAS)

    names = []
    prefix = PurePosixPath("models/loras")
    for entry in manifest.get("loras", []):
        path = PurePosixPath(str(entry.get("path", "")).replace("\\", "/"))
        try:
            names.append(path.relative_to(prefix).as_posix())
        except ValueError:
            continue

    return names or list(FALLBACK_POSE_LORAS)


class AnimaPoseLoRASelect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pose_lora": (pose_lora_names(),),
                "first_pass_strength": (
                    "FLOAT",
                    {
                        "default": 0.8,
                        "min": -20.0,
                        "max": 20.0,
                        "step": 0.05,
                    },
                ),
                "second_pass_strength": (
                    "FLOAT",
                    {
                        "default": 0.8,
                        "min": -20.0,
                        "max": 20.0,
                        "step": 0.05,
                    },
                ),
            }
        }

    RETURN_TYPES = (ANY, "FLOAT", "FLOAT")
    RETURN_NAMES = ("lora_name", "first_pass_strength", "second_pass_strength")
    FUNCTION = "select"
    CATEGORY = "Anima/LoRA"

    def select(self, pose_lora, first_pass_strength, second_pass_strength):
        return (pose_lora, first_pass_strength, second_pass_strength)


NODE_CLASS_MAPPINGS = {
    "AnimaPoseLoRASelect": AnimaPoseLoRASelect,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaPoseLoRASelect": "Anima Pose LoRA Select",
}
