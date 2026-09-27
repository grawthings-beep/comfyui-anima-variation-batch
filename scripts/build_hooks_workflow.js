const fs = require("node:fs");
const path = require("node:path");

const destination = path.join(
    __dirname, "..", "example_workflows", "anima_two_character_hooks_hiresfix.json",
);

function buildWorkflow() {
    const nodes = [];
    const links = [];
    const socket = (name, type = name) => ({ name, type });
    const converted = (name, type) => ({ name, type, widget: { name } });
    const pairOutputs = [socket("positive", "CONDITIONING"), socket("negative", "CONDITIONING")];
    const samplerInputs = [
        socket("model", "MODEL"), socket("positive", "CONDITIONING"),
        socket("negative", "CONDITIONING"), socket("latent_image", "LATENT"),
    ];

    function add(id, type, title, pos, size, widgets = [], inputs = [], outputs = [], extra = {}) {
        const node = {
            id, type, title, pos, size, flags: {}, order: 0, mode: 0,
            inputs: inputs.map((input) => ({ ...input, link: null })),
            outputs: outputs.map((output) => ({ ...output, links: [] })),
            properties: { "Node name for S&R": type, cnr_id: "comfy-core" },
            widgets_values: widgets,
            ...extra,
        };
        nodes.push(node);
        return node;
    }

    function connect(sourceId, sourceSlot, targetId, targetSlot) {
        const source = nodes.find((node) => node.id === sourceId);
        const target = nodes.find((node) => node.id === targetId);
        const output = source.outputs[sourceSlot];
        const input = target.inputs[targetSlot];
        if (output.type !== input.type || input.link !== null) {
            throw new Error(`Invalid connection: ${sourceId}:${sourceSlot} -> ${targetId}:${targetSlot}`);
        }
        const id = links.length + 1;
        output.links.push(id);
        input.link = id;
        links.push([id, sourceId, sourceSlot, targetId, targetSlot, output.type]);
    }

    add(1, "UNETLoader", "WAI-ANIMA", [0, 0], [400, 85],
        ["waiANIMA_v10Base10.safetensors", "default"], [], [socket("MODEL")]);
    add(2, "CLIPLoader", "Qwen text encoder", [0, 135], [400, 110],
        ["qwen_3_06b_base.safetensors", "stable_diffusion", "default"], [], [socket("CLIP")]);
    add(3, "VAELoader", "Qwen Image VAE", [0, 300], [400, 60],
        ["qwen_image_vae.safetensors"], [], [socket("VAE")]);
    add(4, "PrimitiveStringMultiline", "Shared scene / interaction / light", [465, 0], [480, 300], [
        "masterpiece, best quality, score_8, highres, safe, exactly two adult women, full body, a gentle embrace, both faces visible, natural contact, coherent arms and hands, shared ground plane, a bright seaside terrace, soft daylight, consistent lighting and shadows, one continuous scene",
    ], [], [socket("STRING")]);
    add(5, "PrimitiveStringMultiline", "Shared negative", [465, 355], [480, 255], [
        "worst quality, low quality, early, old, score_1, score_2, score_3, cartoon, graphic, painting, crayon, graphite, abstract, glitch, deformed, mutated, ugly, disfigured, long body, bad anatomy, bad hands, missing fingers, extra fingers, extra digits, fewer digits, cropped, very displeasing, artist name, blurry, jpeg artifacts, lowres, censor",
    ], [], [socket("STRING")]);
    add(6, "SolidMask", "Region canvas", [0, 920], [400, 115],
        [0, 1152, 1536], [], [socket("MASK")]);
    add(7, "EmptyLatentImage", "Base resolution", [0, 750], [400, 115],
        [1152, 1536, 1], [], [socket("LATENT")]);
    add(8, "LoraLoaderModelOnly", "Global Turbo", [0, 410], [400, 115],
        ["anima-turbo-lora-v0.2.safetensors", 0.65],
        [socket("model", "MODEL")], [socket("MODEL")]);
    add(9, "LoraLoaderModelOnly", "Global Skin Texture", [0, 580], [400, 115],
        ["anima/Skin Texture Detail.safetensors", 0.4],
        [socket("model", "MODEL")], [socket("MODEL")]);
    connect(1, 0, 8, 0);
    connect(8, 0, 9, 0);

    const characters = [
        {
            id: 10, label: "A", y: 0, x: 0, feather: [0, 0, 48, 0],
            lora: "anima/Bikini Cinderella - Anima.safetensors",
            positive: "The woman on the left: bikinicinderella, black bikini. She embraces the woman on the right, with naturally connected arms and hands.",
            negative: "white outfit, dress",
            color: "#243c3b", bgcolor: "#345451",
        },
        {
            id: 30, label: "B", y: 940, x: 552, feather: [48, 0, 0, 0],
            lora: "anima/White Cinderella - Anima.safetensors",
            positive: "The woman on the right: whitecinderella, white outfit. She embraces the woman on the left, with naturally connected arms and hands.",
            negative: "black bikini, swimsuit",
            color: "#48313d", bgcolor: "#654758",
        },
    ];

    for (const character of characters) {
        const { id, label, y, color, bgcolor } = character;
        const tint = { color, bgcolor };
        add(id, "CreateHookLora", `${label} / LoRA`, [1040, y], [440, 145],
            [character.lora, 0.8, 0.0], [socket("prev_hooks", "HOOKS")], [socket("HOOKS")], tint);
        add(id + 1, "StringConcatenate", `${label} / positive`, [1040, y + 205], [440, 310],
            ["", character.positive, "\n\n"], [converted("string_a", "STRING")], [socket("STRING")], tint);
        add(id + 2, "StringConcatenate", `${label} / negative`, [1040, y + 575], [440, 230],
            ["", character.negative, ", "], [converted("string_a", "STRING")], [socket("STRING")], tint);
        add(id + 3, "CLIPTextEncode", `${label} / positive conditioning`, [1540, y + 205], [300, 135],
            [""], [socket("clip", "CLIP"), converted("text", "STRING")], [socket("CONDITIONING")], tint);
        add(id + 4, "CLIPTextEncode", `${label} / negative conditioning`, [1540, y + 575], [300, 135],
            [""], [socket("clip", "CLIP"), converted("text", "STRING")], [socket("CONDITIONING")], tint);
        add(id + 5, "SolidMask", `${label} / region size`, [1900, y], [310, 115],
            [1.0, 600, 1536], [], [socket("MASK")], tint);
        add(id + 6, "FeatherMask", `${label} / region feather`, [1900, y + 175], [310, 145],
            character.feather, [socket("mask", "MASK")], [socket("MASK")], tint);
        add(id + 7, "MaskComposite", `${label} / region position`, [1900, y + 380], [310, 145],
            [character.x, 0, "add"], [socket("destination", "MASK"), socket("source", "MASK")], [socket("MASK")], tint);
        add(id + 10, "MaskToImage", `${label} / mask image`, [1900, y + 590], [310, 85],
            [], [socket("mask", "MASK")], [socket("IMAGE")], tint);
        add(id + 8, "PreviewImage", `${label} / mask`, [2270, y + 290], [310, 510],
            [], [socket("images", "IMAGE")], [], tint);
        add(id + 9, "PairConditioningSetProperties", `${label} / regional LoRA pair`, [2270, y], [310, 220],
            [1.0, "default"], [
                socket("positive_NEW", "CONDITIONING"), socket("negative_NEW", "CONDITIONING"),
                socket("mask", "MASK"), socket("hooks", "HOOKS"), socket("timesteps", "TIMESTEPS_RANGE"),
            ], pairOutputs, tint);
        connect(4, 0, id + 1, 0);
        connect(5, 0, id + 2, 0);
        connect(2, 0, id + 3, 0);
        connect(id + 1, 0, id + 3, 1);
        connect(2, 0, id + 4, 0);
        connect(id + 2, 0, id + 4, 1);
        connect(id + 5, 0, id + 6, 0);
        connect(6, 0, id + 7, 0);
        connect(id + 6, 0, id + 7, 1);
        connect(id + 7, 0, id + 10, 0);
        connect(id + 10, 0, id + 8, 0);
        connect(id + 3, 0, id + 9, 0);
        connect(id + 4, 0, id + 9, 1);
        connect(id + 7, 0, id + 9, 2);
        connect(id, 0, id + 9, 3);
    }

    add(50, "CLIPTextEncode", "Shared fallback / positive", [465, 680], [480, 135],
        [""], [socket("clip", "CLIP"), converted("text", "STRING")], [socket("CONDITIONING")]);
    add(51, "CLIPTextEncode", "Shared fallback / negative", [465, 875], [480, 135],
        [""], [socket("clip", "CLIP"), converted("text", "STRING")], [socket("CONDITIONING")]);
    add(52, "PairConditioningCombine", "A + B", [2690, 0], [330, 150], [], [
        socket("positive_A", "CONDITIONING"), socket("negative_A", "CONDITIONING"),
        socket("positive_B", "CONDITIONING"), socket("negative_B", "CONDITIONING"),
    ], pairOutputs);
    add(53, "PairConditioningSetDefaultCombine", "A + B + uncovered background", [2690, 210], [330, 170], [], [
        socket("positive", "CONDITIONING"), socket("negative", "CONDITIONING"),
        socket("positive_DEFAULT", "CONDITIONING"), socket("negative_DEFAULT", "CONDITIONING"),
        socket("hooks", "HOOKS"),
    ], pairOutputs);
    add(54, "KSampler", "Joint A/B generation", [3090, 0], [330, 290],
        [2026092701, "fixed", 18, 1.0, "res_multistep", "sgm_uniform", 1.0], samplerInputs, [socket("LATENT")]);
    add(55, "VAEDecode", "Base decode", [3090, 355], [330, 80], [],
        [socket("samples", "LATENT"), socket("vae", "VAE")], [socket("IMAGE")]);
    add(56, "PreviewImage", "Base image", [3090, 500], [330, 510], [], [socket("images", "IMAGE")]);
    add(57, "LatentUpscaleBy", "Latent upscale 1.5x", [3490, 0], [350, 115],
        ["bislerp", 1.5], [socket("samples", "LATENT")], [socket("LATENT")]);
    add(61, "KSampler", "A/B regional Hires-fix", [3910, 0], [350, 290],
        [2026092702, "fixed", 8, 1.0, "res_multistep", "sgm_uniform", 0.55], samplerInputs, [socket("LATENT")]);
    add(62, "VAEDecode", "Final decode", [3910, 355], [350, 80], [],
        [socket("samples", "LATENT"), socket("vae", "VAE")], [socket("IMAGE")]);
    add(63, "SaveImage", "Final image", [3910, 500], [350, 540],
        ["Anima_two_character_hooks_hiresfix"], [socket("images", "IMAGE")]);

    for (const [source, slot, target, input] of [
        [2, 0, 50, 0], [4, 0, 50, 1], [2, 0, 51, 0], [5, 0, 51, 1],
        [19, 0, 52, 0], [19, 1, 52, 1], [39, 0, 52, 2], [39, 1, 52, 3],
        [52, 0, 53, 0], [52, 1, 53, 1], [50, 0, 53, 2], [51, 0, 53, 3],
        [9, 0, 54, 0], [53, 0, 54, 1], [53, 1, 54, 2], [7, 0, 54, 3],
        [54, 0, 55, 0], [3, 0, 55, 1], [55, 0, 56, 0],
        [54, 0, 57, 0],
        [9, 0, 61, 0], [53, 0, 61, 1], [53, 1, 61, 2], [57, 0, 61, 3],
        [61, 0, 62, 0], [3, 0, 62, 1], [62, 0, 63, 0],
    ]) connect(source, slot, target, input);

    // Stable topological order avoids importing stale execution orders after graph edits.
    const ordered = new Set();
    while (ordered.size < nodes.length) {
        const next = nodes.find((node) => !ordered.has(node.id) && links.every(
            (link) => link[3] !== node.id || ordered.has(link[1]),
        ));
        if (!next) throw new Error("Workflow contains a cycle");
        next.order = ordered.size;
        ordered.add(next.id);
    }
    return {
        id: "c0e92976-f0ce-4ce5-b21f-a3e01c29e844",
        revision: 1, last_node_id: 63, last_link_id: links.length,
        nodes, links,
        groups: [
            { title: "Shared models and scene", bounding: [-30, -80, 1005, 1180], color: "#344b5b", font_size: 24 },
            { title: "Character A", bounding: [1010, -80, 1600, 930], color: "#345451", font_size: 24 },
            { title: "Character B", bounding: [1010, 860, 1600, 930], color: "#654758", font_size: 24 },
            { title: "Joint generation", bounding: [2660, -80, 790, 1140], color: "#43505c", font_size: 24 },
            { title: "Regional Hires-fix", bounding: [3460, -80, 830, 1170], color: "#534b38", font_size: 24 },
        ],
        config: {}, extra: { ds: { scale: 0.65, offset: [80, 160] } }, version: 0.4,
    };
}

if (require.main === module) {
    const serialized = `${JSON.stringify(buildWorkflow(), null, 2)}\n`;
    if (process.argv.includes("--check")) {
        if (fs.readFileSync(destination, "utf8") !== serialized) {
            throw new Error("Generated workflow is stale; run node scripts/build_hooks_workflow.js");
        }
        console.log("Regional hooks workflow is up to date.");
    } else {
        fs.writeFileSync(destination, serialized);
        console.log(destination);
    }
}

module.exports = { buildWorkflow };
