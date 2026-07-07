# ComfyUI Anima Upscale and 360 Angle Control

[![CI](https://github.com/grawthings-beep/comfyui-anima-variation-batch/actions/workflows/ci.yml/badge.svg)](https://github.com/grawthings-beep/comfyui-anima-variation-batch/actions/workflows/ci.yml)

This repository contains a small Anima-focused ComfyUI helper set:

- two 2-pass Hires-fix upscale example workflows;
- one custom 360-degree angle-control workflow that generates its own
  OpenPose-style structural guide image and feeds it to Qwen Image Union
  Control LoRA.

Old variation-batch, preset multi-angle, re-pose, diff-maker, ZIP saver, and
LoRA manifest helper workflows have been removed.

## Install

From the ComfyUI custom node directory:

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/grawthings-beep/comfyui-anima-variation-batch.git \
  ComfyUI-AnimaAngleControl
```

Restart ComfyUI, then load one of:

```text
example_workflows/anima_hiresfix_esrgan_2pass.json
example_workflows/anima_hiresfix_latent_2pass.json
example_workflows/ANIMA_360_Angle_Control.json
```

For common RunPod images, the ComfyUI root is often one of:

```text
/opt/ComfyUI
/workspace/ComfyUI
/workspace/comfyui
```

## Hires-fix upscale workflows

Two 2-pass Hires-fix upscale examples are included:

```text
example_workflows/anima_hiresfix_esrgan_2pass.json
example_workflows/anima_hiresfix_latent_2pass.json
```

Both workflows expect the Anima base stack:

```text
models/diffusion_models/anima-base-v1.0.safetensors
models/text_encoders/qwen_3_06b_base.safetensors
models/vae/qwen_image_vae.safetensors
```

`anima_hiresfix_esrgan_2pass.json` starts at 832x1216, upscales the first
pass with a 4x ESRGAN model, resizes to an effective 1.5x with Lanczos,
VAE-re-encodes, then runs a second pass. It additionally needs an anime ESRGAN
upscaler such as:

```text
models/upscale_models/4x-AnimeSharp.pth
```

The default second-pass denoise is `0.45`. Tune around `0.35` to `0.55`,
lowering it to preserve the first pass or raising it for stronger detail
redraw.

`anima_hiresfix_latent_2pass.json` uses only ComfyUI core nodes: it upscales
the latent by 1.5x with bislerp, then runs a second pass. The default
second-pass denoise is `0.55`. Tune around `0.50` to `0.60` depending on how
much structure you want the second pass to revise.

## 360 angle-control workflow

Load:

```text
example_workflows/ANIMA_360_Angle_Control.json
```

This workflow uses two custom nodes:

```text
Anima 360 Angle Control
Anima Apply Reference Latent
```

`Anima 360 Angle Control` creates a synthetic OpenPose-style control image
from numeric camera controls:

- `yaw_degrees`: `0` front, `90` right profile, `180` back, `270` left profile;
- `pitch_degrees`: low-angle to high-angle camera tilt;
- `roll_degrees`: dutch/canted camera tilt;
- `zoom`: wide shot through close-up framing;
- `left_arm_raise`, `right_arm_raise`: raise or lower each arm;
- `left_elbow_bend`, `right_elbow_bend`: bend or extend each elbow;
- `left_leg_lift`, `right_leg_lift`: lift either leg forward;
- `left_knee_bend`, `right_knee_bend`: bend or straighten each knee;
- `line_thickness`: guide strength before VAE encoding.

The browser extension draws a reserved live OpenPose preview widget inside the
node, so camera and limb-pose changes are visible before queueing generation.

The node also encodes a positive prompt that includes the selected camera
angle and larger limb-pose changes. The workflow VAE-encodes the generated
OpenPose-style guide and `Anima Apply Reference Latent` attaches that latent to
the positive and negative conditioning as `reference_latents`. With
`qwen_image_union_diffsynth_lora.safetensors` loaded, Qwen Image receives both
a structural reference and a matching camera prompt, so the angle is much more
enforceable than prompt-only view tags.

Required models:

```text
models/diffusion_models/anima-base-v1.0.safetensors
models/text_encoders/qwen_3_06b_base.safetensors
models/vae/qwen_image_vae.safetensors
models/loras/qwen_image_union_diffsynth_lora.safetensors
```

Suggested defaults:

```text
steps: 30
cfg: 4
sampler: er_sde
scheduler: simple
denoise: 1.0
Qwen union control LoRA strength: 1.0
```

If the camera angle is too weak, keep the base prompt simple, avoid
contradictory view words, raise `line_thickness`, or raise the Union Control
LoRA strength slightly. If the skeleton shape is too visible in the final
image, lower `line_thickness` or the LoRA strength.

## Model downloads

The Qwen Union Control LoRA is hosted by Comfy-Org:

```bash
COMFY=/workspace/ComfyUI
[ -d "$COMFY" ] || COMFY=/workspace/comfyui
[ -d "$COMFY" ] || COMFY=/opt/ComfyUI

mkdir -p "$COMFY/models/loras"
wget -O "$COMFY/models/loras/qwen_image_union_diffsynth_lora.safetensors" \
  "https://huggingface.co/Comfy-Org/Qwen-Image-DiffSynth-ControlNets/resolve/main/split_files/loras/qwen_image_union_diffsynth_lora.safetensors"
```

For the ESRGAN Hires-fix workflow:

```bash
mkdir -p "$COMFY/models/upscale_models"
wget -O "$COMFY/models/upscale_models/4x-AnimeSharp.pth" \
  "https://objectstorage.us-phoenix-1.oraclecloud.com/n/ax6ygfvpvzka/b/open-modeldb-files/o/4x-FatePlus-lite.pth"
```

## License

GPL-3.0-only. See `LICENSE`.

This repository does not distribute Anima, Qwen, Control LoRA, or upscaler
weights. Check the license of every model used in your workflow. The official
Anima model and derivatives are restricted to non-commercial use unless a
commercial license is obtained.

- [Official Anima model card](https://huggingface.co/circlestone-labs/Anima)
- [ComfyUI](https://github.com/Comfy-Org/ComfyUI)
