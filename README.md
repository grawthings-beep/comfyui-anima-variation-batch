# ComfyUI Anima Hires-Fix and Control Workflows

[![CI](https://github.com/grawthings-beep/comfyui-anima-variation-batch/actions/workflows/ci.yml/badge.svg)](https://github.com/grawthings-beep/comfyui-anima-variation-batch/actions/workflows/ci.yml)

This repository contains Anima-focused 2-pass Hires-fix workflows plus a
Pose/Depth controlled variant. It does not distribute model weights.

The latent Hires-fix workflow includes a blank-line Prompt Queue: paste up to
50 Grok-generated scenes at once and ComfyUI runs the complete two-pass
generation for every scene without manual prompt copying.

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

`anima_hiresfix_latent_2pass.json` does not use ESRGAN. Its built-in
`AnimaPromptQueue` splits scenes on blank lines, generates up to 50 scenes per
queue submission, assigns distinct seeds to both passes, and saves results
as one automatically downloaded ZIP containing `scene_001.png`,
`scene_002.png`, and so on.

## Base install

From the ComfyUI custom node directory:

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/grawthings-beep/comfyui-anima-variation-batch.git \
  ComfyUI-AnimaVariationBatch
```

Restart ComfyUI and load either of the two workflows that do not use
Pose/Depth, or continue with the control installer below.

For common RunPod images, the ComfyUI root is often one of:

```text
/opt/ComfyUI
/opt/comfyui-baked
/workspace/ComfyUI
/workspace/comfyui
```

## Install Pose and Depth control

The controlled workflow uses the pinned
[`kohya-ss/ComfyUI-Anima-LLLite`](https://github.com/kohya-ss/ComfyUI-Anima-LLLite)
compatibility node instead of the newer native `ModelPatchLoader`. It works on
baked ComfyUI images that cannot update their core checkout.

Both normal ComfyUI-Manager installs and direct clones are self-bootstrapping.
The repository's `prestartup_script.py` runs before custom-node discovery and
installs the Anima LLLite compatibility node, ControlNet Aux, required Python
packages, two LLLite weights, AnimeSharp, and the workflow. DWPose and Depth
Anything checkpoints are downloaded lazily on first use.

Existing clones should pull the latest `main` and restart ComfyUI once.

Then run the all-in-one installer with the same Python environment that runs
ComfyUI:

```bash
cd /opt/comfyui-baked/custom_nodes/ComfyUI-AnimaVariationBatch
git pull --ff-only
python scripts/install_anima_controls.py --root /opt/comfyui-baked
```

The installer:

- keeps an existing `comfyui_controlnet_aux` installation, or installs a
  tested revision when it is absent;
- installs a pinned Anima LLLite compatibility node, removing the dependency
  on newer ComfyUI core nodes;
- installs the preprocessor Python requirements;
- downloads the Pose and Depth LLLite weights to `models/controlnet/`;
- downloads AnimeSharp to `models/upscale_models/`;
- preloads DWPose and Depth Anything V2 Base into the ControlNet Aux cache;
- copies all ready-to-load workflows to `user/default/workflows/`.

The downloads total approximately 840 MB: 31 MB of Anima patches, 67 MB of
AnimeSharp, and about 742 MB of preprocessors. To leave preprocessor models
for first-run lazy download:

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

`anima_hiresfix_latent_2pass.json` needs no external upscaler or control-node
pack. The dependency-free Prompt Queue ships in this repository; the remaining
graph upscales the latent by 1.5x with bislerp, then runs a second pass. Its
default second-pass denoise is `0.55`; tune around `0.50` to `0.60`.

### Latent Prompt Queue

Paste Grok's scenes into the red Prompt Queue node with at least one blank line
between scenes, then choose `batch_range`: `1-50`, `51-100`, `101-150`,
`151-200`, `201-250`, or `251-300`. Each run accepts a fresh paste of up to 50
prompts. The selected range controls absolute filenames and seeds, so the
second paste produces `scene_051.png` through `scene_100.png` instead of
overwriting the first set.

`start_in_range` defaults to 1 and supports resuming partway through the
selected 50-scene range. `scene_limit` remains capped at 50. The seed sequence
is deterministic from `base_seed`, so resumed scenes keep the same seeds and
filenames. ZIP filenames also contain the zero-padded selected range, such as
`Anima_latent_queue_051-100_00001.zip`.

When the final latent upscale finishes, `AnimaSaveQueueZip` encodes every final
image directly into one ZIP and triggers a single browser download. It does not
duplicate the individual PNG files in ComfyUI's output directory. The ZIP node
also exposes a **Download ZIP** button in case the browser blocks the automatic
download. Set its `auto_download` widget to false if manual ZIP download is
preferred.

## ESRGAN model download

```bash
COMFY=/workspace/ComfyUI
[ -d "$COMFY" ] || COMFY=/workspace/comfyui
[ -d "$COMFY" ] || COMFY=/opt/ComfyUI

mkdir -p "$COMFY/models/upscale_models"
wget -O "$COMFY/models/upscale_models/4x-AnimeSharp.pth" \
  "https://huggingface.co/Kim2091/AnimeSharp/resolve/main/4x-AnimeSharp.pth"
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
