const fs = require("fs");
const path = require("path");

const nodes = [];
const links = [];
let nextLinkId = 1;

function addNode({
    id,
    type,
    pos,
    size,
    title,
    inputs = [],
    outputs = [],
    widgets = [],
    properties = {},
    mode = 0,
    color,
    bgcolor,
}) {
    const node = {
        id,
        type,
        pos,
        size,
        flags: {},
        order: 0,
        mode,
        inputs: inputs.map((input) => ({ ...input, link: input.link ?? null })),
        outputs: outputs.map((output) => ({
            ...output,
            links: output.links ?? [],
        })),
        properties: {
            "Node name for S&R": type,
            ...properties,
        },
        widgets_values: widgets,
    };
    if (title) node.title = title;
    if (color) node.color = color;
    if (bgcolor) node.bgcolor = bgcolor;
    nodes.push(node);
    return node;
}

function connect(sourceId, sourceSlot, targetId, targetSlot, type) {
    const linkId = nextLinkId++;
    const source = nodes.find((node) => node.id === sourceId);
    const target = nodes.find((node) => node.id === targetId);
    source.outputs[sourceSlot].links.push(linkId);
    target.inputs[targetSlot].link = linkId;
    links.push([
        linkId,
        sourceId,
        sourceSlot,
        targetId,
        targetSlot,
        type,
    ]);
}

const modelInput = (link = null) => ({
    name: "model",
    type: "MODEL",
    link,
});
const conditioningInput = (name) => ({
    name,
    type: "CONDITIONING",
});
const clipTextInputs = [{ name: "clip", type: "CLIP" }];
const samplerInputs = [
    modelInput(),
    conditioningInput("positive"),
    conditioningInput("negative"),
    { name: "latent_image", type: "LATENT" },
];

const basePrompt = [
    "masterpiece, best quality, score_7, safe, 2girls, exactly two adult women, no other people, full body, two adult women in a close affectionate hug, natural intertwined pose, close body contact, both faces visible, coherent arms and hands, both standing on the same ground level, detailed school courtyard, anime illustration, anime coloring.",
    "Character A is the taller girl on the left: k0t0h1s4k0, braid, side ponytail, school uniform, serafuku, sailor collar, white shirt, blue neckerchief, black pleated skirt, white kneehighs, brown loafers, arms around Character B's shoulders and upper back.",
    "Character B is the noticeably shorter petite girl on the right: m1ch1n0kuk0m4r0, bags under eyes, ahoge, messy hair, hair between eyes, school uniform, serafuku, green sailor collar, white shirt, long sleeves, green pleated skirt, black pantyhose, brown loafers, arms around Character A's waist.",
].join("\n");

const inpaintPrompt = [
    "Redraw Character B inside the painted mask while preserving the existing pose, contact points, Character A, camera, lighting, and background outside the mask.",
    basePrompt,
    "Character B must keep a distinct face, hair, green uniform details, shorter height, and naturally connected arms and hands where she touches Character A.",
].join("\n");

const negativePrompt = [
    "worst quality, low quality, score_1, score_2, score_3, blurry, jpeg artifacts, bad anatomy, bad hands, standing apart, separate portraits, gap between characters, stiff pose, arms at sides, fused bodies, merged faces, shared limbs, duplicate person, identical faces, ghost, afterimage, transparent person, translucent person, silhouette, third girl, 3girls, extra arms, extra legs, missing limbs, malformed hands, mixed clothing, color bleeding, text, watermark, signature, logo",
].join("");

