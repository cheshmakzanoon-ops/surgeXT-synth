# Aurora skin tools

Aurora is Surge XT's default skin. The instrument is a set of frosted glass tiles floating over a
night sky lit by aurora curtains. Each tile is edge-lit in its section's colour, the displays are
recessed holographic screens with perspective grids, and glowing light pipes in the gutters show
the signal flow: oscillators → mixer → filters → waveshaper → amp → scene output → effects, with
modulation rising into everything from below.

Controls are designed as one family:

- **Slider handles** are jewels set in chrome bezels, in their section's colour, with a mint jewel
  for the modulation handle and a white pearl marking tempo sync.
- **Sliders draw their value** as a glowing fill from their zero point (or centre, for bipolar
  parameters) to the handle, so the state of the whole patch reads at a glance.
- **Rails** are recessed grooves that glow mint when a parameter is modulated.
- **Buttons** are sculpted, top-lit glass. Pink means selected, cyan means in use or hovered, and
  mint means armed for modulation, everywhere.

| Section                          | Colour          |
|----------------------------------|-----------------|
| Oscillators, mixer               | cyan            |
| Bend depth, play mode, scene     | sky blue        |
| FM routing                       | azure           |
| Filter configuration and filters | violet → pink   |
| Scene output                     | magenta         |
| Keytrack, waveshaper             | pink            |
| Filter EG / Amp EG               | rose / coral    |
| Modulators, LFOs, MSEG           | gold            |
| Effects                          | mint            |
| Master volume                    | pearl           |

## How it is made

- `aurora_art.py` draws the background and the jewel handles in HTML/CSS. Chromium gives us what
  Surge's SVG renderer can't: backdrop blur for frosted glass, soft cast shadows, blurred aurora
  light, blend modes and 3D perspective.
- `render_png.js` renders those pages to PNGs at 100, 200 and 400% with Playwright.
- `generate_aurora_skin.py` builds `resources/data/skins/aurora.surge-skin`: it renders the art,
  draws the rails, takes the other widget sprites from the Surge Dark skin with their palette
  remapped and their buttons sculpted, and writes `skin.xml` with a slider class per section.
- `screenshot.sh` runs the standalone on a virtual X display and saves a screenshot of the synth.
  The [UI Screenshot workflow](../../.github/workflows/ui-screenshot.yml) uses it to keep the
  README image current.

```bash
npm install playwright && npx playwright install chromium
```

```bash
python3 scripts/aurora-skin/generate_aurora_skin.py
```

```bash
scripts/aurora-skin/screenshot.sh "build/surge_xt_products/Surge XT" aurora.png 200 "Pads/Communication"
```

## Skin engine features Aurora uses

These are available to every skin and are off unless a skin asks for them:

- `value_fill_color` on a slider (or slider class) draws the glowing value fill in that colour.
- The `modbutton.sheen` colour lays a top-lit highlight over the modulation source buttons.
- Multi-resolution PNGs use the nearest resolution the skin provides, so PNG artwork stays sharp
  at every zoom level.

The skin ships the [Outfit](https://github.com/Outfitio/Outfit-Fonts) typeface under the SIL Open
Font License (see `resources/data/skins/aurora.surge-skin/fonts/OFL-Outfit.txt`).
