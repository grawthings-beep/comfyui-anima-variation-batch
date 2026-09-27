// Browser widget/integration harness; does not claim a live ComfyUI or GPU test.
const { chromium } = require("playwright");
const { createServer } = require("node:http");
const fs = require("node:fs/promises");
const path = require("node:path");
const assert = require("node:assert/strict");

(async () => {
    const root = path.resolve(__dirname, ".."), screenshots = process.env.ANIMA_TEST_OUTPUT;
    const server = createServer(async (req, res) => {
        const filename = path.resolve(root, `.${decodeURIComponent(new URL(req.url, "http://localhost").pathname)}`);
        if (!filename.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
        try {
            res.setHeader("Content-Type", filename.endsWith(".js") ? "text/javascript" : "text/html");
            res.end(await fs.readFile(filename));
        } catch { res.writeHead(404).end(); }
    });
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    let browser;
    try {
        browser = await chromium.launch({ headless:true, channel:process.env.ANIMA_TEST_BROWSER || undefined });
        const errors = [];
        const page = await browser.newPage({ viewport:{ width:1280,height:900 } });
        page.on("pageerror", (e) => errors.push(e.message));
        await page.goto(`http://127.0.0.1:${server.address().port}/tests/region_editor_harness.html`);
        await page.waitForFunction(() => window.ready);
        const canvas = page.getByLabel("Region layout canvas");
        const settle = () => page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        const state = () => page.evaluate(() => window.readState());
        await settle();
        const pixels = await canvas.evaluate((c) => {
            const d = c.getContext("2d").getImageData(0,0,c.width,c.height).data;
            return new Set(Array.from({length:d.length/4}, (_,i) => `${d[4*i]},${d[4*i+1]},${d[4*i+2]}`)).size;
        });
        assert.ok(pixels > 30, "Preview must be nonblank and show feathering");
        if (screenshots) {
            await fs.mkdir(screenshots,{recursive:true});
            await page.screenshot({path:path.join(screenshots,"region-editor-default.png")});
        }
        const unscaled = await canvas.evaluate((c) => [c.width, c.height]);
        await page.locator("#editor").evaluate((host) => {
            host.style.transform = "scale(0.5)";
            host.style.transformOrigin = "top left";
            window.testNode._animaRegionEditor.refresh();
        });
        await settle();
        assert.deepEqual(await canvas.evaluate((c) => [c.width, c.height]), unscaled, "Graph zoom must not shrink the local canvas");
        await page.locator("#editor").evaluate((host) => { host.style.transform = ""; });
        await settle();
        const b = await canvas.boundingBox();
        await page.mouse.move(b.x+b.width/2, b.y+b.height*.3);
        await page.mouse.down(); await page.mouse.move(b.x+b.width*.65, b.y+b.height*.3, {steps:5}); await page.mouse.up();
        const resized = await state();
        assert.ok(resized.layout.regions[0].w > .6);
        assert.equal(resized.layout.regions[0].w, resized.layout.regions[1].x);
        await page.getByLabel("Undo",{exact:true}).click();
        assert.equal((await state()).layout.regions[0].w, .5);
        await page.getByLabel("Redo",{exact:true}).click();
        assert.ok((await state()).layout.regions[0].w > .6);
        for (const name of ["3 columns","4 columns","3 rows","4 rows","2 x 2"]) {
            await page.getByLabel("Layout preset").selectOption(name);
            assert.equal((await state()).layout.regions.length, name.startsWith("3") ? 3 : 4);
        }
        const before = (await state()).layout;
        await page.getByLabel("Aspect ratio").selectOption("4:3"); await settle();
        assert.deepEqual((await state()).layout, before);
        assert.equal((await state()).width,1536);
        assert.equal((await state()).height,1152);
        await page.getByLabel("Character",{exact:true}).selectOption("B");
        assert.equal((await state()).layout.regions[0].owner,"B");
        await page.getByLabel("Region enabled").uncheck();
        assert.equal((await state()).layout.regions[0].enabled,false);
        await page.getByLabel("Region enabled").check();
        await page.getByLabel("Add region",{exact:true}).click();
        const added = (await state()).layout.regions.at(-1).id;
        const bb = await canvas.boundingBox();
        await page.mouse.move(bb.x+bb.width*.5,bb.y+bb.height*.5);
        await page.mouse.down(); await page.mouse.move(bb.x+bb.width*.6,bb.y+bb.height*.55,{steps:4}); await page.mouse.up();
        assert.ok((await state()).layout.regions.find((r) => r.id===added).x > .3);
        await page.getByLabel("Delete region",{exact:true}).click();
        assert.equal((await state()).layout.regions.length,4);
        await page.getByLabel("Feather",{exact:true}).fill("0.075");
        await page.getByLabel("Overlap",{exact:true}).fill("0.055");
        const exported = await page.evaluate(() => window.exportState());
        assert.equal(exported.length,3);
        assert.equal(JSON.parse(exported[2]).feather,.075);
        const expected = await state();
        await page.evaluate(() => {
            window.testNode.widgets[1].value = 1512;
            window.testNode.widgets[1].callback();
        });
        await page.getByLabel("Long edge").selectOption("1024");
        assert.equal((await state()).width,1024);
        assert.equal((await state()).height,1008);
        assert.deepEqual((await state()).layout,expected.layout);
        await page.evaluate((values) => window.restoreState(values), exported); await settle();
        assert.deepEqual(await state(), expected);
        if (screenshots) { await fs.mkdir(screenshots,{recursive:true}); await page.screenshot({path:path.join(screenshots,"region-editor-desktop.png")}); }
        await page.setViewportSize({width:390,height:844});
        await page.getByLabel("Aspect ratio").selectOption("3:4");
        for (let i=0;i<4;i++) await page.getByLabel("Add region",{exact:true}).click();
        await settle();
        assert.equal((await state()).layout.regions.length,8);
        assert.ok(await page.getByLabel("Add region",{exact:true}).isDisabled());
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        const overflow = await page.locator("#editor").evaluate((host) => {
            const root = host.firstElementChild.shadowRoot, panel = root.querySelector(".panel").getBoundingClientRect();
            return [...root.querySelectorAll("button,select,input,.board,.error")].some((e) => {
                const r=e.getBoundingClientRect(); return r.right>panel.right+1 || r.bottom>panel.bottom+1;
            });
        });
        assert.equal(overflow,false,"Controls must fit inside the node at mobile width");
        if (screenshots) await page.screenshot({path:path.join(screenshots,"region-editor-mobile.png")});
        assert.deepEqual(errors,[]);
        console.log("PASS: live canvas, shared-edge drag, presets, aspect, assignment, add/delete/move, sliders, undo/redo, save/reload, mobile layout");
    } finally {
        await browser?.close();
        await new Promise((resolve) => server.close(resolve));
    }
})().catch((error) => { console.error(error); process.exitCode=1; });