addNode({
    id: 1,
    type: "MarkdownNote",
    pos: [-1640, -80],
    size: [620, 980],
    title: "Read first",
    widgets: [
        [
            "# Two-Character Inpaint + Exact 1160x1536 Hires-Fix",
            "",
            "This replaces the retired regional workflow. Character LoRAs are never loaded together.",
            "",
            "## Stage 1: make the interaction",
            "1. Select Character A and Character B by readable name.",
            "2. Put the exact trigger and appearance for both people in the Base Composition prompt.",
            "3. Queue once. Only the purple Base Composition Save node is active.",
            "",
            "## Stage 2: replace Character B",
            "1. Right-click the base Save node and choose Copy (Clipspace).",
            "2. Right-click Load Base + B Mask and choose Paste (Clipspace).",
            "3. Open that Load Image node in Mask Editor.",
            "4. Paint the entire old Character B silhouette, including B's hair, clothes, limbs, shoes, shadow, and the hands/arms that belong to B. Leave Character A's face and hair unpainted.",
            "5. Save the mask, select the red final Save node, and press Ctrl+M once to enable it.",
            "6. Queue again.",
            "",
            "## Defaults",
            "- Base: 768x1024, Turbo 12 steps, CFG 1.5.",
            "- Inpaint: denoise 0.82. Use 0.70-0.78 to preserve more pose, or 0.88-1.00 for a stronger replacement.",
            "- Mask cleanup: threshold 0.05, grow 24 px, blur the outer 12 px, plus 12 px latent grow.",
            "- Hires-fix: AnimeSharp 4x, Lanczos to exact 1160x1536, denoise 0.20.",
            "- Character A LoRA affects only Stage 1. Character B LoRA affects only the masked inpaint sampler. The final low-denoise pass uses Turbo only.",
        ].join("\n"),
    ],
    properties: {},
    color: "#222222",
    bgcolor: "#111111",
});

addNode({
    id: 2,
    type: "UNETLoader",
    pos: [-940, 0],
    size: [330, 82],
    title: "WAI-ANIMA / Anima diffusion model",
    outputs: [{ name: "MODEL", type: "MODEL" }],
    widgets: ["waiANIMA_v10Base10.safetensors", "default"],
    properties: { cnr_id: "comfy-core" },
});

addNode({
    id: 3,
    type: "CLIPLoader",
    pos: [-940, 120],
    size: [330, 106],
    title: "Anima Qwen text encoder",
    outputs: [{ name: "CLIP", type: "CLIP" }],
    widgets: [
        "qwen_3_06b_base.safetensors",
        "stable_diffusion",
        "default",
    ],
    properties: {
        cnr_id: "comfy-core",
        models: [
            {
                name: "qwen_3_06b_base.safetensors",
                url: "https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/text_encoders/qwen_3_06b_base.safetensors",
                directory: "text_encoders",
            },
        ],
    },
});

addNode({
    id: 4,
    type: "VAELoader",
    pos: [-940, 265],
    size: [330, 58],
    title: "Qwen Image VAE",
    outputs: [{ name: "VAE", type: "VAE" }],
    widgets: ["qwen_image_vae.safetensors"],
    properties: {
        cnr_id: "comfy-core",
        models: [
            {
                name: "qwen_image_vae.safetensors",
                url: "https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/vae/qwen_image_vae.safetensors",
                directory: "vae",
            },
        ],
    },
});

addNode({
    id: 5,
    type: "LoraLoaderModelOnly",
    pos: [-940, 365],
    size: [360, 98],
    title: "Global Anima Turbo LoRA v0.2",
    inputs: [
        modelInput(),
        {
            name: "lora_name",
            type: "COMBO",
            widget: { name: "lora_name" },
        },
        {
            name: "strength_model",
            type: "FLOAT",
            widget: { name: "strength_model" },
        },
    ],
    outputs: [{ name: "MODEL", type: "MODEL" }],
    widgets: ["anima-turbo-lora-v0.2.safetensors", 1.0],
    properties: {
        cnr_id: "comfy-core",
        models: [
            {
                name: "anima-turbo-lora-v0.2.safetensors",
                url: "https://huggingface.co/circlestone-labs/Anima-Official-LoRAs/resolve/main/anima-turbo-lora-v0.2.safetensors",
                directory: "loras",
            },
        ],
    },
    color: "#27323a",
    bgcolor: "#34434d",
});

for (const [id, y, title, character, strength] of [
    [6, 0, "Character A for base composition", "Kotobuki Hisako", 0.8],
    [7, 180, "Character B for masked replacement", "Michinoku Komaro", 0.9],
]) {
    addNode({
        id,
        type: "AnimaCharacterLoRASelect",
        pos: [-520, y],
        size: [350, 110],
        title,
        outputs: [
            { name: "lora_name", type: "*" },
            { name: "strength", type: "FLOAT" },
        ],
        widgets: [character, strength],
        properties: { cnr_id: "ComfyUI-AnimaVariationBatch" },
        color: "#233333",
        bgcolor: "#355555",
    });
}

