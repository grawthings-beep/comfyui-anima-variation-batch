const { app } = window.comfyAPI.app;

const PREVIEW_HEIGHT = 260;

function numberWidgetValue(node, name, fallback) {
    const widget = node.widgets?.find((item) => item.name === name);
    const value = Number(widget?.value);
    return Number.isFinite(value) ? value : fallback;
}

function clipped(value, low, high) {
    return Math.max(low, Math.min(high, value));
}

function hasWidget(node, name) {
    return Boolean(node.widgets?.some((item) => item.name === name));
}

class TwoCharacterLayoutWidget {
    constructor() {
        this.type = "custom";
        this.name = "_anima_two_character_layout";
        this.value = "";
        this.options = { serialize: false };
    }

    computeSize(width) {
        return [width, PREVIEW_HEIGHT];
    }

    serializeValue() {
        return undefined;
    }

    draw(ctx, node, width, posY, height) {
        const imageWidth = Math.max(
            1,
            numberWidgetValue(node, "width", 832)
        );
        const imageHeight = Math.max(
            1,
            numberWidgetValue(node, "height", 1216)
        );
        const availableWidth = Math.max(120, width - 28);
        const availableHeight = Math.max(120, height - 20);
        const scale = Math.min(
            availableWidth / imageWidth,
            availableHeight / imageHeight
        );
        const previewWidth = imageWidth * scale;
        const previewHeight = imageHeight * scale;
        const x = (width - previewWidth) / 2;
        const y = posY + (height - previewHeight) / 2;

        const feather = numberWidgetValue(node, "feather_pct", 6);
        let regions;
        if (hasWidget(node, "character_a_x_pct")) {
            regions = [
                {
                    centerX: numberWidgetValue(
                        node,
                        "character_a_x_pct",
                        26
                    ),
                    centerY: numberWidgetValue(
                        node,
                        "character_a_y_pct",
                        50
                    ),
                    width: numberWidgetValue(
                        node,
                        "character_a_width_pct",
                        48
                    ),
                    height: numberWidgetValue(
                        node,
                        "character_a_height_pct",
                        96
                    ),
                },
                {
                    centerX: numberWidgetValue(
                        node,
                        "character_b_x_pct",
                        74
                    ),
                    centerY: numberWidgetValue(
                        node,
                        "character_b_y_pct",
                        50
                    ),
                    width: numberWidgetValue(
                        node,
                        "character_b_width_pct",
                        48
                    ),
                    height: numberWidgetValue(
                        node,
                        "character_b_height_pct",
                        96
                    ),
                },
            ];
        } else {
            const topValue = numberWidgetValue(node, "top_pct", 2);
            const bottomValue = numberWidgetValue(node, "bottom_pct", 98);
            const top = Math.min(topValue, bottomValue);
            const bottom = Math.max(topValue, bottomValue);
            const centerY = (top + bottom) / 2;
            const regionHeight = bottom - top;
            const regionWidth = numberWidgetValue(
                node,
                "region_width_pct",
                48
            );
            regions = [
                {
                    centerX: numberWidgetValue(
                        node,
                        "left_center_pct",
                        26
                    ),
                    centerY,
                    width: regionWidth,
                    height: regionHeight,
                },
                {
                    centerX: numberWidgetValue(
                        node,
                        "right_center_pct",
                        74
                    ),
                    centerY,
                    width: regionWidth,
                    height: regionHeight,
                },
            ];
        }

        ctx.save();
        ctx.fillStyle = "#111820";
        ctx.strokeStyle = "#687784";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.rect(x, y, previewWidth, previewHeight);
        ctx.fill();
        ctx.stroke();
        ctx.clip();

        const drawRegion = (region, color, label) => {
            const hardLeft = region.centerX - region.width / 2;
            const hardRight = region.centerX + region.width / 2;
            const hardTop = region.centerY - region.height / 2;
            const hardBottom = region.centerY + region.height / 2;
            const outerLeft = hardLeft - feather;
            const outerRight = hardRight + feather;
            const outerTop = hardTop - feather;
            const outerBottom = hardBottom + feather;
            const outerX = x + (outerLeft / 100) * previewWidth;
            const outerY = y + (outerTop / 100) * previewHeight;
            const outerW = ((outerRight - outerLeft) / 100) * previewWidth;
            const outerH = ((outerBottom - outerTop) / 100) * previewHeight;
            const hardX = x + (hardLeft / 100) * previewWidth;
            const hardY = y + (hardTop / 100) * previewHeight;
            const hardW = ((hardRight - hardLeft) / 100) * previewWidth;
            const hardH = ((hardBottom - hardTop) / 100) * previewHeight;

            ctx.fillStyle = `${color}24`;
            ctx.fillRect(outerX, outerY, outerW, outerH);
            ctx.fillStyle = `${color}48`;
            ctx.fillRect(hardX, hardY, hardW, hardH);
            ctx.strokeStyle = `${color}d8`;
            ctx.lineWidth = 2;
            ctx.strokeRect(hardX, hardY, hardW, hardH);

            const labelX = clipped(
                x + (region.centerX / 100) * previewWidth,
                x + 18,
                x + previewWidth - 18
            );
            const labelY = clipped(
                y + (region.centerY / 100) * previewHeight,
                y + 18,
                y + previewHeight - 18
            );

            ctx.fillStyle = `${color}e8`;
            ctx.beginPath();
            ctx.arc(labelX, labelY, 15, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 1.5;
            ctx.stroke();

            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 16px sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(label, labelX, labelY);
        };

        drawRegion(regions[0], "#f27052", "A");
        drawRegion(regions[1], "#42a9dc", "B");

        ctx.restore();
    }
}

app.registerExtension({
    name: "AnimaVariationBatch.TwoCharacterLayout",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (
            nodeData.name !== "AnimaTwoCharacterMasks"
            && nodeData.name !== "AnimaTwoCharacterFreeMasks"
        ) {
            return;
        }

        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            originalOnNodeCreated?.apply(this, arguments);
            if (this._animaTwoCharacterLayoutInstalled) {
                return;
            }
            this._animaTwoCharacterLayoutInstalled = true;

            const preview = new TwoCharacterLayoutWidget();
            this.addCustomWidget(preview);
            const computed = this.computeSize();
            this.setSize([
                Math.max(420, this.size[0], computed[0]),
                Math.max(this.size[1], computed[1]),
            ]);
            this.setDirtyCanvas(true, true);
        };
    },
});
