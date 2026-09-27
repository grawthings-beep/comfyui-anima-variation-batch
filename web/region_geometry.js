export const OWNERS = ["A", "B", "C", "D"];
export const COLORS = ["#41b99b", "#e786a3", "#dcb95f", "#76a9e0"];
export const PRESETS = {
    "2 columns": [2, 1], "2 rows": [1, 2],
    "3 columns": [3, 1], "3 rows": [1, 3],
    "4 columns": [4, 1], "4 rows": [1, 4], "2 x 2": [2, 2],
};
export const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

export function preset(name, previous = {}) {
    const [columns, rows] = PRESETS[name];
    return { version: 1, overlap: previous.overlap ?? 0.04, feather: previous.feather ?? 0.04,
        regions: Array.from({ length: columns * rows }, (_, i) => ({
            id: `r${i + 1}`, owner: OWNERS[i], x: (i % columns) / columns,
            y: Math.floor(i / columns) / rows, w: 1 / columns, h: 1 / rows, enabled: true,
        })) };
}

export function normalizeLayout(value) {
    const data = typeof value === "string" ? JSON.parse(value) : value;
    if (!data || data.version !== 1 || !Array.isArray(data.regions) || data.regions.length > 8) {
        throw new Error("Invalid region layout");
    }
    const number = (v, min, max) => {
        if (typeof v !== "number" || !Number.isFinite(v)) throw new Error("Invalid region coordinate");
        return clamp(v, min, max);
    };
    const ids = new Set();
    return { version: 1, overlap: number(data.overlap ?? 0.04, 0, 0.2),
        feather: number(data.feather ?? 0.04, 0, 0.2),
        regions: data.regions.map((r, i) => {
            if (!r || !OWNERS.includes(r.owner)) throw new Error("Invalid character assignment");
            const id = String(r.id ?? `r${i + 1}`);
            if (ids.has(id)) throw new Error("Duplicate region ID");
            ids.add(id);
            const x = number(r.x, 0, 0.98), y = number(r.y, 0, 0.98);
            if (r.enabled !== undefined && typeof r.enabled !== "boolean") throw new Error("Invalid region state");
            return { id, owner: r.owner, x, y, w: number(r.w, 0.02, 1 - x),
                h: number(r.h, 0.02, 1 - y), enabled: r.enabled ?? true };
        }) };
}

export function transform(layout, id, handle, dx, dy) {
    const result = structuredClone(layout);
    const original = layout.regions.find((r) => r.id === id);
    const r = result.regions.find((item) => item.id === id);
    if (!r) return result;
    if (handle === "move") {
        r.x = clamp(r.x + dx, 0, 1 - r.w);
        r.y = clamp(r.y + dy, 0, 1 - r.h);
    } else {
        if (handle.includes("w")) { r.x = clamp(original.x + dx, 0, original.x + original.w - 0.02); r.w = original.x + original.w - r.x; }
        if (handle.includes("e")) r.w = clamp(original.w + dx, 0.02, 1 - original.x);
        if (handle.includes("n")) { r.y = clamp(original.y + dy, 0, original.y + original.h - 0.02); r.h = original.y + original.h - r.y; }
        if (handle.includes("s")) r.h = clamp(original.h + dy, 0.02, 1 - original.y);
        // Keep matching preset neighbours attached while a shared edge moves.
        const close = (a, b) => Math.abs(a - b) < 1e-6;
        for (const other of result.regions) {
            if (other.id === id) continue;
            if (close(other.y, original.y) && close(other.h, original.h)) {
                if (handle === "e" && close(other.x, original.x + original.w)) {
                    const end = other.x + other.w;
                    r.w = Math.min(r.w, end - original.x - 0.02);
                    other.x = r.x + r.w; other.w = end - other.x;
                }
                if (handle === "w" && close(other.x + other.w, original.x)) {
                    r.x = Math.max(r.x, other.x + 0.02); r.w = original.x + original.w - r.x;
                    other.w = r.x - other.x;
                }
            }
            if (close(other.x, original.x) && close(other.w, original.w)) {
                if (handle === "s" && close(other.y, original.y + original.h)) {
                    const end = other.y + other.h;
                    r.h = Math.min(r.h, end - original.y - 0.02);
                    other.y = r.y + r.h; other.h = end - other.y;
                }
                if (handle === "n" && close(other.y + other.h, original.y)) {
                    r.y = Math.max(r.y, other.y + 0.02); r.h = original.y + original.h - r.y;
                    other.h = r.y - other.y;
                }
            }
        }
    }
    return normalizeLayout(result);
}

export function bounds(region, layout, width, height) {
    const margin = layout.overlap * Math.min(width, height) / 2;
    return [Math.max(0, region.x * width - margin), Math.max(0, region.y * height - margin),
        Math.min(width, (region.x + region.w) * width + margin), Math.min(height, (region.y + region.h) * height + margin)];
}

export function weightAt(region, layout, x, y, width, height) {
    if (!region.enabled) return 0;
    const [left, top, right, bottom] = bounds(region, layout, width, height);
    if (x < left || x >= right || y < top || y >= bottom) return 0;
    const feather = layout.feather * Math.min(width, height);
    if (!feather) return 1;
    return (left > 0 ? clamp((x - left) / feather, 0, 1) : 1)
        * (right < width ? clamp((right - x) / feather, 0, 1) : 1)
        * (top > 0 ? clamp((y - top) / feather, 0, 1) : 1)
        * (bottom < height ? clamp((bottom - y) / feather, 0, 1) : 1);
}

export function resolution(ratio, edge) {
    const [w, h] = ratio.split(":").map(Number);
    return { width: Math.max(64, Math.round(edge * w / Math.max(w, h) / 8) * 8),
        height: Math.max(64, Math.round(edge * h / Math.max(w, h) / 8) * 8) };
}
