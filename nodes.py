# SPDX-License-Identifier: GPL-3.0-only

import torch

import node_helpers

try:
    from .angle_control import build_full_prompt, render_angle_guide
except ImportError:
    from angle_control import build_full_prompt, render_angle_guide


def pil_to_image_tensor(image):
    pixels = torch.ByteTensor(torch.ByteStorage.from_buffer(image.tobytes()))
    return pixels.reshape((image.height, image.width, 3)).float() / 255.0


class Anima360AngleControl:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP",),
                "base_prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": False,
                        "default": (
                            "masterpiece, best quality, score_8, highres, safe, "
                            "1girl, original character, detailed outfit"
                        ),
                    },
                ),
                "width": ("INT", {"default": 832, "min": 256, "max": 4096, "step": 64}),
                "height": ("INT", {"default": 1216, "min": 256, "max": 4096, "step": 64}),
                "yaw_degrees": (
                    "INT",
                    {
                        "default": 45,
                        "min": 0,
                        "max": 359,
                        "step": 1,
                        "display": "slider",
                    },
                ),
                "pitch_degrees": (
                    "INT",
                    {
                        "default": 0,
                        "min": -75,
                        "max": 75,
                        "step": 1,
                        "display": "slider",
                    },
                ),
                "roll_degrees": (
                    "INT",
                    {
                        "default": 0,
                        "min": -45,
                        "max": 45,
                        "step": 1,
                        "display": "slider",
                    },
                ),
                "zoom": (
                    "FLOAT",
                    {
                        "default": 5.0,
                        "min": 0.0,
                        "max": 10.0,
                        "step": 0.1,
                        "round": 0.01,
                        "display": "slider",
                    },
                ),
                "line_thickness": (
                    "INT",
                    {"default": 6, "min": 1, "max": 24, "step": 1},
                ),
                "add_angle_prompt": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "CONDITIONING", "STRING")
    RETURN_NAMES = ("control_image", "positive", "full_prompt")
    OUTPUT_TOOLTIPS = (
        "Generated OpenPose-style reference image for Qwen Union Control LoRA.",
        "CLIP conditioning for the base prompt plus the selected camera angle.",
        "The exact prompt text encoded into the positive conditioning.",
    )
    FUNCTION = "build"
    CATEGORY = "Anima/360 control"
    DESCRIPTION = (
        "Generates a custom 360-degree OpenPose-style camera guide image and "
        "matching prompt conditioning from yaw, pitch, roll, and zoom controls."
    )

    def build(
        self,
        clip,
        base_prompt,
        width,
        height,
        yaw_degrees,
        pitch_degrees,
        roll_degrees,
        zoom,
        line_thickness,
        add_angle_prompt,
    ):
        image = render_angle_guide(
            width,
            height,
            yaw_degrees,
            pitch_degrees,
            roll_degrees,
            zoom,
            line_thickness=line_thickness,
        )
        prompt = build_full_prompt(
            base_prompt,
            yaw_degrees,
            pitch_degrees,
            zoom,
            add_angle_prompt,
        )
        tokens = clip.tokenize(prompt)
        positive = clip.encode_from_tokens_scheduled(tokens)
        return (pil_to_image_tensor(image)[None,], positive, prompt)


class AnimaApplyReferenceLatent:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "reference_latent": ("LATENT",),
                "apply_to_negative": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING")
    RETURN_NAMES = ("positive", "negative")
    FUNCTION = "apply"
    CATEGORY = "Anima/360 control"
    DESCRIPTION = (
        "Attaches a VAE-encoded control image as reference_latents for Qwen "
        "Image Union DiffSynth LoRA workflows."
    )

    def apply(self, positive, negative, reference_latent, apply_to_negative=True):
        reference_samples = reference_latent.get("samples")
        if reference_samples is None:
            raise ValueError("reference_latent does not contain samples")

        values = {"reference_latents": [reference_samples]}
        positive = node_helpers.conditioning_set_values(positive, values, append=True)
        if apply_to_negative:
            negative = node_helpers.conditioning_set_values(negative, values, append=True)
        return (positive, negative)


NODE_CLASS_MAPPINGS = {
    "Anima360AngleControl": Anima360AngleControl,
    "AnimaApplyReferenceLatent": AnimaApplyReferenceLatent,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Anima360AngleControl": "Anima 360 Angle Control",
    "AnimaApplyReferenceLatent": "Anima Apply Reference Latent",
}
