import test from "node:test";
import assert from "node:assert/strict";
import { preset, normalizeLayout, transform, resolution, weightAt } from "../web/region_geometry.js";

test("presets cover the canvas and survive save/load", () => {
    for (const name of ["2 columns", "2 rows", "3 columns", "3 rows", "4 columns", "4 rows", "2 x 2"]) {
        const layout = preset(name);
        assert.deepEqual(normalizeLayout(JSON.stringify(layout)), layout);
        assert.ok(Math.abs(layout.regions.reduce((s, r) => s + r.w*r.h, 0) - 1) < 1e-6);
        for (const [w,h] of [[128,192],[192,128]]) {
            const sum = layout.regions.reduce((s, r) => s + weightAt(r, layout, w/2, h/2, w, h), 0);
            assert.ok(Math.abs(sum - 1) < 1e-6);
        }
    }
});
test("shared edge resize moves its neighbour", () => {
    const result = transform(preset("2 columns"), "r1", "e", .1, 0);
    assert.equal(result.regions[0].w, .6);
    assert.equal(result.regions[1].x, .6);
    assert.equal(result.regions[1].w, .4);
    const rows = transform(preset("2 rows"), "r1", "s", 0, .1);
    assert.equal(rows.regions[1].y, .6);
});
test("movement is bounded and aspect ratio never changes coordinates", () => {
    const layout = preset("2 x 2");
    const moved = transform(layout, "r1", "move", 5, -5);
    assert.deepEqual([moved.regions[0].x,moved.regions[0].y], [.5,0]);
    assert.deepEqual(resolution("4:3",1536),{width:1536,height:1152});
    assert.deepEqual(resolution("3:4",1536),{width:1152,height:1536});
    assert.deepEqual(layout, preset("2 x 2"));
});
test("disabled regions and validation", () => {
    const layout = preset("2 columns"); layout.regions[0].enabled = false;
    assert.equal(weightAt(layout.regions[0],layout,0,0,128,192),0);
    assert.throws(() => normalizeLayout({ version:1, regions:[{}] }));
    assert.throws(() => normalizeLayout({ ...layout, feather:NaN }));
});
