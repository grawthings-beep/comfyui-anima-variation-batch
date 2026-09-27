# ComfyUI Anima Hires-Fix and Two-Character Workflows

[![CI](https://github.com/grawthings-beep/comfyui-anima-variation-batch/actions/workflows/ci.yml/badge.svg)](https://github.com/grawthings-beep/comfyui-anima-variation-batch/actions/workflows/ci.yml)

This repository contains Anima-focused 2-pass Hires-fix workflows, a
two-character Mask Editor inpaint workflow, and an experimental two-character
regional LoRA hooks workflow. It does not distribute model weights.

The latent Hires-fix workflow includes a blank-line Prompt Queue: paste up to
50 Grok-generated scenes at once and ComfyUI runs the complete two-pass
generation for every scene without manual prompt copying.

## Workflows

```text
example_workflows/anima_hiresfix_esrgan_2pass.json
example_workflows/anima_hiresfix_latent_2pass.json
example_workflows/anima_two_character_hooks_hiresfix.json
example_workflows/anima_two_character_inpaint_hiresfix.json
```

### Two-character regional LoRA hooks + Hires-fix (experimental)

`anima_two_character_hooks_hiresfix.json` adds simultaneous A/B generation
without replacing any batch or inpaint workflow. It uses ComfyUI core nodes
only, with no ControlNet preprocessors or new Python dependencies.

```text
shared scene + A prompt -> A positive/negative + A LoRA hook + A soft mask
shared scene + B prompt -> B positive/negative + B LoRA hook + B soft mask
A/B pairs + shared fallback for uncovered areas -> one joint KSampler
base latent -> bislerp 1.5x
same A/B hooked conditioning -> low-denoise Hires-fix -> final image
```

The default loaders expect WAI-ANIMA, `qwen_3_06b_base.safetensors`,
`qwen_image_vae.safetensors`, `anima-turbo-lora-v0.2.safetensors`, and
`anima/Skin Texture Detail.safetensors`. Turbo (0.65) and Skin Texture (0.40)
are applied globally to BOTH samplers; character LoRAs remain regional hooks.
No ESRGAN model or decode/re-encode step is used between the sampling passes.
The two visible
`CreateHookLora` dropdowns default to the already installed
`anima/Bikini Cinderella - Anima.safetensors` and
`anima/White Cinderella - Anima.safetensors`. Select other installed LoRAs
directly in those dropdowns; no character download manifest change is needed.

The rendering profile follows the supplied `ComfyUI_temp_enxbg_00002_.json`:
WAI + Turbo 0.65 + Skin Texture 0.40, `res_multistep` / `sgm_uniform`, CFG 1,
18 base steps, 8 hires steps, latent bislerp 1.5x, and hires denoise 0.55.
Its Little Mermaid character LoRA is deliberately NOT copied into the global
model chain, since that would apply one character to both regions. Existing
A/B selectors and strengths remain independent. The batch Prompt Queue / ZIP
workflow is unchanged; this regional workflow still renders one joint image
per queue submission and saves a PNG.

**Prompts and controls:**

- Edit `Shared scene / interaction / light` once for the composition, pose,
  background, and lighting. It is automatically concatenated into BOTH A/B
  positives and also encodes the uncovered-area fallback.
- The supplied Prompt Queue was empty, and its linked positive text box is
  overridden by that queue. The actual generation positive cannot be recovered
  from that export. This workflow therefore keeps an editable two-person sample,
  not a claimed reconstruction of the original prompt. The earlier extra
  `anime illustration` / `detailed anime shading` style phrases were removed.
- Edit `string_b` in `A / positive` and `B / positive` for the corresponding
  character's trigger, appearance, and clothing. Their `string_a` inputs are
  connected to the shared prompt. Avoid copying both identities into both
  character boxes. The sample is a gentle embrace between two adult women.
- `Shared negative` is likewise concatenated into each character's negative.
  The separate A/B negative `string_b` fields can exclude unwanted clothing.
- The sample preserves the supplied `bikinicinderella` and `whitecinderella`
  triggers. Use the exact trained trigger for your installed files; a newer
  download catalog lists `b1k1c1nde` for Bikini, which is not automatically
  substituted here. Change the sample clothing descriptions as needed.
- Set `strength_model` separately in each LoRA node. Leave `strength_clip=0`.
  The LoRAs attach to BOTH sides of their conditioning pair, not globally to
  the MODEL. The `prev_hooks` inputs and fallback `hooks` input stay unconnected.

**Automatic regions:**

`Region canvas` is a 1152x1536 coordinate plane. For each character, `region
size` controls width/height, `region position` controls x/y, and `region
feather` controls its four soft edges. Defaults are A: x=0, width=600;
B: x=552, width=600; both height=1536, y=0, with a 48-pixel inner feather.
This gives a small central overlap without an uncovered seam. The core sampler
resizes both masks to each pass's latent resolution, so their relative
placement survives Hires-fix. Keep rectangles within the region canvas.
Regions can be moved vertically as well as horizontally without painting.

The separately titled `A / mask` and `B / mask` previews show white where the
corresponding branch contributes. These are queue-time previews, not a live
pose preview. To check only masks before expensive sampling, mute both
`Base image` and `Final image` output nodes with `Ctrl+M`, then queue. Restore
those outputs afterward. To test base generation without Hires-fix, mute only
`Final image`. Editing a numeric rectangle is not automatic person segmentation.

**Matched single-character rendering settings, not GPU-validated regional results:**

| Setting | Default |
| --- | --- |
| Base resolution | 1152x1536, batch 1 |
| A / B LoRA strengths | 0.80 / 0.80, CLIP 0 |
| Pair strength / area | 1.0 / `default` (full-image context) |
| Base sampler | 18 steps, CFG 1, res_multistep/sgm_uniform, denoise 1.0 |
| Hires sampler | 8 steps, CFG 1, res_multistep/sgm_uniform, denoise 0.55 |
| Latent upscale | bislerp, 1.5x |
| Final resolution | 1728x2304 |
| Seeds | Fixed, independently editable for each pass |
| Global Anima Turbo | Enabled, 0.65 |
| Global Skin Texture | Enabled, 0.40 |

The reference export's real base dimensions are 1152x1536 despite an outdated
832x1216 node title. For a smaller final 1152x1536 image, set `Base resolution`
to 768x1024 and keep the 1.5x latent upscale. The region canvas can remain
1152x1536; the sampler scales its masks to the latent dimensions.

CFG 1 normally skips negative evaluation in ComfyUI. The negative prompts and
their matching hook/mask pairs remain wired, but their exclusions do not affect
the default CFG 1 sampling. This intentionally matches the supplied profile;
raising CFG above 1 enables negative guidance but also changes the rendering.
Turbo and Skin Texture can be bypassed independently for diagnosis, but the
18/8-step CFG 1 defaults are the Turbo profile, not a non-Turbo recommendation.

**Validation and limits:** graph/schema checks do not establish successful
WAI-ANIMA GPU generation. The hook path was inspected against ComfyUI v0.26.2
and upstream revision `79be670e2d9be63e238785af307369d2b9039ed1`; actual
LoRA application and GPU output still require testing on your Pod. Anima
precomputes embeddings through its model-side `llm_adapter`; LoRAs trained on
that component can differ between standard loading and hooks despite CLIP
strength being zero. This workflow does not patch or claim to fix that path.
See the [upstream hook report](https://github.com/Comfy-Org/ComfyUI/issues/12853).

First compare each LoRA alone using the normal loader versus a full-image
hook mask with the same seed/settings, including strength-zero controls. For
an A-only hook test, set A size to 1152x1536, feather to zero, position to 0/0,
and B region `value` to zero. Check matched LoRA keys as well as image changes:
hook loading can omit unmatched keys without a warning. Then compare four fixed
seeds for side-by-side, back-to-back, and hugging, checking clothing, hair,
arm ownership, hands, and contact shadows. Compare base images before enabling
Hires-fix. Keep the matched 0.55 denoise initially; lowering it can preserve
more first-pass detail but also departs from the reference rendering. Matching
these settings does not prove identical texture under separate A/B hooks.

Each hook branch evaluates the same shared latent; overlapping masks blend
predictions. This is neither separate-image compositing nor strict regional
attention isolation. Wide overlaps can mix clothing, and a rectangular mask
cannot identify whose arm crosses into another region. One KSampler still
performs multiple hook-dependent model evaluations, so timing and VRAM use
must be measured. The existing inpaint workflow remains available when exact
silhouette masks and unmasked-pixel preservation are more important.

Regenerate the JSON with `node scripts/build_hooks_workflow.js`; check it with
`node scripts/build_hooks_workflow.js --check`. Its new filename deliberately
avoids the retired `anima_two_character_regional_hiresfix.json` name removed
by the RunPod startup script.

### Two-character Mask Editor inpaint + Hires-fix

`anima_two_character_inpaint_hiresfix.json` separates composition from both
identity replacements:

```text
checkpoint -> global Anima Turbo -> base interaction without character LoRAs
base image + hand-painted A mask -> Character A LoRA -> masked A inpaint
original base + A inpaint -> exact pixel composite -> intermediate A save
finished A image + hand-painted B mask -> Character B LoRA -> masked B inpaint
finished A image + B inpaint -> exact pixel composite
finished characters -> AnimeSharp 4x -> Lanczos 1160x1536 -> low-denoise Hires-fix
```

The first stage uses only Turbo to establish the complete physical interaction:
crossing arms, hands, gaze, height difference, lighting, and shadows. Copy the
purple base Save result into `Load Base + Paint Character A Mask`, then paint
A's entire old silhouette in ComfyUI's Mask Editor. Include A's hair, clothing,
limbs, shoes, shadow, and contact limbs owned by A. Disable the purple Save,
enable the orange Character A Save with `Ctrl+M`, and queue the second stage.

Copy the orange result into `Load Finished A + Paint Character B Mask`. Paint
B's complete old silhouette while keeping the finished A face and hair outside
the mask. Disable the orange Save, enable the red final Save, and queue the
third stage. Stage 3 replaces B, composites untouched pixels back from the
finished A image, and runs Hires-fix. Only one Save output should be enabled for
each queue submission; disabled branches do not require loaded mask images.

Each green `Anima Character LoRA Loader` reads `config/anima-loras.json` and
shows a visible character-name dropdown instead of a long
`anima/...safetensors` filename. It resolves and loads that character LoRA
internally, without a hidden standard-loader combo retaining a stale filename.
It never edits prompts; enter the exact trigger yourself in all three positive
prompt boxes.

The Character A and B LoRAs are applied only to their own masked samplers:

```text
Turbo LoRA strength:        1.00
Character A LoRA strength:  0.80, A inpaint sampler only
Character B LoRA strength:  0.90, B inpaint sampler only
Base sampler:               12 steps, CFG 1.5, Euler/simple, denoise 1.00, Turbo only
A/B inpaint samplers:       12 steps, CFG 1.5, Euler/simple, denoise 0.82
Mask cleanup per character: threshold 0.05, grow 32 px, edge blur 12 px
Latent mask expansion:      16 px
Final Hires-fix:            12 steps, CFG 1.5, denoise 0.20, Turbo only
```

Use inpaint denoise `0.70-0.78` when the pose should barely move, `0.80-0.88`
for a normal character replacement, or `0.90-1.00` when an identity is not
appearing strongly enough. Each painted mask is thresholded to full opacity
before it is expanded. Only the expanded outer edge is blurred for compositing,
so a partially transparent Mask Editor brush cannot leave the old placeholder
character as a ghost. Each `ImageCompositeMasked` restores original pixels
outside that character's clean mask, preventing whole-image VAE drift.

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

The two-character inpaint workflow reads the normal character manifest directly.
Selecting Character A or B in its green loader applies only the corresponding
`anima/...safetensors` file to that character's sampler. Prompt triggers stay
fully manual.

## License

Repository source: GPL-3.0-only. See `LICENSE`.

The official Anima model and derivatives are restricted to non-commercial
model use unless a commercial license is obtained; generated outputs have
separate terms. Check every upstream license before use.

- [Official Anima model card](https://huggingface.co/circlestone-labs/Anima)
- [ComfyUI](https://github.com/Comfy-Org/ComfyUI)
