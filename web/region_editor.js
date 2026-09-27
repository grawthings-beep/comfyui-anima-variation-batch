import { OWNERS, COLORS, PRESETS, preset, normalizeLayout, transform, weightAt, resolution } from "./region_geometry.js";

export function createRegionEditor({ getState, setState }) {
    const element = document.createElement("div");
    const shadow = element.attachShadow({ mode: "open" });
    shadow.innerHTML = `<style>
        :host{display:block;min-width:0;height:600px;color:#eee;font:12px system-ui;letter-spacing:0}
        *{box-sizing:border-box} .panel{height:100%;padding:8px;background:#242426;display:flex;flex-direction:column;gap:9px}
        .row{display:flex;align-items:center;gap:6px;flex-wrap:wrap;min-width:0}
        label{display:flex;align-items:center;gap:6px;min-width:0} select{min-width:0;flex:1}
        select,button{height:32px;background:#363639;border:1px solid #626267;border-radius:4px;color:inherit;font:inherit}
        button{min-width:32px;padding:0 8px;cursor:pointer} button:hover{background:#4a4a4f}button:disabled{opacity:.4;cursor:default}
        button[aria-pressed=true]{outline:2px solid #fff;outline-offset:-3px}
        input[type=range]{min-width:50px;flex:1;accent-color:#57bca7} input[type=checkbox]{accent-color:#57bca7}
        .board{flex:1;min-height:220px;display:grid;place-items:center;background:#171719;overflow:hidden;border:1px solid #505055}
        canvas{display:block;touch-action:none;outline:none;max-width:100%;max-height:100%}
        canvas:focus{outline:2px solid #aaa;outline-offset:-2px}
        .sliders label{display:flex;width:100%}.sliders span{width:58px}.sliders output{width:40px;text-align:right;font-variant-numeric:tabular-nums}
        .dimensions{margin-left:auto;font-variant-numeric:tabular-nums;color:#ccc}.error{color:#ff9b9b;min-height:15px}
        .swatch{width:12px;height:12px;border-radius:2px}.assignment{flex:1}.assignment select{max-width:80px}
    </style><div class="panel">
        <div class="row"><select aria-label="Layout preset"><option value="">Custom</option></select>
            <button type="button" title="Undo" aria-label="Undo">&#8630;</button><button type="button" title="Redo" aria-label="Redo">&#8631;</button>
            <button type="button" title="Add region" aria-label="Add region">+</button><button type="button" title="Delete region" aria-label="Delete region">&#215;</button></div>
        <div class="row"><select aria-label="Aspect ratio"><option value="">Custom ratio</option></select>
            <select aria-label="Long edge"><option value="">Custom size</option><option>1024</option><option>1536</option><option>2048</option><option>3072</option></select>
            <output class="dimensions"></output></div>
        <div class="row regions" role="group" aria-label="Regions"></div>
        <div class="board"><canvas tabindex="0" aria-label="Region layout canvas"></canvas></div>
        <div class="row"><label class="assignment"><span class="swatch"></span>Character <select aria-label="Character"></select></label>
            <label><input type="checkbox" aria-label="Region enabled">Enabled</label></div>
        <div class="sliders"><label><span>Overlap</span><input aria-label="Overlap" type="range" min="0" max="0.2" step="0.005"><output></output></label>
            <label><span>Feather</span><input aria-label="Feather" type="range" min="0" max="0.2" step="0.005"><output></output></label></div>
        <output class="error" role="alert"></output>
    </div>`;
    const query = (label) => shadow.querySelector(`[aria-label="${label}"]`);
    const canvas = query("Region layout canvas"), board = shadow.querySelector(".board");
    const presets = query("Layout preset"), ratio = query("Aspect ratio"), edge = query("Long edge");
    const owner = query("Character"), enabled = query("Region enabled");
    const overlap = query("Overlap"), feather = query("Feather");
    const undo = query("Undo"), redo = query("Redo"), add = query("Add region"), remove = query("Delete region");
    for (const name of Object.keys(PRESETS)) presets.add(new Option(name, name));
    for (const name of ["3:4", "4:3", "1:1", "2:3", "3:2", "9:16", "16:9"]) ratio.add(new Option(name, name));
    for (const name of OWNERS) owner.add(new Option(name, name));
    let selected = null, drag = null, history = [], future = [], frame = null, disposed = false;
    const read = () => { const s = getState(); return { ...s, layout: normalizeLayout(s.layout) }; };
    const snapshot = () => structuredClone(read());
    const remember = () => { history.push(snapshot()); if (history.length > 40) history.shift(); future = []; };
    const write = (state) => { setState({ ...state, layout: normalizeLayout(state.layout) }); refresh(); };
    const change = (callback) => { remember(); const state = snapshot(); callback(state); write(state); };
    const option = () => read().layout.regions.find((r) => r.id === selected);

    presets.onchange = () => { if (presets.value) change((s) => { s.layout = preset(presets.value, s.layout); selected = s.layout.regions[0].id; }); };
    function resize() {
        change((s) => Object.assign(s, resolution(ratio.value || `${s.width}:${s.height}`, Number(edge.value) || Math.max(s.width, s.height))));
    }
    ratio.onchange = resize; edge.onchange = resize;
    undo.onclick = () => { if (history.length) { future.push(snapshot()); write(history.pop()); } };
    redo.onclick = () => { if (future.length) { history.push(snapshot()); write(future.pop()); } };
    add.onclick = () => change((s) => {
        if (s.layout.regions.length >= 8) return;
        const used = new Set(s.layout.regions.map((r) => r.id));
        let i = 1; while (used.has(`r${i}`)) i++;
        const owners = s.layout.regions.filter((r) => r.enabled).map((r) => r.owner);
        selected = `r${i}`;
        s.layout.regions.push({ id: selected, owner: OWNERS.find((o) => !owners.includes(o)) ?? "A", x: .25, y: .25, w: .5, h: .5, enabled: true });
    });
    remove.onclick = () => { if (option()) change((s) => { s.layout.regions = s.layout.regions.filter((r) => r.id !== selected); selected = null; }); };
    owner.onchange = () => change((s) => { s.layout.regions.find((r) => r.id === selected).owner = owner.value; });
    enabled.onchange = () => change((s) => { s.layout.regions.find((r) => r.id === selected).enabled = enabled.checked; });
    for (const [control, key] of [[overlap, "overlap"], [feather, "feather"]]) {
        control.onpointerdown = remember;
        control.onkeydown = (e) => { if (e.key.startsWith("Arrow")) remember(); };
        control.oninput = () => { const s = snapshot(); s.layout[key] = Number(control.value); write(s); };
    }

    function point(event) {
        const b = canvas.getBoundingClientRect();
        return { x: (event.clientX - b.left) / b.width, y: (event.clientY - b.top) / b.height };
    }
    function hit(p) {
        const s = read(), b = canvas.getBoundingClientRect();
        const tx = 12 / b.width, ty = 12 / b.height;
        const current = s.layout.regions.find((r) => r.id === selected);
        if (current && p.x >= current.x - tx && p.x <= current.x + current.w + tx && p.y >= current.y - ty && p.y <= current.y + current.h + ty) {
            let h = "";
            if (Math.abs(p.y - current.y) < ty) h += "n";
            else if (Math.abs(p.y - current.y - current.h) < ty) h += "s";
            if (Math.abs(p.x - current.x) < tx) h += "w";
            else if (Math.abs(p.x - current.x - current.w) < tx) h += "e";
            if (h) return { id: current.id, handle: h };
        }
        const region = [...s.layout.regions].reverse().find((r) => p.x >= r.x && p.x <= r.x + r.w && p.y >= r.y && p.y <= r.y + r.h);
        return region ? { id: region.id, handle: "move" } : null;
    }
    canvas.onpointerdown = (e) => {
        if (e.button !== 0) return;
        e.preventDefault(); e.stopPropagation(); canvas.focus();
        const p = point(e), target = hit(p);
        if (!target) return;
        remember(); selected = target.id;
        drag = { ...target, start: p, state: snapshot(), pointer: e.pointerId };
        canvas.setPointerCapture(e.pointerId); refresh();
    };
    canvas.onpointermove = (e) => {
        if (!drag) return;
        e.preventDefault(); const p = point(e);
        const layout = transform(drag.state.layout, drag.id, drag.handle, p.x - drag.start.x, p.y - drag.start.y);
        write({ ...drag.state, layout });
    };
    const endDrag = () => { drag = null; };
    canvas.onpointerup = endDrag; canvas.onpointercancel = endDrag; canvas.onlostpointercapture = endDrag;
    canvas.onkeydown = (e) => {
        if (e.key === "Delete" || e.key === "Backspace") { e.preventDefault(); remove.click(); }
        if (e.key.startsWith("Arrow") && option()) {
            e.preventDefault(); remember(); const s = snapshot(), step = e.shiftKey ? .02 : .005;
            write({ ...s, layout: transform(s.layout, selected, "move", e.key === "ArrowLeft" ? -step : e.key === "ArrowRight" ? step : 0, e.key === "ArrowUp" ? -step : e.key === "ArrowDown" ? step : 0) });
        }
    };
    for (const type of ["pointerdown", "pointermove", "pointerup", "keydown"]) element.addEventListener(type, (e) => e.stopPropagation());

    function draw() {
        frame = null; if (disposed) return;
        const s = read();
        // Canvas graph zoom transforms the widget; size in local CSS pixels.
        const scale = Math.min((board.clientWidth - 4) / s.width, (board.clientHeight - 4) / s.height);
        if (scale <= 0) return;
        canvas.width = Math.max(1, Math.round(s.width * scale)); canvas.height = Math.max(1, Math.round(s.height * scale));
        canvas.style.width = `${canvas.width}px`; canvas.style.height = `${canvas.height}px`;
        const ctx = canvas.getContext("2d"), pixels = ctx.createImageData(canvas.width, canvas.height);
        const colors = COLORS.map((color) => [1, 3, 5].map((p) => parseInt(color.slice(p, p + 2), 16)));
        for (let y = 0; y < canvas.height; y++) for (let x = 0; x < canvas.width; x++) {
            const weights = [0, 0, 0, 0];
            for (const region of s.layout.regions) {
                const i = OWNERS.indexOf(region.owner);
                weights[i] = Math.max(weights[i], weightAt(region, s.layout, (x + .5) / canvas.width * s.width, (y + .5) / canvas.height * s.height, s.width, s.height));
            }
            const total = weights.reduce((a, b) => a + b, 0), alpha = Math.min(total, 1) * .68;
            const offset = (y * canvas.width + x) * 4;
            for (let channel = 0; channel < 3; channel++) pixels.data[offset + channel] = 30 * (1 - alpha) + alpha * weights.reduce((sum, w, i) => sum + w * colors[i][channel], 0) / (total || 1);
            pixels.data[offset + 3] = 255;
        }
        ctx.putImageData(pixels, 0, 0);
        for (const r of s.layout.regions) {
            const x = r.x * canvas.width, y = r.y * canvas.height, w = r.w * canvas.width, h = r.h * canvas.height;
            ctx.strokeStyle = r.id === selected ? "#fff" : COLORS[OWNERS.indexOf(r.owner)];
            ctx.lineWidth = r.id === selected ? 2 : 1; ctx.setLineDash(r.enabled ? [] : [5, 4]);
            ctx.strokeRect(x + 1, y + 1, w - 2, h - 2); ctx.setLineDash([]);
            ctx.fillStyle = "#171719"; ctx.fillRect(x + w / 2 - 13, y + h / 2 - 14, 26, 28);
            ctx.fillStyle = COLORS[OWNERS.indexOf(r.owner)]; ctx.font = "bold 16px system-ui"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
            ctx.fillText(r.owner, x + w / 2, y + h / 2);
            if (r.id === selected) {
                ctx.fillStyle = "#fff";
                for (const [a, b] of [[0,0],[.5,0],[1,0],[0,.5],[1,.5],[0,1],[.5,1],[1,1]]) ctx.fillRect(x + w*a - 3, y + h*b - 3, 6, 6);
            }
        }
    }
    function refresh() {
        if (disposed) return;
        try {
            const s = read(); shadow.querySelector(".error").textContent = "";
            if (!s.layout.regions.some((r) => r.id === selected)) selected = s.layout.regions[0]?.id ?? null;
            presets.value = Object.keys(PRESETS).find((name) => {
                const r = preset(name).regions;
                return r.length === s.layout.regions.length && r.every((item, i) => ["x","y","w","h"].every((key) => Math.abs(item[key] - s.layout.regions[i][key]) < 1e-6));
            }) ?? "";
            ratio.value = [...ratio.options].find((o) => o.value && Math.abs(Number(o.value.split(":")[0]) / Number(o.value.split(":")[1]) - s.width / s.height) < .005)?.value ?? "";
            edge.value = String(Math.max(s.width, s.height));
            shadow.querySelector(".dimensions").textContent = `${s.width} \u00d7 ${s.height}`;
            const row = shadow.querySelector(".regions"); row.replaceChildren();
            s.layout.regions.forEach((r, i) => {
                const button = document.createElement("button"); button.textContent = `${i + 1}: ${r.owner}`;
                button.style.color = COLORS[OWNERS.indexOf(r.owner)]; button.title = `Select region ${i + 1}`;
                button.setAttribute("aria-pressed", String(r.id === selected));
                button.onclick = () => { selected = r.id; refresh(); }; row.appendChild(button);
            });
            const r = s.layout.regions.find((item) => item.id === selected);
            owner.disabled = enabled.disabled = remove.disabled = !r;
            if (r) { owner.value = r.owner; enabled.checked = r.enabled; shadow.querySelector(".swatch").style.background = COLORS[OWNERS.indexOf(r.owner)]; }
            add.disabled = s.layout.regions.length >= 8; undo.disabled = !history.length; redo.disabled = !future.length;
            for (const [input, key] of [[overlap, "overlap"], [feather, "feather"]]) { input.value = s.layout[key]; input.nextElementSibling.textContent = `${Math.round(s.layout[key] * 100)}%`; }
            if (frame === null) frame = requestAnimationFrame(draw);
        } catch (error) { shadow.querySelector(".error").textContent = error.message; }
    }
    const observer = new ResizeObserver(refresh); observer.observe(board);
    refresh();
    return { element, refresh, dispose() { disposed = true; observer.disconnect(); if (frame !== null) cancelAnimationFrame(frame); } };
}
