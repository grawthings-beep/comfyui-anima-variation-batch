# ComfyUI Anima Hires-Fix and Control Workflows

[![CI](https://github.com/grawthings-beep/comfyui-anima-variation-batch/actions/workflows/ci.yml/badge.svg)](https://github.com/grawthings-beep/comfyui-anima-variation-batch/actions/workflows/ci.yml)

This repository contains Anima-focused 2-pass Hires-fix workflows plus a
Pose/Depth controlled variant. It does not distribute model weights.

## Workflows

```text
example_workflows/anima_hiresfix_esrgan_2pass.json
example_workflows/anima_hiresfix_esrgan_pose_depth.json
example_workflows/anima_hiresfix_latent_2pass.json
```

`anima_hiresfix_esrgan_pose_depth.json` adds two controls before the existing
ESRGAN Hires-fix pass:

```text
pose reference  -> DWPose             -> Anima Pose LLLite  --+
depth reference -> Depth Anything V2  -> Anima Depth LLLite --+-> first pass
                                                               -> ESRGAN 1.5x
                                                               -> second pass
```

The controls affect the first pass only. The second pass uses the controlled
latent at `denoise 0.45` to redraw detail without applying the control patches
a second time. Pose and Depth control-map previews are included in the graph.

## Base install

From the ComfyUI custom node directory:

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/grawthings-beep/comfyui-anima-variation-batch.git \
  ComfyUI-AnimaHiresFixWorkflows
```

Restart ComfyUI and load either of the two workflows that do not use
Pose/Depth, or continue with the control installer below.

For common RunPod images, the ComfyUI root is often one of:

```text
/opt/ComfyUI
/workspace/ComfyUI
/workspace/comfyui
```

## Install Pose and Depth control

The controlled workflow uses ComfyUI's native `Load Model Patch` and
`Apply Anima LLLite` nodes. They require ComfyUI commit
[`0f42ba5`](https://github.com/Comfy-Org/ComfyUI/commit/0f42ba51463174fb255f2c4605ae0e0b441fe6d7)
or newer. The installer checks this and stops with an actionable error if the
core is too old.

Update ComfyUI first when needed:

```bash
cd /workspace/comfyui  # adjust for your image
git pull --ff-only
```

Then run the all-in-one installer with the same Python environment that runs
ComfyUI:

```bash
cd /workspace/comfyui/custom_nodes/ComfyUI-AnimaHiresFixWorkflows
python scripts/install_anima_controls.py --root /workspace/comfyui
```

The installer:

- keeps an existing `comfyui_controlnet_aux` installation, or installs a
  tested revision when it is absent;
- installs the preprocessor Python requirements;
- downloads the Pose and Depth LLLite patches to `models/model_patches/`;
- preloads DWPose and Depth Anything V2 Base into the ControlNet Aux cache;
- copies the ready-to-load workflow to `user/default/workflows/`.

The downloads total approximately 773 MB: 31 MB of Anima patches and about
742 MB of preprocessors. To leave preprocessor models for first-run lazy
download:

```bash
python scripts/install_anima_controls.py \
  --root /workspace/comfyui \
  --skip-preprocessor-models
```

Use `--dry-run` to inspect every destination and command without changing the
installation. Run `python scripts/install_anima_controls.py --help` for the
remaining options.

After installation, restart ComfyUI and load:

```text
anima_hiresfix_esrgan_pose_depth.json
```

Upload a pose reference and a depth/composition reference. The same source
photo can be uploaded to both nodes.

### Control defaults

The workflow starts with:

```text
Pose:  strength 1.00, start 0.00, end 0.80
Depth: strength 0.65, start 0.00, end 0.70
```

If the result becomes rigid, reduce Depth first. If the pose is too weak,
increase Pose gradually. Avoid increasing both at once because LLLite effects
are additive.

The published Pose and Depth patches are legacy Anima Preview3 sample weights.
Their author states that they run on Anima Base v1.0 with somewhat reduced
quality, and that Pose is a soft prior rather than a strict pose lock. This is
why the workflow exposes both strength and active denoising ranges prominently.

## Hires-fix details

All workflows expect the Anima base stack:

```text
models/diffusion_models/anima-base-v1.0.safetensors
models/text_encoders/qwen_3_06b_base.safetensors
models/vae/qwen_image_vae.safetensors
```

The ESRGAN workflows start at 832x1216, upscale the first pass with a 4x
ESRGAN model, resize to an effective 1.5x with Lanczos, VAE-re-encode, then run
a second pass. They additionally need an anime ESRGAN upscaler such as:

```text
models/upscale_models/4x-AnimeSharp.pth
```

The default second-pass denoise is `0.45`. Tune around `0.35` to `0.55`,
lowering it to preserve the first pass or raising it for stronger detail
redraw.

`anima_hiresfix_latent_2pass.json` uses only ComfyUI core nodes: it upscales
the latent by 1.5x with bislerp, then runs a second pass. Its default
second-pass denoise is `0.55`; tune around `0.50` to `0.60`.

## ESRGAN model download

```bash
COMFY=/workspace/ComfyUI
[ -d "$COMFY" ] || COMFY=/workspace/comfyui
[ -d "$COMFY" ] || COMFY=/opt/ComfyUI

mkdir -p "$COMFY/models/upscale_models"
wget -O "$COMFY/models/upscale_models/4x-AnimeSharp.pth" \
  "https://objectstorage.us-phoenix-1.oraclecloud.com/n/ax6ygfvpvzka/b/open-modeldb-files/o/4x-FatePlus-lite.pth"
```

## Optional character LoRA downloads

`config/anima-loras.json` contains download metadata for the private Anima
character LoRAs. The repository contains only metadata, not model weights.

List available IDs:

```bash
python scripts/download_loras.py --list
```

Download selected LoRAs:

```bash
hf auth login
python scripts/download_loras.py \
  --root /workspace/comfyui \
  --id bikini-cinderella
```

Omit `--id` to download every listed character LoRA. Files are installed under
`models/loras/anima/`.

## License

Repository source: GPL-3.0-only. See `LICENSE`.

The Anima LLLite patches inherit the CircleStone Labs Non-Commercial License.
The official Anima model and derivatives are restricted to non-commercial
model use unless a commercial license is obtained; generated outputs have
separate terms. Check every upstream license before use.

- [Official Anima model card](https://huggingface.co/circlestone-labs/Anima)
- [Anima LLLite model card](https://huggingface.co/kohya-ss/Anima-LLLite)
- [ComfyUI](https://github.com/Comfy-Org/ComfyUI)
- [ComfyUI ControlNet Aux](https://github.com/Fannovel16/comfyui_controlnet_aux)
