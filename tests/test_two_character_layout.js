const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

let extension;
global.window = {
    comfyAPI: {
        app: {
            app: {
                registerExtension(value) {
                    extension = value;
                },
            },
        },
    },
};

const scriptPath = path.join(
    __dirname,
    "..",
    "web",
    "two_character_layout.js"
);
vm.runInThisContext(fs.readFileSync(scriptPath, "utf8"), {
    filename: scriptPath,
});

function LayoutNode() {}

extension.beforeRegisterNodeDef(LayoutNode, {
    name: "AnimaTwoCharacterMasks",
});

const node = new LayoutNode();
node.widgets = [
    { name: "width", value: 832 },
    { name: "height", value: 1216 },
    { name: "left_center_pct", value: 26 },
    { name: "right_center_pct", value: 74 },
    { name: "region_width_pct", value: 48 },
    { name: "top_pct", value: 2 },
    { name: "bottom_pct", value: 98 },
    { name: "feather_pct", value: 6 },
];
node.size = [430, 570];
node.computeSize = () => [430, 570];
node.setSize = (size) => {
    node.size = size;
};
node.setDirtyCanvas = () => {};
node.addCustomWidget = (widget) => {
    node.layoutWidget = widget;
};
node.onNodeCreated();

function drawLayout() {
    const arcs = [];
    const labels = [];
    const ctx = {
        save() {},
        restore() {},
        beginPath() {},
        rect() {},
        fill() {},
        stroke() {},
        clip() {},
        fillRect() {},
        strokeRect() {},
        arc(x, y, radius) {
            arcs.push({ x, y, radius });
        },
        fillText(label, x, y) {
            labels.push({ label, x, y });
        },
    };
    node.layoutWidget.draw(ctx, node, 430, 0, 260);
    return { arcs, labels };
}

let result = drawLayout();
assert.deepEqual(
    result.labels.map((item) => item.label),
    ["A", "B"]
);
assert.equal(result.arcs.length, 2);
assert.ok(result.arcs[0].x < result.arcs[1].x);
assert.ok(Math.abs(result.arcs[0].y - 130) < 0.01);
assert.ok(Math.abs(result.arcs[1].y - 130) < 0.01);

node.widgets.find((item) => item.name === "top_pct").value = 90;
node.widgets.find((item) => item.name === "bottom_pct").value = 10;
result = drawLayout();
assert.ok(Math.abs(result.arcs[0].y - 130) < 0.01);
assert.ok(Math.abs(result.arcs[1].y - 130) < 0.01);

console.log("two-character layout preview ok");
