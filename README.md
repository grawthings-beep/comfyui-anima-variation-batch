# ComfyUI Anima Variation Batch

[![CI](https://github.com/grawthings-beep/comfyui-anima-variation-batch/actions/workflows/ci.yml/badge.svg)](https://github.com/grawthings-beep/comfyui-anima-variation-batch/actions/workflows/ci.yml)

`Anima Flexible Variation Batch Sampler` creates several deliberately varied
images from one base prompt in a single queued ComfyUI execution.

It:

- accepts any number of chained variation categories;
- selects one comma-separated option from every category;
- uses every option in a category before reshuffling that category;
- encodes a separate positive prompt for every output;
- assigns an independent sampling seed to every output;
- samples and VAE-decodes sequentially to keep sampling VRAM close to a
  one-image workflow;
- combines the finished images into one IMAGE batch for previewing and saving;
- saves each execution as a PNG folder and one-click downloadable ZIP.

The default is four images per execution. This is sequential generation inside
one ComfyUI node, not a four-image GPU batch. Four outputs take roughly four
times the sampling time of one output.

## Install

From the ComfyUI custom node directory:

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/grawthings-beep/comfyui-anima-variation-batch.git \
  ComfyUI-AnimaVariationBatch
```

Restart ComfyUI, then load:

```text
example_workflows/anima_variation_batch_workflow.json
```

It is also exposed through ComfyUI's workflow templates browser.

An Easy-Use style Easy MultiAngle example is also included:

```text
example_workflows/ANIMA_EasyMultiAngle.json
```

That workflow mirrors the note.com Easy MultiAngle setup: `easy multiAngle`
outputs a prompt, `RegexExtract` keeps only the text before the coordinate
suffix, and `StringConcatenate` joins it with the character prompt. It requires
ComfyUI-Easy-Use and rgthree-comfy.

A no-extra-dependency preset-batch variant is also included:

```text
example_workflows/anima_easy_multiangle_batch_workflow.json
```

It uses the built-in `Anima MultiAngle Preset Group` node so camera angles can
be selected with toggles instead of editing JSON numbers.

A control-guided batch example is also included:

```text
example_workflows/ANIMA_Control_Canny.json
```

That workflow uses a loaded control image, the built-in ComfyUI Canny node,
Qwen Image's reference latent conditioning, and
`qwen_image_union_diffsynth_lora.safetensors` to keep composition closer to an
input structure while still producing a reusable Anima batch.

An img2img diff-making example is included for CG-set production:

```text
example_workflows/ANIMA_DiffMaker_img2img.json
```

That workflow starts from a finished source image, keeps the source composition
with low-denoise img2img, and creates small reusable variations such as
expression, detail, lighting, and finish changes.

A stronger img2img re-posing example is included for larger pose/composition
changes:

```text
example_workflows/ANIMA_RePose_img2img.json
```

That workflow uses a source image for img2img identity/style carryover and a
separate target pose/control image through Qwen Image Union Control LoRA.

Two pose-authoring variants are also included:

```text
example_workflows/ANIMA_RePose_OpenPoseEditor_img2img.json
example_workflows/ANIMA_RePose_DWPose_img2img.json
```

Use the OpenPose Editor workflow when you want to manually move the skeleton.
Use the DWPose workflow when you want to extract a skeleton from a reference
photo first.

## Hires-fix upscale workflows

Two 2-pass Hires-fix upscale examples are included:

```text
example_workflows/anima_hiresfix_esrgan_2pass.json
example_workflows/anima_hiresfix_latent_2pass.json
```

Both workflows expect the Anima base stack:

```text
anima-base-v1.0
qwen_3_06b_base
qwen_image_vae
```

`anima_hiresfix_esrgan_2pass.json` starts at 832x1216, upscales the first
pass with a 4x ESRGAN model, resizes to an effective 1.5x with Lanczos,
VAE-re-encodes, then runs a second pass. It additionally needs an anime
ESRGAN upscaler such as `models/upscale_models/4x-AnimeSharp.pth`. The
default second-pass denoise is `0.45`; tune around `0.35` to `0.55`, lowering
it to preserve the first pass or raising it for stronger detail redraw.

`anima_hiresfix_latent_2pass.json` uses only ComfyUI core nodes: it upscales
the latent by 1.5x with bislerp, then runs a second pass. The default
second-pass denoise is `0.55`; tune around `0.50` to `0.60` depending on how
much structure you want the second pass to revise.

## Batch ZIP saving

The example workflow uses `Anima Save Batch ZIP` instead of the standard
`Save Image` node. With `auto_download` enabled, the entire batch downloads
to the PC automatically after generation. The node also keeps a
`Download ZIP` button for manual re-download.

Files are stored in:

```text
output/anima_batches/YYYY-MM-DD/anima_batch_00001/
output/anima_batches/YYYY-MM-DD/anima_batch_00001.zip
```

The ZIP contains every PNG plus `prompt_report.txt` with the selected tags,
expanded prompts, and seeds. PNG workflow metadata is preserved.

For the existing RunPod image, the ComfyUI installation is commonly found at
one of:

```text
/opt/ComfyUI
/workspace/ComfyUI
/workspace/comfyui
```

## Inputs

- `base_prompt`: character, clothes, scene, quality tags, and fixed details.
- `variation_groups`: connect the final `Anima Variation Group` node.
- `count`: outputs per queued execution; defaults to `4`.
- `master_seed`: controls category shuffle order and every derived image seed.
- `steps`, `cfg`, `sampler_name`, `scheduler`, `denoise`: KSampler settings.

Each `Anima Variation Group` contains:

- `category_name`: a report label such as `Angle`, `Expression`, or `Pose`.
- `options`: short prompt tags separated by commas or new lines.
- `previous_groups`: connect the preceding Group node here.

Example:

```text
Angle:
from above, from side, from below, eye level, dutch angle

Expression:
smile, serious, angry, surprised, embarrassed

Pose:
standing, sitting, lying, looking back, arms crossed
```

Connect `Angle -> Expression -> Pose -> Flexible Sampler`. Duplicate the Group
node and connect it to the end to add `Composition`, `Lighting`, `Clothes`, or
any other category. There is no fixed category count.

Keep the connected `Empty Latent Image` batch size at `1`. Use `count` on the
custom node to choose the number of outputs.

Each category acts as an independent shuffle bag. With three angle tags and
eight outputs, all three angles are used once in random order, then reshuffled
and used again. This works even when a category has fewer options than
`count`.

Lines beginning with `#` are ignored. Duplicate options are removed
case-insensitively.

The original two-field `Anima Variation Batch Sampler` remains available for
old workflows.

## Easy MultiAngle presets

`ANIMA_EasyMultiAngle.json` is the Easy-Use/rgthree version matching the public
note workflow. It depends on these custom nodes:

```text
ComfyUI-Easy-Use: easy multiAngle, easy positive, easy negative
rgthree-comfy: Power Lora Loader (rgthree)
ComfyUI core: RegexExtract, StringConcatenate, PreviewAny
```

The important extraction pattern is:

```text
^([^\(]*).*
```

It removes Easy MultiAngle's coordinate suffix and keeps the angle prompt text
for ANIMA.

`Anima MultiAngle Preset Group` creates an `Angle` variation category from
twenty camera preset toggles. It is the recommended node for normal use.

Connect:

```text
Anima MultiAngle Preset Group -> Expression Group -> Pose Group -> Flexible Sampler
```

The presets cover front, front-left, front-right, side, and rear angles with
eye-level, high-angle, low-angle, and close-up variants. Toggle the presets you
want included in the shuffle bag; at least one preset must be enabled.

The legacy `Anima MultiAngle` node is still available for JSON-based workflows.
It mirrors Easy-Use's camera prompt mapping. `Anima Easy MultiAngle Group` can
adapt those params into the same `ANIMA_VARIATION_GROUPS` chain. The adapter
removes the parenthetical coordinate suffix by default. For example:

```text
back-right view, high angle, extreme wide shot (horizontal: 145, vertical: 36, zoom: 0.0)
```

becomes:

```text
back-right view, high angle, extreme wide shot
```

This follows the common Anima workflow pattern of keeping only the camera tags
and dropping the coordinate metadata. Comma-containing camera prompts are kept
as one variation option, so `front view, eye level, medium shot` is not split
into three separate choices.

If ComfyUI-Easy-Use v1.3.6 or newer is installed, its `easy multiAngle` node's
`params` output can also be connected to `Anima Easy MultiAngle Group`.

## Control Canny batch

`ANIMA_Control_Canny.json` is the recommended starting point when prompt-only
angle tags are not strong enough. Upload or select a control image in the
`Load Image` node; the workflow scales it to about one megapixel, extracts
Canny edges, VAE-encodes those edges, and connects the latent to the sampler's
`reference_latent` input.

The sampler applies that reference latent to every generated positive and
negative conditioning entry, matching ComfyUI's built-in `ReferenceLatent`
node behavior. The same encoded latent is also used as the sampling latent, so
the output resolution follows the control image after scaling.

The example expects these model filenames:

```text
models/diffusion_models/waiANIMA_v10Base10.safetensors
models/text_encoders/qwen_3_06b_base.safetensors
models/vae/qwen_image_vae.safetensors
models/loras/qwen_image_union_diffsynth_lora.safetensors
models/loras/anima-turbo-lora-v0.2.safetensors
```

Keep the variation groups focused on expression, lighting, clothing, finish,
or other details. Avoid contradictory camera-angle tags when the control image
is supposed to define the composition.

## DiffMaker img2img batch

`ANIMA_DiffMaker_img2img.json` is for turning one accepted base image into
usable CG-set diffs. Upload the base image in the `Source image` node. The
workflow scales it to about one megapixel, VAE-encodes it, and uses that latent
as the sampler's `latent_image`.

The default sampler settings are deliberately conservative:

```text
steps: 24
cfg: 4
denoise: 0.38
sampler: euler
scheduler: normal
```

Use `denoise` as the main control. Around `0.30` keeps the image close and is
best for expression/detail changes. Around `0.45` allows stronger clothing,
lighting, or small pose drift. Higher values can stop being a diff and become
a new image.

This example does not load the Turbo LoRA by default. It is intended for
quality and prompt adherence after a good base image already exists, not for
fast exploration.

## RePose img2img batch

`ANIMA_RePose_img2img.json` is for changing pose or composition more strongly
than DiffMaker. It has two image inputs:

```text
Source image: character/style source, encoded as the img2img latent
Target pose/control image: desired pose or composition, encoded as reference_latent
```

The workflow loads `qwen_image_union_diffsynth_lora.safetensors` and connects
the target control latent to the sampler's `reference_latent` input. The
defaults are stronger than DiffMaker:

```text
steps: 30
cfg: 4
denoise: 0.58
sampler: euler
scheduler: normal
```

Use a target pose/control image with roughly the same aspect ratio as the
source image. If the target image is a full render, edge/pose/depth-like
images usually work better than a busy finished image. Lower `denoise` toward
`0.50` to preserve the source more; raise it toward `0.65` when the pose is
not changing enough.

This workflow expects you to already have a target control image. It does not
provide a skeleton editor by itself.

## OpenPose Editor RePose batch

`ANIMA_RePose_OpenPoseEditor_img2img.json` is the workflow to use when you
want to freely edit the pose. It needs the lightweight OpenPose Editor custom
node:

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/space-nuko/ComfyUI-OpenPose-Editor.git
```

The workflow has a normal `Source image` node and an `OpenPose Editor target
pose` node. Open the editor node, make or edit a skeleton, then queue the
workflow. The edited pose image is VAE-encoded as `reference_latent`, while
the source image is used as the img2img latent.

Defaults:

```text
steps: 30
cfg: 4
denoise: 0.60
sampler: euler
scheduler: normal
```

If the pose is ignored, raise `denoise` toward `0.65`. If the character or
outfit drifts too much, lower it toward `0.52` and keep the prompt focused on
identity, clothing, and finish rather than camera angle.

## DWPose RePose batch

`ANIMA_RePose_DWPose_img2img.json` is for taking a pose from a reference
photo. It needs ComfyUI ControlNet Auxiliary Preprocessors:

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git
cd comfyui_controlnet_aux
python -m pip install -r requirements.txt
```

The workflow has two image inputs:

```text
Source image: character/style source, encoded as the img2img latent
Target pose reference photo: photo/render to extract DWPose skeleton from
```

`DWPose target skeleton` outputs a pose map, the workflow previews that map,
then encodes it as `reference_latent`. If DWPose misses hands or the body,
use a clearer full-body reference, increase the target image size, or switch
to the OpenPose Editor workflow and fix the skeleton manually.

## Optional character LoRA downloads

`config/anima-loras.json` mirrors the private character LoRAs used by the
RunPod image, including Label and Ark Ranger Black. The repository contains
only download metadata, not model weights.

List available IDs:

```bash
python scripts/download_loras.py --list
```

Download selected LoRAs:

```bash
hf auth login
hf auth whoami
python scripts/download_loras.py \
  --root /workspace/comfyui \
  --id label \
  --id arkrangerblack
```

Omit `--id` to download every listed character LoRA. Files are installed under
`models/loras/anima/`. A successful `hf auth login` is required because the
LoRA repository is private.

## Anima Turbo example

The included workflow is configured as an example for:

- Anima-compatible diffusion model
- Qwen 3 0.6B text encoder
- Qwen Image VAE
- Anima Turbo LoRA
- 8 steps
- 4 outputs

Model filenames are examples. Select the files installed in your own ComfyUI
environment.

## What this does not guarantee

Prompt tags increase diversity but do not provide exact pose or camera
control. Closely related tags can still produce visually similar images. Use
`ANIMA_Control_Canny.json` or another reference/depth/pose workflow when
specific 2D structure is required.

## License

GPL-3.0-only. See `LICENSE`.

This repository does not distribute Anima or LoRA weights. Check the license of
every model used in your workflow. The official Anima model and derivatives
are restricted to non-commercial use unless a commercial license is obtained.

- [Official Anima model card](https://huggingface.co/circlestone-labs/Anima)
- [ComfyUI](https://github.com/Comfy-Org/ComfyUI)
