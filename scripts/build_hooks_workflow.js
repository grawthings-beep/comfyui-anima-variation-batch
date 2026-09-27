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
    add(4, "PrimitiveStringMultiline", "Shared scene / interaction / light", [1130, 0], [500, 300], [
        "masterpiece, best quality, score_8, highres, safe, adult women, full body, natural interaction, coherent arms and hands, shared ground plane, a bright seaside terrace, soft daylight, consistent lighting and shadows, one continuous scene",
    ], [], [socket("STRING")]);
    add(5, "PrimitiveStringMultiline", "Shared negative", [1130, 355], [500, 255], [
        "worst quality, low quality, early, old, score_1, score_2, score_3, cartoon, graphic, painting, crayon, graphite, abstract, glitch, deformed, mutated, ugly, disfigured, long body, bad anatomy, bad hands, missing fingers, extra fingers, extra digits, fewer digits, cropped, very displeasing, artist name, blurry, jpeg artifacts, lowres, censor",
    ], [], [socket("STRING")]);
    const layout = { version: 1, overlap: 0.04, feather: 0.04, regions: [
        { id: "r1", owner: "A", x: 0, y: 0, w: 0.5, h: 1, enabled: true },
        { id: "r2", owner: "B", x: 0.5, y: 0, w: 0.5, h: 1, enabled: true },
    ] };
    const layoutNode = add(6, "AnimaRegionLayout", "Region layout", [500, 0], [560, 820],
        [1152, 1536, JSON.stringify(layout)], [], [
            ...["A", "B", "C", "D"].map((label) => socket(`mask_${label}`, "MASK")),
            socket("width", "INT"), socket("height", "INT"),
        ]);
    layoutNode.properties.cnr_id = "ComfyUI-AnimaVariationBatch";
    add(7, "EmptyLatentImage", "Linked base resolution", [1130, 1090], [500, 135],
        [1152, 1536, 1], [converted("width", "INT"), converted("height", "INT")], [socket("LATENT")]);
    connect(6, 4, 7, 0);
    connect(6, 5, 7, 1);
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
            id: 10, label: "A", x: 1690, y: 0,
            lora: "anima/Bikini Cinderella - Anima.safetensors",
            positive: "bikinicinderella, black bikini",
            negative: "white outfit, dress",
            color: "#243c3b", bgcolor: "#345451",
        },
        {
            id: 30, label: "B", x: 2310, y: 0,
            lora: "anima/White Cinderella - Anima.safetensors",
            positive: "whitecinderella, white outfit",
            negative: "black bikini, swimsuit",
            color: "#48313d", bgcolor: "#654758",
        },
        { id: 40, label: "C", x: 1690, y: 740, lora: "(none)", positive: "", negative: "", color: "#433e2a", bgcolor: "#5f583c" },
        { id: 41, label: "D", x: 2310, y: 740, lora: "(none)", positive: "", negative: "", color: "#2d3d4b", bgcolor: "#40576a" },
    ];

    for (const [index, character] of characters.entries()) {
        const { id, label, x, y, color, bgcolor } = character;
        const tint = { color, bgcolor };
        const node = add(id, "AnimaRegionalCharacter", `Character ${label}`, [x, y], [560, 650],
            [character.lora, 0.8, character.positive, character.negative], [
                socket("clip", "CLIP"), socket("mask", "MASK"),
                socket("shared_positive", "STRING"), socket("shared_negative", "STRING"),
            ], pairOutputs, tint);
        node.properties.cnr_id = "ComfyUI-AnimaVariationBatch";
        connect(2, 0, id, 0); connect(6, index, id, 1);
        connect(4, 0, id, 2); connect(5, 0, id, 3);
    }

    add(50, "CLIPTextEncode", "Shared fallback / positive", [1130, 680], [500, 135],
        [""], [socket("clip", "CLIP"), converted("text", "STRING")], [socket("CONDITIONING")]);
    add(51, "CLIPTextEncode", "Shared fallback / negative", [1130, 875], [500, 135],
        [""], [socket("clip", "CLIP"), converted("text", "STRING")], [socket("CONDITIONING")]);
    const combineInputs = [
        socket("positive_A", "CONDITIONING"), socket("negative_A", "CONDITIONING"),
        socket("positive_B", "CONDITIONING"), socket("negative_B", "CONDITIONING"),
    ];
    add(52, "PairConditioningCombine", "A + B", [2950, 0], [330, 150], [], combineInputs, pairOutputs);
    add(58, "PairConditioningCombine", "C + D", [2950, 220], [330, 150], [], combineInputs, pairOutputs);
    add(59, "PairConditioningCombine", "A + B + C + D", [2950, 440], [330, 150], [], combineInputs, pairOutputs);
    add(53, "PairConditioningSetDefaultCombine", "Regions + uncovered background", [2950, 660], [330, 170], [], [
        socket("positive", "CONDITIONING"), socket("negative", "CONDITIONING"),
        socket("positive_DEFAULT", "CONDITIONING"), socket("negative_DEFAULT", "CONDITIONING"),
        socket("hooks", "HOOKS"),
    ], pairOutputs);
    add(54, "KSampler", "Joint generation", [3360, 0], [330, 290],
        [2026092701, "fixed", 18, 1.0, "res_multistep", "sgm_uniform", 1.0], samplerInputs, [socket("LATENT")]);
    add(55, "VAEDecode", "Base decode", [3360, 355], [330, 80], [],
        [socket("samples", "LATENT"), socket("vae", "VAE")], [socket("IMAGE")]);
    add(56, "PreviewImage", "Base image", [3360, 500], [330, 510], [], [socket("images", "IMAGE")]);
    add(57, "LatentUpscaleBy", "Latent upscale 1.5x", [3760, 0], [350, 115],
        ["bislerp", 1.5], [socket("samples", "LATENT")], [socket("LATENT")]);
    add(61, "KSampler", "Regional Hires-fix", [4180, 0], [350, 290],
        [2026092702, "fixed", 8, 1.0, "res_multistep", "sgm_uniform", 0.55], samplerInputs, [socket("LATENT")]);
    add(62, "VAEDecode", "Final decode", [4180, 355], [350, 80], [],
        [socket("samples", "LATENT"), socket("vae", "VAE")], [socket("IMAGE")]);
    add(63, "SaveImage", "Final image", [4180, 500], [350, 540],
        ["Anima_two_character_hooks_hiresfix"], [socket("images", "IMAGE")]);

    for (const [source, slot, target, input] of [
        [2, 0, 50, 0], [4, 0, 50, 1], [2, 0, 51, 0], [5, 0, 51, 1],
        [10, 0, 52, 0], [10, 1, 52, 1], [30, 0, 52, 2], [30, 1, 52, 3],
        [40, 0, 58, 0], [40, 1, 58, 1], [41, 0, 58, 2], [41, 1, 58, 3],
        [52, 0, 59, 0], [52, 1, 59, 1], [58, 0, 59, 2], [58, 1, 59, 3],
        [59, 0, 53, 0], [59, 1, 53, 1], [50, 0, 53, 2], [51, 0, 53, 3],
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
        revision: 2, last_node_id: 63, last_link_id: links.length,
        nodes, links,
        groups: [
            { title: "Models", bounding: [-30, -80, 460, 820], color: "#344b5b", font_size: 24 },
            { title: "Layout", bounding: [470, -80, 620, 940], color: "#345451", font_size: 24 },
            { title: "Shared scene", bounding: [1100, -80, 560, 1350], color: "#43505c", font_size: 24 },
            { title: "Characters", bounding: [1660, -80, 1240, 1520], color: "#654758", font_size: 24 },
            { title: "Joint generation", bounding: [2920, -80, 800, 1140], color: "#43505c", font_size: 24 },
            { title: "Regional Hires-fix", bounding: [3730, -80, 830, 1170], color: "#534b38", font_size: 24 },
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