for (const [id, y, title, loraName, strength] of [
    [
        8,
        0,
        "A LoRA: base composition only",
        "anima/Kotobuki Hisako - Anima.safetensors",
        0.8,
    ],
    [
        9,
        180,
        "B LoRA: masked inpaint only",
        "anima/Michinoku Komaro - Anima.safetensors",
        0.9,
    ],
]) {
    addNode({
        id,
        type: "LoraLoaderModelOnly",
        pos: [-100, y],
        size: [370, 98],
        title,
        inputs: [
            modelInput(),
            {
                name: "lora_name",
                type: "COMBO",
                widget: { name: "lora_name" },
            },
            {
                name: "strength_model",
                type: "FLOAT",
                widget: { name: "strength_model" },
            },
        ],
        outputs: [{ name: "MODEL", type: "MODEL" }],
        widgets: [loraName, strength],
        properties: { cnr_id: "comfy-core" },
    });
}

addNode({
    id: 10,
    type: "CLIPTextEncode",
    pos: [340, -20],
    size: [520, 340],
    title: "Base composition: both characters and interaction",
    inputs: clipTextInputs,
    outputs: [{ name: "CONDITIONING", type: "CONDITIONING" }],
    widgets: [basePrompt],
    properties: { cnr_id: "comfy-core" },
    color: "#233326",
    bgcolor: "#35503a",
});

addNode({
    id: 11,
    type: "CLIPTextEncode",
    pos: [340, 360],
    size: [520, 390],
    title: "Inpaint B: complete scene and B identity",
    inputs: clipTextInputs,
    outputs: [{ name: "CONDITIONING", type: "CONDITIONING" }],
    widgets: [inpaintPrompt],
    properties: { cnr_id: "comfy-core" },
    color: "#33263a",
    bgcolor: "#50385c",
});

addNode({
    id: 12,
    type: "CLIPTextEncode",
    pos: [340, 790],
    size: [520, 240],
    title: "Shared negative prompt",
    inputs: clipTextInputs,
    outputs: [{ name: "CONDITIONING", type: "CONDITIONING" }],
    widgets: [negativePrompt],
    properties: { cnr_id: "comfy-core" },
});

addNode({
    id: 13,
    type: "EmptyLatentImage",
    pos: [980, 30],
    size: [260, 108],
    title: "Base size: 768x1024",
    outputs: [{ name: "LATENT", type: "LATENT" }],
    widgets: [768, 1024, 1],
    properties: { cnr_id: "comfy-core" },
});

addNode({
    id: 14,
    type: "KSampler",
    pos: [1300, -10],
    size: [320, 330],
    title: "Stage 1: Turbo base composition",
    inputs: samplerInputs,
    outputs: [{ name: "LATENT", type: "LATENT" }],
    widgets: [
        566871253377100,
        "randomize",
        12,
        1.5,
        "euler",
        "simple",
        1.0,
    ],
    properties: { cnr_id: "comfy-core" },
    color: "#2e2738",
    bgcolor: "#44364f",
});

addNode({
    id: 15,
    type: "VAEDecode",
    pos: [1670, 20],
    size: [240, 58],
    title: "Decode base composition",
    inputs: [
        { name: "samples", type: "LATENT" },
        { name: "vae", type: "VAE" },
    ],
    outputs: [{ name: "IMAGE", type: "IMAGE" }],
    properties: { cnr_id: "comfy-core" },
});

addNode({
    id: 16,
    type: "SaveImage",
    pos: [1980, -40],
    size: [430, 500],
    title: "STAGE 1 ACTIVE: Save base composition",
    inputs: [{ name: "images", type: "IMAGE" }],
    outputs: [],
    widgets: ["Anima_two_character_inpaint_base"],
    properties: { cnr_id: "comfy-core" },
    color: "#302844",
    bgcolor: "#493a63",
});

addNode({
    id: 17,
    type: "LoadImage",
    pos: [2540, -40],
    size: [360, 410],
    title: "Load Base + Paint Character B Mask",
    outputs: [
        { name: "IMAGE", type: "IMAGE" },
        { name: "MASK", type: "MASK" },
    ],
    widgets: ["paste_base_here.png", "image"],
    properties: { cnr_id: "comfy-core" },
    color: "#3a2c25",
    bgcolor: "#594137",
});

