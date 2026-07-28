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

        const leftCenter = numberWidgetValue(
            node,
            "left_center_pct",
            26
        );
        const rightCenter = numberWidgetValue(
            node,
            "right_center_pct",
            74
        );
        const regionWidth = numberWidgetValue(
            node,
            "region_width_pct",
            48
        );
        const feather = numberWidgetValue(node, "feather_pct", 6);
        const top = numberWidgetValue(node, "top_pct", 2);
        const bottom = numberWidgetValue(node, "bottom_pct", 98);

        ctx.save();
        ctx.fillStyle = "#111820";
        ctx.strokeStyle = "#687784";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.rect(x, y, previewWidth, previewHeight);
        ctx.fill();
        ctx.stroke();
        ctx.clip();

        const drawRegion = (center, color, label) => {
            const hardLeft = center - regionWidth / 2;
            const hardRight = center + regionWidth / 2;
            const outerLeft = hardLeft - feather;
            const outerRight = hardRight + feather;
            const outerX = x + (outerLeft / 100) * previewWidth;
            const outerY = y + ((top - feather) / 100) * previewHeight;
            const outerW = ((outerRight - outerLeft) / 100) * previewWidth;
            const outerH =
                ((bottom - top + feather * 2) / 100) * previewHeight;
            const hardX = x + (hardLeft / 100) * previewWidth;
            const hardY = y + (top / 100) * previewHeight;
            const hardW = ((hardRight - hardLeft) / 100) * previewWidth;
            const hardH = ((bottom - top) / 100) * previewHeight;

            ctx.fillStyle = `${color}24`;
            ctx.fillRect(outerX, outerY, outerW, outerH);
            ctx.fillStyle = `${color}48`;
            ctx.fillRect(hardX, hardY, hardW, hardH);
            ctx.strokeStyle = `${color}d8`;
            ctx.lineWidth = 2;
            ctx.strokeRect(hardX, hardY, hardW, hardH);

            const labelX = clipped(
                x + (center / 100) * previewWidth,
                x + 18,
                x + previewWidth - 18
            );
            const labelY = clipped(hardY + 22, y + 22, y + previewHeight - 8);
            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 16px sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(label, labelX, labelY);
        };

        drawRegion(leftCenter, "#f27052", "A");
        drawRegion(rightCenter, "#42a9dc", "B");

        ctx.restore();
    }
}

app.registerExtension({
    name: "AnimaVariationBatch.TwoCharacterLayout",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "AnimaTwoCharacterMasks") {
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
