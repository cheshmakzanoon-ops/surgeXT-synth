// Renders HTML pages to PNG at several resolutions with Chromium.
//
// Usage: node render_png.js jobs.json
//
// jobs.json is a list of { "html": path, "out": prefix, "width": w, "height": h,
// "scales": [1, 2, 4] }. Each job writes <prefix>_<100 * scale>.png with a
// transparent background wherever the page doesn't paint.

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
    const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
    const browser = await chromium.launch();

    for (const job of jobs) {
        for (const scale of job.scales) {
            const page = await browser.newPage({
                viewport: { width: job.width, height: job.height },
                deviceScaleFactor: scale,
            });
            await page.goto('file://' + path.resolve(job.html));
            await page.evaluate(() => document.fonts.ready);
            await page.screenshot({
                path: `${job.out}_${Math.round(scale * 100)}.png`,
                omitBackground: true,
                clip: { x: 0, y: 0, width: job.width, height: job.height },
            });
            await page.close();
        }
    }

    await browser.close();
})();