addNode({
    id: 18,
    type: "GrowMask",
    pos: [2860, 420],
    size: [280, 90],
    title: "Cover the old B silhouette + 24px",
    inputs: [{ name: "mask", type: "MASK" }],
    outputs: [{ name: "MASK", type: "MASK" }],
    widgets: [24, true],
    properties: { cnr_id: "comfy-core" },
});

addNode({
    id: 30,
    type: "ThresholdMask",
    pos: [2540, 420],
    size: [280, 90],
    title: "Make painted mask fully opaque",
    inputs: [{ name: "mask", type: "MASK" }],
    outputs: [{ name: "MASK", type: "MASK" }],
    widgets: [0.05],
    properties: { cnr_id: "comfy-core" },
});

addNode({
    id: 19,
    type: "VAEEncodeForInpaint",
    pos: [2970, 300],
    size: [330, 110],
    title: "Encode masked B area",
    inputs: [
        { name: "pixels", type: "IMAGE" },
        { name: "vae", type: "VAE" },
        { name: "mask", type: "MASK" },
    ],
    outputs: [{ name: "LATENT", type: "LATENT" }],
    widgets: [12],
    properties: { cnr_id: "comfy-core" },
});

addNode({
    id: 31,
    type: "MaskToImage",
    pos: [3180, 440],
    size: [220, 58],
    title: "Mask to image for edge blur",
    inputs: [{ name: "mask", type: "MASK" }],
    outputs: [{ name: "IMAGE", type: "IMAGE" }],
    properties: { cnr_id: "comfy-core" },
});

addNode({
    id: 32,
    type: "ImageBlur",
    pos: [3440, 410],
    size: [260, 110],
    title: "Blur only the expanded outer edge",
    inputs: [{ name: "image", type: "IMAGE" }],
    outputs: [{ name: "IMAGE", type: "IMAGE" }],
    widgets: [12, 4.0],
    properties: { cnr_id: "comfy-core" },
});

addNode({
    id: 33,
    type: "ImageToMask",
    pos: [3740, 430],
    size: [220, 80],
    title: "Clean composite mask",
    inputs: [{ name: "image", type: "IMAGE" }],
    outputs: [{ name: "MASK", type: "MASK" }],
    widgets: ["red"],
    properties: { cnr_id: "comfy-core" },
});

addNode({
    id: 20,
    type: "KSampler",
    pos: [3370, -10],
    size: [320, 330],
    title: "Stage 2: B-only masked inpaint",
    inputs: samplerInputs,
    outputs: [{ name: "LATENT", type: "LATENT" }],
    widgets: [
        566871253377102,
        "randomize",
        12,
        1.5,
        "euler",
        "simple",
        0.82,
    ],
    properties: { cnr_id: "comfy-core" },
    color: "#3a262f",
    bgcolor: "#573743",
});

addNode({
    id: 21,
    type: "VAEDecode",
    pos: [3750, 20],
    size: [240, 58],
    title: "Decode inpaint",
    inputs: [
        { name: "samples", type: "LATENT" },
        { name: "vae", type: "VAE" },
    ],
    outputs: [{ name: "IMAGE", type: "IMAGE" }],
    properties: { cnr_id: "comfy-core" },
});

addNode({
    id: 22,
    type: "ImageCompositeMasked",
    pos: [4050, -10],
    size: [330, 170],
    title: "Restore untouched original pixels",
    inputs: [
        { name: "destination", type: "IMAGE" },
        { name: "source", type: "IMAGE" },
        {
            name: "x",
            type: "INT",
            widget: { name: "x" },
        },
        {
            name: "y",
            type: "INT",
            widget: { name: "y" },
        },
        {
            name: "resize_source",
            type: "BOOLEAN",
            widget: { name: "resize_source" },
        },
        { name: "mask", type: "MASK" },
    ],
    outputs: [{ name: "IMAGE", type: "IMAGE" }],
    widgets: [0, 0, false],
    properties: { cnr_id: "comfy-core" },
});

