# ComfyUI Anima Hires-Fix and Inpaint Workflows

[![CI](https://github.com/grawthings-beep/comfyui-anima-variation-batch/actions/workflows/ci.yml/badge.svg)](https://github.com/grawthings-beep/comfyui-anima-variation-batch/actions/workflows/ci.yml)

This repository contains Anima-focused 2-pass Hires-fix workflows and a
two-character Mask Editor inpaint workflow. It does not distribute model
weights.

The latent Hires-fix workflow includes a blank-line Prompt Queue: paste up to
50 Grok-generated scenes at once and ComfyUI runs the complete two-pass
generation for every scene without manual prompt copying.

## Workflows

```text
example_workflows/anima_hiresfix_esrgan_2pass.json
example_workflows/anima_hiresfix_latent_2pass.json
example_workflows/anima_two_character_inpaint_hiresfix.json
```

### Two-character Mask Editor inpaint + Hires-fix

`anima_two_character_inpaint_hiresfix.json` separates composition from
identity replacement:

```text
checkpoint -> global Anima Turbo -> Character A LoRA -> base interaction
base image + hand-painted B mask -> Character B LoRA -> masked inpaint
original base + masked inpaint result -> exact pixel composite
composite -> AnimeSharp 4x -> Lanczos 1160x1536 -> low-denoise Hires-fix
```

The first stage generates the complete physical interaction with Character A's
LoRA and a temporary Character B. This establishes crossing arms, hands, gaze,
height difference, lighting, and shadows before any identity replacement.
After the base image is generated, copy it from the purple Save node into
`Load Base + Paint Character B Mask`, open ComfyUI's Mask Editor, and paint
Character B. Include B's hair, clothing, limbs, and contact limbs belonging to
B, while leaving A's face and hair outside the mask.

The red final Save node is disabled when the workflow opens, so the missing
input image cannot block the base pass. After saving the mask, select that node
and press `Ctrl+M` once to enable it, then queue again.

`Anima Character LoRA Select` reads `config/anima-loras.json` and shows short
character names instead of long `anima/...safetensors` filenames. It selects
the model file only and never edits prompts. Enter the exact trigger yourself
in both prompt boxes.

The Character A and B LoRAs are applied to different samplers:

```text
Turbo LoRA strength:        1.00
Character A LoRA strength:  0.80, base sampler only
Character B LoRA strength:  0.90, masked inpaint sampler only
Base sampler:               12 steps, CFG 1.5, Euler/simple, denoise 1.00
Inpaint sampler:            12 steps, CFG 1.5, Euler/simple, denoise 0.82
Mask cleanup:               threshold 0.05, grow 24 px, edge blur 12 px
Latent mask expansion:      12 px
Final Hires-fix:            12 steps, CFG 1.5, denoise 0.20, Turbo only
```

Use inpaint denoise `0.70-0.78` when the pose should barely move, `0.80-0.88`
for a normal character replacement, or `0.90-1.00` when B's identity is not
appearing strongly enough. The painted mask is thresholded to full opacity
before it is expanded. Only the expanded outer edge is blurred for compositing,
so a partially transparent Mask Editor brush cannot leave the old placeholder
character as a ghost. The final `ImageCompositeMasked` restores original pixels
outside that clean mask before upscaling, preventing whole-image VAE drift.

The workflow uses only current ComfyUI core inpaint nodes plus this repository's
lightweight readable LoRA selector. It follows ComfyUI's official
[Mask Editor inpaint workflow](https://docs.comfy.org/tutorials/basic/inpaint)
with `VAEEncodeForInpaint`, then uses
[`ImageCompositeMasked`](https://docs.comfy.org/built-in-nodes/ImageCompositeMasked)
to preserve the unpainted area.

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

Restart ComfyUI and load the desired workflow. The repository does not
automatically install ControlNet Aux, DWPose, Depth Anything, Anima LLLite, or
their Python dependencies.

## Hires-fix details

The single-character workflows expect the official Anima base stack:

```text
models/diffusion_models/anima-base-v1.0.safetensors
models/text_encoders/qwen_3_06b_base.safetensors
models/vae/qwen_image_vae.safetensors
```

The two-character inpaint workflow defaults to
`models/diffusion_models/waiANIMA_v10Base10.safetensors`, matching the RunPod
image manifest. The official `anima-base-v1.0.safetensors` can be selected in
the same loader instead. It also expects:

```text
models/loras/anima-turbo-lora-v0.2.safetensors
```

The single-character ESRGAN workflow starts at 832x1216, upscales the first
pass with a 4x ESRGAN model, resizes to an effective 1.5x with Lanczos,
VAE-re-encodes, then runs a second pass. The two-character inpaint workflow
starts at 768x1024 and resizes its composited result to an exact 1160x1536.
Both need an anime ESRGAN upscaler such as:

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

The latent batch workflow also has an optional pose LoRA selector feeding two
`LoraLoaderModelOnly` nodes, one before each KSampler. Install the separated
pose LoRAs below before using it. The default pose strength is `0.8` for both
passes; lower the second pass first if the pose LoRA starts to overpower final
detail.

### Latent Prompt Queue

Paste up to 500 Grok scenes into the red Prompt Queue node with at least one
blank line between scenes. The default `batch_range` is `1-500` and
`scene_limit` is 500, so one click on Queue Prompt processes the full list.
Outputs use absolute names from `scene_001.png` through `scene_500.png`, and
the completed download is named like
`Anima_latent_queue_001-500_00001.zip`.

`start_in_range` defaults to 1 and supports resuming partway through the list.
The seed sequence is deterministic from `base_seed`, so resumed scenes keep
the same seeds and filenames. For smaller runs, the range menu still provides
the `301-500` continuation preset and 50-scene chunks from `1-50` through
`451-500`. With `301-500`, a fresh paste of 200 prompts is saved as
`scene_301.png` through `scene_500.png`. The actual generated range is included
in the ZIP filename to avoid collisions.

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

## Optional LoRA downloads

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
`models/loras/anima/` with character-first names such as
`Rapi - Anima.safetensors`, so ComfyUI's LoRA selector stays readable. When a
renamed LoRA is present, older `anima_*.safetensors` manifest paths are removed.

Pose/action LoRAs are intentionally kept in a separate manifest and folder so
they do not mix with character LoRAs:

```bash
python scripts/download_loras.py --manifest config/anima-pose-loras.json --list
python scripts/download_loras.py \
  --root /workspace/comfyui \
  --manifest config/anima-pose-loras.json
```

Those files install under `models/loras/anima_pose/` with numbered readable
names. The latent batch workflow's `Anima Pose LoRA Select` node reads that
manifest and sends the selected LoRA name to both Hires-fix passes.

The two-character workflow reads the normal character manifest directly.
Selecting Character A or B by its readable short name sends only the
corresponding `anima/...safetensors` path to that character's sampler. Prompt
triggers stay fully manual.

## License

Repository source: GPL-3.0-only. See `LICENSE`.

The official Anima model and derivatives are restricted to non-commercial
model use unless a commercial license is obtained; generated outputs have
separate terms. Check every upstream license before use.

- [Official Anima model card](https://huggingface.co/circlestone-labs/Anima)
- [ComfyUI](https://github.com/Comfy-Org/ComfyUI)
