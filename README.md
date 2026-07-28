# ComfyUI Anima Hires-Fix and Regional Workflows

[![CI](https://github.com/grawthings-beep/comfyui-anima-variation-batch/actions/workflows/ci.yml/badge.svg)](https://github.com/grawthings-beep/comfyui-anima-variation-batch/actions/workflows/ci.yml)

This repository contains Anima-focused 2-pass Hires-fix workflows and a
two-character regional LoRA workflow. It does not distribute model weights.

The latent Hires-fix workflow includes a blank-line Prompt Queue: paste up to
50 Grok-generated scenes at once and ComfyUI runs the complete two-pass
generation for every scene without manual prompt copying.

## Workflows

```text
example_workflows/anima_hiresfix_esrgan_2pass.json
example_workflows/anima_hiresfix_latent_2pass.json
example_workflows/anima_two_character_regional_hiresfix.json
```

### Two-character regional Hires-fix

`anima_two_character_regional_hiresfix.json` is the recommended starting point
for a coherent image containing two different LoRA characters:

```text
shared scene + Character A details + A LoRA hook + soft A mask --+
shared scene + Character B details + B LoRA hook + soft B mask --+-> same first pass
                                                                   -> ESRGAN 1.5x
                                                                   -> regional second pass
```

Both characters are solved in the same diffusion trajectory. The LoRAs are
attached to their masked conditioning with ComfyUI's model-only hook system,
instead of loading both LoRAs globally. This reduces identity and clothing
bleed while retaining shared lighting, eye contact, body spacing, and contact
between the characters. The masks are soft influence maps inside one latent,
not separately rendered images or a cut-and-paste composite.

The green pair node lists readable character names from
`config/anima-loras.json` and injects each selected LoRA's trigger
automatically. Style LoRAs in that manifest are excluded from this character
menu. Describe the complete interaction in `shared_scene`, then add visible
hair, eye, clothing, expression, and body-direction details for each character.
This follows the
[official Anima multiple-character prompting guidance](https://huggingface.co/circlestone-labs/Anima#natural-language-prompting-tips),
which recommends describing each named character's appearance.

`Anima Two-Character Free Regional Masks` displays the A/B layout live inside
the node and also outputs the exact mask preview. Each character has independent
X, Y, width, and height controls. Its derived position description is connected
back to the character prompt automatically, so moving A or B vertically does
not leave a stale left/right prompt behind. Defaults cover the left and right
halves with a feathered center overlap. Move and overlap the regions around
touching hands or bodies; reduce the overlap if identities begin to mix.
Any area left outside both masks is filled by an unhooked shared-scene default
conditioning, keeping the background coherent without leaking either character
LoRA across the whole image.

The regional nodes default to `default`, so each character sees the complete
image context and only its denoised prediction is masked. Switching both to
`mask bounds` can run faster, but cropped context can weaken interaction
continuity. Start with:

```text
Character LoRA strength: 0.80 (typical range 0.65-0.95)
Mask feather:            6%   (typical range 4-10%)
Second-pass denoise:     0.38 (typical range 0.32-0.42)
```

The primary path is regional rather than sequential replacement inpaint:
inpainting Character B after Character A can overwrite crossing arms, hands,
shadows, and eye contact. Use ComfyUI's Mask Editor for a final local repair
only after the regional result has established both characters.

This workflow needs a current ComfyUI core containing
`CreateHookLoraModelOnly` and `ConditioningSetProperties`; it adds no Python
package or third-party node dependency. See the official
[LoRA hook](https://docs.comfy.org/built-in-nodes/CreateHookLoraModelOnly) and
[masked conditioning](https://docs.comfy.org/built-in-nodes/ConditioningSetProperties)
node documentation.

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

The two-character regional workflow defaults to
`models/diffusion_models/waiANIMA_v10Base10.safetensors`, matching the RunPod
image manifest. The official `anima-base-v1.0.safetensors` can be selected in
the same loader instead.

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
Selecting Character A or B by its readable label automatically sends the
corresponding `anima/...safetensors` path and trigger to the regional graph.

## License

Repository source: GPL-3.0-only. See `LICENSE`.

The official Anima model and derivatives are restricted to non-commercial
model use unless a commercial license is obtained; generated outputs have
separate terms. Check every upstream license before use.

- [Official Anima model card](https://huggingface.co/circlestone-labs/Anima)
- [ComfyUI](https://github.com/Comfy-Org/ComfyUI)