addNode({
    id: 23,
    type: "UpscaleModelLoader",
    pos: [4560, 0],
    size: [330, 58],
    title: "Load anime ESRGAN",
    outputs: [{ name: "UPSCALE_MODEL", type: "UPSCALE_MODEL" }],
    widgets: ["4x-AnimeSharp.pth"],
    properties: {
        cnr_id: "comfy-core",
        models: [
            {
                name: "4x-AnimeSharp.pth",
                url: "https://huggingface.co/Kim2091/AnimeSharp/resolve/main/4x-AnimeSharp.pth",
                directory: "upscale_models",
            },
        ],
    },
});

addNode({
    id: 24,
    type: "ImageUpscaleWithModel",
    pos: [4970, 0],
    size: [280, 72],
    title: "AnimeSharp 4x",
    inputs: [
        { name: "upscale_model", type: "UPSCALE_MODEL" },
        { name: "image", type: "IMAGE" },
    ],
    outputs: [{ name: "IMAGE", type: "IMAGE" }],
    properties: { cnr_id: "comfy-core" },
});

addNode({
    id: 25,
    type: "ImageScale",
    pos: [5330, -10],
    size: [320, 170],
    title: "Exact output size: 1160x1536",
    inputs: [{ name: "image", type: "IMAGE" }],
    outputs: [{ name: "IMAGE", type: "IMAGE" }],
    widgets: ["lanczos", 1160, 1536, "disabled"],
    properties: { cnr_id: "comfy-core" },
});

addNode({
    id: 26,
    type: "VAEEncode",
    pos: [5730, 10],
    size: [250, 58],
    title: "Re-encode exact size",
    inputs: [
        { name: "pixels", type: "IMAGE" },
        { name: "vae", type: "VAE" },
    ],
    outputs: [{ name: "LATENT", type: "LATENT" }],
    properties: { cnr_id: "comfy-core" },
});

addNode({
    id: 27,
    type: "KSampler",
    pos: [6060, -10],
    size: [320, 330],
    title: "Stage 3: Turbo Hires-fix, denoise 0.20",
    inputs: samplerInputs,
    outputs: [{ name: "LATENT", type: "LATENT" }],
    widgets: [
        566871253377103,
        "randomize",
        12,
        1.5,
        "euler",
        "simple",
        0.20,
    ],
    properties: { cnr_id: "comfy-core" },
    color: "#26343a",
    bgcolor: "#374e57",
});

addNode({
    id: 28,
    type: "VAEDecode",
    pos: [6440, 20],
    size: [240, 58],
    title: "Decode final",
    inputs: [
        { name: "samples", type: "LATENT" },
        { name: "vae", type: "VAE" },
    ],
    outputs: [{ name: "IMAGE", type: "IMAGE" }],
    properties: { cnr_id: "comfy-core" },
});

addNode({
    id: 29,
    type: "SaveImage",
    pos: [6760, -40],
    size: [460, 540],
    title: "ENABLE AFTER MASK: Save final 1160x1536",
    inputs: [{ name: "images", type: "IMAGE" }],
    outputs: [],
    widgets: ["Anima_two_character_inpaint_hiresfix"],
    properties: { cnr_id: "comfy-core" },
    mode: 2,
    color: "#4d2020",
    bgcolor: "#702f2f",
});

