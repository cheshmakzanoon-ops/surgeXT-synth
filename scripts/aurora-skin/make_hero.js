// Composes a UI screenshot into a hero image: the instrument floating in
// perspective over an aurora sky, with its reflection and cast light.
//
// Usage: node make_hero.js <screenshot.png> <hero.png>

const fs = require('fs');
const os = require('os');
const path = require('path');
const { chromium } = require('playwright');

const W = 2400;
const H = 1350;

const page = (shot) => `<!doctype html><html><head><meta charset="utf-8"><style>
html, body { margin: 0; width: ${W}px; height: ${H}px; overflow: hidden; background: #05040f; }
.sky { position: absolute; inset: 0;
  background:
    radial-gradient(60% 50% at 18% 8%, rgba(61,232,255,.30), rgba(61,232,255,0) 70%),
    radial-gradient(55% 45% at 82% 6%, rgba(255,79,184,.32), rgba(255,79,184,0) 70%),
    radial-gradient(70% 55% at 50% 40%, rgba(122,70,255,.30), rgba(122,70,255,0) 75%),
    radial-gradient(60% 40% at 80% 100%, rgba(255,154,92,.20), rgba(255,154,92,0) 70%),
    linear-gradient(180deg, #120b34 0%, #07061a 60%, #04030c 100%); }
.curtain { position: absolute; left: -10%; width: 120%; height: 520px; filter: blur(30px);
  mix-blend-mode: screen; opacity: .8; }
.floor { position: absolute; left: -50%; right: -50%; bottom: -10px; height: 900px;
  background-image: linear-gradient(rgba(169,124,255,.30) 2px, transparent 2px),
                    linear-gradient(90deg, rgba(169,124,255,.30) 2px, transparent 2px);
  background-size: 120px 80px; transform-origin: 50% 100%;
  transform: perspective(700px) rotateX(70deg);
  -webkit-mask-image: linear-gradient(to top, rgba(0,0,0,.9), rgba(0,0,0,0) 75%); }
.scene { position: absolute; inset: 0; perspective: 2600px; perspective-origin: 50% 30%; }
.device { position: absolute; left: 50%; top: 70px; width: 1808px; height: 1138px;
  margin-left: -904px; transform-origin: 50% 60%;
  transform: rotateX(16deg) rotateY(-12deg) rotateZ(1.2deg) scale(.8);
  transform-style: preserve-3d; }
.device img { position: absolute; inset: 0; width: 100%; height: 100%; border-radius: 22px;
  box-shadow: 0 0 0 2px rgba(255,255,255,.18), 0 0 80px rgba(169,124,255,.45),
              0 60px 120px rgba(0,0,0,.85), 0 0 220px rgba(61,232,255,.18); }
.glare { position: absolute; inset: 0; border-radius: 22px;
  background: linear-gradient(115deg, rgba(255,255,255,.16) 0%, rgba(255,255,255,0) 32%); }
.edge { position: absolute; inset: -2px; border-radius: 24px; padding: 2px;
  background: linear-gradient(120deg, #3DE8FF, #A97CFF 35%, #FF4FB8 65%, #FFC94D);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor; filter: drop-shadow(0 0 18px rgba(169,124,255,.9)); }
.reflection { position: absolute; left: 0; top: 100%; width: 100%; height: 100%;
  transform: scaleY(-1); transform-origin: 50% 0; margin-top: 18px; opacity: .22;
  -webkit-mask-image: linear-gradient(to bottom, rgba(0,0,0,0) 72%, rgba(0,0,0,1) 100%);
  filter: blur(3px); }
.reflection img { width: 100%; height: 100%; border-radius: 22px; }
</style></head><body>
<div class="sky"></div>
<svg class="curtain" style="top:-120px" viewBox="0 0 1000 300" preserveAspectRatio="none">
  <defs><linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#3DE8FF" stop-opacity="0"/><stop offset=".8" stop-color="#4DFFB4" stop-opacity=".7"/>
    <stop offset="1" stop-color="#4DFFB4" stop-opacity="0"/></linearGradient>
  <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#A97CFF" stop-opacity="0"/><stop offset=".8" stop-color="#FF4FB8" stop-opacity=".7"/>
    <stop offset="1" stop-color="#FF4FB8" stop-opacity="0"/></linearGradient></defs>
  <path d="M0 160 C150 80 300 220 500 140 S800 60 1000 150 L1000 0 L0 0Z" fill="url(#g1)"/>
  <path d="M0 210 C200 170 380 90 600 180 S880 200 1000 120 L1000 0 L0 0Z" fill="url(#g2)"/>
</svg>
<div class="floor"></div>
<div class="scene"><div class="device">
  <div class="reflection"><img src="${shot}"></div>
  <img src="${shot}"><div class="glare"></div><div class="edge"></div>
</div></div>
</body></html>`;

(async () => {
    const [shot, out] = process.argv.slice(2);
    const html = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'hero-')), 'hero.html');
    fs.writeFileSync(html, page('file://' + path.resolve(shot)));

    const browser = await chromium.launch();
    const p = await browser.newPage({ viewport: { width: W, height: H } });
    await p.goto('file://' + html);
    await p.waitForTimeout(300);
    await p.screenshot({ path: out });
    await browser.close();
})();
