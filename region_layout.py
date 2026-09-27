# SPDX-License-Identifier: GPL-3.0-only
import json
import math


OWNERS = ("A", "B", "C", "D")
DEFAULT_LAYOUT = json.dumps({
    "version": 1, "overlap": 0.04, "feather": 0.04,
    "regions": [
        {"id": "r1", "owner": "A", "x": 0, "y": 0, "w": 0.5, "h": 1, "enabled": True},
        {"id": "r2", "owner": "B", "x": 0.5, "y": 0, "w": 0.5, "h": 1, "enabled": True},
    ],
})


def _number(value, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError("Region coordinates must be finite numbers")
    return max(minimum, min(maximum, float(value)))


def normalize_layout(value):
    try:
        data = json.loads(value) if isinstance(value, str) else value
    except (ValueError, TypeError) as error:
        raise ValueError("Invalid region layout JSON") from error
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Region layout version must be 1")
    regions = data.get("regions")
    if not isinstance(regions, list) or len(regions) > 8:
        raise ValueError("Region layout supports zero to eight rectangles")
    result = {"version": 1, "overlap": _number(data.get("overlap", 0.04), 0, 0.2),
              "feather": _number(data.get("feather", 0.04), 0, 0.2), "regions": []}
    seen = set()
    for i, region in enumerate(regions):
        if not isinstance(region, dict) or region.get("owner") not in OWNERS:
            raise ValueError("Each region must belong to A, B, C, or D")
        identifier = str(region.get("id", f"r{i + 1}"))
        if identifier in seen:
            raise ValueError("Region IDs must be unique")
        seen.add(identifier)
        x = _number(region.get("x"), 0, 0.98)
        y = _number(region.get("y"), 0, 0.98)
        enabled = region.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError("Region enabled must be a boolean")
        result["regions"].append({
            "id": identifier, "owner": region["owner"], "x": x, "y": y,
            "w": _number(region.get("w"), 0.02, 1 - x),
            "h": _number(region.get("h"), 0.02, 1 - y), "enabled": enabled,
        })
    return result


def rasterize_layout(layout, width, height):
    import numpy as np

    if any(isinstance(n, bool) or not isinstance(n, int) or not 64 <= n <= 4096 or n % 8
           for n in (width, height)):
        raise ValueError("Width and height must be multiples of 8 between 64 and 4096")
    data = normalize_layout(layout)
    masks = np.zeros((4, height, width), dtype=np.float32)
    short = min(width, height)
    margin = data["overlap"] * short / 2
    feather = data["feather"] * short
    xs = np.arange(width, dtype=np.float32) + 0.5
    ys = np.arange(height, dtype=np.float32) + 0.5
    for region in data["regions"]:
        if not region["enabled"]:
            continue
        left = max(0, region["x"] * width - margin)
        right = min(width, (region["x"] + region["w"]) * width + margin)
        top = max(0, region["y"] * height - margin)
        bottom = min(height, (region["y"] + region["h"]) * height + margin)
        fx = ((xs >= left) & (xs < right)).astype(np.float32)
        fy = ((ys >= top) & (ys < bottom)).astype(np.float32)
        if feather > 0:
            # Do not fade the outer canvas edge; only soften interior boundaries.
            if left > 0:
                fx *= np.clip((xs - left) / feather, 0, 1)
            if right < width:
                fx *= np.clip((right - xs) / feather, 0, 1)
            if top > 0:
                fy *= np.clip((ys - top) / feather, 0, 1)
            if bottom < height:
                fy *= np.clip((bottom - ys) / feather, 0, 1)
        owner = OWNERS.index(region["owner"])
        np.maximum(masks[owner], fy[:, None] * fx[None, :], out=masks[owner])
    return masks


class AnimaRegionLayout:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "width": ("INT", {"default": 1152, "min": 64, "max": 4096, "step": 8}),
            "height": ("INT", {"default": 1536, "min": 64, "max": 4096, "step": 8}),
            "layout": ("STRING", {"default": DEFAULT_LAYOUT}),
        }}

    RETURN_TYPES = ("MASK", "MASK", "MASK", "MASK", "INT", "INT")
    RETURN_NAMES = ("mask_A", "mask_B", "mask_C", "mask_D", "width", "height")
    FUNCTION = "create"
    CATEGORY = "Anima/Regions"

    def create(self, width, height, layout):
        import torch

        masks = rasterize_layout(layout, width, height)
        return (*[torch.from_numpy(mask[None, :, :]) for mask in masks], width, height)


class AnimaRegionalCharacter:
    def __init__(self):
        self._hook_loader = None

    @classmethod
    def INPUT_TYPES(cls):
        import folder_paths

        return {"required": {
            "clip": ("CLIP",), "mask": ("MASK",),
            "shared_positive": ("STRING", {"forceInput": True}),
            "shared_negative": ("STRING", {"forceInput": True}),
            "lora_name": (["(none)"] + folder_paths.get_filename_list("loras"),),
            "strength": ("FLOAT", {"default": 0.8, "min": 0, "max": 2, "step": 0.05}),
            "positive": ("STRING", {"default": "", "multiline": True}),
            "negative": ("STRING", {"default": "", "multiline": True}),
        }}

    @classmethod
    def VALIDATE_INPUTS(cls, lora_name):
        # Inactive slots may retain an unavailable selection. Validate active slots at execution.
        return True

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING")
    RETURN_NAMES = ("positive", "negative")
    FUNCTION = "condition"
    CATEGORY = "Anima/Regions"

    def condition(self, clip, mask, shared_positive, shared_negative, lora_name,
                  strength, positive, negative):
        if not bool(mask.any()):
            self._hook_loader = None
            return ([], [])

        from nodes import CLIPTextEncode
        from comfy_extras.nodes_hooks import CreateHookLora, PairConditioningSetProperties

        hooks = None
        if lora_name != "(none)" and strength != 0:
            import folder_paths

            if not folder_paths.get_full_path("loras", lora_name):
                raise ValueError(f"Active regional LoRA is not installed: {lora_name}")
            if self._hook_loader is None:
                self._hook_loader = CreateHookLora()
            hooks = self._hook_loader.create_hook(lora_name, strength, 0.0)[0]
        else:
            self._hook_loader = None
        encoder = CLIPTextEncode()
        pos = encoder.encode(clip, "\n\n".join(text.strip() for text in (shared_positive, positive) if text.strip()))[0]
        neg = encoder.encode(clip, ", ".join(text.strip() for text in (shared_negative, negative) if text.strip()))[0]
        return PairConditioningSetProperties().set_properties(
            pos, neg, strength=1.0, set_cond_area="default", mask=mask, hooks=hooks,
        )


NODE_CLASS_MAPPINGS = {
    "AnimaRegionLayout": AnimaRegionLayout,
    "AnimaRegionalCharacter": AnimaRegionalCharacter,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaRegionLayout": "Anima Region Layout",
    "AnimaRegionalCharacter": "Anima Regional Character",
}