connect(2, 0, 5, 0, "MODEL");
connect(5, 0, 8, 0, "MODEL");
connect(5, 0, 9, 0, "MODEL");
connect(6, 0, 8, 1, "*");
connect(6, 1, 8, 2, "FLOAT");
connect(7, 0, 9, 1, "*");
connect(7, 1, 9, 2, "FLOAT");
connect(3, 0, 10, 0, "CLIP");
connect(3, 0, 11, 0, "CLIP");
connect(3, 0, 12, 0, "CLIP");
connect(8, 0, 14, 0, "MODEL");
connect(10, 0, 14, 1, "CONDITIONING");
connect(12, 0, 14, 2, "CONDITIONING");
connect(13, 0, 14, 3, "LATENT");
connect(14, 0, 15, 0, "LATENT");
connect(4, 0, 15, 1, "VAE");
connect(15, 0, 16, 0, "IMAGE");
connect(17, 1, 30, 0, "MASK");
connect(30, 0, 18, 0, "MASK");
connect(17, 0, 19, 0, "IMAGE");
connect(4, 0, 19, 1, "VAE");
connect(18, 0, 19, 2, "MASK");
connect(18, 0, 31, 0, "MASK");
connect(31, 0, 32, 0, "IMAGE");
connect(32, 0, 33, 0, "IMAGE");
connect(9, 0, 20, 0, "MODEL");
connect(11, 0, 20, 1, "CONDITIONING");
connect(12, 0, 20, 2, "CONDITIONING");
connect(19, 0, 20, 3, "LATENT");
connect(20, 0, 21, 0, "LATENT");
connect(4, 0, 21, 1, "VAE");
connect(17, 0, 22, 0, "IMAGE");
connect(21, 0, 22, 1, "IMAGE");
connect(33, 0, 22, 5, "MASK");
connect(23, 0, 24, 0, "UPSCALE_MODEL");
connect(22, 0, 24, 1, "IMAGE");
connect(24, 0, 25, 0, "IMAGE");
connect(25, 0, 26, 0, "IMAGE");
connect(4, 0, 26, 1, "VAE");
connect(5, 0, 27, 0, "MODEL");
connect(10, 0, 27, 1, "CONDITIONING");
connect(12, 0, 27, 2, "CONDITIONING");
connect(26, 0, 27, 3, "LATENT");
connect(27, 0, 28, 0, "LATENT");
connect(4, 0, 28, 1, "VAE");
connect(28, 0, 29, 0, "IMAGE");

function assignTopologicalOrder() {
    const incoming = new Map(nodes.map((node) => [node.id, 0]));
    const outgoing = new Map(nodes.map((node) => [node.id, []]));
    for (const link of links) {
        incoming.set(link[3], incoming.get(link[3]) + 1);
        outgoing.get(link[1]).push(link[3]);
    }

    const ready = nodes
        .filter((node) => incoming.get(node.id) === 0)
        .map((node) => node.id)
        .sort((a, b) => a - b);
    const ordered = [];
    while (ready.length) {
        const id = ready.shift();
        ordered.push(id);
        for (const target of outgoing.get(id)) {
            incoming.set(target, incoming.get(target) - 1);
            if (incoming.get(target) === 0) {
                ready.push(target);
                ready.sort((a, b) => a - b);
            }
        }
    }

    if (ordered.length !== nodes.length) {
        throw new Error("Workflow graph contains a cycle.");
    }
    ordered.forEach((id, order) => {
        nodes.find((node) => node.id === id).order = order;
    });
}

assignTopologicalOrder();
for (const node of nodes) {
    for (const output of node.outputs) {
        if (output.links.length === 0) output.links = null;
    }
}

const workflow = {
    id: "b78c3d95-ea63-4ce1-aeb8-6a78f209e46d",
    revision: 0,
    last_node_id: Math.max(...nodes.map((node) => node.id)),
    last_link_id: nextLinkId - 1,
    nodes,
    links,
    groups: [
        {
            id: 1,
            title: "1. Models, readable LoRA selectors, and prompts",
            bounding: [-980, -80, 1880, 1140],
            color: "#3f789e",
            font_size: 24,
            flags: {},
        },
        {
            id: 2,
            title: "2. Build the interaction with Character A LoRA",
            bounding: [940, -80, 1510, 600],
            color: "#7b65a8",
            font_size: 24,
            flags: {},
        },
        {
            id: 3,
            title: "3. Paint B in Mask Editor, then replace with Character B LoRA",
            bounding: [2490, -80, 1940, 730],
            color: "#a45d62",
            font_size: 24,
            flags: {},
        },
        {
            id: 4,
            title: "4. AnimeSharp and exact 1160x1536 Hires-fix",
            bounding: [4510, -80, 2750, 650],
            color: "#4f7f86",
            font_size: 24,
            flags: {},
        },
    ],
    config: {},
    extra: {
        ds: {
            scale: 0.56,
            offset: [1160, 300],
        },
        node_versions: {
            "comfy-core": "0.3.59",
            "ComfyUI-AnimaVariationBatch": "main",
        },
    },
    version: 0.4,
};

const outputPath = path.join(
    __dirname,
    "..",
    "example_workflows",
    "anima_two_character_inpaint_hiresfix.json"
);
fs.writeFileSync(outputPath, `${JSON.stringify(workflow, null, 2)}\n`);
