# SPDX-License-Identifier: GPL-3.0-only

import torch

import comfy.samplers
import nodes

from .variation import (
    add_variation_group,
    build_group_variations,
    build_variations,
)


def sample_variations(
    variations,
    model,
    clip,
    vae,
    negative,
    latent_image,
    steps,
    cfg,
    sampler_name,
    scheduler,
    denoise,
):
    latent_samples = latent_image.get("samples")
    if latent_samples is None:
        raise ValueError("latent_image does not contain samples")
    if latent_samples.shape[0] != 1:
        raise ValueError(
            "Anima Variation Batch Sampler requires latent batch_size=1. "
            "Use count to control the number of output images."
        )

    images = []
    report_lines = []
    for variation in variations:
        tokens = clip.tokenize(variation.prompt)
        positive = clip.encode_from_tokens_scheduled(tokens)

        sampled = nodes.common_ksampler(
            model,
            variation.seed,
            steps,
            cfg,
            sampler_name,
            scheduler,
            positive,
            negative,
            latent_image,
            denoise=denoise,
        )[0]
        decoded = vae.decode(sampled["samples"])
        if len(decoded.shape) == 5:
            decoded = decoded.reshape(
                -1,
                decoded.shape[-3],
                decoded.shape[-2],
                decoded.shape[-1],
            )
        images.append(decoded)
        details = getattr(variation, "selection_report", "")
        details = f" | {details}" if details else ""
        report_lines.append(
            f"{variation.index:02d} | seed={variation.seed}{details} | "
            f"{variation.prompt}"
        )

    return (torch.cat(images, dim=0), "\n".join(report_lines))


class AnimaVariationGroup:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "category_name": (
                    "STRING",
                    {
                        "default": "Angle",
                        "dynamicPrompts": False,
                    },
                ),
                "options": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": False,
                        "default": "from above, from side, from below",
                    },
                ),
            },
            "optional": {
                "previous_groups": ("ANIMA_VARIATION_GROUPS",),
            },
        }

    RETURN_TYPES = ("ANIMA_VARIATION_GROUPS",)
    RETURN_NAMES = ("variation_groups",)
    FUNCTION = "build"
    CATEGORY = "Anima/batch"
    DESCRIPTION = (
        "Adds one unlimited variation category. Enter short prompt tags "
        "separated by commas or new lines, then chain more Group nodes."
    )

    def build(self, category_name, options, previous_groups=None):
        return (
            add_variation_group(previous_groups, category_name, options),
        )


class AnimaVariationBatchSampler:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "vae": ("VAE",),
                "negative": ("CONDITIONING",),
                "latent_image": ("LATENT",),
                "base_prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": False,
                        "default": "masterpiece, best quality, 1girl",
                    },
                ),
                "shot_recipes": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": False,
                        "default": (
                            "close-up portrait, eye-level, head tilted\n"
                            "upper body shot, low angle, leaning forward\n"
                            "cowboy shot, three-quarter view, hand on hip\n"
                            "full body shot, high angle, dynamic standing pose"
                        ),
                    },
                ),
                "expressions": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": False,
                        "default": (
                            "gentle smile, closed mouth\n"
                            "laughing, open mouth, closed eyes\n"
                            "surprised expression, wide eyes\n"
                            "embarrassed expression, blush"
                        ),
                    },
                ),
                "count": ("INT", {"default": 4, "min": 1, "max": 32, "step": 1}),
                "master_seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "control_after_generate": True,
                    },
                ),
                "steps": ("INT", {"default": 8, "min": 1, "max": 10000}),
                "cfg": (
                    "FLOAT",
                    {
                        "default": 1.0,
                        "min": 0.0,
                        "max": 100.0,
                        "step": 0.1,
                        "round": 0.01,
                    },
                ),
                "sampler_name": (comfy.samplers.KSampler.SAMPLERS,),
                "scheduler": (comfy.samplers.KSampler.SCHEDULERS,),
                "denoise": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "prompt_report")
    OUTPUT_TOOLTIPS = (
        "A batch containing one independently sampled and decoded image per prompt.",
        "The expanded prompts and seeds used for the batch.",
    )
    FUNCTION = "sample"
    CATEGORY = "Anima/batch"
    DESCRIPTION = (
        "Creates unique shot/expression prompt combinations and samples each one "
        "with an independent seed in a single queued execution."
    )

    def sample(
        self,
        model,
        clip,
        vae,
        negative,
        latent_image,
        base_prompt,
        shot_recipes,
        expressions,
        count,
        master_seed,
        steps,
        cfg,
        sampler_name,
        scheduler,
        denoise,
    ):
        variations = build_variations(
            base_prompt,
            shot_recipes,
            expressions,
            count,
            master_seed,
        )
        return sample_variations(
            variations,
            model,
            clip,
            vae,
            negative,
            latent_image,
            steps,
            cfg,
            sampler_name,
            scheduler,
            denoise,
        )


class AnimaFlexibleVariationBatchSampler:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "vae": ("VAE",),
                "negative": ("CONDITIONING",),
                "latent_image": ("LATENT",),
                "variation_groups": ("ANIMA_VARIATION_GROUPS",),
                "base_prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": False,
                        "default": "masterpiece, best quality, 1girl",
                    },
                ),
                "count": ("INT", {"default": 4, "min": 1, "max": 32, "step": 1}),
                "master_seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "control_after_generate": True,
                    },
                ),
                "steps": ("INT", {"default": 8, "min": 1, "max": 10000}),
                "cfg": (
                    "FLOAT",
                    {
                        "default": 1.0,
                        "min": 0.0,
                        "max": 100.0,
                        "step": 0.1,
                        "round": 0.01,
                    },
                ),
                "sampler_name": (comfy.samplers.KSampler.SAMPLERS,),
                "scheduler": (comfy.samplers.KSampler.SCHEDULERS,),
                "denoise": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "prompt_report")
    OUTPUT_TOOLTIPS = (
        "A batch containing one independently sampled and decoded image per prompt.",
        "The selected category values, expanded prompts, and seeds.",
    )
    FUNCTION = "sample"
    CATEGORY = "Anima/batch"
    DESCRIPTION = (
        "Uses every option in each connected Variation Group once before "
        "reshuffling that category. Chain any number of groups."
    )

    def sample(
        self,
        model,
        clip,
        vae,
        negative,
        latent_image,
        variation_groups,
        base_prompt,
        count,
        master_seed,
        steps,
        cfg,
        sampler_name,
        scheduler,
        denoise,
    ):
        variations = build_group_variations(
            base_prompt,
            variation_groups,
            count,
            master_seed,
        )
        return sample_variations(
            variations,
            model,
            clip,
            vae,
            negative,
            latent_image,
            steps,
            cfg,
            sampler_name,
            scheduler,
            denoise,
        )


NODE_CLASS_MAPPINGS = {
    "AnimaVariationGroup": AnimaVariationGroup,
    "AnimaVariationBatchSampler": AnimaVariationBatchSampler,
    "AnimaFlexibleVariationBatchSampler": AnimaFlexibleVariationBatchSampler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaVariationGroup": "Anima Variation Group",
    "AnimaVariationBatchSampler": "Anima Variation Batch Sampler",
    "AnimaFlexibleVariationBatchSampler": "Anima Flexible Variation Batch Sampler",
}
