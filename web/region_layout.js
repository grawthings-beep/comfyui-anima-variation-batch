import { createRegionEditor } from "./region_editor.js";
import { preset } from "./region_geometry.js";

const { app } = window.comfyAPI.app;
app.registerExtension({
    name: "AnimaVariationBatch.RegionLayout",
    beforeRegisterNodeDef(_nodeType, nodeData) {
        if (nodeData.name === "AnimaRegionLayout") nodeData.input.required.layout[0] = "ANIMA_REGION_LAYOUT";
    },
    getCustomWidgets() {
        return { ANIMA_REGION_LAYOUT(node, inputName, inputData) {
            let value = inputData[1]?.default ?? JSON.stringify(preset("2 columns"));
            const width = node.widgets.find((w) => w.name === "width");
            const height = node.widgets.find((w) => w.name === "height");
            const editor = createRegionEditor({
                getState: () => ({ width: width.value, height: height.value, layout: value }),
                setState(state) {
                    node.graph?.beforeChange?.();
                    width.value = state.width; height.value = state.height; value = JSON.stringify(state.layout);
                    node.graph?.afterChange?.(); node.setDirtyCanvas(true, true);
                },
            });
            const widget = node.addDOMWidget(inputName, "ANIMA_REGION_LAYOUT", editor.element, {
                serialize: true, getValue: () => value,
                setValue(v) { value = v; editor.refresh(); },
                getMinHeight: () => 600, getMaxHeight: () => 600, hideOnZoom: false,
            });
            widget.serializeValue = () => value;
            for (const control of [width, height]) {
                const previous = control.callback;
                control.callback = function () { previous?.apply(this, arguments); editor.refresh(); };
            }
            const previousConfigure = node.onConfigure;
            node.onConfigure = function () { previousConfigure?.apply(this, arguments); editor.refresh(); };
            const previousRemoved = node.onRemoved;
            node.onRemoved = function () { editor.dispose(); previousRemoved?.apply(this, arguments); };
            node._animaRegionEditor = editor;
            return { widget, minWidth: 520, minHeight: 720 };
        } };
    },
    nodeCreated(node) {
        if (node.comfyClass === "AnimaRegionLayout") node.setSize([Math.max(node.size[0], 560), Math.max(node.size[1], 820)]);
    },
    afterConfigureGraph() {
        for (const node of app.graph?._nodes ?? []) node._animaRegionEditor?.refresh();
    },
});
